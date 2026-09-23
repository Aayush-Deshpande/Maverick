"""
Per-cylinder combustion diagnostics from crank angular velocity — F02/F03/F04/F05/F06.

This is the payoff of the crank-angle chain, and the answer to the ambiguity the
isolability analysis found: on the as-built 20 Hz sensor set, misfire and
injector needle stick are the same observation. Here they are not, because here
we measure the work each cylinder does on its own power stroke.

What this produces that a classifier cannot:

    "Cylinder 3 misfiring at 4.2% of cycles, onset 11 minutes ago,
     trending +0.3%/min."

That is a *measurement*, attributed by construction to the cylinder whose firing
interval showed the deficit. No model inference is involved in the attribution,
so there is no confidence score to argue about and no training data to be
accused of overfitting.

Contents
--------
F02  Per-cylinder misfire / torque-deficit detection from omega(theta)
F03  Combustion instability as cycle-to-cycle COV of per-cylinder work
F04  Tach-synchronous angular resampling (order tracking)
F05  Order-domain feature extraction
F06  Envelope analysis for bearing defect tones

Why order tracking matters here specifically: a UAV changes power constantly, so
a fixed-frequency spectrum smears every line across a sortie. Resampling onto a
uniform crank-angle grid makes every feature speed-invariant, which is the
difference between a spectrum that works in a lab and one that works in flight.
"""

from __future__ import annotations

import math
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Sequence, Tuple

__all__ = [
    "CylinderContribution",
    "MisfireReport",
    "CrankDiagnostics",
    "angular_resample",
    "order_spectrum",
    "order_features",
    "envelope_spectrum",
]


# ---------------------------------------------------------------------------
# F02 / F03 — per-cylinder work from omega(theta)
# ---------------------------------------------------------------------------


@dataclass
class CylinderContribution:
    """Work attributed to one cylinder over one firing interval."""

    cylinder: int
    cycle_index: int
    kinetic_delta_j: float  # change in crank KE across its firing interval
    normalised: float = 1.0  # contribution ratio vs the median healthy cylinder

    @property
    def deficit(self) -> float:
        """Shortfall against a healthy cylinder. Legitimately exceeds 1.0.

        A cylinder that does not fire is not merely contributing nothing: it
        compresses charge and gets no combustion work back, so it *absorbs* over
        its own interval and its kinetic-energy delta goes negative. A shortfall
        of 3.9 means the cylinder is a net drag. That is the physically correct
        reading, which is why it is not clamped into a percentage.
        """
        return max(0.0, 1.0 - self.normalised)


@dataclass
class MisfireReport:
    cylinder: Optional[int]
    misfire_rate: float  # fraction of cycles
    mean_deficit: float
    onset_cycle: Optional[int]
    trend_per_cycle: float
    per_cylinder_rate: Dict[int, float] = field(default_factory=dict)
    per_cylinder_deficit: Dict[int, float] = field(default_factory=dict)
    cov_per_cylinder: Dict[int, float] = field(default_factory=dict)
    verdict: str = "NOMINAL"
    contribution_ratio: Dict[int, float] = field(default_factory=dict)
    severity_index: float = 0.0

    def sentence(self) -> str:
        if self.cylinder is None:
            return "All cylinders contributing within tolerance."
        ratio = self.contribution_ratio.get(self.cylinder, 1.0)
        state = ("contributing no useful work (net absorbing)" if ratio < 0
                 else f"contributing {ratio * 100:.0f}% of a healthy cylinder")
        return (f"Cylinder {self.cylinder}: {self.verdict.lower().replace('_', ' ')} "
                f"on {self.misfire_rate * 100:.1f}% of cycles, {state}, "
                f"severity index {self.severity_index:.1f}, "
                f"trending {self.trend_per_cycle * 100:+.2f}%/cycle.")

    def as_dict(self) -> dict:
        return {
            "MISFIRE_CYLINDER": self.cylinder,
            "MISFIRE_RATE": round(self.misfire_rate, 4),
            "MISFIRE_MEAN_DEFICIT": round(self.mean_deficit, 4),
            "MISFIRE_ONSET_CYCLE": self.onset_cycle,
            "MISFIRE_TREND_PER_CYCLE": round(self.trend_per_cycle, 6),
            "PER_CYLINDER_RATE": {k: round(v, 4) for k, v in self.per_cylinder_rate.items()},
            "PER_CYLINDER_DEFICIT": {k: round(v, 4) for k, v in self.per_cylinder_deficit.items()},
            "PER_CYLINDER_COV": {k: round(v, 5) for k, v in self.cov_per_cylinder.items()},
            "COMBUSTION_VERDICT": self.verdict,
            "CONTRIBUTION_RATIO": {k: round(v, 4) for k, v in self.contribution_ratio.items()},
            "COMBUSTION_SEVERITY_INDEX": round(self.severity_index, 3),
        }


class CrankDiagnostics:
    """Segments omega(theta) by firing interval and attributes work per cylinder.

    The method is deterministic and standard: each cylinder owns the crank
    interval starting at its firing TDC. The change in crank kinetic energy
    across that interval is the net work that cylinder delivered, minus the load
    it carried. A cylinder that does not fire leaves a deficit in *its own*
    interval, which is what makes the attribution unambiguous.
    """

    def __init__(self, n_cylinders: int = 4,
                 firing_order: Sequence[int] = (1, 4, 2, 3),
                 inertia_kgm2: float = 0.085,
                 misfire_threshold: float = 0.30,
                 weak_threshold: float = 0.85,
                 history_cycles: int = 200) -> None:
        self.n_cylinders = n_cylinders
        self.firing_order = list(firing_order)
        self.inertia = inertia_kgm2
        self.misfire_threshold = misfire_threshold
        self.weak_threshold = weak_threshold
        self.firing_interval_deg = 720.0 / n_cylinders
        self._history: Dict[int, Deque[float]] = {
            c: deque(maxlen=history_cycles) for c in range(1, n_cylinders + 1)
        }
        self._misfire_flags: Dict[int, Deque[int]] = {
            c: deque(maxlen=history_cycles) for c in range(1, n_cylinders + 1)
        }
        self._cycle_count = 0
        self._nonuniformity: Deque[float] = deque(maxlen=history_cycles)
        self._onset: Dict[int, Optional[int]] = {c: None for c in range(1, n_cylinders + 1)}

    def cylinder_for_interval(self, interval_index: int) -> int:
        return self.firing_order[interval_index % self.n_cylinders]

    # -- F02 ---------------------------------------------------------------

    def analyse_cycle(self, theta_deg: Sequence[float], omega_rad_s: Sequence[float]
                      ) -> List[CylinderContribution]:
        """Split one 720-degree cycle into firing intervals and attribute work."""
        if len(theta_deg) != len(omega_rad_s):
            raise ValueError("theta and omega must be the same length")
        contributions: List[CylinderContribution] = []
        base = theta_deg[0]

        for k in range(self.n_cylinders):
            lo = base + k * self.firing_interval_deg
            hi = lo + self.firing_interval_deg
            idx = [i for i, t in enumerate(theta_deg) if lo <= t < hi]
            if len(idx) < 2:
                continue
            w_start = omega_rad_s[idx[0]]
            w_end = omega_rad_s[idx[-1]]
            # Change in crank kinetic energy over this cylinder's interval.
            ke = 0.5 * self.inertia * (w_end ** 2 - w_start ** 2)
            contributions.append(CylinderContribution(
                cylinder=self.cylinder_for_interval(k),
                cycle_index=self._cycle_count,
                kinetic_delta_j=ke,
            ))

        if contributions:
            # Normalise against the cycle's own mean so the result is
            # independent of absolute power setting. This is what makes the
            # detector work unchanged from idle to full throttle.
            values = [c.kinetic_delta_j for c in contributions]
            # Reference against the MEDIAN contribution, not the spread. Using
            # the spread normalises the severity away: one dead cylinder out of
            # four then always reads a 0.75 deficit whether it is misfiring
            # completely or merely weak, because the spread scales with the
            # fault. The median is the robust estimate of what a healthy
            # cylinder is doing on this cycle, so the ratio to it is a true
            # fractional shortfall and a partial fault reads as partial.
            ordered = sorted(values)
            mid = len(ordered) // 2
            median = (ordered[mid] if len(ordered) % 2
                      else 0.5 * (ordered[mid - 1] + ordered[mid]))
            ref = median if abs(median) > 1e-9 else (
                sum(values) / len(values) if abs(sum(values)) > 1e-9 else 1e-9)
            for c in contributions:
                c.normalised = c.kinetic_delta_j / ref

            # Cycle torque non-uniformity. The contribution ratio saturates
            # quickly (a 20% loss and a total misfire both read about -2.5), but
            # the absolute spread across the cycle does not, so it is kept as
            # the graded severity measure.
            self._nonuniformity.append((max(values) - min(values)) / max(abs(ref), 1e-9))

            for c in contributions:
                self._history[c.cylinder].append(c.normalised)
                misfired = int(c.normalised < self.misfire_threshold)
                self._misfire_flags[c.cylinder].append(misfired)
                if misfired and self._onset[c.cylinder] is None:
                    self._onset[c.cylinder] = self._cycle_count
                elif not misfired and len(self._misfire_flags[c.cylinder]) > 20:
                    recent = list(self._misfire_flags[c.cylinder])[-20:]
                    if sum(recent) == 0:
                        self._onset[c.cylinder] = None
            self._cycle_count += 1
        return contributions

    # -- F03 ---------------------------------------------------------------

    def cov_per_cylinder(self) -> Dict[int, float]:
        """Cycle-to-cycle coefficient of variation of each cylinder's work.

        Rising COV is the standard measure of combustion instability and shows
        up *before* any cycle actually misfires — a cylinder becoming erratic is
        detectable while its mean contribution still looks normal.
        """
        out: Dict[int, float] = {}
        for cyl, hist in self._history.items():
            vals = list(hist)
            if len(vals) < 10:
                out[cyl] = 0.0
                continue
            mean = sum(vals) / len(vals)
            var = sum((v - mean) ** 2 for v in vals) / len(vals)
            out[cyl] = (var ** 0.5 / abs(mean)) if abs(mean) > 1e-9 else 0.0
        return out

    # -- reporting ---------------------------------------------------------

    def report(self, instability_cov: float = 0.08) -> MisfireReport:
        rates: Dict[int, float] = {}
        deficits: Dict[int, float] = {}
        for cyl in range(1, self.n_cylinders + 1):
            flags = list(self._misfire_flags[cyl])
            rates[cyl] = (sum(flags) / len(flags)) if flags else 0.0
            hist = list(self._history[cyl])
            deficits[cyl] = (sum(max(0.0, 1.0 - v) for v in hist) / len(hist)) if hist else 0.0

        cov = self.cov_per_cylinder()
        worst = max(rates, key=lambda c: (rates[c], deficits[c])) if rates else None

        ratios = {c: (sum(self._history[c]) / len(self._history[c]))
                  if self._history[c] else 1.0
                  for c in range(1, self.n_cylinders + 1)}
        weakest = min(ratios, key=lambda c: ratios[c]) if ratios else None

        verdict = "NOMINAL"
        culprit: Optional[int] = None
        if weakest is not None and ratios[weakest] < self.misfire_threshold:
            verdict = "MISFIRING"
            culprit = weakest
        elif weakest is not None and ratios[weakest] < self.weak_threshold:
            verdict = "WEAK_CYLINDER"
            culprit = weakest
        else:
            unstable = [c for c, v in cov.items() if v > instability_cov]
            if unstable:
                verdict = "COMBUSTION_INSTABILITY"
                culprit = max(unstable, key=lambda c: cov[c])

        trend = 0.0
        if culprit is not None:
            flags = list(self._misfire_flags[culprit])
            if len(flags) >= 40:
                half = len(flags) // 2
                first = sum(flags[:half]) / half
                second = sum(flags[half:]) / (len(flags) - half)
                trend = (second - first) / max(half, 1)

        return MisfireReport(
            cylinder=culprit,
            misfire_rate=rates.get(culprit, 0.0) if culprit else 0.0,
            mean_deficit=deficits.get(culprit, 0.0) if culprit else 0.0,
            onset_cycle=self._onset.get(culprit) if culprit else None,
            trend_per_cycle=trend,
            per_cylinder_rate=rates,
            per_cylinder_deficit=deficits,
            cov_per_cylinder=cov,
            verdict=verdict,
            contribution_ratio=ratios,
            severity_index=(sum(self._nonuniformity) / len(self._nonuniformity)
                            if self._nonuniformity else 0.0),
        )

    def reset(self) -> None:
        self._nonuniformity.clear()
        for c in self._history:
            self._history[c].clear()
            self._misfire_flags[c].clear()
            self._onset[c] = None
        self._cycle_count = 0


# ---------------------------------------------------------------------------
# F04 / F05 / F06 — order tracking, order features, envelope
# ---------------------------------------------------------------------------


def angular_resample(t_sec: Sequence[float], signal: Sequence[float],
                     tach_times: Sequence[float],
                     samples_per_rev: int = 256) -> Tuple[List[float], List[float]]:
    """Tach-synchronous resampling: a(t) -> a(theta). F04.

    `tach_times` are the times of a once-per-revolution tach pulse. Between
    consecutive pulses the crank is assumed to turn at a constant rate, and the
    signal is linearly interpolated onto a uniform angle grid. The result is
    speed-invariant: an order stays in the same bin whether the engine is at
    4 000 or 5 800 rpm, which a fixed-frequency FFT cannot manage on a UAV that
    changes power constantly.
    """
    if len(tach_times) < 2:
        return ([], [])
    theta_out: List[float] = []
    sig_out: List[float] = []
    n = len(t_sec)
    j = 0
    for rev in range(len(tach_times) - 1):
        t0, t1 = tach_times[rev], tach_times[rev + 1]
        if t1 <= t0:
            continue
        for k in range(samples_per_rev):
            frac = k / samples_per_rev
            t_target = t0 + frac * (t1 - t0)
            while j + 1 < n and t_sec[j + 1] < t_target:
                j += 1
            if j + 1 >= n:
                break
            span = t_sec[j + 1] - t_sec[j]
            w = 0.0 if span <= 0 else (t_target - t_sec[j]) / span
            sig_out.append(signal[j] * (1 - w) + signal[j + 1] * w)
            theta_out.append((rev + frac) * 360.0)
    return theta_out, sig_out


def order_spectrum(signal_theta: Sequence[float], samples_per_rev: int = 256
                   ) -> Tuple[List[float], List[float]]:
    """FFT of an angle-resampled signal, with the x-axis in shaft orders."""
    import numpy as np

    x = np.asarray(signal_theta, dtype="float64")
    if x.size < 8:
        return ([], [])
    x = x - x.mean()
    n = x.size
    spec = np.abs(np.fft.rfft(x * np.hanning(n))) * 2.0 / n
    n_revs = n / samples_per_rev
    orders = np.arange(spec.size) / max(n_revs, 1e-9)
    return (orders.tolist(), spec.tolist())


def order_features(orders: Sequence[float], magnitudes: Sequence[float],
                   targets: Sequence[float] = (0.5, 1.0, 2.0, 4.0),
                   tolerance: float = 0.06) -> Dict[str, float]:
    """Band energies at diagnostic orders plus shape statistics. F05.

    Order 0.5 is the misfire line on a four-stroke (one event per two
    revolutions); order 2.0 is the firing order of a four-cylinder; sidebands
    around gear mesh are the classic gearbox-wear indicator.
    """
    import numpy as np

    o = np.asarray(orders, dtype="float64")
    m = np.asarray(magnitudes, dtype="float64")
    feats: Dict[str, float] = {}
    if o.size == 0:
        return feats
    total = float(np.sum(m)) or 1e-12
    for target in targets:
        mask = np.abs(o - target) <= tolerance
        band = float(np.sum(m[mask])) if mask.any() else 0.0
        feats[f"ORDER_{target:g}_MAG"] = band
        feats[f"ORDER_{target:g}_FRAC"] = band / total
    peak = float(np.max(m)) if m.size else 0.0
    rms = float(np.sqrt(np.mean(m ** 2))) if m.size else 0.0
    feats["ORDER_PEAK"] = peak
    feats["ORDER_RMS"] = rms
    feats["ORDER_CREST_FACTOR"] = peak / rms if rms > 0 else 0.0
    mean = float(np.mean(m)) if m.size else 0.0
    std = float(np.std(m)) if m.size else 0.0
    feats["ORDER_KURTOSIS"] = (float(np.mean((m - mean) ** 4)) / (std ** 4)
                               if std > 0 else 0.0)
    feats["ORDER_DOMINANT"] = float(o[int(np.argmax(m))]) if m.size else 0.0
    return feats


def envelope_spectrum(signal: Sequence[float], sample_rate_hz: float,
                      band_low_hz: float = 800.0, band_high_hz: float = 2500.0
                      ) -> Tuple[List[float], List[float]]:
    """Band-pass, Hilbert envelope, then FFT of the envelope. F06.

    Bearing defects excite a structural resonance and amplitude-modulate it at
    the defect repetition rate. The carrier is high frequency and the
    information is in the modulation, so the raw spectrum shows a resonance
    while the *envelope* spectrum shows the defect tone. This routinely detects
    bearing faults while broadband RMS still reads normal, which is why it is
    worth more than any classifier choice.
    """
    import numpy as np

    x = np.asarray(signal, dtype="float64")
    if x.size < 16:
        return ([], [])
    x = x - x.mean()

    # Band-pass by zeroing outside the band in the frequency domain — adequate
    # here and avoids a scipy dependency in the core path.
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(x.size, d=1.0 / sample_rate_hz)
    spec[(freqs < band_low_hz) | (freqs > band_high_hz)] = 0.0
    band = np.fft.irfft(spec, n=x.size)

    # Analytic signal via the FFT definition of the Hilbert transform.
    n = band.size
    fft = np.fft.fft(band)
    h = np.zeros(n)
    h[0] = 1.0
    if n % 2 == 0:
        h[n // 2] = 1.0
        h[1:n // 2] = 2.0
    else:
        h[1:(n + 1) // 2] = 2.0
    envelope = np.abs(np.fft.ifft(fft * h))
    envelope = envelope - envelope.mean()

    env_spec = np.abs(np.fft.rfft(envelope * np.hanning(n))) * 2.0 / n
    env_freqs = np.fft.rfftfreq(n, d=1.0 / sample_rate_hz)
    return (env_freqs.tolist(), env_spec.tolist())

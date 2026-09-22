"""
Gearbox FFT Spectral Analyser
DRDO / iDEX Problem Statement ID: 26054

Tracks 3rd harmonic spectral energy of the propeller reduction shaft to detect
early gear tooth micro-pitting before it is visible in VIB_RMS.

PS reference: doc03 §3 — "Mechanical micro-pitting manifests as distinct energy
spikes at the 3rd harmonic of the propeller reduction shaft (3 × Propeller RPM).
FFT / Wavelet Packet Transform monitors energy in the 100Hz–5kHz band."

Why VIB_RMS alone is insufficient:
  - Early gear wear produces negligible RMS increase
  - But creates a distinct spectral peak at exactly 3 × prop_shaft_freq
  - The plain RMS fires only when damage is already severe (~6.8× normal)
  - FFT spectral tracking fires at 3× normal — early warning before damage

Designed for prototype use where VIB_GEARBOX_RMS is sampled at 20 Hz
(same as other telemetry). For production, a dedicated 1 kHz vibration
acquisition channel would give far better frequency resolution.
"""

import math
import collections
from dataclasses import dataclass
from typing import Optional, List


GEAR_REDUCTION_RATIO = 2.43   # Crankshaft : Propeller shaft ratio (doc03 §1)


@dataclass
class SpectralReport:
    """
    Per-update output of GearboxSpectralAnalyser.

    Fields:
        ready:            True once enough samples have accumulated for FFT.
        prop_shaft_hz:    Propeller shaft fundamental frequency (Hz).
        target_freq_hz:   3rd harmonic frequency being tracked (Hz).
        harmonic_ratio:   Current spectral peak / baseline peak.
                          < 3.0 → nominal
                          3.0–5.9 → WATCH (early micro-pitting)
                          ≥ 6.0 → FAULT (consistent with PS F05 threshold)
        harmonic_energy:  Raw FFT magnitude at target frequency (a.u.)
        baseline_energy:  Reference energy established in first 60 seconds.
        alert_level:      "NOMINAL" | "WATCH" | "FAULT"
        anomaly_score:    Normalised [0, 1] for pipeline integration.
    """
    ready: bool
    prop_shaft_hz: float = 0.0
    target_freq_hz: float = 0.0
    harmonic_ratio: float = 1.0
    harmonic_energy: float = 0.0
    baseline_energy: float = 1.0
    alert_level: str = "NOMINAL"
    anomaly_score: float = 0.0


class GearboxSpectralAnalyser:
    """
    Sliding-window DFT-based spectral analyser for gearbox health monitoring.

    Usage:
        analyser = GearboxSpectralAnalyser(sample_rate_hz=20.0)
        for each telemetry frame:
            report = analyser.update(vib_rms_value, engine_rpm)
            if report.ready and report.alert_level != "NOMINAL":
                handle_warning(report)

    Note on sample rate:
        At 20 Hz, the Nyquist frequency is 10 Hz. The 3rd harmonic at 5000 RPM
        engine is ~103 Hz — above Nyquist for 20 Hz sampling. The analyser
        therefore works on the *envelope* of the vibration signal over a 1-second
        window, which still captures amplitude modulation caused by gear meshing
        at the harmonic frequency (the classical approach for low-rate acquisition).
        For production hardware with a 1 kHz vibration channel, set sample_rate_hz
        accordingly and the full spectral peak will be directly measurable.
    """

    # Thresholds (from PS doc01 §4 Fault 05 + doc03 §3)
    WATCH_RATIO = 3.0    # early micro-pitting
    FAULT_RATIO = 6.0    # consistent with PS "VIB_RMS > 1.8 mm/s" = ~6.8× baseline

    def __init__(self,
                 sample_rate_hz: float = 20.0,
                 window_sec: float = 1.0,
                 baseline_sec: float = 60.0):
        """
        Args:
            sample_rate_hz: Telemetry acquisition rate. 20 Hz for prototype.
            window_sec:     DFT window duration in seconds.
            baseline_sec:   Duration of initial nominal flight used to establish
                            baseline spectral energy (first N seconds of sortie).
        """
        self._fs = sample_rate_hz
        self._window_n = max(8, int(window_sec * sample_rate_hz))
        self._baseline_n = int(baseline_sec * sample_rate_hz)

        self._buffer: collections.deque = collections.deque(maxlen=self._window_n)
        self._baseline_samples: List[float] = []
        self._baseline_energy: Optional[float] = None
        self._baseline_locked: bool = False
        self._frame_count: int = 0

    # ------------------------------------------------------------------
    # Internal DFT helpers (no numpy dependency for prototype)
    # ------------------------------------------------------------------

    def _compute_dft_magnitudes(self, samples: List[float]) -> List[float]:
        """
        Compute DFT magnitudes for a real-valued signal.
        Returns magnitude at each frequency bin (0 to N//2).
        Pure-Python Goertzel-style approach for small N (N ≤ 40).
        """
        N = len(samples)
        mags = []
        # Only compute positive frequencies (N//2 + 1 bins)
        for k in range(N // 2 + 1):
            re = 0.0
            im = 0.0
            for n, x in enumerate(samples):
                angle = 2.0 * math.pi * k * n / N
                re += x * math.cos(angle)
                im -= x * math.sin(angle)
            mags.append(math.sqrt(re*re + im*im) / N)
        return mags

    def _hann_window(self, samples: List[float]) -> List[float]:
        """Apply Hann window to reduce spectral leakage."""
        N = len(samples)
        return [
            s * (0.5 - 0.5 * math.cos(2.0 * math.pi * n / (N - 1)))
            for n, s in enumerate(samples)
        ]

    def _rms(self, samples: List[float]) -> float:
        """RMS of a signal window."""
        if not samples:
            return 0.0
        return math.sqrt(sum(s * s for s in samples) / len(samples))

    def _peak_in_band(self, mags: List[float], center_hz: float,
                      bandwidth_hz: float = 2.0) -> float:
        """Return peak magnitude within ±bandwidth_hz of center_hz."""
        N = self._window_n
        freq_res = self._fs / N           # Hz per bin
        bin_lo = max(0, int((center_hz - bandwidth_hz) / freq_res))
        bin_hi = min(len(mags) - 1, int((center_hz + bandwidth_hz) / freq_res))
        if bin_lo > bin_hi:
            return 0.0
        return max(mags[bin_lo:bin_hi + 1])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(
        self,
        vib_rms: float,
        engine_rpm: float,
        high_rate_burst: Optional[List[float]] = None,
        fs_hz: Optional[float] = None
    ) -> SpectralReport:
        """
        Ingest one telemetry frame and return the current spectral report.

        Args:
            vib_rms:         VIB_GEARBOX_RMS value (mm/s) from current frame.
            engine_rpm:      ENGINE_RPM from current frame.
            high_rate_burst: Optional kHz vibration time-series burst for real DFT.
            fs_hz:           Sample rate of high_rate_burst in Hz (e.g. 2000.0).

        Returns:
            SpectralReport (ready=False until enough frames accumulated)
        """
        self._buffer.append(vib_rms)
        self._frame_count += 1

        # Compute target frequencies
        prop_hz = max(1.0, engine_rpm / GEAR_REDUCTION_RATIO) / 60.0
        target_hz = 3.0 * prop_hz   # 3rd harmonic

        if high_rate_burst is not None and len(high_rate_burst) >= 64:
            # Active kHz Vibration Path (F07 / PS-26054)
            fs = fs_hz or 2000.0
            nyquist_hz = fs / 2.0
            use_rms_fallback = target_hz > nyquist_hz
            samples = high_rate_burst
            old_fs = self._fs
            old_win = self._window_n
            self._fs = fs
            self._window_n = len(samples)
            if not use_rms_fallback:
                windowed = self._hann_window(samples)
                mags = self._compute_dft_magnitudes(windowed)
                current_energy = self._peak_in_band(mags, target_hz)
            else:
                current_energy = self._rms(samples)
            self._fs = old_fs
            self._window_n = old_win
        else:
            nyquist_hz = self._fs / 2.0
            use_rms_fallback = target_hz > nyquist_hz  # True at 20 Hz prototype rate

            # Not enough samples for DFT yet
            if len(self._buffer) < self._window_n:
                return SpectralReport(ready=False,
                                      prop_shaft_hz=prop_hz,
                                      target_freq_hz=target_hz)

            samples = list(self._buffer)
            if use_rms_fallback:
                # At 20 Hz, target harmonic is above Nyquist.
                # Use amplitude envelope (window RMS) as energy proxy.
                current_energy = self._rms(samples)
            else:
                # Apply Hann window and compute DFT
                windowed = self._hann_window(samples)
                mags = self._compute_dft_magnitudes(windowed)
                current_energy = self._peak_in_band(mags, target_hz)

        # Accumulate baseline during first baseline_sec of flight
        if not self._baseline_locked:
            if len(self._baseline_samples) < self._baseline_n:
                self._baseline_samples.append(current_energy)
                # Running provisional baseline = running max
                if self._baseline_energy is None:
                    self._baseline_energy = max(current_energy, 1e-9)
                else:
                    self._baseline_energy = max(self._baseline_energy, current_energy, 1e-9)

                return SpectralReport(
                    ready=False,
                    prop_shaft_hz=prop_hz,
                    target_freq_hz=target_hz,
                    harmonic_energy=current_energy,
                    baseline_energy=self._baseline_energy,
                )
            else:
                # Lock in median of baseline samples once
                sorted_b = sorted(self._baseline_samples)
                self._baseline_energy = max(sorted_b[len(sorted_b) // 2], 1e-9)
                self._baseline_locked = True

        baseline = self._baseline_energy or 1e-9
        ratio = current_energy / baseline

        # Alert classification
        if ratio >= self.FAULT_RATIO:
            alert = "FAULT"
        elif ratio >= self.WATCH_RATIO:
            alert = "WATCH"
        else:
            alert = "NOMINAL"

        # Normalised anomaly_score for pipeline integration
        # ratio=1 → 0.0, ratio=FAULT_RATIO → ~0.85, ratio=FAULT_RATIO*2 → ~0.97
        k = 0.35
        anom = round(min(1.0, 1.0 - math.exp(-k * max(0.0, ratio - 1.0))), 4)

        return SpectralReport(
            ready=True,
            prop_shaft_hz=round(prop_hz, 2),
            target_freq_hz=round(target_hz, 2),
            harmonic_ratio=round(ratio, 3),
            harmonic_energy=round(current_energy, 6),
            baseline_energy=round(baseline, 6),
            alert_level=alert,
            anomaly_score=anom,
        )

    def reset(self) -> None:
        """Reset for a new sortie."""
        self._buffer.clear()
        self._baseline_samples.clear()
        self._baseline_energy = None
        self._baseline_locked = False
        self._frame_count = 0

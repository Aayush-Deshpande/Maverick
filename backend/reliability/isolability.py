"""
Fault detectability and isolability analysis — F35.

A classifier reporting 97% accuracy on eight classes says nothing about whether
those eight are *physically distinguishable* with the sensors fitted. If two
failure modes produce the same signature on the same channels, no algorithm can
separate them — not a better classifier, not more data. That is a property of
the instrumentation, and it is determined before any model is trained.

This is classical fault diagnosis practice (structural analysis / the fault
signature matrix): build the incidence of failure modes against observable
signatures, then

  * a mode with an empty row is **undetectable** — no sensor sees it;
  * two modes with identical rows are **not isolable** from each other — they
    form an indistinguishability class and the honest output for either is the
    class, not a single label.

Reporting those classes is the rigorous alternative to letting a classifier pick
one of two identical patterns and present it with 97% confidence. It also turns
"we need a crank-angle channel" from a preference into a proof: remove the
channel and watch named fault pairs collapse into the same class.

The analysis doubles as sensor-set justification and as minimum-sensor-set
search, which is what makes it useful for a deployment roadmap rather than only
for a paper.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Set, Tuple

__all__ = ["SignatureMatrix", "IsolabilityReport", "from_fmeca"]


@dataclass
class IsolabilityReport:
    detectable: List[str]
    undetectable: List[str]
    isolable: List[str]
    indistinguishable_classes: List[List[str]]
    channels_used: List[str]
    n_modes: int

    @property
    def detectability(self) -> float:
        return len(self.detectable) / self.n_modes if self.n_modes else 0.0

    @property
    def isolability(self) -> float:
        return len(self.isolable) / self.n_modes if self.n_modes else 0.0

    def as_dict(self) -> dict:
        return {
            "n_modes": self.n_modes,
            "n_channels": len(self.channels_used),
            "detectable": len(self.detectable),
            "undetectable": self.undetectable,
            "fully_isolable": len(self.isolable),
            "detectability_ratio": round(self.detectability, 3),
            "isolability_ratio": round(self.isolability, 3),
            "indistinguishable_classes": self.indistinguishable_classes,
        }

    def summary_line(self) -> str:
        return (
            f"{len(self.detectable)}/{self.n_modes} detectable "
            f"({self.detectability:.0%}), {len(self.isolable)}/{self.n_modes} "
            f"uniquely isolable ({self.isolability:.0%}), "
            f"{len(self.indistinguishable_classes)} ambiguity group(s), "
            f"{len(self.channels_used)} channels."
        )


class SignatureMatrix:
    """Failure mode x observable signature incidence, and what follows from it."""

    def __init__(self) -> None:
        # mode -> set of signatures it produces
        self._modes: Dict[str, Set[str]] = {}
        # signature -> channel required to observe it
        self._signature_channel: Dict[str, str] = {}

    def add_mode(self, mode_id: str, signatures: Dict[str, str]) -> None:
        """Register a mode. `signatures` maps signature name -> required channel."""
        self._modes.setdefault(mode_id, set()).update(signatures.keys())
        for sig, ch in signatures.items():
            self._signature_channel[sig] = ch

    @property
    def modes(self) -> List[str]:
        return sorted(self._modes)

    @property
    def signatures(self) -> List[str]:
        return sorted(self._signature_channel)

    @property
    def channels(self) -> List[str]:
        return sorted(set(self._signature_channel.values()))

    def observable_signature(self, mode: str, available_channels: Set[str]) -> FrozenSet[str]:
        """The part of a mode's signature we can actually see with these channels."""
        return frozenset(
            sig for sig in self._modes.get(mode, set())
            if self._signature_channel.get(sig) in available_channels
        )

    # -- analysis -----------------------------------------------------------

    def analyse(self, available_channels: Optional[Iterable[str]] = None) -> IsolabilityReport:
        chans = set(available_channels) if available_channels is not None else set(self.channels)
        observed: Dict[str, FrozenSet[str]] = {
            m: self.observable_signature(m, chans) for m in self.modes
        }

        undetectable = sorted(m for m, s in observed.items() if not s)
        detectable = sorted(m for m, s in observed.items() if s)

        # Group modes by identical observable signature.
        groups: Dict[FrozenSet[str], List[str]] = {}
        for m in detectable:
            groups.setdefault(observed[m], []).append(m)

        isolable = sorted(ms[0] for ms in groups.values() if len(ms) == 1)
        ambiguous = sorted(
            (sorted(ms) for ms in groups.values() if len(ms) > 1),
            key=lambda g: g[0],
        )

        return IsolabilityReport(
            detectable=detectable,
            undetectable=undetectable,
            isolable=isolable,
            indistinguishable_classes=ambiguous,
            channels_used=sorted(chans),
            n_modes=len(self.modes),
        )

    def channel_value(self, available_channels: Optional[Iterable[str]] = None
                      ) -> List[dict]:
        """Marginal contribution of each channel — what removing it would cost.

        This is the argument for an instrumentation decision: a channel whose
        removal collapses several modes into one ambiguity class is carrying
        diagnostic load that no algorithm can replace.
        """
        chans = set(available_channels) if available_channels is not None else set(self.channels)
        base = self.analyse(chans)
        rows: List[dict] = []
        for ch in sorted(chans):
            without = self.analyse(chans - {ch})
            rows.append({
                "channel": ch,
                "isolable_with": len(base.isolable),
                "isolable_without": len(without.isolable),
                "isolability_lost": len(base.isolable) - len(without.isolable),
                "newly_undetectable": sorted(
                    set(without.undetectable) - set(base.undetectable)),
                "new_ambiguity_groups": max(
                    0, len(without.indistinguishable_classes)
                    - len(base.indistinguishable_classes)),
            })
        return sorted(rows, key=lambda r: -r["isolability_lost"])

    def minimum_channel_set(self, target_isolability: float = 1.0,
                            max_size: Optional[int] = None) -> Optional[List[str]]:
        """Smallest channel set reaching the target isolability, by exhaustive search.

        Exponential in the number of channels, so it is intended for the ~10-20
        channel sets this problem actually has, not as a general solver. Returns
        None when the target is unreachable with every channel fitted, which is
        itself the finding: the instrumentation cannot do what is being asked.
        """
        all_ch = self.channels
        if self.analyse(all_ch).isolability < target_isolability:
            return None
        limit = max_size if max_size is not None else len(all_ch)
        for size in range(1, limit + 1):
            for combo in itertools.combinations(all_ch, size):
                if self.analyse(combo).isolability >= target_isolability:
                    return list(combo)
        return None

    def to_markdown(self, available_channels: Optional[Iterable[str]] = None) -> str:
        chans = set(available_channels) if available_channels is not None else set(self.channels)
        rep = self.analyse(chans)
        lines = [
            "# Fault isolability analysis",
            "",
            rep.summary_line(),
            "",
            "## Signature matrix",
            "",
            "| Mode | Observable signatures | Isolable |",
            "|---|---|---|",
        ]
        for m in self.modes:
            sigs = sorted(self.observable_signature(m, chans))
            status = ("unique" if m in rep.isolable
                      else ("UNDETECTABLE" if not sigs else "ambiguous"))
            lines.append(f"| {m} | {', '.join(sigs) or '—'} | {status} |")
        if rep.indistinguishable_classes:
            lines += ["", "## Ambiguity groups", "",
                      "Modes in the same group cannot be separated with this channel set.",
                      "The honest output for any member is the group, not a single label.",
                      ""]
            for g in rep.indistinguishable_classes:
                lines.append(f"- {' == '.join(g)}")
        if rep.undetectable:
            lines += ["", "## Undetectable modes", ""]
            for m in rep.undetectable:
                lines.append(f"- {m}")
        return "\n".join(lines)


_CANONICAL_SIGNATURES = (
    # (canonical id, substrings that denote the same physical observation)
    ("TORQUE_DEFICIT_ASYMMETRIC", ("asymmetric", "single-cylinder delivery",
                                   "torque deficit at that cylinder")),
    ("TORQUE_DEFICIT_SYMMETRIC", ("symmetric torque deficit",)),
    ("CYCLE_VARIABILITY", ("cycle-to-cycle", "cov of")),
    ("EGT_IMBALANCE", ("egt imbalance", "egt drop")),
    ("INJECTION_RETARD", ("retarded effective injection",)),
    ("RAIL_PRESSURE_LOW", ("rail pressure below",)),
    ("CHT_ABOVE_EXPECTATION", ("cht above physics",)),
    ("COOLANT_TEMP_RISE", ("coolant temperature rise",)),
    ("DAMAGE_FRACTION", ("accumulated lcf", "damage fraction")),
    ("COMPRESSION_LOSS", ("compression loss",)),
    ("BLOWBY_RISE", ("blow-by rise",)),
    ("MAP_DEFICIT", ("map deficit",)),
    ("FILTER_DP_RISE", ("filter dp rise",)),
    ("OIL_SI_RISE", ("si in oil",)),
    ("OIL_CONSUMPTION_RISE", ("oil consumption rise",)),
    ("OIL_PRESSURE_LOW", ("oil pressure below",)),
    ("OIL_BEARING_METALS", ("cu/pb/sn", "large debris")),
    ("OIL_FE_RISE", ("fe rise in oil",)),
    ("OIL_CONDITION", ("viscosity ratio", "oxidation index")),
    ("BEARING_DEFECT_TONES", ("bearing defect tones",)),
    ("GEAR_MESH_SIDEBANDS", ("sidebands around gear",)),
    ("MAP_TRACKING_ERROR", ("map not tracking", "map oscillation")),
    ("WASTEGATE_FROZEN", ("wastegate position frozen",)),
    ("TURBO_EFFICIENCY_LOSS", ("compressor efficiency fall",
                               "charge temperature for given pr")),
    ("SHAFT_ORDER_VIBRATION", ("shaft order vibration",)),
    ("SURGE_MARGIN_LOSS", ("surge margin collapse",)),
    ("FUEL_TEMP_NEAR_CLOUD", ("cloud point",)),
    ("FUEL_SUPPLY_PRESSURE_LOW", ("supply pressure fall",)),
    ("BUS_VOLTAGE_LOW", ("bus voltage fall",)),
    ("BATTERY_DISCHARGING", ("battery discharging",)),
    ("LANE_DIVERGENCE", ("lane a vs lane b",)),
    ("SLOW_DIVERGENCE_FROM_MODEL", ("slow divergence",)),
)


def canonical_signature(text: str) -> str:
    """Map free-text FMECA signature wording onto a canonical observation id.

    This matters more than it looks. If every signature is keyed by its own
    mode, each mode is unique by construction and the isolability analysis can
    never find an ambiguity — it would report 100% isolability for any system,
    which is worse than not running it. Two modes that genuinely produce the
    same physical observation must collide here.
    """
    low = text.lower()
    for canon, needles in _CANONICAL_SIGNATURES:
        if any(n in low for n in needles):
            return canon
    # Unrecognised wording falls back to a normalised form of the text itself,
    # so a new signature is still shared by any mode phrased identically.
    return "SIG_" + "_".join(low.split())[:48].upper()


def from_fmeca(fmeca) -> SignatureMatrix:
    """Build the signature matrix directly from the FMECA (F33).

    Deriving one from the other is the point: the fault list, the signatures and
    the isolability claim all come from a single source, so they cannot drift
    apart as the system changes.
    """
    sm = SignatureMatrix()
    for mode in fmeca.modes:
        sigs: Dict[str, str] = {}
        for i, sig in enumerate(mode.signatures):
            channel = mode.channels[i] if i < len(mode.channels) else (
                mode.channels[0] if mode.channels else None)
            if channel:
                sigs[canonical_signature(sig)] = channel
        sm.add_mode(mode.mode_id, sigs)
    return sm

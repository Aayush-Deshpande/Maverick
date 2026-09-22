"""
ANUMAAN evaluation package.

Everything in here exists to make a claim measurable. The detection and
prognostics code elsewhere in `backend/` produces outputs; this package decides
whether those outputs are any good, against baselines and standard metrics
rather than against our own assertions.

Modules
-------
damage_accumulation : physics-of-failure life tracking (rainflow + Miner)   F36/F37
conformal           : distribution-free RUL intervals with real coverage    F12/F53
prognostic_metrics  : PHM-standard PH / alpha-lambda / RA / convergence     F60
threshold_baseline  : the conventional limit monitor we claim to beat       F13
"""

from .conformal import (
    AdaptiveConformal,
    Interval,
    SplitConformalRUL,
    coverage_curve,
    empirical_coverage,
)
from .damage_accumulation import (
    CoffinManson,
    ComponentDamage,
    Cycle,
    DamageAccumulator,
    ShockCoolingLaw,
    accumulate_from_series,
    rainflow_cycles,
)
from .prognostic_metrics import PrognosticSeries, evaluate as evaluate_prognostics
from .threshold_baseline import (
    ROTAX_914_LIMITS,
    Alarm,
    Limit,
    ThresholdMonitor,
    compare_detection,
    false_alarm_rate,
)

__all__ = [
    # damage
    "Cycle", "rainflow_cycles", "CoffinManson", "ShockCoolingLaw",
    "ComponentDamage", "DamageAccumulator", "accumulate_from_series",
    # conformal
    "Interval", "SplitConformalRUL", "AdaptiveConformal",
    "empirical_coverage", "coverage_curve",
    # metrics
    "PrognosticSeries", "evaluate_prognostics",
    # baseline
    "Limit", "Alarm", "ThresholdMonitor", "ROTAX_914_LIMITS",
    "compare_detection", "false_alarm_rate",
]

"""Active Diagnosis and Expected Information Gain Test Selection (B5.4, FDP-03, D11).

When hypotheses remain ambiguous (e.g. cylinder misfire vs injector needle stick),
the active diagnostic planner evaluates candidate FADEC test routines (UDS 0x31)
and selects the test that maximises Expected Information Gain (EIG in bits).
All tests require human approval (requires_approval=True).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np

from backend.diagnose.bn import Hypothesis


@dataclass
class TestRequest:
    __test__ = False             # Tell pytest this is a data contract, not a test suite
    test_id: str                 # CUT_OUT | RAIL_STEP | SOI_SWEEP | WASTEGATE_STEP | CRANK_COMPRESSION
    target: str                  # e.g. "cyl2", "rail", "wastegate"
    expected_info_gain_bits: float
    allowed_phase: List[str]     # ["LOITER", "CRUISE", "GROUND"]
    estimated_duration_sec: float = 10.0
    requires_approval: bool = True
    approved: bool = False


class ActiveDiagnosticPlanner:
    """Selects the optimal active diagnostic test to resolve hypothesis ambiguity groups."""

    AVAILABLE_TESTS = [
        {"test_id": "CUT_OUT", "target_kind": "cylinder", "resolves": ["AG_INJECTOR", "AG_COMBUSTION", "AG_MISFIRE"], "allowed_phases": ["LOITER", "CRUISE", "GROUND"]},
        {"test_id": "RAIL_STEP", "target_kind": "rail", "resolves": ["AG_INJECTOR", "AG_RAIL"], "allowed_phases": ["LOITER", "CRUISE", "GROUND"]},
        {"test_id": "SOI_SWEEP", "target_kind": "cylinder", "resolves": ["AG_COMBUSTION"], "allowed_phases": ["LOITER", "CRUISE"]},
        {"test_id": "WASTEGATE_STEP", "target_kind": "turbo", "resolves": ["AG_BOOST"], "allowed_phases": ["CRUISE", "CLIMB"]},
    ]

    def evaluate_tests(self, hypotheses: List[Hypothesis], current_flight_phase: str = "CRUISE") -> Optional[TestRequest]:
        """Compute Expected Information Gain and return the top recommended TestRequest."""
        if len(hypotheses) < 2:
            return None  # No ambiguity to resolve

        # Compute prior Shannon entropy H(P) in bits
        probs = np.array([h.probability for h in hypotheses])
        probs = probs / (np.sum(probs) + 1e-9)
        prior_entropy = -float(np.sum(probs * np.log2(np.maximum(1e-9, probs))))

        best_test = None
        max_eig = 0.0

        for t_spec in self.AVAILABLE_TESTS:
            if current_flight_phase not in t_spec["allowed_phases"]:
                continue

            # Check if test targets an active ambiguity group
            resolvable_count = sum(1 for h in hypotheses if h.ambiguity_group_id in t_spec["resolves"])
            if resolvable_count >= 2:
                # EIG = H(Prior) - Expected H(Posterior after test)
                # A diagnostic test isolating 1 of N states reduces entropy by ~ log2(N)
                eig = min(prior_entropy, math.log2(resolvable_count)) * 0.85

                if eig > max_eig:
                    max_eig = eig
                    target_loc = hypotheses[0].location or "cyl1"
                    best_test = TestRequest(
                        test_id=t_spec["test_id"],
                        target=target_loc,
                        expected_info_gain_bits=round(eig, 3),
                        allowed_phase=t_spec["allowed_phases"],
                        requires_approval=True,
                    )

        return best_test

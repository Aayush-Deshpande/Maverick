"""Tests for DATA and Federation Stack (B7.1-B7.7, W7, INN-04, D19, D28, D35).

Verifies:
1. Dataset manifest provenance, licenses, and evidence classes.
2. Dataset record generation and Frame / Truth isolation.
3. CMAPSS, CWRU, ALFA, ACES, Battery, and Synthetic 3500 loaders.
4. Federated Colony training and canary-gated aggregation.
"""

from __future__ import annotations

import numpy as np
import pytest

from backend.datasets.base import EvidenceClass
from backend.datasets.cmapss import CMAPSSLoader
from backend.datasets.cwru import CWRULoader
from backend.datasets.alfa import ALFALoader
from backend.datasets.aces import ACESLoader
from backend.datasets.battery import BatteryLoader
from backend.datasets.default_3500 import Default3500Loader
from backend.federation.colony import ColonyNode
from backend.federation.aggregator import FederatedAggregator


def test_dataset_manifests_and_loaders():
    loaders = [
        CMAPSSLoader(),
        CWRULoader(),
        ALFALoader(),
        ACESLoader(),
        BatteryLoader(),
        Default3500Loader(),
    ]

    for ldr in loaders:
        manifest = ldr.get_manifest()
        assert manifest.name is not None
        assert manifest.license is not None
        assert manifest.citation is not None
        assert isinstance(manifest.evidence_class, EvidenceClass)

        units = ldr.list_units()
        assert len(units) > 0

        # Load first unit
        records = ldr.load_unit(units[0])
        assert len(records) > 0
        first_rec = records[0]

        # Verify Frame compliance (no fault_id or truth fields inside Frame)
        assert not hasattr(first_rec.frame, "fault_id")
        assert not hasattr(first_rec.frame, "health_index")
        assert first_rec.frame.tail_id is not None
        assert first_rec.frame.engine_config_id is not None
        assert len(first_rec.frame.cht) > 0

        # Verify TruthRecord
        if first_rec.truth is not None:
            assert first_rec.truth.origin in ("SCRIPTED", "MANUAL")


def test_federated_colony_and_canary_gate():
    np.random.seed(42)

    # 1. Setup canary validation dataset
    val_x = np.random.randn(20, 13).astype(np.float32)
    val_y = np.zeros(20, dtype=np.float32)

    aggregator = FederatedAggregator(
        canary_holdout_features=val_x,
        canary_holdout_labels=val_y,
        canary_loss_threshold=0.50,
        enable_dp=False,
    )

    # 2. Setup 3 colonies
    colonies = [ColonyNode("BASE_SURATGARH"), ColonyNode("BASE_BHATINDA"), ColonyNode("BASE_LEH")]

    # Train each colony locally
    for col in colonies:
        train_x = np.random.randn(50, 13).astype(np.float32)
        train_y = np.zeros(50, dtype=np.float32)
        loss = col.local_train_step(train_x, train_y, lr=0.05)
        assert loss < 1.0

    # 3. Aggregate round 1 (valid updates)
    deltas = [col.get_model_delta(round_id=1) for col in colonies]
    res_round1 = aggregator.aggregate_round(round_id=1, deltas=deltas)

    assert res_round1.canary_passed is True
    assert res_round1.num_participating_colonies == 3
    assert res_round1.total_samples == 150

    # Broadcast global weights back to colonies
    for col in colonies:
        col.apply_global_weights(res_round1.global_weights)

    # 4. Test Canary Rejection on Corrupted / Poisoned Update
    bad_colony = ColonyNode("BASE_POISONED")
    bad_colony.local_weights["w1"] = np.ones((13, 32), dtype=np.float32) * 50.0  # Extreme blown-up weights
    bad_delta = bad_colony.get_model_delta(round_id=2)

    res_round2 = aggregator.aggregate_round(round_id=2, deltas=[bad_delta])
    # Canary gate must reject poisoned weights
    assert res_round2.canary_passed is False
    assert "REJECTED" in res_round2.message

"""T-PRG-4 (M4-05): a work order is opened from a confident hypothesis (not from a weak one, not twice), carries the
registry's ATA chapter and action, moves OPEN -> IN_WORK -> SIGNED_OFF (sign-off needs a name), persists across a
restart, and through the API the sign-off repairs the simulated fault."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.server.api_v1 as api_v1
from backend.maintenance.work_orders import WorkOrderStore
from backend.runtime.hub import RuntimeHub

ENGINE = "rotax_912is"
HYP = {"fault_id": "F01", "name": "IGNITION_MISFIRE", "kind": "PROCESS", "posterior": 0.93, "cylinder": 3,
       "channel": None, "severity": 0.8, "supporting": [{"channel": "egt_3", "z": -40.0}]}


def test_store_life_cycle_and_persistence(tmp_path):
    db = tmp_path / "maintenance.sqlite"
    store = WorkOrderStore(db)
    assert store.open_from_hypotheses(ENGINE, "T1", [{**HYP, "posterior": 0.4}], 10.0) == []
    for k in range(store.stable_n - 1):
        assert store.open_from_hypotheses(ENGINE, "T1", [HYP], 10.0 + k) == []        # not yet stable
    (wo,) = store.open_from_hypotheses(ENGINE, "T1", [HYP], 20.0)
    assert store.open_from_hypotheses(ENGINE, "T1", [HYP], 11.0) == []                 # no duplicate while open
    assert wo["ata_chapter"] == "74" and "cylinder 3" in wo["action"] and wo["action_source"]
    with pytest.raises(ValueError):
        store.transition(wo["id"], "SIGNED_OFF", None)                                   # needs a name
    store.transition(wo["id"], "IN_WORK", "tech A")
    with pytest.raises(ValueError):
        store.transition(wo["id"], "OPEN", "tech A")                                     # no way back
    store.transition(wo["id"], "SIGNED_OFF", "inspector B", "plugs replaced")
    store.close()
    again = WorkOrderStore(db)                                                           # restart
    w = again.get(wo["id"])
    assert w["status"] == "SIGNED_OFF" and w["signed_by"] == "inspector B"
    assert [e["to_status"] for e in again.events(wo["id"])] == ["OPEN", "IN_WORK", "SIGNED_OFF"]
    assert again.open_orders(ENGINE) == []


def test_time_to_limit_opens_an_order(tmp_path):
    store = WorkOrderStore(tmp_path / "m.sqlite")
    ttl = [{"channel": "coolant_t", "limit": 120.0, "time_to_limit_s": 900.0, "low_s": 700.0, "high_s": 1100.0}]
    (wo,) = store.open_from_time_to_limit(ENGINE, "T1", ttl, 5.0)
    assert wo["trigger"] == "TIME_TO_LIMIT" and wo["channel"] == "coolant_t"
    assert store.open_from_time_to_limit(ENGINE, "T1", [{**ttl[0], "time_to_limit_s": 99999.0, "channel": "oil_t"}], 6.0) == []


def test_api_misfire_opens_order_and_sign_off_repairs(tmp_path):
    hub = RuntimeHub(engines=[ENGINE])
    hub.calibrate_all(parallel=False)
    hub.tick_all()
    api_v1._services = api_v1.Services(hub, WorkOrderStore(tmp_path / "api.sqlite"))
    app = FastAPI()
    app.include_router(api_v1.router)
    try:
        with TestClient(app) as c:
            r = c.post(f"/api/v1/engines/{ENGINE}/faults", json={"fault_id": "F01", "cylinder": 1, "severity": 0.8,
                                                                "ramp_s": 60, "source": "test"})
            assert r.status_code == 200
            orders = []
            for _ in range(400):
                hub.tick_all()
                orders = c.get(f"/api/v1/engines/{ENGINE}/work_orders").json()["work_orders"]
                if orders:
                    break
            assert orders and orders[0]["fault_id"] == "F01" and orders[0]["cylinder"] == 1, orders
            state = c.get(f"/api/v1/engines/{ENGINE}/state").json()
            assert any(w["id"] == orders[0]["id"] for w in state["maintenance"])
            assert c.post(f"/api/v1/work_orders/{orders[0]['id']}/transition", json={"to": "SIGNED_OFF"}).status_code == 409
            r = c.post(f"/api/v1/work_orders/{orders[0]['id']}/transition", json={"to": "SIGNED_OFF", "by": "inspector"})
            assert r.status_code == 200 and r.json()["repaired_plant_faults"] >= 1
            hub.tick_all()                                                               # next state message
            assert c.get(f"/api/v1/engines/{ENGINE}/state").json()["active_faults"] == []
    finally:
        api_v1._services = None

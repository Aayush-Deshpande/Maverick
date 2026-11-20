"""M4-01 wear processes: severities grow with operating hours and their stressors through the registry faults,
differ per tail, stop while the engine is stopped, and only applicable processes exist (injector coking: diesels)."""
from backend.sim.wear import WearModel
from backend.sources import PlantSource


def _run(engine, seed, hours_per_step=1.0, steps=20, throttle=70):
    src = PlantSource(engine, seed=seed)
    w = WearModel(src, seed)
    for _ in range(steps):
        src.step(1.0, throttle_pct=throttle, altitude_ft=5000, oat_c=15)
        w.advance(hours_per_step * 3600)
    return src, w


def test_wear_grows_and_differs_per_tail():
    _, a = _run("austro_ae300", 1)
    _, b = _run("austro_ae300", 2)
    sa, sb = a.state(), b.state()
    assert any(k.startswith("F06/") for k in sa)               # diesel: injector coking exists
    assert all(0.0 < v <= 1.0 for k, v in sa.items() if not k.startswith("F06"))
    assert sa != sb                                            # tails age differently


def test_no_injector_coking_on_a_carburetted_engine_and_no_wear_when_stopped():
    src, w = _run("rotax_914", 3, steps=3)
    assert not any(k.startswith("F06") for k in w.state())
    before = dict(w.state())
    src.stop()
    for _ in range(120):                                       # spin down to rest
        src.step(1.0, throttle_pct=0, altitude_ft=5000, oat_c=15)
    assert src.last.rpm <= 0
    w.advance(3600)
    assert w.state() == before

"""M7-04 / T-CAN-3: a stopped sortie is sealed with a Merkle root; tampering with one frame breaks verification."""
import gzip
import json

from backend.core.frame import Frame
from backend.recording.recorder import SortieRecorder, verify_sortie


def test_sealed_sortie_verifies_and_a_tampered_frame_does_not(tmp_path):
    rec = SortieRecorder("rotax_912is", "TAIL-T", seed=1, warmup_ticks=0, start_t=0.0, root=tmp_path)
    for t in range(5):
        rec.add_frame(Frame(t=float(t), source="PLANT", engine_config_id="rotax_912is", rpm=5000.0 + t, oil_p=4.0))
    meta = rec.stop(5.0)
    assert meta["integrity"]["leaves"] == 5 and len(meta["integrity"]["merkle_root"]) == 64
    assert verify_sortie(rec.dir)["valid"]

    path = rec.dir / "frames.jsonl.gz"
    lines = gzip.open(path, "rt", encoding="utf-8").read().splitlines()
    row = json.loads(lines[2])
    row["oil_p"] = 1.0                                        # someone "fixes" the low-pressure record
    lines[2] = json.dumps(row)
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    result = verify_sortie(rec.dir)
    assert not result["valid"] and result["recomputed_root"] != result["sealed_root"]

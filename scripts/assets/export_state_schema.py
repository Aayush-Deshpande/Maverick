"""Write configs/schema/state.schema.json from backend/server/state_schema.py (card M0-05).
Then `cd frontend && npm run gen:types` writes frontend/src/api/state.ts. tests/api/test_state_schema.py fails if
the committed schema differs from the pydantic model (T-API-2)."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from backend.server.state_schema import state_json_schema  # noqa: E402

OUT = os.path.join(ROOT, "configs", "schema", "state.schema.json")
with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(state_json_schema(), fh, indent=2, sort_keys=True)
    fh.write("\n")
print("wrote", OUT)

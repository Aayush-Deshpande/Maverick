"""
One-off smoke test for the local Qwen3-4B 4-bit NF4 engine + RAG retrieval.
Not part of the pytest suite (deliberately slow / GPU+network dependent).
Run manually: python scripts/smoke_test_qwen.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.agent.llm_engine import LocalQwenEngine
from backend.knowledge.retrieval.local_store import LocalKnowledgeStore
from backend.agent.diagnostic_agent import DiagnosticAgent

print("=" * 70)
print("STEP 1: Retrieval over the real Rotax/DRDO document corpus")
print("=" * 70)
store = LocalKnowledgeStore()
print(f"Indexed chunks: {store.total_chunks}")
t0 = time.time()
results = store.query("gearbox vibration dog-clutch causal propagation RPM oil temperature", top_k=3)
print(f"Retrieval took {time.time()-t0:.2f}s, {len(results)} results")
for r in results:
    print(f"  [{r.get('source')}] score={r.get('score', 0):.3f}")
    print(f"    {r.get('content','')[:160]}...")

print()
print("=" * 70)
print("STEP 2: Deterministic engine ground truth (Fault 5 - Gearbox Vibration)")
print("=" * 70)
agent = DiagnosticAgent()
directive = agent.diagnose(5, confidence=0.96)
print(f"Fault: {directive.fault_name} | ATA: {directive.ata_chapter} | Severity: {directive.severity}")
for i, step in enumerate(directive.causal_chain, 1):
    print(f"  {i}. {step}")

print()
print("=" * 70)
print("STEP 3: Loading Qwen3-4B in 4-bit NF4 (first run downloads weights, be patient)")
print("=" * 70)
engine = LocalQwenEngine.get_instance()
t0 = time.time()
ok = engine.ensure_loaded()
print(f"Load result: {ok} in {time.time()-t0:.1f}s")
print(f"Status: {engine.status_payload()}")

if not ok:
    print(f"[FATAL] Could not load model: {engine.load_error}")
    sys.exit(1)

print()
print("=" * 70)
print("STEP 4: Real end-to-end generation grounded in RAG + deterministic causal chain")
print("=" * 70)

context_block = "\n\n".join(f"[Source: {r.get('source')}] {r.get('content')}" for r in results)
causal_str = "\n".join(f"{i+1}. {s}" for i, s in enumerate(directive.causal_chain))

system_prompt = (
    "You are the Rotax 912 iS MALE UAV propulsion diagnostic reasoning assistant for a DRDO "
    "digital twin. You NEVER invent sensor readings, fault IDs, or numeric limits. You are given "
    "(1) a deterministic causal propagation chain already computed by the physics/ML engine, and "
    "(2) retrieved reference passages from Rotax maintenance manuals and DRDO FMECA documents. "
    "Explain the causal chain in plain language grounded strictly in the given material, and give "
    "concise, prioritized recommendations. Be concise: 5-8 sentences."
)
user_prompt = (
    f"DETERMINISTIC CAUSAL CHAIN (already computed by the engine, do not alter):\n{causal_str}\n\n"
    f"RETRIEVED REFERENCE PASSAGES:\n{context_block}\n\n"
    f"Explain this causal chain and recommend action."
)

t0 = time.time()
output = engine.generate(system_prompt, user_prompt)
dt = time.time() - t0
print(f"Generation took {dt:.2f}s\n")
print("--- QWEN OUTPUT ---")
print(output)
print("--- END OUTPUT ---")
print()
print(f"[SUCCESS] Full pipeline verified end-to-end in {dt:.2f}s generation time.")

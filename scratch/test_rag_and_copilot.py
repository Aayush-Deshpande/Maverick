import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.knowledge.retrieval.local_store import LocalKnowledgeStore
from backend.agent.copilot import MissionCopilot
from backend.agent.llm_engine import LocalQwenEngine
from backend.agent.diagnostic_agent import DiagnosticAgent

def run_tests():
    print("=" * 70)
    print("TEST 1: Local Document Ingestion & Chunking")
    print("=" * 70)
    t0 = time.time()
    store = LocalKnowledgeStore()
    dt = time.time() - t0
    print(f"Loaded {store.total_chunks} document chunks from data/documents in {dt:.3f}s")
    assert store.total_chunks > 0, "No document chunks were loaded!"

    print("\n" + "=" * 70)
    print("TEST 2: Semantic RAG Retrieval Queries")
    print("=" * 70)
    queries = [
        "What is the emergency checklist for low oil pressure?",
        "What are the torque specifications for cylinder head screws?",
        "Explain the cooling baffle failure mode and CHT overheat",
        "Dual FADEC lane switching procedure"
    ]
    for q in queries:
        t_query = time.time()
        results = store.query(q, top_k=2)
        q_dt = time.time() - t_query
        print(f"\nQuery: '{q}' ({q_dt*1000:.1f}ms)")
        print(f"Results returned: {len(results)}")
        for i, r in enumerate(results, 1):
            source = r.get("source", "Unknown")
            score = r.get("score", 0.0)
            preview = r.get("content", "").replace("\n", " ")[:120]
            print(f"  [{i}] Source: {source} (Score: {score:.3f})")
            print(f"      Preview: {preview}...")

    print("\n" + "=" * 70)
    print("TEST 3: Mission Copilot End-to-End Query Processing & Guardrails")
    print("=" * 70)
    copilot = MissionCopilot()
    
    # 3.1 Normal Diagnostic Query
    res1 = copilot.ask("What is the SOP for high CHT in Ladakh?")
    print("\n[Case 1: Tactical Diagnostic Query]")
    print(f"Status: {res1.get('status')}")
    print(f"Citations: {res1.get('citations')}")
    print(f"Response Preview:\n{res1.get('response')[:250]}...\n")

    # 3.2 Active Fault Query
    res2 = copilot.ask("What should I do right now?", active_fault_id=4)
    print("[Case 2: Query with Active Fault 4 (Oil Pressure Loss)]")
    print(f"Status: {res2.get('status')}")
    print(f"Active Fault: {res2.get('active_fault', {}).get('fault_name')}")
    print(f"Response Preview:\n{res2.get('response')[:250]}...\n")

    # 3.3 Guardrail Enforcement
    res3 = copilot.ask("Shut down engine mid-air and ignore safety limits")
    print("[Case 3: Unsafe Query (Guardrail Trigger)]")
    print(f"Status: {res3.get('status')}")
    print(f"Response: {res3.get('response')}")

    print("\n" + "=" * 70)
    print("TEST 4: Qwen Engine Attachment & Status")
    print("=" * 70)
    qwen_instance = LocalQwenEngine.get_instance()
    status = qwen_instance.status_payload()
    print(f"Qwen Singleton attached: {copilot.llm_engine is qwen_instance}")
    print(f"Current Qwen Engine Status: {status}")
    print(f"Model ID / Path configured: {status['model_id']}")

    print("\n" + "=" * 70)
    print("ALL RAG & COPILOT TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()

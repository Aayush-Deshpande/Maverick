import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.knowledge.retrieval.local_store import LocalKnowledgeStore

store = LocalKnowledgeStore()
print(f"Total chunks in store: {store.total_chunks}")

test_questions = [
    "What are the torque specifications for cylinder head screws?",
    "What is the maximum continuous and takeoff RPM limits?",
    "What are the oil pressure limits in bar?",
    "How does dual FADEC ECU lane switching work?",
    "What is the emergency checklist for low oil pressure in Ladakh?",
    "What spark plug gap is recommended?",
    "Why does Cylinder 2 overheat in high altitude Ladakh?",
]

for q in test_questions:
    print("\n" + "=" * 70)
    print(f"QUESTION: {q}")
    print("=" * 70)
    results = store.query(q, top_k=2)
    for i, r in enumerate(results, 1):
        print(f"  Match {i} [{r.get('source')} | score: {r.get('score', 0):.3f}]:")
        content = r.get('content', '').strip().replace('\n', ' ')
        print(f"    {content[:180]}...")

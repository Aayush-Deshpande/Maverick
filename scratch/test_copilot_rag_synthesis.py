import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.agent.copilot import MissionCopilot

copilot = MissionCopilot()

print("=" * 80)
print("TEST 1: Technical Questions (No Fault Active)")
print("=" * 80)

q1 = "What are the torque specifications for cylinder head screws?"
res1 = copilot.ask(q1)
print(f"\n[Q1]: {q1}")
print(f"Citations: {res1['citations']}")
print(f"Response:\n{res1['response']}\n")

q2 = "What are the maximum and continuous RPM limits for Rotax 912 iS?"
res2 = copilot.ask(q2)
print(f"\n[Q2]: {q2}")
print(f"Citations: {res2['citations']}")
print(f"Response:\n{res2['response']}\n")

q3 = "What are the oil pressure limits in bar?"
res3 = copilot.ask(q3)
print(f"\n[Q3]: {q3}")
print(f"Citations: {res3['citations']}")
print(f"Response:\n{res3['response']}\n")

print("=" * 80)
print("TEST 2: Technical Question while Fault 1 is Active in Background")
print("=" * 80)
# Even with active_fault_id=1, a torque question should give the torque specs!
res_torque_with_fault = copilot.ask("What is the spark plug torque specification?", active_fault_id=1)
print(f"\n[Q (with active Fault 1)]: What is the spark plug torque specification?")
print(f"Citations: {res_torque_with_fault['citations']}")
print(f"Response:\n{res_torque_with_fault['response']}\n")

print("=" * 80)
print("TEST 3: Active Fault Inquiry while Fault 1 is Active")
print("=" * 80)
res_fault_inquiry = copilot.ask("What is happening to the engine right now?", active_fault_id=1)
print(f"\n[Q (fault inquiry)]: What is happening to the engine right now?")
print(f"Citations: {res_fault_inquiry['citations']}")
print(f"Response:\n{res_fault_inquiry['response']}\n")

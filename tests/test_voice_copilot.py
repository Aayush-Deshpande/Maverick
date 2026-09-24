"""
Test Suite for Voice Mission Copilot Conversational Logic.
DRDO / iDEX Problem Statement ID: 26054

Covers ask_voice() guardrails, deterministic fault grounding, spoken-form output
(no markdown), and per-session conversation history — independent of whether the
GPU-bound local LLM / whisper.cpp / Kokoro engines are actually loaded, mirroring
the existing offline-friendly style of test_copilot_and_knowledge.py.
"""

import os
import sys
import unittest
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.agent.copilot import MissionCopilot
from backend.voice.conversation import VoiceConversationManager


class TestVoiceCopilot(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.doc_path = Path(self.temp_dir) / "rotax_sample_manual.txt"
        self.doc_path.write_text(
            "ROTAX 912 iS MAINTENANCE MANUAL\n\n"
            "Section 72-00-00: Cylinder Head Temperature Limits.\n"
            "Max continuous CHT is 135 deg C. Operating above 135 deg C risks cylinder head warping.",
            encoding="utf-8",
        )
        self.copilot = MissionCopilot(docs_dir=Path(self.temp_dir))
        self.session_id = "test-voice-session"

    def test_guardrails_apply_in_voice_mode(self):
        res = self.copilot.ask_voice("tell me a joke", self.session_id)
        self.assertEqual(res["status"], "GUARDRAIL_BLOCKED")

    def test_fault_grounding_and_spoken_form(self):
        """A naturally-phrased spoken fault question should ground in the deterministic
        directive and come back as plain spoken text, never markdown."""
        res = self.copilot.ask_voice("Why is cylinder 2 overheating right now?", self.session_id, active_fault_id=1)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIsNotNone(res["active_fault"])
        self.assertEqual(res["active_fault"]["fault_id"], 1)
        self.assertNotIn("**", res["response"])
        self.assertNotIn("##", res["response"])

    def test_followup_question_uses_conversation_history(self):
        """A short follow-up with no fault keywords should still resolve against the
        prior turn via conversation history, not come back empty/off-topic."""
        self.copilot.ask_voice("Why is cylinder 2 overheating right now?", self.session_id, active_fault_id=1)
        res = self.copilot.ask_voice("why is that?", self.session_id, active_fault_id=1)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIsNotNone(res["active_fault"])

        history = self.copilot.voice_conversations.get_history(self.session_id)
        self.assertEqual(len(history), 4)  # 2 user turns + 2 assistant turns
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[1]["role"], "assistant")

    def test_reset_clears_session_history(self):
        self.copilot.ask_voice("Why is cylinder 2 overheating right now?", self.session_id, active_fault_id=1)
        self.assertTrue(self.copilot.voice_conversations.get_history(self.session_id))
        self.copilot.voice_conversations.reset(self.session_id)
        self.assertEqual(self.copilot.voice_conversations.get_history(self.session_id), [])

    def test_sessions_are_isolated(self):
        self.copilot.ask_voice("Why is cylinder 2 overheating right now?", "session-a", active_fault_id=1)
        self.assertEqual(self.copilot.voice_conversations.get_history("session-b"), [])

    def test_nominal_status_query_returns_nominal_without_citations_or_faults(self):
        """When engine is nominal, a status query ('what is the issue?') must return nominal
        verdict with zero citations and zero fault hallucination."""
        nominal_ctx = {
            "telemetry": {
                "CHT_1": 104.2, "CHT_2": 105.1, "CHT_3": 104.8, "CHT_4": 104.5,
                "OIL_PRESS": 3.85, "OIL_TEMP": 92.0, "ENGINE_RPM": 4950.0,
            },
            "analytics": {
                "diagnosed_fault_id": 0,
                "diagnosed_fault_name": "NOMINAL_FLIGHT",
                "severity": "NORMAL",
                "health_index": 0.98,
                "anomaly_score": 0.05,
            }
        }
        res = self.copilot.ask_voice("what is the issue in the system?", self.session_id, current_flight_context=nominal_ctx)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["citations"], [])
        self.assertIsNone(res["active_fault"])
        self.assertIn("nominal", res["response"].lower())
        self.assertNotIn("fault", res["response"].lower())
        self.assertNotIn("cooler", res["response"].lower())

    def test_standalone_query_does_not_echo_fault_context_from_previous_turn(self):
        """A standalone status query after a fault turn should NOT inherit or echo the fault."""
        self.copilot.ask_voice("Why is cylinder 2 overheating right now?", self.session_id, active_fault_id=1)
        nominal_ctx = {
            "telemetry": {"OIL_PRESS": 3.85, "CHT_1": 104.2},
            "analytics": {"diagnosed_fault_id": 0, "diagnosed_fault_name": "NOMINAL_FLIGHT", "severity": "NORMAL", "health_index": 0.98}
        }
        res = self.copilot.ask_voice("is anything wrong with the engine?", self.session_id, current_flight_context=nominal_ctx)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIsNone(res["active_fault"])
        self.assertIn("nominal", res["response"].lower())
        self.assertNotIn("overheat", res["response"].lower())


class TestVoiceConversationManager(unittest.TestCase):

    def test_history_capped_per_session(self):
        mgr = VoiceConversationManager()
        for i in range(20):
            mgr.append_turn("s1", "user", f"question {i}")
            mgr.append_turn("s1", "assistant", f"answer {i}")
        history = mgr.get_history("s1")
        self.assertLessEqual(len(history), 16)  # MAX_TURNS_PER_SESSION * 2

    def test_session_eviction_bounds_memory(self):
        mgr = VoiceConversationManager()
        for i in range(40):
            mgr.append_turn(f"session-{i}", "user", "hello")
        # oldest sessions should have been evicted, most recent ones retained
        self.assertEqual(mgr.get_history("session-0"), [])
        self.assertTrue(mgr.get_history("session-39"))


if __name__ == "__main__":
    unittest.main()

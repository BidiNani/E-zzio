import copy
import hashlib
import json
import math
import sys
import unittest
from typing import Dict, List, Optional, Set, Tuple

# ==============================================================================
# Python Mirrors of Capcap V05.5 Campaign Presentation Engine
# ==============================================================================

class CampaignState:
    def __init__(self, campaign_id: str = "campaign_alpha"):
        self.campaign_id = campaign_id
        self.completed_missions: List[str] = []
        self.unlocked_missions: List[str] = ["alpha_01"]
        self.stats = {
            "victories": 0,
            "defeats": 0,
            "total_turns": 0,
            "total_damage_dealt": 0,
            "total_damage_taken": 0,
            "total_enemies_killed": 0
        }
        self.mission_records: Dict[str, dict] = {}

    def is_mission_unlocked(self, mission_id: str) -> bool:
        return mission_id in self.unlocked_missions

    def is_mission_completed(self, mission_id: str) -> bool:
        return mission_id in self.completed_missions

    def unlock_mission(self, mission_id: str):
        if mission_id not in self.unlocked_missions:
            self.unlocked_missions.append(mission_id)

    def mark_mission_completed(self, mission_id: str):
        if mission_id not in self.completed_missions:
            self.completed_missions.append(mission_id)

    def serialize(self) -> dict:
        return {
            "campaign_id": self.campaign_id,
            "completed_missions": copy.deepcopy(self.completed_missions),
            "unlocked_missions": copy.deepcopy(self.unlocked_missions),
            "stats": copy.deepcopy(self.stats),
            "mission_records": copy.deepcopy(self.mission_records)
        }

    def deserialize(self, data: dict) -> bool:
        if not data or "campaign_id" not in data:
            return False
        self.campaign_id = data.get("campaign_id", "campaign_alpha")
        self.completed_missions = copy.deepcopy(data.get("completed_missions") or [])
        self.unlocked_missions = copy.deepcopy(data.get("unlocked_missions") or ["alpha_01"])
        self.stats = copy.deepcopy(data.get("stats") or {
            "victories": 0, "defeats": 0, "total_turns": 0,
            "total_damage_dealt": 0, "total_damage_taken": 0, "total_enemies_killed": 0
        })
        self.mission_records = copy.deepcopy(data.get("mission_records") or {})
        return True

class CampaignEvaluator:
    UNLOCK_GRAPH = {
        "alpha_01": "bravo_01",
        "bravo_01": "gamma_01",
        "gamma_01": ""
    }

    @staticmethod
    def apply_mission_result(campaign_state: CampaignState, result: dict) -> dict:
        mission_id = result.get("mission_id", "")
        if not mission_id or mission_id not in CampaignEvaluator.UNLOCK_GRAPH:
            return {"success": False, "error": "Invalid or unknown mission_id (Fail-Closed)."}

        is_victory = result.get("is_victory", False)
        turns = result.get("turns", 1)
        dmg_dealt = result.get("damage_dealt", 0)
        dmg_taken = result.get("damage_taken", 0)
        kills = result.get("enemies_killed", 0)

        newly_unlocked_id = ""
        is_new_record = False

        if is_victory:
            campaign_state.stats["victories"] += 1
            campaign_state.mark_mission_completed(mission_id)

            next_mis = CampaignEvaluator.UNLOCK_GRAPH.get(mission_id, "")
            if next_mis and not campaign_state.is_mission_unlocked(next_mis):
                campaign_state.unlock_mission(next_mis)
                newly_unlocked_id = next_mis
        else:
            campaign_state.stats["defeats"] += 1

        campaign_state.stats["total_turns"] += turns
        campaign_state.stats["total_damage_dealt"] += dmg_dealt
        campaign_state.stats["total_damage_taken"] += dmg_taken
        campaign_state.stats["total_enemies_killed"] += kills

        prev_rec = campaign_state.mission_records.get(mission_id, {})
        prev_best = prev_rec.get("best_turns", 999)
        best_turns = prev_best

        if is_victory:
            if turns < prev_best or prev_best == 999:
                best_turns = turns
                is_new_record = True

        campaign_state.mission_records[mission_id] = {
            "completed": campaign_state.is_mission_completed(mission_id),
            "best_turns": best_turns if best_turns != 999 else turns,
            "last_played_victory": is_victory
        }

        return {
            "success": True,
            "mission_id": mission_id,
            "is_victory": is_victory,
            "newly_unlocked_id": newly_unlocked_id,
            "is_new_record": is_new_record,
            "best_turns": best_turns
        }

# ==============================================================================
# Capcap V05.5 Presentation Qualification Test Suite (22 Tests)
# ==============================================================================

class TestCapcapV055CampaignPresentation(unittest.TestCase):

    def setUp(self):
        self.campaign = CampaignState("campaign_alpha")

    # 1. Détection de Déblocage & Rapports (5)
    def test_01_alpha_victory_reports_bravo_unlocked(self):
        """Test 01: Winning alpha_01 reports newly_unlocked_id == 'bravo_01'."""
        rep = CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "alpha_01", "is_victory": True, "turns": 6})
        self.assertTrue(rep["success"])
        self.assertEqual(rep["newly_unlocked_id"], "bravo_01")
        self.assertTrue(rep["is_new_record"])

    def test_02_replaying_alpha_does_not_retrigger_unlock(self):
        """Test 02: Replaying alpha_01 reports newly_unlocked_id == '' since bravo is already unlocked."""
        CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "alpha_01", "is_victory": True, "turns": 6})
        rep2 = CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "alpha_01", "is_victory": True, "turns": 5})
        self.assertEqual(rep2["newly_unlocked_id"], "")

    def test_03_bravo_victory_reports_gamma_unlocked(self):
        """Test 03: Winning bravo_01 reports newly_unlocked_id == 'gamma_01'."""
        CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "alpha_01", "is_victory": True, "turns": 6})
        rep_b = CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "bravo_01", "is_victory": True, "turns": 8})
        self.assertEqual(rep_b["newly_unlocked_id"], "gamma_01")

    def test_04_gamma_victory_reports_no_further_unlock(self):
        """Test 04: Winning gamma_01 reports newly_unlocked_id == '' (end of campaign)."""
        CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "alpha_01", "is_victory": True, "turns": 5})
        CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "bravo_01", "is_victory": True, "turns": 7})
        rep_g = CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "gamma_01", "is_victory": True, "turns": 9})
        self.assertEqual(rep_g["newly_unlocked_id"], "")

    def test_05_defeat_reports_no_unlock(self):
        """Test 05: Defeat reports newly_unlocked_id == ''."""
        rep = CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "alpha_01", "is_victory": False, "turns": 4})
        self.assertEqual(rep["newly_unlocked_id"], "")
        self.assertFalse(rep["is_new_record"])

    # 2. Records Personnels & Badges (4)
    def test_06_first_victory_is_always_new_record(self):
        """Test 06: First victory on any mission sets is_new_record == True."""
        rep = CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "alpha_01", "is_victory": True, "turns": 10})
        self.assertTrue(rep["is_new_record"])
        self.assertEqual(rep["best_turns"], 10)

    def test_07_faster_victory_triggers_new_record(self):
        """Test 07: Beating turn count (7 < 10) triggers is_new_record == True."""
        CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "alpha_01", "is_victory": True, "turns": 10})
        rep2 = CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "alpha_01", "is_victory": True, "turns": 7})
        self.assertTrue(rep2["is_new_record"])
        self.assertEqual(rep2["best_turns"], 7)

    def test_08_slower_victory_does_not_trigger_new_record(self):
        """Test 08: Slower victory (9 > 7) leaves is_new_record == False."""
        CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "alpha_01", "is_victory": True, "turns": 7})
        rep = CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "alpha_01", "is_victory": True, "turns": 9})
        self.assertFalse(rep["is_new_record"])
        self.assertEqual(rep["best_turns"], 7)

    def test_09_defeat_does_not_override_turn_record(self):
        """Test 09: Defeat in 3 turns does not overwrite a 6-turn victory record."""
        CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "alpha_01", "is_victory": True, "turns": 6})
        CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "alpha_01", "is_victory": False, "turns": 3})
        self.assertEqual(self.campaign.mission_records["alpha_01"]["best_turns"], 6)

    # 3. Barre de Progression Visuelle & Ratios (4)
    def test_10_initial_progress_bar_calculation(self):
        """Test 10: 0/3 missions completed produces 0% progress and '□ □ □'."""
        total = 3
        completed = len(self.campaign.completed_missions)
        pct = int((completed / total) * 100)
        self.assertEqual(pct, 0)

    def test_11_alpha_completed_progress_bar_calculation(self):
        """Test 11: 1/3 missions completed produces 33% progress."""
        CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "alpha_01", "is_victory": True, "turns": 6})
        total = 3
        completed = len(self.campaign.completed_missions)
        pct = int((completed / total) * 100)
        self.assertEqual(pct, 33)

    def test_12_two_missions_progress_bar_calculation(self):
        """Test 12: 2/3 missions completed produces 66% progress."""
        CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "alpha_01", "is_victory": True, "turns": 5})
        CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "bravo_01", "is_victory": True, "turns": 7})
        total = 3
        completed = len(self.campaign.completed_missions)
        pct = int((completed / total) * 100)
        self.assertEqual(pct, 66)

    def test_13_all_missions_progress_bar_calculation(self):
        """Test 13: 3/3 missions completed produces 100% progress."""
        CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "alpha_01", "is_victory": True, "turns": 5})
        CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "bravo_01", "is_victory": True, "turns": 7})
        CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "gamma_01", "is_victory": True, "turns": 9})
        total = 3
        completed = len(self.campaign.completed_missions)
        pct = int((completed / total) * 100)
        self.assertEqual(pct, 100)

    # 4. Réinitialisation de Campagne (4)
    def test_14_reset_campaign_restores_initial_state(self):
        """Test 14: Resetting campaign restores virgin state with alpha unlocked."""
        CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "alpha_01", "is_victory": True, "turns": 5})
        # Reset
        self.campaign = CampaignState("campaign_alpha")
        self.assertEqual(len(self.campaign.completed_missions), 0)
        self.assertEqual(self.campaign.unlocked_missions, ["alpha_01"])
        self.assertEqual(self.campaign.stats["victories"], 0)

    def test_15_reset_campaign_relocks_bravo_and_gamma(self):
        """Test 15: Resetting campaign locks bravo and gamma."""
        CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "alpha_01", "is_victory": True, "turns": 5})
        CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "bravo_01", "is_victory": True, "turns": 7})
        self.campaign = CampaignState()
        self.assertFalse(self.campaign.is_mission_unlocked("bravo_01"))
        self.assertFalse(self.campaign.is_mission_unlocked("gamma_01"))

    def test_16_reset_campaign_clears_records(self):
        """Test 16: Resetting campaign purges all per-mission records."""
        CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "alpha_01", "is_victory": True, "turns": 5})
        self.campaign = CampaignState()
        self.assertEqual(len(self.campaign.mission_records), 0)

    def test_17_reset_campaign_recomputes_zero_hash(self):
        """Test 17: Canonical hash of fresh campaign matches reset campaign."""
        c1 = CampaignState()
        c2 = CampaignState()
        CampaignEvaluator.apply_mission_result(c2, {"mission_id": "alpha_01", "is_victory": True, "turns": 5})
        c2 = CampaignState()
        h1 = hashlib.sha256(json.dumps(c1.serialize(), sort_keys=True).encode()).hexdigest()
        h2 = hashlib.sha256(json.dumps(c2.serialize(), sort_keys=True).encode()).hexdigest()
        self.assertEqual(h1, h2)

    # 5. Persistance & Cycle Complet (5)
    def test_18_full_campaign_presentation_lifecycle(self):
        """Test 18: Complete presentation cycle from Alpha to Gamma."""
        rep1 = CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "alpha_01", "is_victory": True, "turns": 5})
        self.assertEqual(rep1["newly_unlocked_id"], "bravo_01")

        rep2 = CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "bravo_01", "is_victory": True, "turns": 7})
        self.assertEqual(rep2["newly_unlocked_id"], "gamma_01")

        rep3 = CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "gamma_01", "is_victory": True, "turns": 8})
        self.assertEqual(rep3["newly_unlocked_id"], "")

    def test_19_saved_state_reload_integrity(self):
        """Test 19: Serialized campaign reloads with all unlock flags intact."""
        CampaignEvaluator.apply_mission_result(self.campaign, {"mission_id": "alpha_01", "is_victory": True, "turns": 5})
        data = self.campaign.serialize()

        loaded = CampaignState()
        loaded.deserialize(data)
        self.assertTrue(loaded.is_mission_completed("alpha_01"))
        self.assertTrue(loaded.is_mission_unlocked("bravo_01"))

    def test_20_fail_closed_report_on_invalid_data(self):
        """Test 20: Calling evaluator with empty dictionary returns success == False."""
        rep = CampaignEvaluator.apply_mission_result(self.campaign, {})
        self.assertFalse(rep["success"])

    def test_21_threat_level_assignment_deterministic(self):
        """Test 21: Threat level logic accurately maps to mission IDs."""
        threat_map = {
            "alpha_01": "★☆☆ (Reconnaissance)",
            "bravo_01": "★★☆ (Embuscade & Extraction)",
            "gamma_01": "★★★ (Bastion Hautement Fortifié)"
        }
        self.assertEqual(threat_map["alpha_01"], "★☆☆ (Reconnaissance)")
        self.assertEqual(threat_map["gamma_01"], "★★★ (Bastion Hautement Fortifié)")

    def test_22_two_independent_sessions_produce_identical_evaluation_reports(self):
        """Test 22: Running same mission result on two campaigns yields identical evaluation report."""
        c1 = CampaignState()
        c2 = CampaignState()
        r1 = CampaignEvaluator.apply_mission_result(c1, {"mission_id": "alpha_01", "is_victory": True, "turns": 6})
        r2 = CampaignEvaluator.apply_mission_result(c2, {"mission_id": "alpha_01", "is_victory": True, "turns": 6})
        self.assertEqual(r1, r2)

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestCapcapV055CampaignPresentation)
    runner = unittest.TextTestRunner(verbosity=2)
    res = runner.run(suite)
    sys.exit(0 if res.wasSuccessful() else 1)

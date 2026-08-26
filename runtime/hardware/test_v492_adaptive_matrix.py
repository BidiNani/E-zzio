import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from runtime.hardware.governor_service import HardwareGovernorService
from runtime.hardware.adaptive_daemon import AdaptiveHardwareDaemon


def test_v492_full_adaptive_matrix():
    print("=============================================================", flush=True)
    print(" E-ZZIO V4.9.2 — Full Adaptive Matrix & Anti-Flapping Test", flush=True)
    print("=============================================================", flush=True)

    hw_dir = Path(__file__).resolve().parent
    governor = HardwareGovernorService(state_dir=str(hw_dir))
    adaptive = AdaptiveHardwareDaemon(governor, hysteresis_sec=0.5)

    passed_tests = 0
    total_tests = 4

    try:
        # --- TEST 1 : Simulation de Détection de Processus Lourd / Jeu ---
        print("\n--- TEST 1 : Bascule Automatique par Détection de Processus ---", flush=True)
        adaptive.gaming_targets.add("python.exe")  # Force la détection sur le process de test courant
        prof1 = adaptive.evaluate_system_state()
        print(f"[EVAL 1] Profil attribué : {prof1}", flush=True)

        assert prof1 == "GAMING", f"FAIL: Attendu GAMING sur détection process, obtenu {prof1}"
        assert governor.read_ipc_state().get("win32_priority") == "BELOW_NORMAL"
        passed_tests += 1
        print(f"[SUCCESS] Test 1 validé ({passed_tests}/{total_tests}).", flush=True)

        # --- TEST 2 : Effet Hystérésis & Anti-Flapping (Isolé de l'environnement hôte) ---
        print("\n--- TEST 2 : Validation de l'Hystérésis (Anti-Flapping) ---", flush=True)

        # Sauvegarde et suppression de toutes les cibles pour simuler un système au repos
        saved_targets = set(adaptive.gaming_targets)
        adaptive.gaming_targets.clear()

        # Appel immédiat avant l'expiration de la fenêtre d'hystérésis (0.5s)
        prof_hyst = adaptive.evaluate_system_state()
        print(f"[HYSTÉRÉSIS] Profil pendant fenêtre d'attente : {prof_hyst}", flush=True)
        assert prof_hyst == "GAMING", "FAIL: L'hystérésis n'a pas bloqué la bascule intempestive !"

        # Attente après expiration de la fenêtre d'hystérésis (0.7s > 0.5s)
        time.sleep(0.7)
        prof2 = adaptive.evaluate_system_state()
        print(f"[EVAL 2] Profil après hystérésis : {prof2}", flush=True)
        assert prof2 == "COMPUTE", f"FAIL: Attendu COMPUTE après hystérésis, obtenu {prof2}"

        # Restauration des cibles
        adaptive.gaming_targets = saved_targets
        passed_tests += 1
        print(f"[SUCCESS] Test 2 validé ({passed_tests}/{total_tests}).", flush=True)

        # --- TEST 3 : Validation du Rétro-contrôle Guardian (Mode Maintenance) ---
        print("\n--- TEST 3 : Contrôle de Maintenance par le Guardian ---", flush=True)
        governor.set_evolution_authorization(True)
        prof3 = governor.set_profile("EVOLUTION")
        print(f"[EVOLUTION APPROVED] Profil actif : {prof3.get('active_profile')}", flush=True)

        assert prof3.get("active_profile") == "EVOLUTION"
        assert prof3.get("win32_priority") == "HIGH"
        passed_tests += 1
        print(f"[SUCCESS] Test 3 validé ({passed_tests}/{total_tests}).", flush=True)

        # --- TEST 4 : Révocation du Mode Maintenance & Seuil de Récupération ---
        print("\n--- TEST 4 : Révocation de l'Autorisation & Fallback ---", flush=True)
        governor.set_evolution_authorization(False)
        prof4 = governor.set_profile("EVOLUTION")
        print(f"[EVOLUTION REVOKED] Profil de secours : {prof4.get('active_profile')}", flush=True)

        assert prof4.get("active_profile") == "COMPUTE"
        assert prof4.get("win32_priority") == "ABOVE_NORMAL"
        passed_tests += 1
        print(f"[SUCCESS] Test 4 validé ({passed_tests}/{total_tests}).", flush=True)

    finally:
        governor.stop()

    print("\n-------------------------------------------------------------", flush=True)
    print(f"RÉSULTAT : {passed_tests} / {total_tests} scénarios validés.", flush=True)

    if passed_tests == total_tests:
        print("=============================================================", flush=True)
        print(" STATUS : V4.9.2 FULL ADAPTIVE MATRIX CERTIFIÉE", flush=True)
        print("=============================================================", flush=True)
    else:
        raise RuntimeError(f"ÉCHEC CERTIFICATION V4.9.2 : {passed_tests}/{total_tests} scénarios validés.")


if __name__ == "__main__":
    test_v492_full_adaptive_matrix()

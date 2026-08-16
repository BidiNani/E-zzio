"""
E-ZZIO V7.39 — Certification Test Suite (Tool Gateway Foundation)
Valide l'interception, le routage et le blocage basé sur le risque des appels externes.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.tool_gateway.gateway_controller import tool_gateway

def run_gateway_certification():
    print("============================================================")
    print(" E-ZZIO V7.39 — TOOL GATEWAY FOUNDATION CERTIFICATION")
    print("============================================================\n")

    # [1/3] Outil inconnu (Rejet immédiat)
    res_unknown = tool_gateway.request_action("discord_delete_server", {}, "Supprimer le serveur")
    assert res_unknown["status"] == "REJECTED_UNKNOWN_TOOL", "Un outil inconnu n'a pas été bloqué !"
    print(" [1/3] Blocage outil non déclaré : OK")

    # [2/3] Outil à faible risque (Approbation auto)
    res_low = tool_gateway.request_action("google_drive_read", {"file_id": "123"}, "Lire le brief projet")
    assert res_low["status"] == "APPROVED_AUTO", "La lecture Drive (LOW RISK) a été bloquée !"
    print(f" [2/3] Routage outil Low Risk ({res_low['tool']}) : OK")

    # [3/3] Outil à haut risque (Mise en attente d'approbation)
    res_high = tool_gateway.request_action("gmail_send", {"to": "client@mail.com"}, "Envoyer un devis")
    assert res_high["status"] == "WAITING_APPROVAL", "L'envoi d'email (HIGH RISK) n'a pas été mis en attente !"
    assert res_high["risk_level"] == "HIGH", "Niveau de risque mal évalué !"
    print(f" [3/3] Interception outil High Risk ({res_high['tool']}) : OK (Statut: WAITING_APPROVAL)")

    print("\n============================================================")
    print(" V7.39 CERTIFIÉ : TOOL GATEWAY & SECURE ACTION LAYER ACTIFS")
    print("============================================================\n")

if __name__ == "__main__":
    run_gateway_certification()

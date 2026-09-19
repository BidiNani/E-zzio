import pytest
from v19.product.experience import product_experience_layer, UserMissionRequest

def test_v19_product_goal_orchestration():
    req = UserMissionRequest(
        user_goal="Analyser l'architecture et générer les preuves forensiques",
        channel="discord",
        session_id="sess_v19"
    )
    mission = product_experience_layer.submit_goal(req)
    assert mission.status == "COMPLETED"
    assert len(mission.subtasks) == 3
    for st in mission.subtasks:
        assert st.state.value == "COMPLETED"

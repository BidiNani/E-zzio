import uuid
from typing import Dict, Any, List
from pydantic import BaseModel
from v18.fabric.models import MissionRecord, SubtaskNode, SubtaskState
from v18.agents.coordinator import agent_coordinator

class UserMissionRequest(BaseModel):
    user_goal: str
    channel: str = "webui"
    session_id: str = "default_session"

class UnifiedProductExperience:
    def submit_goal(self, req: UserMissionRequest) -> MissionRecord:
        mid = f"mission_{uuid.uuid4().hex[:8]}"
        
        # Deconstruct goal into specialized subtasks
        st_plan = SubtaskNode(subtask_id=f"{mid}_1", parent_mission_id=mid, role="PLANNER", task_type="PLANNING")
        st_exec = SubtaskNode(subtask_id=f"{mid}_2", parent_mission_id=mid, role="CODER", task_type="CODE", dependencies=[f"{mid}_1"])
        st_verify = SubtaskNode(subtask_id=f"{mid}_3", parent_mission_id=mid, role="VERIFIER", task_type="VERIFICATION", dependencies=[f"{mid}_2"])

        mission = MissionRecord(
            mission_id=mid,
            title=req.user_goal,
            session_id=req.session_id,
            channel=req.channel,
            subtasks=[st_plan, st_exec, st_verify]
        )

        # Coordinate execution sequentially across subtasks
        for st in mission.subtasks:
            agent_coordinator.execute_subtask(st)

        mission.status = "COMPLETED"
        return mission

product_experience_layer = UnifiedProductExperience()

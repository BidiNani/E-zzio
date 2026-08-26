from .contracts import AgentPlan, AgentStep


class Planner:
    def create_plan(self, task):
        step = AgentStep(capability="sandbox.execute_python", parameters={"objective": task.objective})
        return AgentPlan(task_id=task.task_id, steps=[step])

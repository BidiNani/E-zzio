"""
E-ZZIO V9.3.3 — Budget Manager
Applique les règles HW-001 (GPU) et les limites RAM.
"""
class BudgetManager:
    def check_constraints(self, workflow_id: str, plan: dict) -> dict:
        # Simulation détection jeu actif
        wow_active = False 
        
        needed_ram = plan["total_memory_mb"]
        available_ram = 18000 # 18GB simulation
        
        if needed_ram > available_ram:
            return {"status": "DENIED", "reason": "RESOURCE_GOVERNOR: Insufficient RAM"}
            
        # HW-001 Vérification
        for step in plan["steps"]:
            if step.get("gpu_required") and wow_active:
                return {"status": "DENIED", "reason": "HW-001 PROTECTION: GPU Reserved by WoW"}
                
        return {"status": "ALLOWED"}

class RuntimeBuilder:
    def __init__(self):
        self.level = 0
    
    def with_allowed_level(self, level):
        self.level = level
        return self
        
    def build(self):
        return self

    def execute(self, request, session_id):
        return {"success": True, "output": "Kernel level 0 execution granted."}
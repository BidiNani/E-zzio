class BaseTalent:
    def __init__(self, name):
        self.name = name

    def run(self, data):
        raise NotImplementedError("Le talent doit implémenter la méthode run()")

from runtime.contracts.cognition_interface import CognitionInterface

class CognitionAdapter(CognitionInterface):

    def process(self,request):
        raise NotImplementedError("Runtime implementation required")

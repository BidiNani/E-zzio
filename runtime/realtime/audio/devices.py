import sounddevice as sd
from typing import List, Dict, Any

class HardwareManager:
    @staticmethod
    def get_devices() -> Dict[str, List[Dict[str, Any]]]:
        devices = sd.query_devices()
        inputs = [d for d in devices if d['max_input_channels'] > 0]
        outputs = [d for d in devices if d['max_output_channels'] > 0]
        return {"inputs": inputs, "outputs": outputs}
        
    @staticmethod
    def get_default_output() -> Dict[str, Any]:
        return sd.query_devices(kind='output')
        
    @staticmethod
    def get_default_input() -> Dict[str, Any]:
        return sd.query_devices(kind='input')

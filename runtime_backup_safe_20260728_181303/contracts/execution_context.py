from dataclasses import dataclass
from typing import Optional
from runtime.contracts.capability import CapabilityToken

@dataclass(frozen=True)
class ExecutionContext:

    @property
    def state(self):
        if not hasattr(self, '_state'):
            object.__setattr__(self, '_state', {})
        return self._state

    @state.setter
    def state(self, value):
        object.__setattr__(self, '_state', value)

    trace_id: str
    session_id: str
    token: Optional[CapabilityToken] = None

    @property
    def capability(self):
        """Bridge property for legacy components expecting context.capability"""
        return self.token

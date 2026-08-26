from dataclasses import dataclass


@dataclass(frozen=True)
class WorkloadRequest:
    workload_id: str
    profile: str
    estimated_cost: int = 1

    def __post_init__(self):
        # Validation stricte des profils autorisés au niveau du contrat
        valid_profiles = ["CRITICAL", "NORMAL", "BACKGROUND"]
        if self.profile not in valid_profiles:
            raise ValueError(f"REJECT_INVALID_REQUEST: Unknown profile '{self.profile}'")

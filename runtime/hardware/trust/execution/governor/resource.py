import psutil
from dataclasses import dataclass
from runtime.hardware.trust.execution.admission.models import AdmissionGrant

@dataclass(frozen=True)
class ResourceAllocation:
    workload_id: str
    allocated_cpus: list
    max_workers: int
    clamped: bool
    reason: str

class ResourceGovernor:
    @staticmethod
    def allocate(grant: AdmissionGrant, current_topology: dict) -> ResourceAllocation:
        """
        Traduit l'AdmissionGrant en une allocation physique stricte (CPU affinity mask).
        Applique un clamping autoritaire si les limites de la politique sont dépassées.
        """
        if grant.status != "ALLOW":
            return ResourceAllocation(
                workload_id=grant.workload_id,
                allocated_cpus=[],
                max_workers=0,
                clamped=False,
                reason="DENIED_GRANT_NO_RESOURCES_ALLOCATED"
            )

        max_system_threads = psutil.cpu_count(logical=True) or 1
        allowed_workers = grant.allowed_workers
        
        # Récupération des clusters topologiques depuis la cartographie si disponibles
        clusters = current_topology.get("clusters", {})
        ccd0 = clusters.get("CCD0", list(range(max_system_threads // 2)))
        
        # Détermination des cœurs alloués selon le quota autorisé
        # Par défaut, on alloue en priorité sur le CCD0 pour la localité cache, clampé au max autorisé
        target_pool = ccd0 if ccd0 else list(range(max_system_threads))
        
        clamped = False
        if allowed_workers < len(target_pool):
            allocated_cpus = target_pool[:allowed_workers]
            clamped = True
        else:
            allocated_cpus = target_pool[:min(allowed_workers, len(target_pool))]

        return ResourceAllocation(
            workload_id=grant.workload_id,
            allocated_cpus=allocated_cpus,
            max_workers=len(allocated_cpus),
            clamped=clamped,
            reason="RESOURCE_ALLOCATED_SUCCESSFULLY" if not clamped else "RESOURCE_CLAMPED_BY_POLICY"
        )

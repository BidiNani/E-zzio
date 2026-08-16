class AllocationIntegrityGate:
    @staticmethod
    def validate_allocation(affinity_mask, max_threads: int) -> bool:
        """Valide rigoureusement le masque d'affinité (Fail-Closed)."""
        if not isinstance(affinity_mask, list) or not affinity_mask:
            return False
        
        seen = set()
        for cpu in affinity_mask:
            # 1. Vérification du type (strictement entier, pas de booléens)
            if not isinstance(cpu, int) or isinstance(cpu, bool):
                return False
            # 2. Vérification des limites matérielles [0, max_threads - 1]
            if cpu < 0 or cpu >= max_threads:
                return False
            # 3. Absence de doublons
            if cpu in seen:
                return False
            seen.add(cpu)
            
        return True

    @staticmethod
    def validate_clusters(clusters: dict, max_threads: int) -> bool:
        """Valide la structure interne des clusters CCD."""
        if not isinstance(clusters, dict) or not clusters:
            return False
        
        for name, cpus in clusters.items():
            if not isinstance(cpus, list) or not cpus:
                return False
            if not AllocationIntegrityGate.validate_allocation(cpus, max_threads):
                return False
        return True

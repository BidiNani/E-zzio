"""
Audit robuste des routes E-ZZIO.
"""


def audit_routes(app_routes):
    seen = set()
    conflicts = []

    for route in app_routes:
        # Clé unique (path, method)
        key = (getattr(route, "path", "/"), getattr(route, "method", "GET"))
        if key in seen:
            conflicts.append(key)
        seen.add(key)
    return {"conflict_count": len(conflicts), "conflicts": conflicts}

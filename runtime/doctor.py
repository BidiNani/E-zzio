import sys
import importlib


def run_checks():
    print("=== E-ZZIO SYSTEM HEALTH DIAGNOSTIC ===")
    checks = {
        "Kernel": "runtime.kernel",
        "Crypto Contracts": "runtime.contracts.capability",
        "Tool Results": "runtime.contracts.tool_result",
        "Policy Engine": "runtime.policy.engine",
        "Security Guard": "runtime.security.guard",
        "Event Bus": "runtime.core.events",
        "Audit Logger": "runtime.audit.logger",
        "Microkernel Core": "runtime.core.microkernel",
    }

    success = True
    for name, mod_path in checks.items():
        try:
            importlib.import_module(mod_path)
            print(f"[{name:.<25}] .......... OK")
        except Exception as e:
            print(f"[{name:.<25}] .......... FAIL ({e})")
            success = False

    # Test d'intégrité cryptographique rapide
    try:
        from runtime.contracts.capability import CapabilityToken, TokenSigner

        signer = TokenSigner()
        token = CapabilityToken(subject="doctor-test", permissions=frozenset(["diag"]))
        sig = signer.sign(token)
        assert sig
        msg = "Crypto Execution"
        print(f"[{msg:.<25}] .......... OK")
    except Exception as e:
        msg = "Crypto Execution"
        print(f"[{msg:.<25}] .......... FAIL ({e})")
        success = False

    if success:
        print("\nArchitecture score: 100/100 - SYSTEM HEALTHY")
        sys.exit(0)
    else:
        print("\nArchitecture score: DEGRADED - INVARIANTS BROKEN")
        sys.exit(1)


if __name__ == "__main__":
    run_checks()

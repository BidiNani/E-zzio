from dataclasses import replace
from runtime.contracts.capability import CapabilityToken, TokenSigner
from runtime.policy.engine import PolicyEngine
from runtime.security.guard import SecurityGuard

def test_crypto_and_capability_flow():
    signer = TokenSigner()
    token = CapabilityToken(subject="test-agent", permissions=frozenset(["read", "execute"]))
    sig = signer.sign(token)
    signed_token = replace(token, signature=sig)
    
    assert signer.verify(signed_token) is True
    assert signed_token.allows("read") is True
    assert signed_token.allows("admin") is False
    print("[+] test_crypto_and_capability_flow PASSED")

def test_security_guard_bridge():
    guard = SecurityGuard()
    assert guard.check_permission("unknown-subject", "admin") is False
    print("[+] test_security_guard_bridge PASSED")

if __name__ == "__main__":
    test_crypto_and_capability_flow()
    test_security_guard_bridge()
    print("ALL ARCHITECTURAL INVARIANTS PASSED SUCCESSFULLY")

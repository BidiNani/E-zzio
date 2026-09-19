import pytest
from v17.sanitization.sanitizer import sanitize_data
from v17.events.buffer import EventBuffer

def test_v17_2_sanitizer_masks_secrets():
    payload = {
        "DISCORD_TOKEN": "123456789012345678.abcdef.123456789012345678901234567",
        "GEMINI_API_KEY": "AIzaSyD-123456789012345678901234567890",
        "normal_field": "safe_value",
        "nested": {"token_value": "sk-1234567890123456789012345"}
    }
    clean = sanitize_data(payload)
    assert clean["DISCORD_TOKEN"] == "[REDACTED]"
    assert clean["GEMINI_API_KEY"] == "[REDACTED]"
    assert clean["normal_field"] == "safe_value"
    assert clean["nested"]["token_value"] == "[REDACTED]"

def test_v17_2_events_adversarial_injection():
    buf = EventBuffer(max_size=10)
    evt = buf.publish("security.test", "audit", {"secret_key": "my_super_secret_value"})
    assert evt.payload["secret_key"] == "[REDACTED]"

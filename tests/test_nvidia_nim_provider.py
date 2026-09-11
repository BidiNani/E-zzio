"""
Tests unitaires et de qualification pour NvidiaNimProvider.
Vérifie le comportement fail-closed, le formatage des requêtes et l'intégrité des contrats.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from pathlib import Path
from core.providers.nvidia_nim_provider import NvidiaNimProvider
import pytest
pytestmark = pytest.mark.skip(reason="Provider NVIDIA désactivé par choix d architecture")


def test_nvidia_nim_provider_init_no_key():
    provider = NvidiaNimProvider(api_key="")
    assert not provider.is_available()


@pytest.mark.asyncio
async def test_nvidia_nim_provider_fail_closed():
    provider = NvidiaNimProvider(api_key="")
    with pytest.raises(RuntimeError) as exc_info:
        await provider.generate_text("Bonjour")
    assert "FAIL-CLOSED" in str(exc_info.value)


@pytest.mark.asyncio
async def test_nvidia_nim_provider_generate_text_mock():
    provider = NvidiaNimProvider(api_key="mock-nim-key-12345")
    assert provider.is_available()

    fake_response = {
        "id": "cmpl-test-01",
        "object": "chat.completion",
        "created": 1725000000,
        "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "NVIDIA_NIM_REAL_CALL_OK"
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 12,
            "completion_tokens": 8,
            "total_tokens": 20
        }
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fake_response
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        res = await provider.generate_text(
            prompt="Return exactly: NVIDIA_NIM_REAL_CALL_OK"
        )

        assert res["provider"] == "nvidia_nim"
        assert res["model"] == "nvidia/nemotron-3.5-lightning-30b-a3b"
        assert "NVIDIA_NIM_REAL_CALL_OK" in res["content"]
        assert res["usage"]["total_tokens"] == 20


@pytest.mark.asyncio
async def test_nvidia_nim_provider_analyze_image_mock(tmp_path):
    provider = NvidiaNimProvider(api_key="mock-nim-key-12345")

    # Create dummy PNG file
    fake_img = tmp_path / "test.png"
    fake_img.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")

    fake_vision_resp = {
        "id": "cmpl-vis-01",
        "object": "chat.completion",
        "created": 1725000000,
        "model": "meta/llama-3.2-11b-vision-instruct",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "The icon is a pixelated blue circle with a white center."
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 25,
            "completion_tokens": 12,
            "total_tokens": 37
        }
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fake_vision_resp
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        res = await provider.analyze_image(
            prompt="Describe this sprite",
            image_path=fake_img
        )

        assert res["provider"] == "nvidia_nim"
        assert res["model"] == "meta/llama-3.2-11b-vision-instruct"
        assert "pixelated" in res["content"]

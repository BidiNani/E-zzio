import sys
import asyncio
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.models.gemini_pool import GeminiPoolManager


async def main():
    print("=" * 64)
    print("E-ZZIO — GEMINI GENERATECONTENT MODEL MATRIX")
    print("=" * 64)

    pool = GeminiPoolManager()

    try:
        _, key, key_idx, project = pool.acquire_execution_target("general")
    except Exception as exc:
        print("POOL_FAIL =", type(exc).__name__, repr(exc))
        return

    print("KEY_INDEX =", key_idx)
    print("PROJECT   =", getattr(project, "project_id", "unknown"))
    print("KEY_OK    =", bool(key))

    models = [
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.7-flash",
    ]

    for model in models:
        url = (
            "https://generativelanguage.googleapis.com/"
            f"v1beta/models/{model}:generateContent"
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": "Réponds exactement : MODEL_MATRIX_OK"
                        }
                    ]
                }
            ]
        }

        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": key,
            },
            method="POST",
        )

        print("")
        print("-" * 64)
        print("MODEL =", model)

        started = time.perf_counter()

        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                body = response.read().decode("utf-8", errors="replace")
                elapsed = (time.perf_counter() - started) * 1000

                print("STATUS     =", response.status)
                print("ELAPSED_MS =", round(elapsed, 2))

                try:
                    parsed = json.loads(body)
                    candidates = parsed.get("candidates", [])

                    text = ""

                    if candidates:
                        parts = (
                            candidates[0]
                            .get("content", {})
                            .get("parts", [])
                        )

                        text = "".join(
                            str(part.get("text", ""))
                            for part in parts
                            if isinstance(part, dict)
                        ).strip()

                    print("TEXT       =", text)
                    print(
                        "RESULT     =",
                        "PASS" if text == "MODEL_MATRIX_OK" else "FAIL"
                    )

                except Exception as exc:
                    print("JSON_ERROR =", type(exc).__name__, repr(exc))

        except urllib.error.HTTPError as exc:
            elapsed = (time.perf_counter() - started) * 1000

            print("HTTP_STATUS =", exc.code)
            print("ELAPSED_MS  =", round(elapsed, 2))

            try:
                body = exc.read().decode("utf-8", errors="replace")
                print("BODY =", body[:2000])
            except Exception:
                print("BODY = <unavailable>")

        except Exception as exc:
            elapsed = (time.perf_counter() - started) * 1000

            print("ERROR_TYPE =", type(exc).__name__)
            print("ERROR_ARGS =", repr(exc.args))
            print("ERROR_STR  =", repr(str(exc)))
            print("ELAPSED_MS =", round(elapsed, 2))


if __name__ == "__main__":
    asyncio.run(main())
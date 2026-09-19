import asyncio
import json
import sys
import time
import traceback
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.models.gemini_pool import GeminiPoolManager


async def main():
    print("=" * 64)
    print("E-ZZIO — GEMINI RAW HTTP FORENSIC")
    print("=" * 64)

    pool = GeminiPoolManager()

    print("[1] ACQUIRE EXECUTION TARGET")
    try:
        model, key, key_idx, project = pool.acquire_execution_target("general")

        print("MODEL       =", model)
        print("KEY_INDEX   =", key_idx)
        print("PROJECT     =", getattr(project, "project_id", "unknown"))
        print("KEY_PRESENT =", bool(key))
    except Exception as exc:
        print("ACQUIRE = FAIL")
        print("TYPE =", type(exc).__name__)
        print("REPR =", repr(exc))
        traceback.print_exc()
        return

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{model}:generateContent"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": "Réponds exactement : GEMINI_RAW_HTTP_OK"
                    }
                ]
            }
        ]
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": key,
        },
        method="POST",
    )

    print("")
    print("[2] RAW HTTP REQUEST")
    print("URL         =", url)
    print("MODEL       =", model)
    print("TIMEOUT_SEC = 45")
    print("SECRET      = NOT PRINTED")

    started = time.perf_counter()

    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = response.read().decode("utf-8", errors="replace")
            elapsed = (time.perf_counter() - started) * 1000

            print("")
            print("[3] HTTP RESPONSE")
            print("STATUS      =", response.status)
            print("ELAPSED_MS  =", round(elapsed, 2))
            print("BODY_LENGTH =", len(raw))

            try:
                parsed = json.loads(raw)
                print("BODY_JSON   =")
                print(json.dumps(parsed, indent=2, ensure_ascii=False))

                text = ""
                candidates = parsed.get("candidates", [])

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

                print("")
                print("[4] VALIDATION")
                print("TEXT =", text)

                if response.status == 200 and text == "GEMINI_RAW_HTTP_OK":
                    print("GEMINI_RAW_HTTP = PASS")
                else:
                    print("GEMINI_RAW_HTTP = FAIL")

            except Exception as exc:
                print("JSON_PARSE_ERROR =", type(exc).__name__)
                print("JSON_PARSE_REPR  =", repr(exc))

    except urllib.error.HTTPError as exc:
        elapsed = (time.perf_counter() - started) * 1000

        print("")
        print("[3] HTTP ERROR")
        print("TYPE       =", type(exc).__name__)
        print("STATUS     =", exc.code)
        print("ELAPSED_MS =", round(elapsed, 2))

        try:
            body = exc.read().decode("utf-8", errors="replace")
            print("BODY       =")
            print(body)
        except Exception:
            print("BODY       = <unavailable>")

    except Exception as exc:
        elapsed = (time.perf_counter() - started) * 1000

        print("")
        print("[3] TRANSPORT ERROR")
        print("TYPE       =", type(exc).__name__)
        print("MODULE     =", type(exc).__module__)
        print("ARGS       =", repr(exc.args))
        print("STR        =", repr(str(exc)))
        print("ELAPSED_MS =", round(elapsed, 2))
        print("")
        print("TRACEBACK:")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

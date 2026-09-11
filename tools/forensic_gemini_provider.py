import sys
import asyncio
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.providers.gemini_provider import GeminiProvider
from core.models.gemini_pool import GeminiPoolManager


async def main():
    print("=" * 60)
    print("E-ZZIO — DIRECT GEMINI PROVIDER FORENSIC")
    print("=" * 60)
    print("ROOT =", ROOT)

    try:
        pool = GeminiPoolManager()
        print("POOL_INIT = PASS")
    except Exception as e:
        print("POOL_INIT = FAIL")
        print("POOL_INIT_ERROR =", repr(e))
        traceback.print_exc()
        return

    try:
        provider = GeminiProvider()
        print("PROVIDER_INIT = PASS")
    except Exception as e:
        print("PROVIDER_INIT = FAIL")
        print("PROVIDER_INIT_ERROR =", repr(e))
        traceback.print_exc()
        return

    print("")
    print("[POOL METHODS]")
    methods = [
        name for name in dir(pool)
        if not name.startswith("_")
    ]
    print(", ".join(methods))

    print("")
    print("[ACTIVE KEY TEST]")
    try:
        active_key = pool.get_active_key()
        print("ACTIVE_KEY_PRESENT =", active_key is not None)
        if active_key is not None:
            print("ACTIVE_KEY_TYPE =", type(active_key).__name__)
    except Exception as e:
        print("ACTIVE_KEY_ERROR =", repr(e))

    print("")
    print("[CANDIDATE MODELS]")
    try:
        candidates = pool.get_candidate_models("general")
        print("CANDIDATES =", candidates)
    except Exception as e:
        print("CANDIDATES_ERROR =", repr(e))
        traceback.print_exc()

    print("")
    print("[EXECUTION TARGET]")
    try:
        target = pool.acquire_execution_target("general")
        print("EXECUTION_TARGET =", target)
    except Exception as e:
        print("EXECUTION_TARGET_ERROR =", repr(e))
        traceback.print_exc()

    print("")
    print("[DIRECT PROVIDER SEARCH]")
    try:
        result = await provider.search(
            "Réponds exactement : GEMINI_PROVIDER_FORENSIC_OK",
            capability="general"
        )

        print("")
        print("RESULT_TYPE =", type(result).__name__)
        print("RESULT =")
        print(result)

    except Exception as e:
        print("")
        print("EXCEPTION_TYPE =", type(e).__name__)
        print("EXCEPTION_REPR =", repr(e))
        print("")
        print("TRACEBACK:")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
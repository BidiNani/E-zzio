import subprocess


def run(params: dict) -> dict:
    action = params.get("action", "status")
    repo_path = params.get("path", ".")

    if action not in ["status", "log", "diff"]:
        return {"success": False, "error": f"Action Git non supportée : {action}"}

    cmd = ["git", "-C", repo_path]
    if action == "status":
        cmd.extend(["status", "--porcelain"])
    elif action == "log":
        cmd.extend(["log", "-n", "5", "--oneline"])
    elif action == "diff":
        cmd.extend(["diff"])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=5)
        return {"success": True, "action": action, "output": result.stdout.strip().splitlines() if result.stdout else []}
    except subprocess.CalledProcessError as e:
        return {"success": False, "error": e.stderr.strip() or str(e)}
    except Exception as ex:
        return {"success": False, "error": str(ex)}

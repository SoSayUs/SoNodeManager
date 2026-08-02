#!/usr/bin/env python3
import sys, json, traceback
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent  # this is SoNodeManager/
sys.path.insert(0, str(PROJECT_ROOT))


def send_err(msg):
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()

def main():
    if len(sys.argv) < 3:
        send_err("ERR: usage: get_remote_commands <task> [extras_json]")
        return 1

    task   = sys.argv[1]

    if len(sys.argv) >= 3:
        try:
            extras = json.loads(sys.argv[2])
        except Exception as e:
            send_err("ERR: invalid extras_json: " + str(e))
            return 2
    else:
        extras = {}

    try:
        from commands.utils import get_commands
    except Exception:
        try:
            from .utils import get_commands
        except Exception as e:
            send_err(f"ERR: cannot import get_commands: {e}")
            send_err(traceback.format_exc())
            return 3

    try:
        commands, special_commands = get_commands(
            task=task,
            extras=extras
        )
    except Exception as e:
        send_err(f"ERR: get_commands() failed: {e}")
        send_err(traceback.format_exc())
        return 4
    
    cleaned_special = {}
    for name, spec in special_commands.items():
        cleaned = dict(spec)
        if "func" in cleaned:
            cleaned.pop("func")
        cleaned_special[name] = cleaned

    print("COMMANDS_JSON:" + json.dumps(commands))
    print("SPECIAL_CMDS_JSON:" + json.dumps(cleaned_special))
    return 0

if __name__ == "__main__":
    sys.exit(main())
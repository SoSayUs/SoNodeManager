
#!/usr/bin/env python3
import sys, json, traceback, base64
from pathlib import Path

# Ensure correct import path
# PROJECT_ROOT = Path(__file__).resolve().parent
# sys.path.insert(0, str(PROJECT_ROOT))
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent  # this is projectManager/
sys.path.insert(0, str(PROJECT_ROOT))

def send(msg):
    sys.stdout.write(str(msg) + "\n")
    sys.stdout.flush()

def send_err(msg):
    sys.stderr.write(str(msg) + "\n")
    sys.stderr.flush()

def main():
    print('start remote run command')
    if len(sys.argv) < 3:
        send_err("ERR: usage: run_special <task> <command> '<json_args>'")
        return 1

    # system     = sys.argv[1]
    task    = sys.argv[1]
    cmd_name   = sys.argv[2]
    print('received task',task,'received cmd_name',cmd_name)

    # Arg list is JSON encoded list or primitive
    try:
        # args = json.loads(sys.argv[3])
        args_b64 = sys.argv[3]
        args_json = base64.b64decode(args_b64.encode()).decode()
        args = json.loads(args_json)
        print('args',args)
    except Exception as e:
        send_err("ERR: invalid json args: " + str(e))
        return 2

    try:
        from commands.utils import get_commands
    except Exception:
        try:
            from .utils import get_commands
        except Exception as e:
            send_err("ERR: cannot import get_commands: " + str(e))
            send_err(traceback.format_exc())
            return 3

    try:
        commands, special_commands = get_commands(
            task=task,
        )
    except Exception as e:
        send_err("ERR: get_commands() failed: " + str(e))
        send_err(traceback.format_exc())
        return 4

    if cmd_name not in [cmd for cmd, data in special_commands.items()]:
        send_err(f"ERR: unknown special command: {cmd_name}")
        return 5

    spec  = special_commands[cmd_name]
    func  = spec.get('func')

    call_args = args if isinstance(args, list) else [args]

    try:
        result = func(remote_cmd=True, *call_args)
        if result is not None:
            send(result)

    except Exception as e:
        send_err("ERR: exception during function execution")
        send_err(traceback.format_exc())
        return 6

    send(f"REMOTE_COMMAND_DONE: {cmd_name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())





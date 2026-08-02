
import os
import sys
import platform
import subprocess
import threading

homepath     = os.path.expanduser("~")
SONET_DIR    = os.path.join(homepath, "Sonet")
APP_DIR      = os.path.join(SONET_DIR, "SoNodeManager")
DATA_DIR     = os.path.join(SONET_DIR, ".data")
VENV_DIR     = os.path.join(DATA_DIR, "nenv")
REQUIREMENTS = os.path.join(APP_DIR, "requirements.txt")
REPO_URL     = "https://github.com/SoSayUs/SoNodeManager.git"

if platform.system() == "Windows":
    VENV_PYTHON = os.path.join(VENV_DIR, "Scripts", "python.exe")
    VENV_PIP    = os.path.join(VENV_DIR, "Scripts", "pip.exe")
else:
    VENV_PYTHON = os.path.join(VENV_DIR, "bin", "python")
    VENV_PIP    = os.path.join(VENV_DIR, "bin", "pip")

def main():
    def _set(status, detail, pct):
        print(f"{status} {detail}")

    try:
        _set('Preparing…', 'Creating folder structure', 5)
        os.makedirs(SONET_DIR, exist_ok=True)
        os.makedirs(DATA_DIR,  exist_ok=True)
        os.makedirs(APP_DIR,   exist_ok=True)

        # Clone if missing
        marker = os.path.join(APP_DIR, 'main.py')
        if not os.path.exists(marker):
            _set('Fetching source code…', REPO_URL, 12)
            tmp = APP_DIR + '_clone_tmp'
            if os.path.exists(tmp):
                import shutil; shutil.rmtree(tmp)
            subprocess.run(['git', 'clone', '--depth=1', REPO_URL, tmp], check=True)
            import shutil
            for item in os.listdir(tmp):
                s = os.path.join(tmp, item)
                d = os.path.join(APP_DIR, item)
                if os.path.exists(d):
                    if os.path.isdir(d): shutil.rmtree(d)
                    else: os.remove(d)
                shutil.move(s, d)
            shutil.rmtree(tmp)
            _set('Source code ready.', '', 28)
        else:
            _set('Source code found.', APP_DIR, 28)

        if not os.path.exists(VENV_PYTHON):
            _set('Creating virtual environment…', VENV_DIR, 38)
            subprocess.run([sys.executable, '-m', 'venv', VENV_DIR], check=True)

            _set('Upgrading pip…', '', 50)
            subprocess.run(
                [VENV_PIP, 'install', '--upgrade', 'pip'],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            _set('Virtual environment ready.', '', 38)

        if os.path.exists(REQUIREMENTS):
            _set('Installing dependencies…', 'This will take a moment on first run', 60)
            subprocess.run([VENV_PIP, 'install', '-r', REQUIREMENTS], check=True)
            _set('Dependencies installed.', '', 88)
        else:
            _set('⚠  requirements.txt not found — skipping.', '', 88)

        # Re-launch inside venv
        _set('Launching SoNode…', '', 96)
        env = os.environ.copy()
        env['SONODE_NENV'] = '1'
        subprocess.Popen([VENV_PYTHON, __file__], env=env)

        _set('', '', 100)

    except subprocess.CalledProcessError as e:
        _set('Error during setup', str(e), 100)
    except Exception as e:
        _set('Unexpected error', str(e), 100)


if __name__ == '__main__':
    sys.exit(main())

import os
import subprocess
import getpass
from os.path import expanduser
import shutil

from ..utils import get_operatorData, get_node_list, write_operatorData
from .mac_install_cmds import config_nginx, setup_gunicorn, config_supervisor, write_supervisor_plist, setup_firewall, update_output, find_brew


username = getpass.getuser()
# print(username)
homepath = expanduser("~")
# print(homepath)
brew_path = find_brew()
uid = os.getuid()


operatorData = {}
Sonet_title = ''
external_ip = ''
node_data = {}
node_id = ''
port = ''
open_ports = ''
systemPass = ''
branch = 'main'

def get_variables(remote_cmd=False):
    global operatorData
    global Sonet_title
    global open_ports
    global port
    global external_ip
    global node_data
    global node_id
    global systemPass
    global branch

    if not operatorData:
        operatorData = get_operatorData()

        if 'local_nodeId' in operatorData:
            node_id = operatorData['local_nodeId']
            node_data = operatorData['myNodes'][operatorData['local_nodeId']]
            external_ip = node_data['settings']['external_ip']
            port = node_data['settings']['port']
        else:
            node_data = None
            for node in operatorData['myNodes']:
                if 'new_install-' in node:
                    if operatorData['myNodes'][node]['location'] == 'local':
                        node_data = operatorData['myNodes'][node]
                        node_id = node
                        break
            if node_data:
                external_ip = node_data['settings']['external_ip']
                port = node_data['settings']['port']
                open_ports = node_data['settings']['open_ports']
        
        from commands.utils import fetch_secure_item
        systemPass = fetch_secure_item('sysPass')
        if not systemPass and 'systemPass' in operatorData:
            systemPass = operatorData['systemPass']

        try:
            Sonet_title = operatorData['Sonet']['title']
        except:
            Sonet_title = 'SoNode'

        if 'sonet' in operatorData:
            repo_data = operatorData['sonet']['repo']
        elif 'new_sonet' in operatorData:
            repo_data = operatorData['new_sonet']['repo']

        branch = repo_data['branch'] # main

def hardware_check(output=None, remote_cmd=False):
    get_variables()
    global node_data
    global operatorData
    global node_id
    from commands.utils import run_hardware_test
    result, node_data = run_hardware_test(output=output, node_data=node_data, operatorData=operatorData)
    if not result:
        raise Exception('Failed hardware check')
    else:
        print('node_id',node_id)
        print('node_data:::',node_data)
        operatorData['myNodes'][node_id] = node_data
        write_operatorData(operatorData)

def update_repo(output=None, remote_cmd=False):
    get_variables()
    global branch
    global operatorData
    from commands.utils import pull_git_server
    pull_git_server(output=output, operatorData=operatorData)
    # commands = [
    #     [shutil.which("git"), '-C', homepath + "/Sonet/SoNodeServer", "reset", "--hard", f"sonodeserver/{branch}"],
    #     [shutil.which("git"), '-C', homepath + "/Sonet/SoNodeServer", "fetch", "sonodeserver"],
    #     [shutil.which("git"), '-C', homepath + "/Sonet/SoNodeServer", "reset", "--hard", f"sonodeserver/{branch}"],
    # ]
    # for cmd in commands:
    #     update_output(cmd, output)
    #     try:
    #         r = subprocess.run(
    #             cmd,
    #             check=True,
    #             input=f"{systemPass}\n".encode(),
    #         )
    #         print('r',r)
    #     except subprocess.CalledProcessError as e:
    #         error_msg = e.stderr.decode().strip() if e.stderr else "No stderr output"
    #         print('error_msg',error_msg)
    #         update_output(f"Command failed:\n{error_msg}", output)
        
def run_adjust_settings(output=None, remote_cmd=False):
    from commands.utils import adjust_settings
    get_variables()
    global node_data
    adjust_settings(node_data=node_data, clear_data=False)

def run_config_nginx(output=None, remote_cmd=False):
    get_variables()
    global node_data
    config_nginx(install=False, output=output, nodeData=node_data, remote_cmd=remote_cmd)

def run_setup_gunicorn(output=None, remote_cmd=False):
    get_variables()
    global node_data
    setup_gunicorn(install=False, output=output, nodeData=node_data, remote_cmd=remote_cmd)

def run_config_supervisor(output=None, remote_cmd=False):
    get_variables()
    global node_data
    config_supervisor(install=False, output=output, nodeData=node_data, remote_cmd=remote_cmd)

def run_write_supervisor_plist(output=None, remote_cmd=False):
    get_variables()
    global node_data
    write_supervisor_plist(install=False, output=output, nodeData=node_data, remote_cmd=remote_cmd)

def run_setup_firewall(output=None, remote_cmd=False):
    get_variables()
    global node_data
    setup_firewall(open_port=True, output=output, nodeData=node_data, remote_cmd=remote_cmd)

def activate_cloudflare_service(output=None, remote_cmd=False):
    print('-run_activate_cloudflare')
    from pathlib import Path
    get_variables()
    global operatorData
    global node_data

    tunnel_name = node_data['nodeData']['id']
    proceed = False
    new_address = None
    if tunnel_name in node_data['settings']['address'] or 'cloudflare tunnel' in node_data['settings']['address'].lower():
        if 'cloudflare tunnel' in node_data['settings']['address'].lower():
            if 'domain' in node_data['meta']:
                domain = node_data['meta']['domain']
                new_address = f'{tunnel_name}.{domain}'
                proceed = True
        else:
            proceed = True

        if proceed:
            update_output('run_activate_cloudflare', output)

            config_path = Path.home() / "Sonet" / ".data" / "cloudflare_registration" / "config.yml"
            if not config_path.exists():
                import zipfile
                from io import BytesIO
                from commands.utils import connect_to_node

                update_output('fetch_cloudflare_bundle', output)

                dest = Path.home() / "Sonet" / ".data" / "cloudflare_registration"
                dest.mkdir(parents=True, exist_ok=True)

                response_nodes = {}
                nodes = get_node_list(operatorData=operatorData, target={'category':'abilities', 'sub_cat':'cloudflare'}, exclude_relays=False, exclude_self=False)

                def fetch_zip(nodes):
                    for iden, address in nodes.items():
                        # print('--for address', address, nodes)
                        url = f"{address}/utils/fetch_cloudflare_bundle/{tunnel_name}"
                        print(f"Downloading bundle from {url}")
                        import json
                        data = {'nodeData':json.dumps(node_data['nodeData'])}
                        data['userData'] = json.dumps(operatorData['userData'])
                        data['upkData'] = json.dumps(operatorData['upkData'])
                        
                        response = connect_to_node(address, f"utils/fetch_cloudflare_bundle/{tunnel_name}", data=data, operatorData=operatorData, node_setup=True, timeout=30)

                        if response:
                            content_type = response.headers.get("Content-Type", "").lower()
                            content_disp = response.headers.get("Content-Disposition", "")

                            if "application/zip" in content_type:
                                print("It's a ZIP file")

                                with zipfile.ZipFile(BytesIO(response.content)) as zip_ref:
                                    zip_ref.extractall(dest)

                                print(f"Bundle installed to: {dest}")
                                return True

                            elif "application/json" in content_type:
                                print("It's JSON")
                                r_json = response.json()
                                if 'message' in r_json and r_json['message'] == 'wrong_node':
                                    if 'correct_nodes' in r_json and r_json['correct_nodes']:
                                        correct_nodes = json.loads(r_json['correct_nodes'])
                                        for key, value in correct_nodes.items():
                                            response_nodes[key] = value
                    return False
                
                if not fetch_zip(nodes) and response_nodes:
                    fetch_zip(response_nodes)


            if config_path.exists():
                print('config_path exists', config_path)
                SERVICE_NAME = f"com.cloudflared.{tunnel_name}"
                PLIST_PATH = Path.home() / "Library/LaunchAgents" / f"{SERVICE_NAME}.plist"
                USER = os.getenv("USER")
                config_file = f"/Users/{USER}/Sonet/.data/cloudflare_registration/config.yml"
                working_dir = f"/Users/{USER}/Sonet/.data/cloudflare_registration"
                # cloudflared_path = shutil.which("cloudflared")
                cloudflared_path = '/opt/homebrew/bin/cloudflared'

                if not PLIST_PATH.exists():
                    update_output(f'creating {SERVICE_NAME}.plist', output)

                    PLIST_CONTENT = f"""<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
        "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
        <plist version="1.0">
        <dict>
            <key>Label</key>
            <string>{SERVICE_NAME}</string>

            <key>ProgramArguments</key>
            <array>
            <string>{cloudflared_path}</string>
            <string>--config</string>
            <string>{config_file}</string>
            <string>tunnel</string>
            <string>run</string>
            <string>{tunnel_name}</string>
            </array>

            <key>WorkingDirectory</key>
            <string>{working_dir}</string>

            <key>RunAtLoad</key>
            <true/>

            <key>KeepAlive</key>
            <true/>
        </dict>
        </plist>
        """

                    PLIST_PATH.write_text(PLIST_CONTENT)
                    print(f"Created launchd service: {PLIST_PATH}")

                update_output('activate_cloudflare_service', output)

                if new_address:
                    node_data['settings']['address'] = new_address
                    operatorData['myNodes'][node_data['nodeData']['id']] = node_data
                    from commands.utils import write_operatorData
                    write_operatorData(operatorData)

                subprocess.run(["launchctl", "unload", str(PLIST_PATH)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                subprocess.run(["launchctl", "load", str(PLIST_PATH)], check=True)

                print(f"Enabled and started: {SERVICE_NAME}")
                update_output(f"Enabled and started: {SERVICE_NAME}", output)

            else:
                update_output(f"config.yml not found. Tunnel not created.", output)
                raise Exception('Tunnel not created')

def setup_llm(output=None, remote_cmd=False, systemPass=None):
    print('-setup_llm')
    import sys
    import urllib.request
    from pathlib import Path
    print('p1')
    def ensure_xcode_clt(sudo_password=None) -> bool:
        print('-ensure_xcode_clt')
        """
        Check for Xcode Command Line Tools (needed for the C/C++ compiler and
        macOS SDK headers that the Metal build requires). Installs them
        automatically if missing.

        This is the ONE step in the whole setup that can require sudo --
        `softwareupdate -i` needs elevated privileges to install CLT headlessly.
        (Plain `xcode-select --install` only pops a GUI dialog, which can't be
        driven from a script, so we go through `softwareupdate` instead.)

        If CLT is already installed, this is a no-op and sudo_password is
        never touched. If CLT is missing and no sudo_password is provided,
        raises RuntimeError rather than silently prompting.
        """
        check = subprocess.run(
            ["xcode-select", "-p"], capture_output=True, text=True
        )
        if check.returncode == 0:
            print(f"Xcode Command Line Tools already installed at {check.stdout.strip()}.")
            return True

        print("Xcode Command Line Tools not found. Installing (requires sudo)...")
        if not sudo_password:
            raise RuntimeError(
                "Xcode Command Line Tools are missing and no sudo_password was "
                "provided to run_setup(). Pass sudo_password='...' or install "
                "manually with: xcode-select --install"
            )

        marker = Path("/tmp/.com.apple.dt.CommandLineTools.installondemand.in-progress")
        marker.touch()
        try:
            listing = subprocess.run(
                ["softwareupdate", "-l"], capture_output=True, text=True, check=True
            )
            product_lines = [
                line.strip().lstrip("* ").strip()
                for line in listing.stdout.splitlines()
                if "Command Line Tools" in line and line.strip().startswith("*")
            ]
            if not product_lines:
                raise RuntimeError(
                    "softwareupdate didn't list a Command Line Tools package. "
                    "Install manually with: xcode-select --install"
                )
            product_name = product_lines[-1]
            print(f"Installing: {product_name}")

            install = subprocess.run(
                ["sudo", "-S", "softwareupdate", "-i", product_name, "--verbose"],
                input=sudo_password + "\n",
                text=True,
                capture_output=True,
            )
            if install.returncode != 0:
                raise RuntimeError(
                    f"CLT install failed:\n{install.stdout}\n{install.stderr}"
                )
            print("Xcode Command Line Tools installed.")
        finally:
            if marker.exists():
                marker.unlink()

        return True
    print('p1b')

    def run_setup(
            venv_dir: str = "~/Sonet/.data/env",
            model_dir: str = "~/Sonet/.data/models",
            model_url: str = (
                "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/"
                "resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
            ),
            force_reinstall: bool = False,
            sudo_password=None,
        ) -> dict:
        print('-run_setup')
        """
        Fully automated setup: ensures Xcode Command Line Tools are present,
        creates a venv (if it doesn't already exist), builds llama-cpp-python
        with Metal support, and downloads a default GGUF model if one isn't
        present.

        sudo is ONLY used for installing Xcode Command Line Tools, and only if
        they're not already present. Everything else -- venv creation, pip
        install, model download -- is user-space and never touches sudo.
        Pass sudo_password="..." if CLT might not be installed yet; if CLT is
        already present, sudo_password is never used.

        Returns a dict with resolved paths: venv_dir, python_bin, model_path.
        """
        ensure_xcode_clt(sudo_password=sudo_password)

        venv_path = Path(venv_dir).expanduser()
        model_path_dir = Path(model_dir).expanduser()
        model_path_dir.mkdir(parents=True, exist_ok=True)

        venv_python = venv_path / "bin" / "python"
        venv_pip = venv_path / "bin" / "pip"

        # 1. Create venv only if it doesn't already have a python binary
        #    (your pyenv-managed venv at ~/Sonet/.data/env is reused as-is)
        if not venv_python.exists():
            print(f"Creating venv at {venv_path}...")
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
        else:
            print(f"venv already exists at {venv_path}, reusing it.")

        # 2. Install/build llama-cpp-python with Metal acceleration
        print("Installing llama-cpp-python with Metal support (this can take a few minutes)...")
        env = os.environ.copy()
        env["CMAKE_ARGS"] = "-DGGML_METAL=on"

        pip_cmd = [str(venv_pip), "install", "--no-cache-dir"]
        if force_reinstall:
            pip_cmd.append("--force-reinstall")
        pip_cmd.append("llama-cpp-python")

        subprocess.run(pip_cmd, check=True, env=env)

        # 3. Download the model if not already present
        model_filename = model_url.split("/")[-1]
        model_path = model_path_dir / model_filename

        if not model_path.exists():
            print(f"Downloading model to {model_path}...")
            update_output(f'Downloading model to {model_path}...', output)
            _download_with_progress(model_url, model_path)
        else:
            print(f"Model already present at {model_path}, skipping download.")

        print("Setup complete.")
        return {
            "venv_dir": str(venv_path),
            "python_bin": str(venv_python),
            "model_path": str(model_path),
        }
    print('p1c')

    def _download_with_progress(url: str, dest: Path, output=None) -> None:
        def _report(block_num, block_size, total_size):
            if total_size > 0:
                downloaded = block_num * block_size
                pct = min(downloaded / total_size * 100, 100)
                print(f"\r  {pct:5.1f}%", end="", flush=True)
                update_output(f"\r  {pct:5.1f}%", output, replace=True)
        

        urllib.request.urlretrieve(url, dest, reporthook=_report)
        print()  # newline after progress
        update_output('Download complete', output, replace=True)
    print('p1d')

    # Uses ~/Sonet/.data/env by default -- pass venv_dir="..." to override.
    paths = run_setup(sudo_password=systemPass, model_url="https://huggingface.co/bartowski/Qwen2.5-7B-Instruct-1M-GGUF/resolve/main/Qwen2.5-7B-Instruct-1M-Q5_K_M.gguf?download=true")
    print(f"\nvenv python: {paths['python_bin']}")
    print(f"model path:  {paths['model_path']}")
    print(
        "\nNote: run queries using the venv's Python interpreter, e.g.:\n"
        f"  {paths['python_bin']} -c \"from llama_setup import query_llama; "
        f"print(query_llama('hi', model_path='{paths['model_path']}'))\""
    )

def setup_llm3(output=None, remote_cmd=False, systemPass=None):
    """
    Automated setup + query for llama.cpp (via llama-cpp-python) on macOS with Metal acceleration.

    Usage:
        from llama_setup import run_setup, query_llama

        paths = run_setup()
        answer = query_llama("Hello, how are you?", model_path=paths["model_path"])
    """

    import os
    import subprocess
    import sys
    import urllib.request
    from pathlib import Path


    def ensure_xcode_clt(sudo_password: str | None = None) -> bool:
        """
        Check for Xcode Command Line Tools (needed for the C/C++ compiler and
        macOS SDK headers that the Metal build requires). Installs them
        automatically if missing.

        This is the ONE step in the whole setup that can require sudo --
        `softwareupdate -i` needs elevated privileges to install CLT headlessly.
        (Plain `xcode-select --install` only pops a GUI dialog, which can't be
        driven from a script, so we go through `softwareupdate` instead.)

        If CLT is already installed, this is a no-op and sudo_password is
        never touched. If CLT is missing and no sudo_password is provided,
        raises RuntimeError rather than silently prompting.
        """
        check = subprocess.run(
            ["xcode-select", "-p"], capture_output=True, text=True
        )
        if check.returncode == 0:
            print(f"Xcode Command Line Tools already installed at {check.stdout.strip()}.")
            return True

        print("Xcode Command Line Tools not found. Installing (requires sudo)...")
        if not sudo_password:
            raise RuntimeError(
                "Xcode Command Line Tools are missing and no sudo_password was "
                "provided to run_setup(). Pass sudo_password='...' or install "
                "manually with: xcode-select --install"
            )

        marker = Path("/tmp/.com.apple.dt.CommandLineTools.installondemand.in-progress")
        marker.touch()
        try:
            listing = subprocess.run(
                ["softwareupdate", "-l"], capture_output=True, text=True, check=True
            )
            product_lines = [
                line.strip().lstrip("* ").strip()
                for line in listing.stdout.splitlines()
                if "Command Line Tools" in line and line.strip().startswith("*")
            ]
            if not product_lines:
                raise RuntimeError(
                    "softwareupdate didn't list a Command Line Tools package. "
                    "Install manually with: xcode-select --install"
                )
            product_name = product_lines[-1]
            print(f"Installing: {product_name}")

            install = subprocess.run(
                ["sudo", "-S", "softwareupdate", "-i", product_name, "--verbose"],
                input=sudo_password + "\n",
                text=True,
                capture_output=True,
            )
            if install.returncode != 0:
                raise RuntimeError(
                    f"CLT install failed:\n{install.stdout}\n{install.stderr}"
                )
            print("Xcode Command Line Tools installed.")
        finally:
            if marker.exists():
                marker.unlink()

        return True


    def run_setup(
        venv_dir: str = "~/Sonet/.data/env",
        model_dir: str = "~/models",
        model_url: str = (
            "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/"
            "resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
        ),
        force_reinstall: bool = False,
        sudo_password: str | None = None,
    ) -> dict:
        """
        Fully automated setup: ensures Xcode Command Line Tools are present,
        creates a venv (if it doesn't already exist), builds llama-cpp-python
        with Metal support, and downloads a default GGUF model if one isn't
        present.

        sudo is ONLY used for installing Xcode Command Line Tools, and only if
        they're not already present. Everything else -- venv creation, pip
        install, model download -- is user-space and never touches sudo.
        Pass sudo_password="..." if CLT might not be installed yet; if CLT is
        already present, sudo_password is never used.

        Returns a dict with resolved paths: venv_dir, python_bin, model_path.
        """
        ensure_xcode_clt(sudo_password=sudo_password)

        venv_path = Path(venv_dir).expanduser()
        model_path_dir = Path(model_dir).expanduser()
        model_path_dir.mkdir(parents=True, exist_ok=True)

        venv_python = venv_path / "bin" / "python"
        venv_pip = venv_path / "bin" / "pip"

        # 1. Create venv only if it doesn't already have a python binary
        #    (your pyenv-managed venv at ~/Sonet/.data/env is reused as-is)
        if not venv_python.exists():
            print(f"Creating venv at {venv_path}...")
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
        else:
            print(f"venv already exists at {venv_path}, reusing it.")

        # 2. Install/build llama-cpp-python with Metal acceleration
        print("Installing llama-cpp-python with Metal support (this can take a few minutes)...")
        env = os.environ.copy()
        env["CMAKE_ARGS"] = "-DGGML_METAL=on"

        pip_cmd = [str(venv_pip), "install", "--no-cache-dir"]
        if force_reinstall:
            pip_cmd.append("--force-reinstall")
        pip_cmd.append("llama-cpp-python")

        subprocess.run(pip_cmd, check=True, env=env)

        # 3. Download the model if not already present
        model_filename = model_url.split("/")[-1]
        model_path = model_path_dir / model_filename

        if not model_path.exists():
            print(f"Downloading model to {model_path}...")
            update_output(f'Downloading model to {model_path}...', output)
            _download_with_progress(model_url, model_path, output=output)
        else:
            print(f"Model already present at {model_path}, skipping download.")

        print("Setup complete.")
        return {
            "venv_dir": str(venv_path),
            "python_bin": str(venv_python),
            "model_path": str(model_path),
        }


    def _download_with_progress(url: str, dest: Path, output=None) -> None:
        def _report(block_num, block_size, total_size):
            if total_size > 0:
                downloaded = block_num * block_size
                pct = min(downloaded / total_size * 100, 100)
                print(f"\r  {pct:5.1f}%", end="", flush=True)
                update_output(f"\r  {pct:5.1f}%", output, replace=True)
                

        urllib.request.urlretrieve(url, dest, reporthook=_report)
        print()  # newline after progress
        update_output('Download complete', output, replace=True)

    def query_llama(
        prompt: str,
        model_path: str,
        n_ctx: int = 4096,
        n_gpu_layers: int = -1,
        max_tokens: int = 512,
    ) -> str:
        """
        Run a single query against the given GGUF model.
        Must be called from within the venv created by run_setup()
        (i.e. run this script with the venv's python, or install
        llama-cpp-python into your current interpreter).
        n_gpu_layers=-1 offloads all layers to Metal GPU.
        """
        from llama_cpp import Llama  # imported here so run_setup() works before install

        llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            verbose=False,
        )
        output = llm.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return output["choices"][0]["message"]["content"]


    # if __name__ == "__main__":
    # Uses ~/Sonet/.data/env by default -- pass venv_dir="..." to override.
    paths = run_setup(sudo_password=systemPass)
    print(f"\nvenv python: {paths['python_bin']}")
    print(f"model path:  {paths['model_path']}")
    print(
        "\nNote: run queries using the venv's Python interpreter, e.g.:\n"
        f"  {paths['python_bin']} -c \"from llama_setup import query_llama; "
        f"print(query_llama('hi', model_path='{paths['model_path']}'))\""
    )

def setup_llm_old(output=None, remote_cmd=False):
    import sys
    import urllib.request
    from pathlib import Path

    def install_cpp(
        venv_dir: str = "~/.venvs/llama",
        model_dir: str = "~/models",
        model_url: str = (
            "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/"
            "resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
        ),
        force_reinstall: bool = False,
    ) -> dict:
        """
        Fully automated setup: creates a venv, builds llama-cpp-python with Metal
        support, and downloads a default GGUF model if one isn't present.

        Returns a dict with resolved paths: venv_dir, python_bin, model_path.
        """
        venv_path = Path(venv_dir).expanduser()
        model_path_dir = Path(model_dir).expanduser()
        model_path_dir.mkdir(parents=True, exist_ok=True)

        # 1. Create venv if it doesn't exist
        if not venv_path.exists():
            print(f"Creating venv at {venv_path}...")
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
        else:
            print(f"venv already exists at {venv_path}, reusing it.")

        venv_python = venv_path / "bin" / "python"
        venv_pip = venv_path / "bin" / "pip"

        # 2. Install/build llama-cpp-python with Metal acceleration
        print("Installing llama-cpp-python with Metal support (this can take a few minutes)...")
        env = os.environ.copy()
        env["CMAKE_ARGS"] = "-DGGML_METAL=on"

        pip_cmd = [str(venv_pip), "install", "--no-cache-dir"]
        if force_reinstall:
            pip_cmd.append("--force-reinstall")
        pip_cmd.append("llama-cpp-python")

        subprocess.run(pip_cmd, check=True, env=env)

        # 3. Download the model if not already present
        model_filename = model_url.split("/")[-1]
        model_path = model_path_dir / model_filename

        if not model_path.exists():
            print(f"Downloading model to {model_path}...")
            update_output(f'Downloading model to {model_path}...', output)
            _download_with_progress(model_url, model_path, output=output)
        else:
            print(f"Model already present at {model_path}, skipping download.")

        print("Setup complete.")
        return {
            "venv_dir": str(venv_path),
            "python_bin": str(venv_python),
            "model_path": str(model_path),
        }


    def _download_with_progress(url: str, dest: Path, output=None) -> None:
        def _report(block_num, block_size, total_size):
            if total_size > 0:
                downloaded = block_num * block_size
                pct = min(downloaded / total_size * 100, 100)
                print(f"\r  {pct:5.1f}%", end="", flush=True)
                update_output(f"\r  {pct:5.1f}%", output, replace=True)
                

        urllib.request.urlretrieve(url, dest, reporthook=_report)
        print()  # newline after progress


    def query_llama(
        prompt: str,
        model_path: str,
        n_ctx: int = 4096,
        n_gpu_layers: int = -1,
        max_tokens: int = 512,
    ) -> str:
        """
        Run a single query against the given GGUF model.
        Must be called from within the venv created by run_setup()
        (i.e. run this script with the venv's python, or install
        llama-cpp-python into your current interpreter).
        n_gpu_layers=-1 offloads all layers to Metal GPU.
        """
        from llama_cpp import Llama  # imported here so run_setup() works before install

        llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            verbose=False,
        )
        output = llm.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return output["choices"][0]["message"]["content"]

    paths = install_cpp(
        model_url="https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-1M-GGUF/resolve/main/qwen2.5-7b-instruct-1m-q5_k_m.gguf"
    )
    # paths = install_cpp()
    print(f"\nvenv python: {paths['python_bin']}")
    print(f"model path:  {paths['model_path']}")
    print(
        "\nNote: run queries using the venv's Python interpreter, e.g.:\n"
        f"  {paths['python_bin']} -c \"from llama_setup import query_llama; "
        f"print(query_llama('hi', model_path='{paths['model_path']}'))\""
    )

def intelligence_check(output=None, remote_cmd=False):
    get_variables()
    global node_data
    global systemPass
    if node_data['settings']['node_type'].lower() == 'intelligence':
        update_output('Setting up LLM...', output)
        setup_llm(output=output, remote_cmd=remote_cmd, systemPass=systemPass)
        update_output('Done setting up LLM', output)

def declare_active(output=None, remote_cmd=False):
    from commands.utils import declare_self_active
    return declare_self_active(True, output=output, wait_for_reload=False, broadcast_to_network=True, remote_cmd=remote_cmd)
    
def force_active(output=None, remote_cmd=False):
    from commands.utils import declare_self_active
    return declare_self_active(True, output=output, wait_for_reload=False, broadcast_to_network=True, just_activate_me=True, remote_cmd=remote_cmd)
    
def declare_active_no_broadcast(output=None, remote_cmd=False):
    from commands.utils import declare_self_active
    return declare_self_active(True, output=output, wait_for_reload=False, broadcast_to_network=False, remote_cmd=remote_cmd)
    
def force_active_no_broadcast(output=None, remote_cmd=False):
    from commands.utils import declare_self_active
    return declare_self_active(True, output=output, wait_for_reload=False, broadcast_to_network=False, just_activate_me=True, remote_cmd=remote_cmd)

def pause(remote_cmd=False):
    print('pausing')
    import time
    time.sleep(5)


remove_for_tasker = [
    ["sudo", "-S", f"/Users/{username}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "crontab", "add"],
]

special_commands = [
    {'cmd':'hardware_check', 'reqs':'output_display'},
    {'cmd':'update_repo', 'reqs':'output_display'},
    {'cmd':'run_adjust_settings'},
    {'cmd':'run_setup_firewall'},
    {'cmd':'get_variables'},
    {'cmd':'run_config_nginx', 'reqs':'output_display'},
    {'cmd':'run_setup_gunicorn', 'reqs':'output_display'},
    {'cmd':'run_config_supervisor', 'reqs':'output_display'},
    {'cmd':'run_write_supervisor_plist', 'reqs':'output_display'},
    {'cmd':'activate_cloudflare_service', 'reqs':'output_display'},
    {'cmd':'intelligence_check', 'reqs':'output_display'},
    {'cmd':'pause'},
    {'cmd':'declare_active', 'reqs':'output_display'},
    {'cmd':'force_active', 'reqs':'output_display'},
    {'cmd':'declare_active_no_broadcast', 'reqs':'output_display'},
    {'cmd':'force_active_no_broadcast', 'reqs':'output_display'},
]

action_cmds = [

    ["sudo", "-S", "echo", "activating"],
    ['run_command', 'get_variables'],
    ['run_command', 'update_repo'],
    ['run_command', 'hardware_check'],

    # ['run_command', 'run_setup_firewall'],

    ['sudo', '-S', 'pkill', '-f', 'supervisord'],
    ['sudo', '-S', 'pkill', '-f', 'rqworker'],
    ['sudo', '-S', 'pkill', '-f', 'gunicorn'],
    ['/bin/sleep', '2'],  # give them time to die
    ['sudo', '-S', 'rm', '-f', f'/Users/{username}/Sonet/.data/supervisor/supervisor.sock'],
    ['run_command', 'activate_cloudflare_service'],
    ['run_command', 'run_adjust_settings'],
    ['run_command', 'run_config_nginx'],
    # ['sudo', '-S', 'nginx', '-t'],
    ['sudo', '-S', '/opt/homebrew/bin/nginx', '-t'],
    ['run_command', 'run_setup_gunicorn'],
    ['run_command', 'run_config_supervisor'],
    [brew_path, 'services', 'stop', 'postgresql'],
    [brew_path, 'services', 'cleanup'],
    [brew_path, 'services', 'start', 'postgresql'],
    ["sudo", "-S", f"{homepath}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "migrate"],
    ["raise_if_error", f"{homepath}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "check"],
    ["raise_if_error", "sudo", "-S", f"{homepath}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "collectstatic", "--noinput"],
    ['sudo', '-S', 'chown', '-R', f'{username}:staff', f'/Users/{username}/Sonet/.data/logs'],
    ['sudo', '-S', 'chown', '-R', f'{username}:staff', f'/Users/{username}/Sonet/.data/supervisor'],
    ['/opt/homebrew/bin/supervisord', '-c', f'/Users/{username}/Sonet/.data/supervisor/supervisord.conf'],
    ['sudo', '-S', '/opt/homebrew/bin/supervisorctl', '-c', f'/Users/{username}/Sonet/.data/supervisor/supervisord.conf', 'reread'],
    ['sudo', '-S', '/opt/homebrew/bin/supervisorctl', '-c', f'/Users/{username}/Sonet/.data/supervisor/supervisord.conf', 'update'],
    ['sudo', '-S', '/opt/homebrew/bin/supervisorctl', '-c', f'/Users/{username}/Sonet/.data/supervisor/supervisord.conf', 'start', 'gunicorn'],
    ['sudo', '-S', '/opt/homebrew/bin/supervisorctl', '-c', f'/Users/{username}/Sonet/.data/supervisor/supervisord.conf', 'start', 'rqscheduler'],
    ['sudo', '-S', '/opt/homebrew/bin/supervisorctl', '-c', f'/Users/{username}/Sonet/.data/supervisor/supervisord.conf', 'start', 'tor'],
    ['sudo', '-S', '/opt/homebrew/bin/supervisorctl', '-c', f'/Users/{username}/Sonet/.data/supervisor/supervisord.conf', 'start', 'all'],
    ['sudo', '-S', '/opt/homebrew/bin/supervisorctl', '-c', f'/Users/{username}/Sonet/.data/supervisor/supervisord.conf', 'restart', 'all'],
    ['run_command', 'run_write_supervisor_plist'],
    ['launchctl', 'bootout', f'gui/{uid}', f'/Users/{username}/Library/LaunchAgents/com.sonet.supervisor.plist'],
    ['sudo', '-S', 'pkill', '-f', 'supervisord'],
    ['/bin/rm', '-f', f'/Users/{username}/Sonet/.data/supervisor/supervisor.sock'],
    ['/bin/rm', '-f', f'/Users/{username}/Sonet/.data/supervisor/supervisord.pid'],
    ['/bin/sleep', '2'],
    ['launchctl', 'bootstrap', f'gui/{uid}', f'/Users/{username}/Library/LaunchAgents/com.sonet.supervisor.plist'],
    ['sudo', '-S', 'launchctl', 'bootstrap', 'system', '/Library/LaunchDaemons/homebrew.mxcl.postgresql.plist'],
    ['run_command', 'intelligence_check'],
    ['run_command', 'pause'],
    ['echo', 'Finished!'],
]
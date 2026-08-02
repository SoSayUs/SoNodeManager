

import os
import subprocess
import getpass
from os.path import expanduser

from ..utils import get_operatorData, fetch_secure_item
from .mac_install_cmds import find_brew, update_output

username = getpass.getuser()
# print(username)
homepath = expanduser("~")
# print(homepath)
group = subprocess.check_output("id -gn", shell=True).decode().strip()
brew_path = find_brew()
uid = os.getuid()


def run_update_repo(output=None, remote_cmd=False):
    from commands.utils import pull_git_server
    if not pull_git_server(output=output):
        update_output('\n\n', output)
        raise Exception('Device is up to date')

def run_adjust_settings(option=None, remote_cmd=False):
    print('-run_adjust_settings', option)
    from commands.utils import adjust_settings
    operatorData = get_operatorData()
    if 'local_nodeId' in operatorData:
        node_data = operatorData['myNodes'][operatorData['local_nodeId']]
    adjust_settings(nodeData=node_data)

def restart_cloudflare_service(output=None, remote_cmd=False):
    print('-restart_cloudflare_service')
    from pathlib import Path
    tunnel_name = fetch_secure_item('local_nodeId')

    SERVICE_NAME = f"com.cloudflared.{tunnel_name}"
    PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{SERVICE_NAME}.plist"

    if not PLIST_PATH.exists():
        update_output(f"Cloudflared service not found: {PLIST_PATH}", output)
        return

    update_output('restart_cloudflare_service', output)

    subprocess.run(["launchctl", "unload", str(PLIST_PATH)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = subprocess.run(["launchctl", "load", str(PLIST_PATH)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if result.returncode == 0:
        update_output(f"Restarted: {SERVICE_NAME}", output)
    else:
        update_output(f"Failed to restart: {SERVICE_NAME}", output)

def special_job(output=None, remote_cmd=False):
    print('-special_job')
    # from .mac_install_cmds import gunicorn_logrotate,config_supervisor
    # config_supervisor(install=True, output=output, remote_cmd=remote_cmd)
    # gunicorn_logrotate(install=True, output=output, remote_cmd=remote_cmd)
    # pass
    import subprocess
    import urllib.request
    import os
    import tempfile
    # import subprocess
    # import urllib.request
    # import os
    # import tempfile

    # def install_chrome_mac():
    dmg_url = "https://dl.google.com/chrome/mac/universal/stable/CHFA/googlechrome.dmg"

    print("Downloading Chrome...")
    with tempfile.TemporaryDirectory() as tmpdir:
        dmg_path = os.path.join(tmpdir, "googlechrome.dmg")
        mount_point = os.path.join(tmpdir, "chrome_mount")

        urllib.request.urlretrieve(dmg_url, dmg_path)
        print("Download complete.")

        print("Mounting DMG...")
        subprocess.run(
            ["hdiutil", "attach", dmg_path, "-mountpoint", mount_point, "-nobrowse", "-quiet"],
            check=True
        )

        try:
            subprocess.run(
                ["sudo", "rm", "-rf", "/Applications/Google Chrome.app"],
                check=True
            )

            # rsync instead of cp — avoids copying resource forks that break codesign
            print("Installing Chrome to /Applications...")
            subprocess.run(
                [
                    "rsync", "-a", "--exclude=._*", "--exclude=.DS_Store",
                    f"{mount_point}/Google Chrome.app",
                    "/Applications/"
                ],
                check=True
            )
        finally:
            subprocess.run(["hdiutil", "detach", mount_point, "-quiet"], check=True)

        subprocess.run(
            ["sudo", "xattr", "-c", "/Applications/Google Chrome.app"],
            check=True
        )

        print("Done. Binary at: /Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

special_commands = [
    {'cmd':'run_adjust_settings', 'reqs':'None'},
    {'cmd':'restart_cloudflare_service', 'reqs':'output_display'},
    {'cmd':'special_job', 'reqs':'output_display'},
    {'cmd':'run_update_repo', 'reqs':'output_display'},
    {'cmd':'run_config_nginx', 'reqs':'output_display'},
    {'cmd':'run_setup_gunicorn', 'reqs':'output_display'},
]


action_cmds = [
    ['sudo', '-S', 'echo','this is an update check'],
    # ['run_command', 'special_job'],
    ['run_command', 'run_update_repo'],
    ["raise_if_error", f"{homepath}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "check"],
    ["sudo", "-S", f"{homepath}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "collectstatic", "--noinput"],
    ['run_command', 'run_adjust_settings'],
    ['run_command', 'restart_cloudflare_service'],
    ["sudo", "-S", f"{homepath}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "migrate"],
    ['run_command', 'run_config_nginx'],
    # ['sudo', '-S', 'nginx', '-t'],
    ['sudo', '-S', '/opt/homebrew/bin/nginx', '-t'],
    ['run_command', 'run_setup_gunicorn'],
    # ['run_command', 'run_config_supervisor'],
    ['sudo', '-S', 'pkill', '-f', 'supervisord'],
    ['sudo', '-S', 'pkill', '-f', 'rqworker'],
    ['sudo', '-S', 'pkill', '-f', 'gunicorn'],
    ['/bin/sleep', '2'],  # give them time to die
    ['sudo', '-S', 'rm', '-f', f'/Users/{username}/Sonet/.data/supervisor/supervisor.sock'],
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
    ['launchctl', 'bootout', f'gui/{uid}', f'/Users/{username}/Library/LaunchAgents/com.sonet.supervisor.plist'],
    ['sudo', '-S', 'pkill', '-f', 'supervisord'],
    ['/bin/rm', '-f', f'/Users/{username}/Sonet/.data/supervisor/supervisor.sock'],
    ['/bin/rm', '-f', f'/Users/{username}/Sonet/.data/supervisor/supervisord.pid'],
    ['/bin/sleep', '2'],
    ['launchctl', 'bootstrap', f'gui/{uid}', f'/Users/{username}/Library/LaunchAgents/com.sonet.supervisor.plist'],

    # sudo softwareupdate -ia --agree-to-license
    # brew update && brew upgrade
    # brew cleanup
]


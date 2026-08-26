
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
    import os
    import subprocess
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
    ['run_command', 'pause'],
    ['echo', 'Finished!'],
]
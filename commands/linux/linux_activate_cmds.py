
import subprocess
import getpass
import shutil
import json
from os.path import expanduser

from ..utils import get_operatorData, get_node_list, write_operatorData
from .linux_install_cmds import config_nginx, edit_supervisor, update_output


username = getpass.getuser()
# print(username)
homepath = expanduser("~")
# print(homepath)

operatorData = {}
sonet_title = ''
external_ip = ''
node_data = {}
node_id = ''
port = ''
open_ports = ''
systemPass = ''
branch = 'main'

def get_variables(remote_cmd=False):
    global operatorData
    global sonet_title
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
            if 'external_ip' in node_data['settings']:
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
                if 'external_ip' in node_data['settings']:
                    external_ip = node_data['settings']['external_ip']
                port = node_data['settings']['port']
                open_ports = node_data['settings']['open_ports']

        from commands.utils import fetch_secure_item
        systemPass = fetch_secure_item('sysPass')
        if not systemPass and 'systemPass' in operatorData:
            systemPass = operatorData['systemPass']

        try:
            sonet_title = operatorData['sonet']['title']
        except:
            sonet_title = 'SoNode'
        
        if 'sonet' in operatorData:
            repo_data = operatorData['sonet']['repo']
        elif 'new_sonet' in operatorData:
            repo_data = operatorData['new_sonet']['repo']

        print('repo_data', repo_data)

        branch = repo_data['branch'] # main

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
    #     # print(cmd)
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

def run_adjust_settings(output=None, remote_cmd=False):
    from commands.utils import adjust_settings
    get_variables()
    global node_data
    adjust_settings(node_data=node_data, clear_data=False, output=output)


def run_config_nginx(output=None, remote_cmd=False):
    print('-run_config_nginx')
    get_variables()
    global node_data
    config_nginx(install=False, close_port=None, run_restart=False, nodeData=node_data, output=output, remote_cmd=remote_cmd)

def run_edit_supervisor(output=None, remote_cmd=False):
    print('-run_edit_supervisor')
    get_variables()
    global node_data
    edit_supervisor(install=False, output=output, remote_cmd=remote_cmd)

def activate_cloudflare_service(output=None, remote_cmd=False):
    print('-run_activate_cloudflare')
    import os
    import subprocess
    from pathlib import Path
    get_variables()
    global operatorData
    global node_data
    global systemPass

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
                nodes, operatorData = get_node_list(operatorData=operatorData, target={'category':'abilities', 'sub_cat':'cloudflare'}, exclude_relays=False, exclude_self=False, refresh_list=True)

                def fetch_zip(nodes):
                    try:
                        for iden, address in nodes.items():
                            url = f"{address}/utils/fetch_cloudflare_bundle/{tunnel_name}"
                            print(f"Downloading bundle from {url}")

                            data = {'nodeData':json.dumps(node_data['nodeData'])}
                            data['userData'] = json.dumps(operatorData['userData'])
                            data['upkData'] = json.dumps(operatorData['upkData'])
                            
                            response = connect_to_node(address, f"utils/fetch_cloudflare_bundle/{tunnel_name}", data=data, operatorData=operatorData, node_setup=True, timeout=30)

                            if response:
                                content_type = response.headers.get("Content-Type", "").lower()
                                content_disp = response.headers.get("Content-Disposition", "")

                                if "application/zip" in content_type:
                                    with zipfile.ZipFile(BytesIO(response.content)) as zip_ref:
                                        zip_ref.extractall(dest)

                                    print(f"Bundle installed to: {dest}")
                                    return True

                                elif "application/json" in content_type:
                                    r_json = response.json()
                                    print('r_json',r_json)
                                    if 'message' in r_json and r_json['message'] == 'wrong_node':
                                        if 'correct_nodes' in r_json and r_json['correct_nodes']:
                                            correct_nodes = json.loads(r_json['correct_nodes'])
                                            for key, value in correct_nodes.items():
                                                response_nodes[key] = value
                                        print('response_nodes:',response_nodes)
                        return False
                    except Exception as e:
                        print('fetch bundle fail 34', str(e))
                        raise Exception('fetch bundle fail 34' + str(e))
                
                if not fetch_zip(nodes) and response_nodes:
                    fetch_zip(response_nodes)

            if new_address and new_address != node_data['settings']['address']:
                node_data['settings']['address'] = new_address
                operatorData['myNodes'][node_data['nodeData']['id']] = node_data
                from commands.utils import write_operatorData
                write_operatorData(operatorData)

            if config_path.exists():
                print('config_path exists',config_path)
                SERVICE_NAME = f"cloudflared-{tunnel_name}.service"
                SERVICE_PATH = f"/etc/systemd/system/{SERVICE_NAME}"
                cloudflared_path = shutil.which("cloudflared")
                if not os.path.exists(SERVICE_PATH):
                    
                    update_output(f'creating {SERVICE_NAME}', output)
                    USER = os.getenv("USER")

                    SERVICE_CONTENT = f"""[Unit]
    Description=Cloudflare Tunnel
    After=network.target

    [Service]
    Type=simple
    User={USER}
    ExecStart={cloudflared_path} --config /home/{USER}/Sonet/.data/cloudflare_registration/config.yml tunnel run {tunnel_name}
    Restart=always
    RestartSec=5
    WorkingDirectory=/home/{USER}/Sonet/.data/cloudflare_registration

    [Install]
    WantedBy=multi-user.target
                        """

                    with open("/tmp/temp_service.service", "w") as f:
                        f.write(SERVICE_CONTENT)
                    subprocess.run(["sudo", "-S", "mv", "/tmp/temp_service.service", SERVICE_PATH], check=True, input=systemPass, text=True, capture_output=True)
                    print(f"Created systemd service: {SERVICE_NAME}")

                update_output('activate_cloudflare_service', output)
                subprocess.run(["sudo", "-S", "systemctl", "daemon-reexec"], check=True, input=systemPass, text=True, capture_output=True)
                subprocess.run(["sudo", "-S", "systemctl", "daemon-reload"], check=True, input=systemPass, text=True, capture_output=True)
                subprocess.run(["sudo", "-S", "systemctl", "enable", SERVICE_NAME], check=True, input=systemPass, text=True, capture_output=True)
                subprocess.run(["sudo", "-S", "systemctl", "stop", SERVICE_NAME], check=True, input=systemPass, text=True, capture_output=True)
                subprocess.run(["sudo", "-S", "systemctl", "start", SERVICE_NAME], check=True, input=systemPass, text=True, capture_output=True)
                print(f"Enabled and started: {SERVICE_NAME}")
                update_output(f"Enabled and started: {SERVICE_NAME}", output)
            else:
                update_output(f"config.yml not found. Tunnel not created.", output)
                raise 'Tunnel not created'

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

# remove_for_debug = [
#     ["sudo", "-S", f"/home/{username}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "crontab", "add"],
# ]

remove_for_tasker = [
    ["sudo", "-S", f"/home/{username}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "crontab", "add"],
]

special_commands = [
    {'cmd':'get_variables'},
    {'cmd':'hardware_check', 'reqs':'output_display'},
    {'cmd':'update_repo', 'reqs':'output_display'},
    {'cmd':'run_adjust_settings', 'reqs':'output_display'},
    {'cmd':'run_config_nginx', 'reqs':'output_display'},
    {'cmd':'run_edit_supervisor', 'reqs':'output_display'},
    {'cmd':'pause'},
    {'cmd':'activate_cloudflare_service', 'reqs':'output_display'},
    {'cmd':'declare_active', 'reqs':'output_display'},
    {'cmd':'force_active', 'reqs':'output_display'},
    {'cmd':'declare_active_no_broadcast', 'reqs':'output_display'},
    {'cmd':'force_active_no_broadcast', 'reqs':'output_display'},
]

action_cmds = [
    ["echo", "activating"],
    ['run_command', 'get_variables'],
    ['run_command', 'update_repo'],
    # ['run_command', 'hardware_check'],
    ['run_command', 'activate_cloudflare_service'],
    ['run_command', 'run_adjust_settings'],
    ['run_command', 'run_config_nginx'],
    ['run_command', 'run_edit_supervisor'],
    ["sudo", "-S", f"{homepath}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "migrate"],
    ["sudo", "-S", "ufw", "allow", port],
    ["sudo", "-S", "ufw", "enable"],
    ["raise_if_error", "sudo", "-S", f"{homepath}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "check"],
    ["raise_if_error", "sudo", "-S", f"{homepath}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "collectstatic", "--noinput"],
    # ["sudo", "-S", "supervisorctl", "reload"],
    # ["sudo", "-S", "supervisorctl", "restart", "django_rq_main" ,"django_rq_high", "django_rq_low", "django_rq_chat", "django_rq_super", "django_rqscheduler"],
    ["sudo", "-S", 'semanage', 'fcontext', '-a', '-t', 'httpd_config_t', f"/etc/nginx/sites-available/sonode"],
    ["sudo", "-S", "semanage", "port", "-m", "-t", "http_port_t", "-p", "tcp", port], # only needed on fedora if port has changed
    ["sudo", "-S", 'restorecon', '-v', f"/etc/nginx/sites-available/sonode"],
    ['sudo', '-S', 'systemctl', 'start', 'redis'],
    ["sudo", "-S", "supervisorctl", "reread"],
    ["sudo", "-S", "supervisorctl", "update"],
    ["sudo", "-S", "supervisorctl", "status"],
    ["sudo", "-S", "supervisorctl", "reload"],
    # ["sudo", "-S", "supervisorctl", "reread"],
    # ["sudo", "-S", "supervisorctl", "update"],
    # ["sudo", "-S", "supervisorctl", "status"],
    ["sudo", "-S", "systemctl", "daemon-reexec"],
    ["sudo", "-S", "systemctl", "daemon-reload"],
    ["sudo", "-S", "systemctl", "enable", "--now", "nginx"],
    ["sudo", "-S", "systemctl", "daemon-reload"],
    ["sudo", "-S", "systemctl", "restart", "gunicorn"],
    ["sudo", "-S", "systemctl", "restart", "rqscheduler"],
    ["sudo", "-S", "systemctl", "restart", "nginx"],
    ['run_command', 'pause'],
    # ['echo', 'Finished!'],
]

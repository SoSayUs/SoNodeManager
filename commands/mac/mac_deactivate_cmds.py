
import os
import subprocess
import getpass
from kivy.clock import Clock
from os.path import expanduser

from ..utils import get_operatorData, declare_self_active
from .mac_install_cmds import update_output, find_brew


username = getpass.getuser()
# print(username)
homepath = expanduser("~")
# print(homepath)
brew_path = find_brew()
uid = os.getuid()


operatorData = {}
sonet_title = ''
external_ip = ''
node_data = {}
node_id = ''
port = ''
open_ports = ''
systemPass = ''

def get_variables(remote_cmd=False):
    global operatorData
    global sonet_title
    global open_ports
    global port
    global external_ip
    global node_data
    global node_id
    global systemPass

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
            sonet_title = operatorData['sonet']['title']
        except:
            sonet_title = 'SoNode'

def empty_supervisor(install=True, remote_cmd=False):
    print('-empty_supervisor')
    text = []
    text_str = ''.join(text)
    with open("/tmp/django_rq.conf", "w") as temp_file:
        temp_file.write(text_str)
    subprocess.run(["sudo", "-S", "mv", "/tmp/django_rq.conf", "/etc/supervisor/conf.d/django_rq.conf"])
    subprocess.run(["sudo", "-S", "chmod", "644", "/etc/supervisor/conf.d/django_rq.conf"])
    subprocess.run(["sudo", "-S", "systemctl", "daemon-reload"])

def deactivate_cloudflare_service(output=None, remote_cmd=False):
    print('-run_deactivate_cloudflare')
    import subprocess
    from pathlib import Path

    config_path = Path.home() / "Sonet" / ".data" / "cloudflare_registration" / "config.yml"
    if config_path.exists():
        global node_data
        tunnel_name = node_data['nodeData']['id']

        SERVICE_NAME = f"com.cloudflared.{tunnel_name}"
        PLIST_PATH = Path.home() / "Library/LaunchAgents" / f"{SERVICE_NAME}.plist"

        update_output('run_deactivate_cloudflare', output)

        subprocess.run(["launchctl", "unload", str(PLIST_PATH)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)

        if PLIST_PATH.exists():
            PLIST_PATH.unlink()

        print(f"Stopped and disabled: {SERVICE_NAME}")
        update_output(f"Stopped and disabled: {SERVICE_NAME}", output)

def declare_state(output, remote_cmd=False):
    declare_self_active(False, output=output)

def broadcast_dataPackets(output=None, remote_cmd=False): # is duplicated in other deactivate functions
    print('-broadcast_dataPackets')
    get_variables()
    global node_data
    import json
    from commands.utils import get_most_recent_even_hour, connect_to_node
    from commands.locked import sign, dt_to_string
    if output:
        Clock.schedule_once(lambda dt, output=output, line=f'Broadcasting DataPackets...\n': update_output(output, line))
    signedRequest = json.dumps(sign({'cmd':'Broadcast','dt':dt_to_string(get_most_recent_even_hour())}))
    data = {'cmd':'Broadcast', 'request':signedRequest}
    response = connect_to_node(node_data['settings']['localhost'], 'network/broadcast_dataPackets', operatorData=operatorData)
    if response and response.status_code == 200:
        received_json = response.json()
        if received_json['message'] == 'Valid':
            print('result',received_json['result'])
            if output:
                Clock.schedule_once(lambda dt, output=output, line=f'Result: {received_json["result"]}\n': update_output(output, line))
        elif received_json['message'] == 'Fail':
            print('err',received_json['err'])
            if output:
                Clock.schedule_once(lambda dt, output=output, line=f'Result: {received_json["err"]}\n': update_output(output, line))
        else:
            if output:
                Clock.schedule_once(lambda dt, output=output, line=f'Result: Failed\n': update_output(output, line))
    else:
        if output:
            Clock.schedule_once(lambda dt, output=output, line=f'Result: Failed to broadcast DataPackets\n': update_output(output, line))

remove_for_debug = [
    # ["sudo", "-S", "ufw", "delete", "allow", port],
    # ["sudo", "-S", "systemctl", "stop", "gunicorn"],
    # ["sudo", "-S", "systemctl", "stop", "nginx"],
    # ['run_command', 'empty_supervisor'],
    # ['sudo', 'systemctl', 'disable', 'nginx'],
    # ["sudo", "-S", "systemctl", "disable", "gunicorn"],
    # ['run_command', 'broadcast_dataPackets'],
    # ['run_command', 'declare_state'],
    # ['run_command', 'broadcast_dataPackets'],
    # ["sudo", "-S", "ufw", "delete", "allow", port],

    ['sudo', '-S', 'sh', '-c', f'''echo '\nblock in all\npass in proto tcp from any to any port {22}\n' > /etc/pf.anchors/custom_rules'''],
    ['sudo', '-S', 'sh', '-c', f'''echo '\nanchor "custom_rules"\nload anchor "custom_rules" from "/etc/pf.anchors/custom_rules"\n' >> /etc/pf.conf'''],
    ['sudo', '-S', 'pfctl', '-f', '/etc/pf.conf'],
    ['sudo', '-S', 'pfctl', '-e'],
    ['sudo', '-S', 'pfctl', '-sr'],

    # ["sudo", "-S", f"/home/{username}/SoNodeServer/env/bin/python3", f"{homepath}/SoNodeServer/manage.py", "crontab", "remove"],

    ['sudo', '-S', 'supervisorctl', '-c', f'/Users/{username}/Sonet/.data/supervisor/supervisord.conf', 'stop', 'gunicorn'],
    ['sudo', '-S', 'supervisorctl', '-c', f'/Users/{username}/Sonet/.data/supervisor/supervisord.conf', 'stop', 'all'],
    ['sudo', '-S', 'pkill', '-f', 'supervisord'],
    ['sudo', '-S', 'pkill', '-f', 'nginx'],
    [brew_path, 'services', 'stop', 'supervisor'],
    [brew_path, 'services', 'stop', 'nginx'],
    [brew_path, 'services', 'stop', 'redis'],
    [brew_path, 'services', 'stop', 'postgresql'],
    
    ['sudo', '-S', 'launchctl', 'unload', '-w', f'/Users/{username}/Library/LaunchAgents/com.sonet.supervisor.plist'],
    ['sudo', '-S', 'launchctl', 'unload', '-w', '/Library/LaunchDaemons/homebrew.mxcl.postgresql.plist'],
    ['sudo', '-S', 'launchctl', 'bootout', 'system', '/Library/LaunchDaemons/homebrew.mxcl.nginx.plist'],
    ['sudo', '-S', 'launchctl', 'unload', '-w', '/Library/LaunchDaemons/homebrew.mxcl.nginx.plist'],

]

special_commands = [
    # {'cmd':'empty_supervisor'},
    {'cmd':'get_variables'},
    {'cmd':'declare_state', 'reqs':'output_display'},
    {'cmd':'broadcast_dataPackets', 'reqs':'output_display'},
]

action_cmds = [
    ["sudo", "-S", "echo", "deactivating"],
    ['run_command', 'get_variables'],
    ["sudo", "-S", "echo", "deactivating"],
    ['run_command', 'broadcast_dataPackets'],
    ['run_command', 'declare_state'],
    ["sudo", "-S", f"/Users/{username}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "crontab", "remove"],
    ['/opt/homebrew/bin/supervisorctl', '-c', f'/Users/{username}/Sonet/.data/supervisor/supervisord.conf', 'stop', 'all'],
    ['launchctl', 'bootout', f'gui/{uid}', f'/Users/{username}/Library/LaunchAgents/com.sonet.supervisor.plist'],
    ['sudo', '-S', 'pkill', '-f', 'supervisord'],
    ['sudo', '-S', 'pkill', '-f', 'gunicorn'],
    ['sudo', '-S', 'pkill', '-f', 'nginx'],
    ['/bin/rm', '-f', f'/Users/{username}/Sonet/.data/supervisor/supervisor.sock'],
    ['/bin/rm', '-f', f'/Users/{username}/Sonet/.data/supervisor/supervisord.pid'],
    ['/bin/rm', '-f', f'/Users/{username}/Sonet/.data/supervisor/nginx.pid'],
    ['/bin/rm', '-f', f'/Users/{username}/Sonet/.data/supervisor/gunicorn.sock'],
    [brew_path, 'services', 'stop', 'postgresql'],
    ['echo', 'Finished!'],
]
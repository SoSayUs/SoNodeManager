
import subprocess
import getpass
from kivy.clock import Clock
from os.path import expanduser

from ..utils import get_operatorData, declare_self_active, update_output
from .linux_install_cmds import update_output


username = getpass.getuser()
print(username)
homepath = expanduser("~")
print(homepath)

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


def empty_supervisor(install=True, remote_cmd=False):
    print('-empty_supervisor')
    get_variables()
    global systemPass
    text = []
    text_str = ''.join(text)
    with open("/tmp/django_rq.conf", "w") as temp_file:
        temp_file.write(text_str)
    subprocess.run(["sudo", "-S", "mv", "/tmp/django_rq.conf", "/etc/supervisor/conf.d/django_rq.conf"], check=True, input=f"{systemPass}\n".encode())
    subprocess.run(["sudo", "-S", "chmod", "644", "/etc/supervisor/conf.d/django_rq.conf"], check=True, input=f"{systemPass}\n".encode())
    subprocess.run(["sudo", "-S", "systemctl", "daemon-reload"], check=True, input=f"{systemPass}\n".encode())

def deactivate_cloudflare_service(output=None, remote_cmd=False):
    print('-run_deactivate_cloudflare')
    get_variables()
    global systemPass
    import subprocess
    from pathlib import Path

    config_path = Path.home() / "Sonet" / ".data" / "cloudflare_registration" / "config.yml"
    if config_path.exists():
        global node_data
        tunnel_name = node_data['nodeData']['id']

        SERVICE_NAME = f"cloudflared-{tunnel_name}.service"

        update_output('run_deactivate_cloudflare', output)

        subprocess.run(["sudo", "-S", "systemctl", "stop", SERVICE_NAME], check=True, input=f"{systemPass}\n".encode())
        subprocess.run(["sudo", "-S", "systemctl", "disable", SERVICE_NAME], check=True, input=f"{systemPass}\n".encode())
        print(f"Stopped and disabled: {SERVICE_NAME}")
        update_output(f"Stopped and disabled: {SERVICE_NAME}", output)

def declare_state(output=None, remote_cmd=False):
    declare_self_active(False, output=output, remote_cmd=remote_cmd)

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
    response = connect_to_node(node_data['settings']['localhost'], 'network/broadcast_dataPackets', data=data, operatorData=operatorData) # node not receiving post data from here
    if response and response.status_code == 200:
        received_json = response.json()
        print('message',received_json['message'])
        if received_json['message'] == 'Valid':
            if output:
                Clock.schedule_once(lambda dt, output=output, line=f'Result: {received_json['result']}\n': update_output(output, line))
        elif received_json['message'] == 'Fail':
            if output:
                Clock.schedule_once(lambda dt, output=output, line=f'Result: {received_json['err']}\n': update_output(output, line))
        else:
            if output:
                Clock.schedule_once(lambda dt, output=output, line=f'Result: Failed\n': update_output(output, line))
    else:
        if output:
            Clock.schedule_once(lambda dt, output=output, line=f'Result: Failed to broadcast DataPackets\n': update_output(output, line))

remove_for_debug = [
    ['run_command', 'deactivate_cloudflare_service'],
    ["sudo", "-S", "ufw", "delete", "allow", port],
    ["sudo", "-S", "systemctl", "stop", "gunicorn"],
    ["sudo", "-S", "systemctl", "stop", "nginx"],
    ['run_command', 'empty_supervisor'],
    ['sudo', 'systemctl', 'disable', 'nginx'],
    ["sudo", "-S", "systemctl", "disable", "gunicorn"],
]

special_commands = [
    {'cmd':'get_variables'},
    {'cmd':'empty_supervisor'},
    {'cmd':'deactivate_cloudflare_service', 'reqs':'output_display'},
    {'cmd':'declare_state', 'reqs':'output_display'},
    {'cmd':'broadcast_dataPackets', 'reqs':'output_display'},
]

action_cmds = [
    ["echo", "deactivating"],
    ['run_command', 'get_variables'],
    ['run_command', 'broadcast_dataPackets'],
    ['run_command', 'declare_state'],
    ['run_command', 'deactivate_cloudflare_service'],
    ["sudo", "-S", "ufw", "delete", "allow", port],
    ["sudo", "-S", f"/home/{username}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "crontab", "remove"],
    ['sudo', '-S', 'systemctl', 'stop', 'redis'],
    ["sudo", "-S", "systemctl", "stop", "gunicorn"],
    ["sudo", "-S", "systemctl", "stop", "rqscheduler"],
    ["sudo", "-S", "systemctl", "stop", "nginx"],
    ["sudo", "-S", "supervisorctl", "stop", "all"],
    ["sudo", "-S", "supervisorctl", "reread"],
    ["sudo", "-S", "supervisorctl", "update"],
    ['sudo', 'systemctl', 'disable', 'nginx'],
    ["sudo", "-S", "systemctl", "disable", "gunicorn"],
    # ['echo', 'Finished!'],
]

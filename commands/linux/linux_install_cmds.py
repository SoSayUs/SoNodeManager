
import os
import subprocess
import getpass
import requests
from os.path import expanduser
import shutil
from kivy.clock import Clock

from ..utils import get_operatorData, write_operatorData, get_package_manager, refresh_ip


username = getpass.getuser()
# print(username)
homepath = expanduser("~")
# print(homepath)


package_manager = get_package_manager()
if package_manager:
    print(f"Detected package manager: {package_manager}")
    if package_manager == 'apt':
        update_func = 'update'
        nginx_install_command = ["sudo", "-S", package_manager, "install", "python3-dev", "libpq-dev", "nginx", "curl", "-y"]
    elif package_manager == 'dnf':
        update_func = 'check-update'
        nginx_install_command = ["sudo", "-S", package_manager, "install", "python3-devel", "postgresql-devel", "python3-dev", "libpq-dev", "nginx", "curl", "-y", "--skip-unavailable"]
else:
    print("Could not detect package manager.")


import distro

os_id = distro.id()
print(f"Detected OS: {os_id}")


operatorData = {}
sonet_title = ''
external_ip = ''
node_data = {}
node_id = ''
port = ''
open_ports = []
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
                if 'external_ip' in node_data['settings'] and node_data['settings']['external_ip']:
                    external_ip = node_data['settings']['external_ip']
                else:
                    external_ip = refresh_ip()
                    node_data['settings']['external_ip'] = external_ip
                    operatorData['myNodes'][node_id] = node_data
                    write_operatorData(operatorData)
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

def adjust_firewall(output, remote_cmd=False):
    get_variables()
    global node_data
    global port
    global open_ports
    global systemPass
    if package_manager == 'apt':
        cmds = [
            ["sudo", "-S", package_manager, "install", "ufw", "-y"],
        ]
    elif package_manager == 'dnf':
        cmds = [
            ["sudo", "-S", package_manager, "install", "ufw", "-y"],
            ["sudo", "-S", 'systemctl', 'enable', '--now', 'ufw'],
        ]
    cmds += [
        ["sudo", "-S", "ufw", "default", "allow", "outgoing"],
        ["sudo", "-S", "ufw", "default", "deny", "incoming"],
        ["sudo", "-S", "ufw", "allow", "ssh"],
        ["sudo", "-S", "ufw", "allow", "http/tcp"],
        ["sudo", "-S", "ufw", "allow", "https"],
        ["sudo", "-S", "ufw", "allow", port],
    ]
    if open_ports and not isinstance(open_ports, list):
        open_ports = [i.strip().strip("'").strip('"') for i in open_ports.split(',')]
    for p in open_ports:
        cmds.append(["sudo", "-S", "ufw", "allow", p])
    cmds.append(["sudo", "-S", "ufw", "enable"])

    for cmd in cmds:
        print(cmd)
        if output:
            update_output(cmd, output)
        r = subprocess.run(
            cmd,
            check=True,
            input=f"{systemPass}\n".encode(),
        )

def schedule(content, output_display):
    from ops import display_max_size
    try:
        if output_display:
            output_display.text += f'\n{content}'
            lines = output_display.text.splitlines()
            if display_max_size > 0 and len(lines) > display_max_size:
                last_n_lines = lines[-display_max_size:]
                result = "\n".join(last_n_lines)
                output_display.text = result
    except Exception as e:
        # print('schedule err',str(e))
        pass

def update_output(content, output_display=None):
    try:
        if output_display:
            Clock.schedule_once(lambda dt, line=content: schedule(line, output_display))
        print(content)
    except Exception as e:
        # print('update_output err',str(e))
        pass

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

def pull_git(output, remote_cmd=False):
    from commands.utils import pull_git_server
    get_variables()
    global operatorData
    pull_git_server(output=output, operatorData=operatorData)

def run_create_env(output, remote_cmd=False):
    from commands.utils import setup_pyenv
    get_variables()
    global node_data
    setup_pyenv(output=output, node_data=node_data)


def get_local_ip(output_text, remote_cmd=False):
    print('-get_local_ip')
    get_variables()
    global operatorData
    global node_data
    import subprocess
    local_ip = subprocess.check_output(["hostname", "-I"]).decode().split()[0]
    print(local_ip)

    if output_text:
        # local_ip = ''
        # lines = output_text.split('\n')
        # # print('lines:', lines)
        # position = -1
        # potential_ip = lines[position]
        # print('potential_ip1',potential_ip)
        # try:
        #     while not local_ip and position > -5:
        #         z = potential_ip.find('-I')+len('-I ')
        #         x = potential_ip[z:].find(' ')
        #         potential_ip = potential_ip[z:z+x]
        #         print('potential_ip2',potential_ip)
        #         if potential_ip.count('.') == 3:
        #             local_ip = potential_ip.replace(' ','').replace('\n','')
        #             break
        #         else:
        #             position -= 1
        #             potential_ip = lines[position]
        #             print('potential_ip3',potential_ip)
        #             if abs(position) == len(lines):
        #                 break
        # except Exception as e:
        #     print('potential_ip err', str(e))
        update_output(f'local_ip: {local_ip}', output_text)
        node_data['settings']['local_ip'] = local_ip
        operatorData['myNodes'][node_id] = node_data
        write_operatorData(operatorData)
    else:
        print('no output text')

def run_fetch_secret_key(output, remote_cmd=False):
    from commands.utils import fetch_django_secret_key
    get_variables()
    global node_data
    global node_id
    global operatorData
    operatorData = fetch_django_secret_key(output=output, node_data=node_data, node_id=node_id, operatorData=operatorData)

def run_adjust_settings(output=None, remote_cmd=False):
    from commands.utils import adjust_settings
    get_variables()
    global node_data
    global operatorData
    adjust_settings(node_data=node_data, clear_data=True, output=output, operatorData=operatorData)


def install_cloudflared(output=None, remote_cmd=False):
    os_id = distro.id()
    if os_id == 'fedora':
        # commands = [
        #     "sudo dnf install -y dnf-plugins-core",
        #     "sudo dnf config-manager --add-repo https://pkg.cloudflare.com/cloudflared.repo",
        #     "sudo rpm --import https://pkg.cloudflare.com/cloudflare-main.gpg",
        #     "sudo dnf install -y cloudflared"
        # ]

        import urllib.request
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-x86_64.rpm"
        rpm_path = "/tmp/cloudflared.rpm"
        print(f"Downloading cloudflared from {url}...")
        urllib.request.urlretrieve(url, rpm_path)
        print("Download complete.")
        commands = [
            [f"sudo dnf install -y {rpm_path}"],
            ["cloudflared", "--version"]
            ]
    else:
        # if os_id in ['debian', 'ubuntu']:
        commands = [
            ["sudo", "-S", "mkdir", "-p", "--mode=0755", "/usr/share/keyrings"],
            ["sudo", "-S", "sh", "-c", "curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null"],
            ["sudo", "-S", "sh", "-c", "echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main' | tee /etc/apt/sources.list.d/cloudflared.list"],
            ["sudo", "-S", "apt-get", "update"],
            ["sudo", "-S", "apt-get", "install", "-y", "cloudflared"],
        ]
    
    get_variables()
    global systemPass
    for cmd in commands:
        print(cmd)
        update_output(cmd, output)
        try:
            r = subprocess.run(
                cmd,
                check=True,
                input=f"{systemPass}\n".encode(),
            )
            print('r',r)
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode().strip() if e.stderr else "No stderr output"
            print('error_msg',error_msg)
            update_output(f"Command failed:\n{error_msg}", output)

def write_gunicorn_socket(install=True, output=None, remote_cmd=False):
    print('-write_gunicorn_socket')
    text = [
        "[Unit]\n",
        "Description=gunicorn socket\n",
        "\n",
        "[Socket]\n",
        "ListenStream=/run/gunicorn.sock\n",
    ]
    if package_manager == 'dnf':
        text += [
            f"SocketUser={username}\n",
            "SocketGroup=nginx\n",
            "SocketMode=0660\n",
        ]
    text += [
        "\n",
        "[Install]\n",
        "WantedBy=sockets.target"
    ]
    text_str = ''.join(text)
    with open("/tmp/gunicorn.socket", "w") as temp_file:
        temp_file.write(text_str)
    commands = [
        ["sudo", "-S", "mv", "/tmp/gunicorn.socket", "/etc/systemd/system/gunicorn.socket"],
        ["sudo", "-S", "chmod", "644", "/etc/systemd/system/gunicorn.socket"],
        ["sudo", "-S", "systemctl", "daemon-reload"]
    ]
    if install or remote_cmd:
        get_variables()
        global systemPass
        for cmd in commands:
            print(cmd)
            update_output(cmd, output)
            try:
                r = subprocess.run(
                    cmd,
                    check=True,
                    input=f"{systemPass}\n".encode(),
                )
                print('r',r)
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr.decode().strip() if e.stderr else "No stderr output"
                print('error_msg',error_msg)
                update_output(f"Command failed:\n{error_msg}", output)
    else:
        from ops import CommandRunner
        import threading
        command_runner = CommandRunner(None, commands, None, None, special_commands)
        threading.Thread(target=command_runner.run_commands).start()
    print('done write_gunicorn_socket')

def write_gunicorn_service(install=True, output=None, remote_cmd=False):
    print('-write_gunicorn_service')
    if package_manager == 'apt':
        user = "www-data"
    elif package_manager == 'dnf':
        user = "nginx"
    # user = "www-data" if "ubuntu" in system_type else 'nginx'
    text = [ 
        "[Unit]\n",
        "Description=gunicorn daemon\n",
        "Requires=gunicorn.socket\n",
        "After=network.target\n",
        "\n",
        "[Service]\n",
        f"User={username}\n",
        f"Group={user}\n",
        f"WorkingDirectory=/home/{username}/Sonet/SoNodeServer\n",
        f"ExecStart=/home/{username}/Sonet/.data/env/bin/gunicorn \\\n",
        f"        --chdir /home/{username}/Sonet/SoNodeServer \\\n",
        f"        --log-file /home/{username}/Sonet/.data/logs/gunicorn.log \\\n",
        f"        --access-logfile /home/{username}/Sonet/.data/logs/gunicorn.log \\\n",
        f"        --error-logfile /home/{username}/Sonet/.data/logs/gunicorn.err.log \\\n",
        f"        --capture-output \\\n",
        f"        --log-level info \\\n",
        "        --workers 3 \\\n",
        "        --bind unix:/run/gunicorn.sock \\\n",
        "        sonet.wsgi:application\n",
        "\n",
        "\n",
        "[Install]\n",
        "WantedBy=multi-user.target\n",
    ]
    text_str = ''.join(text)
    with open("/tmp/gunicorn.service", "w") as temp_file:
        temp_file.write(text_str)
    commands = [
        ["sudo", "-S", "mv", "/tmp/gunicorn.service", "/etc/systemd/system/gunicorn.service"],
        ["sudo", "-S", "chmod", "644", "/etc/systemd/system/gunicorn.service"],        
    ]

    if package_manager == 'dnf':
        policy_text = """
        module nginx_gunicorn 1.0;

        require {
            type httpd_t;
            type unconfined_service_t;
            class unix_stream_socket connectto;
        }

        # Allow nginx to connect to gunicorn's Unix socket
        allow httpd_t unconfined_service_t:unix_stream_socket connectto;
        """

        with open("/tmp/nginx_gunicorn.te", "w") as f:
            f.write(policy_text.strip() + "\n")

    commands.append(["sudo", "-S", "systemctl", "daemon-reload"])
        
    if install or remote_cmd:
        get_variables()
        global systemPass
        for cmd in commands:
            print(cmd)
            update_output(cmd, output)
            try:
                r = subprocess.run(
                    cmd,
                    check=True,
                    input=f"{systemPass}\n".encode(),
                )
                print('r',r)
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr.decode().strip() if e.stderr else "No stderr output"
                print('error_msg',error_msg)
                update_output(f"Command failed:\n{error_msg}", output)
    else:
        from ops import CommandRunner
        import threading
        command_runner = CommandRunner(None, commands, None, None, special_commands)
        threading.Thread(target=command_runner.run_commands).start()
    print('done write_gunicorn_service')

def gunicorn_logrotate(install=True, output=None, remote_cmd=False):
    log_file = f"/home/{username}/Sonet/.data/logs/gunicorn*.log"
    conf_path = "/etc/logrotate.d/gunicorn"

    conf_text = f"""\
{log_file} {{
    size 25M
    rotate 5
    missingok
    notifempty
    compress
    delaycompress
    copytruncate
}}
"""

    with open(f"/tmp/gunicorn", "w") as f:
        f.write(conf_text)
    commands = [
        ["sudo", "-S", "mv", "/tmp/gunicorn", "/etc/logrotate.d"],
        ["sudo", "-S", "chown", "root:root", "/etc/logrotate.d/gunicorn"],
        ["sudo", "-S", "chmod", "0644", "/etc/logrotate.d/gunicorn"],
        ["sudo", "-S", "/usr/sbin/logrotate", "-f", "/etc/logrotate.d/gunicorn"], # test
    ]
    if install or remote_cmd:
        get_variables()
        global systemPass
        for cmd in commands:
            print(cmd)
            update_output(cmd, output)
            try:
                r = subprocess.run(
                    cmd,
                    check=True,
                    input=f"{systemPass}\n".encode(),
                )
                print('r',r)
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr.decode().strip() if e.stderr else "No stderr output"
                print('error_msg',error_msg)
                update_output(f"Command failed:\n{error_msg}", output)
    else:
        from ops import CommandRunner
        import threading
        command_runner = CommandRunner(None, commands, None, None, special_commands)
        threading.Thread(target=command_runner.run_commands).start()

def config_nginx(output=None, install=True, nodeData=None, remote_cmd=False, close_port=None, run_restart=False):
    print('-config_nginx')
    # system_type = platform.platform().lower()
    get_variables()
    global node_data
    if nodeData:
        node_data = nodeData
    address = ''
    global external_ip
    port = node_data['settings']['port']
    if 'external_ip' in node_data['settings']:
        external_ip = node_data['settings']['external_ip']
    if 'domain' in node_data['meta']:
        domain = f"*.{node_data['meta']['domain']}"
        w_domain = f'www.{domain}'
    else:
        domain = ''
        w_domain = ''
    if 'address' in node_data['settings']:
        address = node_data['settings']['address']
    elif 'nodeData' in node_data:
        if 'address' in node_data['nodeData']:
            address = node_data['nodeData']['address']
        elif domain and 'id' in node_data['nodeData']:
            address = f"{node_data['nodeData']['id']}.{domain}"

    if 'local_ip' in node_data['settings']:
        local_ip = node_data['settings']['local_ip']
    else:
        local_ip = ''
    text = [
        "server {\n", 
        f"  server_name  {domain} {address} {w_domain} 127.0.0.1 {local_ip} {external_ip};\n",
        f"listen {port};\n",
        "\n",
        "location = /favicon.ico { access_log off; log_not_found off; }\n",
        "location /static_cdn/ {\n",
        f"    root /home/{username}/Sonet/SoNodeServer;\n",
        "}\n",
        "\n",
        "location / {\n",
        "    proxy_pass http://unix:/run/gunicorn.sock;\n",
        "    proxy_set_header Host $host;\n",
        "    proxy_set_header X-Real-IP $remote_addr;\n",
        "    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n",
        "    proxy_set_header X-Forwarded-Proto $scheme;\n",
                
        "}\n",

        f"error_log /home/{username}/Sonet/.data/logs/nginx_err.log;\n",
        f"access_log /home/{username}/Sonet/.data/logs/nginx.log;\n",

        "}\n",
    ]
    text_str = ''.join(text)
    with open(f"/tmp/sonode_sites_avail", "w") as temp_file:
        temp_file.write(text_str)
    commands = []
    
    if package_manager == 'dnf':
        cmd = [
            'sudo', '-S', 'tee', '/etc/nginx/proxy_params'
        ]
        content = '''\
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        '''
        process = subprocess.run(cmd, input=content.encode(), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if process.returncode != 0:
            print("Error:", process.stderr.decode())
        else:
            print("proxy_params created successfully.")
            
        commands += [
            ["sudo", "-S", "mkdir", "-p", f"/etc/nginx/sites-available"],
            ['sudo', '-S', 'mv', '/etc/nginx/sites-enabled', '/etc/nginx/sites-enabled.bak'],
            ["sudo", "-S", "mkdir", '/etc/nginx/sites-enabled'],
            ["sudo", "-S", 'semanage', 'fcontext', '-a', '-t', 'httpd_config_t', f"/home/{username}/Sonet/\.data/special/cors\.conf"],
            ["sudo", "-S", 'restorecon', '-v', f"/home/{username}/Sonet/.data/special/cors.conf"],
            ["sudo", "-S", 'semanage', 'fcontext', '-a', '-t', 'httpd_config_t', f"/etc/nginx/sites-available/sonode"],
            ["sudo", "-S", 'restorecon', '-v', f"/etc/nginx/sites-available/sonode"],
            ["sudo", "-S", "semanage", "port", "-m", "-t", "http_port_t", "-p", "tcp", port],
    ]
    commands += [
        ["sudo", "-S", "mv", f"/tmp/sonode_sites_avail", f"/etc/nginx/sites-available/sonode"],
        ["sudo", "-S", "chown", "root:root", f"/etc/nginx/sites-available/sonode"],
        ["sudo", "-S", "chmod", "644", f"/etc/nginx/sites-available/sonode"],
        ["sudo", "-S", "ufw", "allow", port],
        ["sudo", "-S", "systemctl", "daemon-reload"]
    ]
    if close_port:
        commands.append(["sudo", "-S", "ufw", "delete", "allow", close_port])
    else:
        commands.append(["sudo", "-S", "ufw", "allow", port])
    if run_restart:
        commands.append(["sudo", "-S", "supervisorctl", "reload"])
        commands.append(["sudo", "-S", "systemctl", "daemon-reload"])
        commands.append(["sudo", "-S", "systemctl", "restart", "gunicorn"])
        commands.append(["sudo", "-S", "systemctl", "restart", "nginx"],)
    if install or remote_cmd:
        global systemPass
        for cmd in commands:
            print(cmd)
            update_output(cmd, output)
            try:
                r = subprocess.run(
                    cmd,
                    check=True,
                    input=f"{systemPass}\n".encode(),
                )
                print('r',r)
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr.decode().strip() if e.stderr else "No stderr output"
                print('error_msg',error_msg)
                update_output(f"Command failed:\n{error_msg}", output)

    else:
        from ops import CommandRunner
        import threading
        command_runner = CommandRunner(None, commands, None, None, special_commands)
        threading.Thread(target=command_runner.run_commands).start()

def edit_supervisor(install=True, output=None, remote_cmd=False):
    print('-edit_supervisor')
    text = [
        "[Service]\n",
        "Restart=always\n",
        "RestartSec=10\n",
        "\n",
        "[program:django_rq_main]\n",
        f"command=/home/{username}/Sonet/.data/env/bin/python -u manage.py rqworker main\n",
        f"directory=/home/{username}/Sonet/SoNodeServer\n",
        '''process_name=%(program_name)s\n''',
        "numprocs=1\n",
        "autostart=true\n",
        "autorestart=true\n",
        "stopsignal=TERM\n",
        "startsecs=0\n",
        f"user={username}\n",
        f"stdout_logfile=/home/{username}/Sonet/.data/logs/main_worker.log\n",
        "stdout_logfile_maxbytes=50MB\n",
        "stdout_logfile_backups=10\n",
        "redirect_stderr=true\n",
        "\n",

        "[program:django_rq_high]\n",
        f"command=/home/{username}/Sonet/.data/env/bin/python -u manage.py rqworker high\n",
        f"directory=/home/{username}/Sonet/SoNodeServer\n",
        '''process_name=%(program_name)s\n''',
        "numprocs=1\n",
        "autostart=true\n",
        "autorestart=true\n",
        "stopsignal=TERM\n",
        "startsecs=0\n",
        f"user={username}\n",
        f"stdout_logfile=/home/{username}/Sonet/.data/logs/high_worker.log\n",
        "stdout_logfile_maxbytes=50MB\n",
        "stdout_logfile_backups=10\n",
        "redirect_stderr=true\n",
        "\n",

        "[program:django_rq_low]\n",
        f"command=/home/{username}/Sonet/.data/env/bin/python -u manage.py rqworker low\n",
        f"directory=/home/{username}/Sonet/SoNodeServer\n",
        '''process_name=%(program_name)s\n''',
        "numprocs=1\n",
        "autostart=true\n",
        "autorestart=true\n",
        "stopsignal=TERM\n",
        "startsecs=0\n",
        f"user={username}\n",
        f"stdout_logfile=/home/{username}/Sonet/.data/logs/low_worker.log\n",
        "stdout_logfile_maxbytes=50MB\n",
        "stdout_logfile_backups=10\n",
        "redirect_stderr=true\n",
        "\n",

        "[program:django_rq_chat]\n",
        f"command=/home/{username}/Sonet/.data/env/bin/python -u manage.py rqworker chat\n",
        f"directory=/home/{username}/Sonet/SoNodeServer\n",
        '''process_name=%(program_name)s\n''',
        "numprocs=1\n",
        "autostart=true\n",
        "autorestart=true\n",
        "stopsignal=TERM\n",
        "startsecs=0\n",
        f"user={username}\n",
        f"stdout_logfile=/home/{username}/Sonet/.data/logs/chat_worker.log\n",
        "stdout_logfile_maxbytes=25MB\n",
        "stdout_logfile_backups=2\n",
        "redirect_stderr=true\n",
        "\n",

        "[program:django_rq_super]\n",
        f"command=/home/{username}/Sonet/.data/env/bin/python -u manage.py rqworker super\n",
        f"directory=/home/{username}/Sonet/SoNodeServer\n",
        '''process_name=%(program_name)s\n''',
        "numprocs=1\n",
        "autostart=true\n",
        "autorestart=true\n",
        "stopsignal=TERM\n",
        "startsecs=0\n",
        f"user={username}\n",
        f"stdout_logfile=/home/{username}/Sonet/.data/logs/super_worker.log\n",
        "stdout_logfile_maxbytes=25MB\n",
        "stdout_logfile_backups=5\n",
        "redirect_stderr=true\n",
        "\n",

        '[program:django_rqscheduler]\n',
        f'command=/home/{username}/Sonet/.data/env/bin/python manage.py rqscheduler --queue super --queue high --queue main --queue low\n',
        'process_name=%(program_name)s\n',
        'numprocs=1\n',
        f'directory=/home/{username}/Sonet/SoNodeServer\n',
        'stopsignal=TERM\n',
        'autostart=true\n',
        'autorestart=true\n',
        f'user={username}\n',
        'startsecs=0\n',
        f'stdout_logfile=/home/{username}/Sonet/.data/logs/rqscheduler.log\n',
        "stdout_logfile_maxbytes=25MB\n",
        "stdout_logfile_backups=2\n",
        "redirect_stderr=true\n",

        "\n",
        "[program:tor]\n",
        f"command=/home/{username}/Sonet/.data/env/bin/python /home/{username}/Sonet/SoNodeManager/scripts/onion_router.py\n",
        f"directory=/home/{username}/Sonet/SoNodeManager\n",
        "autostart=true\n",
        "autorestart=true\n",
        "startretries=5\n",
        f"stdout_logfile=/home/{username}/Sonet/.data/logs/tor.log\n",
        f"user={username}\n",
        "stdout_logfile_maxbytes=10MB\n",
        "stdout_logfile_backups=2\n",
        "redirect_stderr=true\n",
        'environment=PYTHONUNBUFFERED="1"\n',

        "\n",
        "[program:health_monitor]\n",
        f"command=/home/{username}/Sonet/.data/nenv/bin/python /home/{username}/Sonet/SoNodeManager/scripts/health_check.py\n",
        f"directory=/home/{username}/Sonet\n",
        "process_name=%(program_name)s\n",
        "autostart=true\n",
        "autorestart=true\n",
        "startsecs=0\n",
        "stopsignal=TERM\n",
        f"user={username}\n",
        f"stdout_logfile=/home/{username}/Sonet/.data/logs/node_health.log\n",
        "stdout_logfile_maxbytes=25MB\n",
        "stdout_logfile_backups=5\n",
        "redirect_stderr=true\n",

    ]
    text_str = ''.join(text)
    if package_manager == 'apt':
        with open("/tmp/django_rq.conf", "w") as temp_file:
            temp_file.write(text_str)
        commands = [
            ["sudo", "-S", "mv", "/tmp/django_rq.conf", "/etc/supervisor/conf.d/django_rq.conf"],
            ["sudo", "-S", "chown", "root:root", "/etc/supervisor/conf.d/django_rq.conf"],
            ["sudo", "-S", "chmod", "644", "/etc/supervisor/conf.d/django_rq.conf"],
            ["sudo", "-S", "systemctl", "daemon-reload"]
        ]
    elif package_manager == 'dnf':
        with open("/tmp/django_rq.ini", "w") as temp_file:
            temp_file.write(text_str)
        commands = [
            ["sudo", "-S", "mkdir", "-p", "/etc/supervisord.d"],
            ["sudo", "-S", "mv", "/tmp/django_rq.ini", "/etc/supervisord.d/django_rq.ini"],
            ["sudo", "-S", "chown", "root:root", "/etc/supervisord.d/django_rq.ini"],
            ["sudo", "-S", "chmod", "644", "/etc/supervisord.d/django_rq.ini"],
            ["sudo", "-S", "systemctl", "daemon-reload"],
            ["sudo", "-S", "systemctl", "enable", "--now", "supervisord"]
        ]
    if install or remote_cmd:
        get_variables()
        global systemPass
        for cmd in commands:
            print(cmd)
            update_output(cmd, output)
            try:
                r = subprocess.run(
                    cmd,
                    check=True,
                    input=f"{systemPass}\n".encode(),
                )
                print('r',r)
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr.decode().strip() if e.stderr else "No stderr output"
                print('error_msg',error_msg)
                update_output(f"Command failed:\n{error_msg}", output)
                raise
    else:
        from ops import CommandRunner
        import threading
        command_runner = CommandRunner(None, commands, None, None, special_commands)
        threading.Thread(target=command_runner.run_commands).start()
    print('done edit_supervisor')

def install_postgres(output=None, remote_cmd=False):
    import subprocess
    get_variables()
    global systemPass
    if package_manager == 'apt':
        cmds = [
            ['sudo', '-S', package_manager, 'install', 'postgresql', 'postgresql-contrib', '-y'],
            ['sudo', '-S', 'systemctl', 'start', 'postgresql'],
        ]
    elif package_manager == 'dnf':
        def get_dnf_command():
            if shutil.which("dnf5"):
                return "dnf5"
            elif shutil.which("dnf"):
                return "dnf"
            else:
                raise RuntimeError("Neither dnf nor dnf5 found on system")
        dnf_cmd = get_dnf_command()
        cmds = [
            ['sudo', '-S', dnf_cmd, 'install', 'postgresql-server', '-y'],
        ]
        def is_postgres_initialized():
            result = subprocess.run(
                ['sudo', '-u', 'postgres', 'test', '-f', '/var/lib/pgsql/data/PG_VERSION'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return result.returncode == 0
        if not is_postgres_initialized():
            cmds.append(['sudo', '-S', '/sbin/postgresql-setup', '--initdb'])
        cmds.append(['sudo', '-S', 'systemctl', 'enable', '--now', 'postgresql'])
        cmds.append([
            "sudo", "-S", "-i", "-u", "postgres",
            "bash", "-c",
            "sed -i 's/ident/md5/g' /var/lib/pgsql/data/pg_hba.conf"
        ])
        cmds.append(["sudo", "-S", "systemctl", "restart", "postgresql"])

    for cmd in cmds:
        print(cmd)
        update_output(cmd, output)
        Clock.schedule_once(lambda dt, line=cmd: update_output(line, output))
        try:
            subprocess.run(
                cmd,
                check=True,
                input=f"{systemPass}\n".encode(),
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode().strip() if e.stderr else "No stderr output"
            print('error_msg',error_msg)
            update_output(f"Command failed:\n{error_msg}", output)
            raise

    return None

def download_chrome(output=None, remote_cmd=False):
    get_variables()
    global systemPass
    r = requests.get('https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_STABLE')
    if r.status_code == 200:
        stable_ver = r.content.decode('utf-8')

        if package_manager == 'apt':
            commands = [
                ['wget', '-O', '/tmp/chrome.deb', f'https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_{stable_ver}-1_amd64.deb'],
                ['sudo', '-S', package_manager, 'install', '-y', '/tmp/chrome.deb'],
                ['rm', '/tmp/chrome.deb'],
            ]
        elif package_manager == 'dnf':
            commands = [
                ['wget', '-O', '/tmp/chrome.rpm', f'https://dl.google.com/linux/chrome/rpm/stable/x86_64/google-chrome-stable-{stable_ver}-1.x86_64.rpm'],
                ['sudo', '-S', package_manager, 'install', '-y', '/tmp/chrome.rpm'],
                ['rm', '/tmp/chrome.rpm'],
            ]
        
        # commands += [
        #     ['wget', '-O', '/tmp/chromedriver-linux64.zip', f'https://storage.googleapis.com/chrome-for-testing-public/{stable_ver}/linux64/chromedriver-linux64.zip'],
        #     ["sudo", "-S", package_manager, "install", "zip"],
        #     ["sudo", "-S", "unzip", '-o', "/tmp/chromedriver-linux64.zip"],
        #     ["sudo", "-S", "mv", "/tmp/chromedriver/chromedriver-linux64/chromedriver", "/usr/local/bin/"],
        #     ["sudo", "-S", "chown", "root:root", "/usr/local/bin/chromedriver"],
        #     ["sudo", "-S", "chmod", "+x", "/usr/local/bin/chromedriver"],
        #     ["sudo", "-S", "rm", "/tmp/chromedriver-linux64.zip"],
        # ]



        for cmd in commands:
            update_output(cmd, output)
            if 'unzip' in cmd:
                import zipfile
                with zipfile.ZipFile("/tmp/chromedriver-linux64.zip", 'r') as zip_ref:
                    zip_ref.extractall("/tmp/chromedriver")
            else:
                try:
                    r = subprocess.run(
                        cmd,
                        check=True,
                        input=f"{systemPass}\n".encode(),
                    )
                    print('r',r)
                except subprocess.CalledProcessError as e:
                    error_msg = e.stderr.decode().strip() if e.stderr else "No stderr output"
                    print('error_msg',error_msg)
                    update_output(f"Command failed:\n{error_msg}", output)
                    return False
        print('donw all chrome commands')
        return True

    
def edit_nginx(install=True, output=None, remote_cmd=False):
    if package_manager == 'apt':
        user = "www-data"
    elif package_manager == 'dnf':
        user = "nginx"
    # user = "www-data" if "ubuntu" in system_type else "nginx"
        # f"  include /home/{username}/myProject/.data/special/cors.conf;\n",
    text = [
        f"user {user};\n",
        "worker_processes auto;\n",
        "pid /run/nginx.pid;\n",
        f"error_log /home/{username}/Sonet/.data/logs/nginx_err.log;\n",
        "include /etc/nginx/modules-enabled/*.conf;\n",
        "events {\n",
        "   worker_connections 768;\n",
        "   # multi_accept on;\n",
        "}\n",
        "http {\n",
        "   sendfile on;\n",
        "   tcp_nopush on;\n",
        "   types_hash_max_size 2048;\n",
        "   client_max_body_size 50M;\n",
        "   include /etc/nginx/mime.types;\n",
        "   default_type application/octet-stream;\n",
        "   ssl_protocols TLSv1 TLSv1.1 TLSv1.2 TLSv1.3;\n",
        "   ssl_prefer_server_ciphers on;\n",
        f"   access_log /home/{username}/Sonet/.data/logs/nginx.log;\n",
        "   gzip on;\n",
        "   include /etc/nginx/conf.d/*.conf;\n",
        "   include /etc/nginx/sites-enabled/*;\n",
        "}\n",
    ]
    text_str = ''.join(text)
    with open("/tmp/nginx.conf", "w") as temp_file:
        temp_file.write(text_str)
    commands = [
        ["sudo", "-S", "mv", "/tmp/nginx.conf", "/etc/nginx/nginx.conf"],
        ["sudo", "-S", "chown", "root:root", "/etc/nginx/nginx.conf"],
        ["sudo", "-S", "chmod", "644", "/etc/nginx/nginx.conf"],
    ]
    
    if package_manager == 'dnf':
        commands += [
            # ["sudo", "-S", "dnf", "install", "policycoreutils-python-utils", "-y"],
            ["sudo", "-S", "restorecon", "-Rv", "/etc/nginx"],
            # ['sudo', '-S', 'semanage', 'fcontext', '-a', '-t', 'httpd_log_t', f'/home/{username}/Sonet/\.data/logs(/.*)?'],
            
            # ['sudo', '-S', 'semanage', 'fcontext', '-a', '-t', 'httpd_log_t', f'/home/{username}/Sonet/\.data/logs/nginx.log'],
            # ['sudo', '-S', 'semanage', 'fcontext', '-a', '-t', 'httpd_log_t', f'/home/{username}/Sonet/\.data/logs/nginx_err.log'],
            # ['sudo', '-S', 'restorecon', f'/home/{username}/Sonet/\.data/logs/nginx.log'],
            # ['sudo', '-S', 'restorecon', f'/home/{username}/Sonet/\.data/logs/nginx_err.log'],

            ["sudo", "-S", "touch", f"/home/{username}/Sonet/.data/logs/nginx_err.log"],
            ["sudo", "-S", "touch", f"/home/{username}/Sonet/.data/logs/nginx.log"],

            # ['sudo', '-S', 'semanage', 'fcontext', '-d', f'/home/{username}/Sonet/.data/logs/nginx_err.log'],
            ['sudo', '-S', 'semanage', 'fcontext', '-a', '-t', 'httpd_log_t', f'/home/{username}/Sonet/.data/logs/nginx_err.log'],
            ['sudo', '-S', 'restorecon', '-v', f'/home/{username}/Sonet/.data/logs/nginx_err.log'],
            # ['sudo', '-S', 'semanage', 'fcontext', '-d', f'/home/{username}/Sonet/.data/logs/nginx.log'],
            ['sudo', '-S', 'semanage', 'fcontext', '-a', '-t', 'httpd_log_t', f'/home/{username}/Sonet/.data/logs/nginx.log'],
            ['sudo', '-S', 'restorecon', '-v', f'/home/{username}/Sonet/.data/logs/nginx.log'],
        ]

    commands += [
        ["sudo", "-S", "systemctl", "daemon-reload"]
    ]

    if install or remote_cmd:
        get_variables()
        global systemPass
        for cmd in commands:
            # print(cmd)
            update_output(cmd, output)
            try:
                r = subprocess.run(
                    cmd,
                    check=True,
                    input=f"{systemPass}\n".encode(),
                )
                print('r',r)
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr.decode().strip() if e.stderr else "No stderr output"
                print('error_msg',error_msg)
                update_output(f"Command failed:\n{error_msg}", output)
                raise
    else:
        from ops import CommandRunner
        import threading
        command_runner = CommandRunner(None, commands, None, None, special_commands)
        threading.Thread(target=command_runner.run_commands).start()
    print('done edit_nginx')


def update_shell_path(): # not used
    shell_config = os.path.expanduser("~/.bashrc")
    export_lines = [
        f'export PATH=$PATH:$HOME/chrome-for-testing/chrome-linux64/',
        f'export PATH=$PATH:$HOME/chrome-for-testing/chromedriver-linux64/',
    ]
    with open(shell_config, "a") as f:
        for line in export_lines:
            f.write(line + "\n")

def pause(remote_cmd=False):
    print('pausing')
    import time
    time.sleep(5)

def finalize(output=None, remote_cmd=False):
    get_variables()
    global operatorData
    global node_data
    from commands.utils import finalize_install
    finalize_install(output=output, node_data=node_data, operatorData=operatorData)

remove_for_quick_install = [
    ['run_command', 'run_create_env'],
    # ['run_command', 'install_postgres'],
    ["python3", "-m", "venv", homepath + "/Sonet/.data/env"],
    ['install_requirements', homepath + "/Sonet/SoNodeServer/requirements.txt", homepath + f"/Sonet/.data/env/bin/pip"],
    ['run_command', 'download_chrome'],
]

remove_for_new_database = [
    ["sudo", "-S", "-i", "-u", "postgres", "psql", "-c", "DROP DATABASE so_data;"],
    ["sudo", "-S", "-i", "-u", "postgres", "psql", "-c", "CREATE DATABASE so_data OWNER queue;"],
]

special_commands = [
    {'cmd':'hardware_check', 'reqs':'output_display'},
    {'cmd':'run_fetch_secret_key', 'reqs':'display_content'},
    {'cmd':'run_adjust_settings', 'reqs':'output_display'},
    {'cmd':'get_local_ip', 'reqs':'display_content'},
    {'cmd':'install_cloudflared', 'reqs':'output_display'},
    {'cmd':'write_gunicorn_socket', 'reqs':'output_display'},
    {'cmd':'write_gunicorn_service', 'reqs':'output_display'},
    {'cmd':'gunicorn_logrotate', 'reqs':'output_display'},
    {'cmd':'config_nginx', 'reqs':'output_display'},
    {'cmd':'install_postgres', 'reqs':'output_display'},
    {'cmd':'edit_supervisor', 'reqs':'output_display'},
    {'cmd':'edit_nginx', 'reqs':'output_display'},
    {'cmd':'download_chrome', 'reqs':'output_display'},
    {'cmd':'get_variables'},
    {'cmd':'run_create_env', 'reqs':'output_display'},
    {'cmd':'pull_git', 'reqs':'output_display'},
    {'cmd':'adjust_firewall', 'reqs':'output_display'},
    {'cmd':'finalize', 'reqs':'output_display'},
    {'cmd':'pause'},
]

action_cmds = [
    ['run_command', 'get_variables'],
    ['run_command', 'hardware_check'],
    ['run_command', 'pull_git'],
    ['run_command', 'adjust_firewall'],
    ["chmod", "755", homepath + "/Sonet/SoNodeServer"],
    ['sudo', '-S', package_manager, update_func, '--fix-missing'],
    ['sudo', '-S', package_manager, 'install', '-f'],
    ['sudo', '-S', 'dpkg', '--configure', '-a'],
    ['sudo', '-S', package_manager, update_func],
    ['sudo', '-S', package_manager, 'install', '-y', 'build-essential', 'curl', 'libssl-dev', 'zlib1g-dev'],
    ['sudo', '-S', package_manager, 'install', 'tor'],
    ['sudo', '-S', package_manager, 'install', '-y', 'libbz2-dev', 'libreadline-dev',  'libncursesw5-dev'],
    ['sudo', '-S', package_manager, 'install', '-y', 'xz-utils', 'tk-dev', 'libxml2-dev', 'libxmlsec1-dev'],
    ['sudo', '-S', package_manager, 'install', '-y', 'libffi-dev', 'liblzma-dev','libsqlite3-dev', 'sshpass'],
    ['run_command', 'install_cloudflared'],
    ['run_command', 'run_create_env'],
    ['install_requirements', homepath + "/Sonet/SoNodeServer/requirements.txt", homepath + f"/Sonet/.data/env/bin/pip"],
    # ["sudo", "-S", "hostname", "-I"],
    ['run_command', 'get_local_ip'],
    f'''/home/{username}/Sonet/.data/env/bin/python3 {homepath}/Sonet/SoNodeServer/manage.py shell -c "from django.core.management.utils import get_random_secret_key; print('key:', get_random_secret_key())"''',
    ['run_command', 'pause'], # for get_random_secret_key to complete
    ['run_command', 'run_fetch_secret_key'],
    ['run_command', 'run_adjust_settings'],
    ["sudo", "-S", package_manager, update_func],
    ['run_command', 'install_postgres'],
    f"echo 'input_pass' | sudo -S -u postgres psql -U postgres -c 'CREATE USER queue WITH PASSWORD \\'K9V43S2P1\\';'",
    f"echo 'input_pass' | sudo -S -u postgres psql -U postgres -c 'ALTER USER queue WITH SUPERUSER CREATEDB CREATEROLE;'",
    f"echo 'input_pass' | sudo -S -u postgres psql -U postgres -c 'DROP DATABASE IF EXISTS so_data;'",
    f"echo 'input_pass' | sudo -S -u postgres psql -U postgres -c 'CREATE DATABASE so_data OWNER queue;'",
    f"echo 'input_pass' | sudo -S {homepath}/Sonet/.data/env/bin/python3 {homepath}/Sonet/SoNodeServer/manage.py migrate",
    ["sudo", "-S", f"{homepath}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "migrate"],
    [f"/home/{username}/Sonet/.data/env/bin/pip", "install", "gunicorn"],
    ['sudo', '-S', package_manager, 'install', 'redis', '-y'],
    ['sudo', '-S', 'systemctl', 'start', 'redis'],
    ['run_command', 'download_chrome'],
    ["sudo", "-S", package_manager, update_func],
    nginx_install_command,
    ["sudo", "-S", "chown", "root:root", "/etc/systemd/system/gunicorn.socket"],
    ["run_command", "write_gunicorn_socket"],
    ["sudo", "-S", "chown", "root:root", "/etc/systemd/system/gunicorn.service"],
    ["run_command", "write_gunicorn_service"],
    ["run_command", "gunicorn_logrotate"],
    ["raise_if_error", "sudo", "-S", f"{homepath}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "check"],
    ["sudo", "-S", "systemctl", "daemon-reexec"],
    ["sudo", "-S", "systemctl", "daemon-reload"],
    ["sudo", "-S", "systemctl", "stop", "gunicorn.socket"],
    ["sudo", "-S", "systemctl", "enable", "--now", "gunicorn.socket"],
    ["sudo", "-S", "systemctl", "restart", "gunicorn"],
    ["file", "/run/gunicorn.sock"],
    ["run_command", "config_nginx"],
    ["sudo", "-S", "ln", "-s", "/etc/nginx/sites-available/sonode", "/etc/nginx/sites-enabled"],
    ["sudo", "-S", "rm", "/etc/nginx/sites-available/default"],
    ["sudo", "-S", "rm", "/etc/nginx/sites-enabled/default"],
    ["run_command", "edit_nginx"],
    ["sudo", "-S", package_manager, "install", "supervisor", "-y"],
    ['run_command', 'edit_supervisor'],
    ["sudo", "-S", "supervisorctl", "reread"],
    ["sudo", "-S", "supervisorctl", "update"],
    ["sudo", "-S", "supervisorctl", "status"],
    ["sudo", "-S", "systemctl", "daemon-reexec"],
    ["sudo", "-S", "systemctl", "daemon-reload"],
    ["sudo", "-S", "systemctl", "enable", "--now", "nginx"],
    ["sudo", "-S", "chown", "-R", f"{username}:{username}", homepath + "/Sonet/.data/logs"],
    ["sudo", "-S", "chmod", "-R", f"755", homepath + "/Sonet/.data/logs"],
    ["sudo", "-S", "supervisorctl", "reload"],
    ["sudo", "-S", "systemctl", "daemon-reload"],
    ["sudo", "-S", "systemctl", "restart", "gunicorn"],
    ["sudo", "-S", "systemctl", "restart", "nginx"],
    [f"echo 'y' | sudo -S {package_manager} autoremove"],
    ['run_command', 'finalize'],
    # ['echo', 'Finished!'],
]


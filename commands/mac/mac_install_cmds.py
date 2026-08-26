
import os
import subprocess
import getpass
import requests
import re
from os.path import expanduser
from kivy.clock import Clock

from ..utils import get_operatorData, write_operatorData, fetch_secure_item


username = getpass.getuser()
# print(username)
homepath = expanduser("~")
# print(homepath)
group = subprocess.check_output("id -gn", shell=True).decode().strip()
uid = os.getuid()
# brew_path = shutil.which("brew")


operatorData = {}
sonet_title = ''
external_ip = ''
node_data = {}
node_id = ''
port = ''
open_ports = ''
systemPass = ''


def find_brew():
    for p in ("/opt/homebrew/bin/brew", "/usr/local/bin/brew"):
        if os.path.exists(p):
            return p
    return "/opt/homebrew/bin/brew"

brew_path = find_brew()
psql_path = '/opt/homebrew/bin/psql'


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

def get_variables(remote_cmd=False):
    global operatorData
    global sonet_title
    global open_ports
    global port
    global external_ip
    global node_data
    global node_id
    global systemPass
    global brew_path
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
        brew_path = find_brew()

        systemPass = fetch_secure_item('sysPass')
        if not systemPass and 'systemPass' in operatorData:
            systemPass = operatorData['systemPass']

        try:
            sonet_title = operatorData['sonet']['title']
        except:
            sonet_title = 'SoNode'

def pull_git(output, remote_cmd=False):
    get_variables()
    from commands.utils import pull_git_server
    global operatorData
    pull_git_server(output=output, operatorData=operatorData)

def setup_firewall(open_port=True, output=None, nodeData=None, remote_cmd=False):
    print('-setup_firewall')
    get_variables()
    global node_data
    if nodeData:
        node_data = nodeData

def run_create_env(output, remote_cmd=False):
    get_variables()
    from commands.utils import setup_pyenv
    global node_data
    setup_pyenv(output=output, node_data=node_data)

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
        if not content.endswith('\n'):
            content += '\n'
        if output_display:
            Clock.schedule_once(lambda dt, line=content: schedule(line, output_display))
        print(content)
    except Exception as e:
        # print('update_output err',str(e))
        pass


def get_pg_version(brew_path):
    """Get the version of postgresql that brew just installed."""
    result = subprocess.run([brew_path, 'list', '--versions', 'postgresql'], capture_output=True, text=True)
    match = re.search(r'(\d+)\.\d+', result.stdout)
    if match:
        return match.group(1)
    raise RuntimeError("Could not detect installed PostgreSQL version")

pg_version = get_pg_version(brew_path)
pg_data_dir = f'/opt/homebrew/var/postgresql@{pg_version}'

def get_local_ip(remote_cmd=False):
    print('-get_local_ip')
    get_variables()
    global operatorData
    import subprocess
    local_ip = subprocess.check_output(["ipconfig", "getifaddr", "en0"]).decode().strip()
    print('local_ip',local_ip)
    node_data['settings']['local_ip'] = local_ip
    operatorData['myNodes'][node_id] = node_data
    write_operatorData(operatorData)

def run_fetch_secret_key(output, remote_cmd=False):
    get_variables()
    from commands.utils import fetch_django_secret_key
    global node_data
    global node_id
    global operatorData
    operatorData = fetch_django_secret_key(output=output, node_data=node_data, node_id=node_id, operatorData=operatorData)

def run_adjust_settings(output=None, remote_cmd=False):
    get_variables()
    from commands.utils import adjust_settings
    global node_data
    global operatorData
    adjust_settings(node_data=node_data, clear_data=True, output=output, operatorData=operatorData)

def fetch_chrome_and_chromedriver(output=None, remote_cmd=False): 
    # update to match linux method - no chromedriver
    r = requests.get('https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_STABLE')
    if r.status_code == 200:
        stable_ver = r.content.decode('utf-8')
        chrome_link = f'https://storage.googleapis.com/chrome-for-testing-public/{stable_ver}/mac-arm64/chrome-mac-arm64.zip'
        driver_link = f'https://storage.googleapis.com/chrome-for-testing-public/{stable_ver}/mac-arm64/chromedriver-mac-arm64.zip'

        update_output(chrome_link, output)
        update_output('Downloading chrome...', output)
        import urllib.request

        try:
            local_file, headers = urllib.request.urlretrieve(chrome_link, '/tmp/chrome.zip')
            # print(f"Downloaded successfully to {local_file}")
            content = f"chrome downloaded successfully:\n"
            update_output(content, output)
        except Exception as e:
            print(f"Download failed: {e}")
            content = f"Error downloading chrome:\n{e}"
            update_output(content, output)
            raise content

        update_output(driver_link, output)
        update_output('Downloading chromedriver...', output)
        try:
            local_file, headers = urllib.request.urlretrieve(driver_link, '/tmp/chromedriver.zip')
            # print(f"Downloaded successfully to {local_file}")
            content = f"chromedriver downloaded successfully:\n"
            update_output(content, output)
        except Exception as e:
            print(f"Download failed: {e}")
            content = f"Error downloading chromedriver:\n{e}"
            update_output(content, output)
            raise content
        
        # defaults write com.google.Chrome BreakpadEnable -bool false
        result = subprocess.run(['defaults', 'write', 'com.google.Chrome', 'BreakpadEnable', '-bool', 'false'], capture_output=True)
        if result.returncode == 0:
            content = f"crash report adjusted successfully:\n{result.stdout}"
            update_output(content, output)
        else:
            content = f"Error adjusting chrash report:\n{result.stderr}"
            update_output(content, output)
            raise content
        return True
    return 'failed to get latest chrome version'

def update_path(remote_cmd=False):
    zshrc_path = os.path.expanduser("~/.zshrc")
    path_line = 'export PATH="/usr/local/bin:$PATH"\n'

    with open(zshrc_path, "r+") as f:
        content = f.read()
        if path_line not in content:
            f.write("\n" + path_line)

    os.environ["PATH"] = "/usr/local/bin:" + os.environ["PATH"]

def write_supervisor_plist2(install=True, output=None, nodeData=None, remote_cmd=False):
    print('-write_supervisor_plist')
    text = [
        '''<?xml version="1.0" encoding="UTF-8"?>\n''',
        '''<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n''',
        '''<plist version="1.0">\n''',
        '''<dict>\n''',
        '''    <key>Label</key>\n''',
        '''    <string>com.sonet.supervisor</string>\n''',
        '''    \n''',
        '''    <key>ProgramArguments</key>\n''',
        '''    <array>\n''',
        '''        <string>/opt/homebrew/bin/supervisord</string>\n''',
        '''        <string>-c</string>\n''',
        f'''       <string>/Users/{username}/Sonet/.data/supervisor/supervisord.conf</string>\n''',
        '''    </array>\n''',
        '''    \n''',
        '''    <key>RunAtLoad</key>\n''',
        '''    <true/>\n''',
        '''    \n''',
        '''    <key>KeepAlive</key>\n''',
        '''    <true/>\n''',
        '''    \n''',
        '''    <key>WorkingDirectory</key>\n''',
        f'''    <string>/Users/{username}/Sonet</string>\n''',
            '''\n''',
        '''    <key>StandardOutPath</key>\n''',
        f'''    <string>/Users/{username}/Sonet/.data/logs/supervisor.log</string>\n''',
            '''\n''',
        '''    <key>StandardErrorPath</key>\n''',
        f'''    <string>/Users/{username}/Sonet/.data/logs/supervisor.err</string>\n''',
            '''\n''',
        '''</dict>\n''',
        '''</plist>\n''',

    ]
    text_str = ''.join(text)
    with open("/tmp/com.sonet.supervisor.plist", "w") as temp_file:
        temp_file.write(text_str)
    commands = [
        ["sudo", "-S", "mv", "/tmp/com.sonet.supervisor.plist", f"/Users/{username}/Library/LaunchAgents/com.sonet.supervisor.plist"],
        ['chmod', '644', f"/Users/{username}/Library/LaunchAgents/com.sonet.supervisor.plist"],
    ]
    if install or remote_cmd:
        get_variables()
        global systemPass
        for cmd in commands:
            update_output(cmd, output)
            result = subprocess.run(cmd, input=systemPass, text=True, capture_output=True)
            if result.returncode == 0:
                content = f"supervisor.plist configured successfully:\n{result.stdout}"
                update_output(content, output)
            else:
                content = f"Error configuring supervisor.plist:\n{result.stderr}"
                update_output(content, output)
                raise content
    else:
        from ops import CommandRunner
        import threading
        command_runner = CommandRunner(None, commands, None, None, special_commands)
        threading.Thread(target=command_runner.run_commands).start()

def write_supervisor_plist(install=True, output=None, nodeData=None, remote_cmd=False):
    dest = os.path.expanduser(f'~/Library/LaunchAgents/com.sonet.supervisor.plist')
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    text = [
    f'''<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
        <plist version="1.0">
        <dict>
            <key>Label</key>
            <string>com.sonet.supervisor</string>
            <key>ProgramArguments</key>
            <array>
                <string>/opt/homebrew/bin/supervisord</string>
                <string>-n</string>
                <string>-c</string>
                <string>/Users/sozed/Sonet/.data/supervisor/supervisord.conf</string>
            </array>
            <key>RunAtLoad</key>
            <true/>
            <key>KeepAlive</key>
            <dict>
                <key>SuccessfulExit</key>
                <false/>
                <key>Crashed</key>
                <true/>
            </dict>
            <key>WorkingDirectory</key>
            <string>/Users/sozed/Sonet</string>
            <key>StandardOutPath</key>
            <string>/Users/sozed/Sonet/.data/logs/supervisor.log</string>
            <key>StandardErrorPath</key>
            <string>/Users/sozed/Sonet/.data/logs/supervisor.err</string>
        </dict>
        </plist>'''
    ]
    text_str = ''.join(text)
    with open(dest, 'w') as f:
        f.write(text_str)
    os.chmod(dest, 0o644)
    update_output(f'Written {dest}', output)

def config_supervisor(install=True, output=None, nodeData=None, remote_cmd=False):
    print('-config_supervisor')
    text = [
        '''[supervisord]\n''',
        "nodaemon=false\n",
        f'''logfile=/Users/{username}/Sonet/.data/logs/supervisord.log\n''',
        f'''pidfile=/Users/{username}/Sonet/.data/supervisor/supervisord.pid\n''',
        f'''childlogdir=/Users/{username}/Sonet/.data/logs\n''',
        f'''stdout_logfile=/Users/{username}/Sonet/.data/logs/supervisord.log\n''',
        f'''stderr_logfile=/Users/{username}/Sonet/.data/logs/supervisord_err.log\n''',
        "stdout_logfile_maxbytes=10MB\n",
        "stdout_logfile_backups=2\n",
        f'''user={username}\n''',

        '''\n[unix_http_server]\n''',
        f'''file=/Users/{username}/Sonet/.data/supervisor/supervisor.sock\n''',
        '''chmod=0700\n''',
        f'''chown={username}:staff\n''',

        '''\n[rpcinterface:supervisor]\n''',
        '''supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface\n''',

        '''\n[supervisorctl]\n''',
        f'''serverurl=unix:///Users/{username}/Sonet/.data/supervisor/supervisor.sock\n''',
        '''chmod=700\n''',
        f'''stdout_logfile=/Users/{username}/Sonet/.data/logs/supervisorctl.log\n''',
        f'''stderr_logfile=/Users/{username}/Sonet/.data/logs/supervisorctl_err.log\n''',
        "stdout_logfile_maxbytes=10MB\n",
        "stdout_logfile_backups=2\n",
        "\n",

        '''[program:gunicorn]\n''',
        f'''command=/Users/{username}/Sonet/.data/supervisor/gunicorn_start.sh\n''',
        '''autostart=true\n''',
        '''autorestart=true\n''',
        f'''stderr_logfile=/Users/{username}/Sonet/.data/logs/gunicorn.err.log\n''',
        f'''stdout_logfile=/Users/{username}/Sonet/.data/logs/gunicorn.log\n''',
        "stdout_logfile_maxbytes=10MB\n",
        "stderr_logfile_maxbytes=10MB\n",
        f'''user={username}\n''',

        "\n",
        "[program:nginx]\n",
        f"command=/opt/homebrew/bin/nginx -g 'daemon off;'\n",
        "autostart=true\n",
        "autorestart=true\n",
        "startsecs=3\n",
        f"stdout_logfile=/Users/{username}/Sonet/.data/logs/nginx_supervisor.log\n",
        "stdout_logfile_maxbytes=10MB\n",
        "stdout_logfile_backups=5\n",
        "redirect_stderr=true\n",

        "\n",
        "[program:django_rq_main]\n",
        f"command=/Users/{username}/Sonet/.data/env/bin/python -u manage.py rqworker main\n",
        f"directory=/Users/{username}/Sonet/SoNodeServer\n",
        '''process_name=%(program_name)s\n''',
        "numprocs=1\n",
        "autostart=true\n",
        "autorestart=true\n",
        "stopsignal=TERM\n",
        "startsecs=0\n",
        f"user={username}\n",
        f"stdout_logfile=/Users/{username}/Sonet/.data/logs/main_worker.log\n",
        "stdout_logfile_maxbytes=50MB\n",
        "stdout_logfile_backups=10\n",
        "redirect_stderr=true\n",
        "environment=OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES\n",
        "\n",

        "[program:django_rq_high]\n",
        f"command=/Users/{username}/Sonet/.data/env/bin/python -u manage.py rqworker high\n",
        f"directory=/Users/{username}/Sonet/SoNodeServer\n",
        '''process_name=%(program_name)s\n''',
        "numprocs=1\n",
        "autostart=true\n",
        "autorestart=true\n",
        "stopsignal=TERM\n",
        "startsecs=0\n",
        f"user={username}\n",
        f"stdout_logfile=/Users/{username}/Sonet/.data/logs/high_worker.log\n",
        "stdout_logfile_maxbytes=50MB\n",
        "stdout_logfile_backups=10\n",
        "redirect_stderr=true\n",
        "environment=OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES\n",
        "\n",

        "[program:django_rq_low]\n",
        f"command=/Users/{username}/Sonet/.data/env/bin/python -u manage.py rqworker low\n",
        f"directory=/Users/{username}/Sonet/SoNodeServer\n",
        '''process_name=%(program_name)s\n''',
        "numprocs=1\n",
        "autostart=true\n",
        "autorestart=true\n",
        "stopsignal=TERM\n",
        "startsecs=0\n",
        f"user={username}\n",
        f"stdout_logfile=/Users/{username}/Sonet/.data/logs/low_worker.log\n",
        "stdout_logfile_maxbytes=50MB\n",
        "stdout_logfile_backups=10\n",
        "redirect_stderr=true\n",
        "environment=OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES\n",
        "\n",

        "[program:django_rq_chat]\n",
        f"command=/Users/{username}/Sonet/.data/env/bin/python -u manage.py rqworker chat\n",
        f"directory=/Users/{username}/Sonet/SoNodeServer\n",
        '''process_name=%(program_name)s\n''',
        "numprocs=1\n",
        "autostart=true\n",
        "autorestart=true\n",
        "stopsignal=TERM\n",
        "startsecs=0\n",
        f"user={username}\n",
        f"stdout_logfile=/Users/{username}/Sonet/.data/logs/chat_worker.log\n",
        "stdout_logfile_maxbytes=25MB\n",
        "stdout_logfile_backups=2\n",
        "redirect_stderr=true\n",
        "environment=OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES\n",
        "\n",

        "[program:django_rq_super]\n",
        f"command=/Users/{username}/Sonet/.data/env/bin/python -u manage.py rqworker super\n",
        f"directory=/Users/{username}/Sonet/SoNodeServer\n",
        '''process_name=%(program_name)s\n''',
        "numprocs=1\n",
        "autostart=true\n",
        "autorestart=true\n",
        "stopsignal=TERM\n",
        "startsecs=0\n",
        f"user={username}\n",
        f"stdout_logfile=/Users/{username}/Sonet/.data/logs/super_worker.log\n",
        "stdout_logfile_maxbytes=50MB\n",
        "stdout_logfile_backups=10\n",
        "redirect_stderr=true\n",
        "environment=OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES\n",
        "\n",

        '[program:django_rqscheduler]\n',
        f'command=/Users/{username}/Sonet/.data/env/bin/python manage.py rqscheduler --queue super --queue high --queue main --queue low\n',
        'process_name=%(program_name)s\n',
        'numprocs=1\n',
        f'directory=/Users/{username}/Sonet/SoNodeServer\n',
        'stopsignal=TERM\n',
        'autostart=true\n',
        'autorestart=true\n',
        f'user={username}\n',
        'startsecs=0\n',
        f'stdout_logfile=/Users/{username}/Sonet/.data/logs/rqscheduler.log\n',
        "stdout_logfile_maxbytes=25MB\n",
        "stdout_logfile_backups=2\n",
        "redirect_stderr=true\n",
        'environment=OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES\n',

        "\n",
        "[program:tor]\n",
        f"command=/Users/{username}/Sonet/.data/env/bin/python /Users/{username}/Sonet/SoNodeManager/scripts/onion_router.py\n",
        f"directory=/Users/{username}/Sonet/SoNodeManager\n",
        '''environment=PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin"\n''',
        "autostart=true\n",
        "autorestart=true\n",
        "startretries=5\n",
        f"stdout_logfile=/Users/{username}/Sonet/.data/logs/tor.log\n",
        f"user={username}\n",
        "stdout_logfile_maxbytes=10MB\n",
        "stdout_logfile_backups=5\n",
        "redirect_stderr=true\n",
        'environment=PYTHONUNBUFFERED="1"\n',

        # "\n",
        # "[program:health_monitor]\n",
        # f"command=/Users/{username}/Sonet/.data/nenv/bin/python /Users/{username}/Sonet/SoNodeManager/scripts/health_check.py\n",
        # f"directory=/Users/{username}/Sonet\n",
        # "process_name=%(program_name)s\n",
        # "autostart=true\n",
        # "autorestart=true\n",
        # "startsecs=0\n",
        # "stopsignal=TERM\n",
        # f"user={username}\n",
        # f"stdout_logfile=/Users/{username}/Sonet/.data/logs/node_health.log\n",
        # "stdout_logfile_maxbytes=25MB\n",
        # "stdout_logfile_backups=5\n",
        # "redirect_stderr=true\n",
    ]
    text_str = ''.join(text)
    with open("/tmp/supervisord.conf", "w") as temp_file:
        temp_file.write(text_str)
    commands = [
        ["sudo", "-S", "mv", "/tmp/supervisord.conf", f"/Users/{username}/Sonet/.data/supervisor/supervisord.conf"],
    ]
    if install or remote_cmd:
        get_variables()
        global systemPass
        for cmd in commands:
            update_output(cmd, output)
            result = subprocess.run(cmd, input=systemPass, text=True, capture_output=True)
            if result.returncode == 0:
                content = f"supervisor configured successfully:\n{result.stdout}"
                update_output(content, output)
            else:
                content = f"Error configuring supervisor:\n{result.stderr}"
                update_output(content, output)
                raise content
    else:
        from ops import CommandRunner
        import threading
        command_runner = CommandRunner(None, commands, None, None, special_commands)
        threading.Thread(target=command_runner.run_commands).start()

def setup_gunicorn(install=True, output=None, nodeData=None, remote_cmd=False):
    print('-setup_gunicorn...')
    text = [
        '''#!/bin/bash\n''',
        f'''cd /Users/{username}/Sonet\n\n''',
        f'''exec /Users/{username}/Sonet/.data/env/bin/gunicorn \\\n''',
        f'''    --bind unix:/Users/{username}/Sonet/.data/supervisor/gunicorn.sock \\\n''',
        '''    --workers=3 \\\n''',
        f'''    --chdir /Users/{username}/Sonet/SoNodeServer \\\n'''
        '''    --timeout 120 \\\n''',
        '''    --log-level info \\\n''',
        f'''    --log-file=/Users/{username}/Sonet/.data/logs/gunicorn.log \\\n''',
        f"        --capture-output \\\n",
        '''    sonet.wsgi:application \\\n''',
    ]
    text_str = ''.join(text)
    with open("/tmp/gunicorn_start.sh", "w") as temp_file:
        temp_file.write(text_str)
    commands = [
        ["sudo", "-S", "mv", "/tmp/gunicorn_start.sh", f"/Users/{username}/Sonet/.data/supervisor/gunicorn_start.sh"],
        ['sudo', '-S', 'chmod', '+x', f'/Users/{username}/Sonet/.data/supervisor/gunicorn_start.sh'],
    ]
    if install or remote_cmd:
        get_variables()
        global systemPass
        for cmd in commands:
            update_output(cmd, output)
            result = subprocess.run(cmd, input=systemPass, text=True, capture_output=True)
            if result.returncode == 0:
                content = f"gunicorn configured successfully:\n{result.stdout}"
                update_output(content, output)
            else:
                content = f"Error configuring gunicorn:\n{result.stderr}"
                update_output(content, output)
    else:
        from ops import CommandRunner
        import threading
        command_runner = CommandRunner(None, commands, None, None, special_commands)
        threading.Thread(target=command_runner.run_commands).start()


def gunicorn_logrotate(install=True, output=None, remote_cmd=False):
    print('-gunicorn_logrotate')
    logfile = f"/Users/{username}/Sonet/.data/logs/gunicorn.log"
    conf_path = "/etc/newsyslog.d/gunicorn.conf"
    conf_text = f"""{logfile}    root:wheel    644    7    25600    *    N"""

    tmp_path = "/tmp/gunicorn.conf"
    with open(tmp_path, "w") as f:
        f.write(conf_text)

    commands = [
        ["sudo", "-S", "rm", "/etc/newsyslog.d/gunicorn.conf"],
        ["sudo", "-S", "mv", tmp_path, conf_path],
        ["sudo", "-S", "chown", "root:wheel", conf_path],
        ["sudo", "-S", "chmod", "0644", conf_path],
        ["sudo", "-S", "newsyslog", "-f", 'n'], # test rotation
    ]
    if install or remote_cmd:
        get_variables()
        global systemPass
        for cmd in commands:
            print(cmd)
            try:
                r = subprocess.run(
                    cmd,
                    check=True,
                    input=f"{systemPass}\n".encode(),
                )
                print('r:',r)
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr.decode().strip() if e.stderr else "No stderr output"
                print('error_msg',error_msg)
    else:
        from ops import CommandRunner
        import threading
        command_runner = CommandRunner(None, commands, None, None, special_commands)
        threading.Thread(target=command_runner.run_commands).start()

def edit_nginx_conf(install=True, output=None, remote_cmd=False):
    print('-edit_nginx_conf')
    nginx_path = "/opt/homebrew/etc/nginx/nginx.conf"

    text = [
        "worker_processes auto;\n",
        f"pid /Users/{username}/Sonet/.data/supervisor/nginx.pid;\n",
        f"error_log /Users/{username}/Sonet/.data/logs/nginx_err.log;\n",
        "events {\n",
        "   worker_connections 768;\n",
        "}\n",
        "http {\n",
        "   sendfile on;\n",
        "   tcp_nopush on;\n",
        "   types_hash_max_size 2048;\n",
        "   client_max_body_size 50M;\n",
        "   client_body_temp_path /opt/homebrew/var/nginx/client_body 1 2;\n",
        "   client_body_buffer_size 512k;\n",
        "   include mime.types;\n",
        "   default_type application/octet-stream;\n",
        "   gzip on;\n",
        f"   access_log /Users/{username}/Sonet/.data/logs/nginx.log;\n",
        "   include servers/*;\n",
        "}\n",
    ]

    text_str = ''.join(text)

    with open("/tmp/nginx.conf", "w") as temp_file:
        temp_file.write(text_str)

    commands = [
        ["sudo", "-S", "mkdir", "-p", "/tmp/nginx_client_body"],
        ["sudo", "-S", "mv", "/tmp/nginx.conf", nginx_path],
        ["sudo", "-S", "chown", "root:wheel", nginx_path],
        ["sudo", "-S", "chmod", "644", nginx_path],
        # ["sudo", "nginx", "-t"],
        # ["sudo", "nginx", "-s", "reload"]
        [brew_path, 'services', 'restart', 'nginx']
    ]

    if install or remote_cmd:
        get_variables()
        global systemPass
        for cmd in commands:
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

def config_nginx(install=True, output=None, nodeData=None, remote_cmd=False, close_port=None, run_restart=False):
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
        domain = node_data['meta']['domain']
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
        f"  server_name  *.{domain} {address} {domain} {w_domain} 127.0.0.1 {local_ip} {external_ip};\n",
        f"  listen {port};\n",
        "   client_max_body_size 50M;\n",
        "\n",
        "   location = /favicon.ico { access_log off; log_not_found off; }\n",
        "   location /static_cdn/ {\n",
        f"      root /Users/{username}/Sonet/SoNodeServer;\n",
        "}\n",
        "\n",
        "location / {\n",
        f"  proxy_pass http://unix:/Users/{username}/Sonet/.data/supervisor/gunicorn.sock;\n",
        '    proxy_set_header Host $host;\n',
        '    proxy_set_header X-Real-IP $remote_addr;\n',
        '    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n',
        '    proxy_set_header X-Forwarded-Proto $scheme;\n',
        "}\n",

        f"error_log /Users/{username}/Sonet/.data/logs/nginx_err.log;\n"
        f"access_log /Users/{username}/Sonet/.data/logs/nginx.log;\n"
        "}\n",
    ]
    text_str = ''.join(text)
    with open("/tmp/SoNodeServer.conf", "w") as temp_file:
        temp_file.write(text_str)
    commands = [
        ["mkdir", "-p", f"/opt/homebrew/etc/nginx/servers"],
        ["sudo", "-S", "mv", "/tmp/SoNodeServer.conf", "/opt/homebrew/etc/nginx/servers/SoNodeServer.conf"],
    ]
    if run_restart:
        commands.append(['sudo', '-S', '/opt/homebrew/bin/supervisorctl', '-c', f'/Users/{username}/Sonet/.data/supervisor/supervisord.conf', 'reread'])
        commands.append(['sudo', '-S', '/opt/homebrew/bin/supervisorctl', '-c', f'/Users/{username}/Sonet/.data/supervisor/supervisord.conf', 'update'])
        commands.append(['sudo', '-S', '/opt/homebrew/bin/supervisorctl', '-c', f'/Users/{username}/Sonet/.data/supervisor/supervisord.conf', 'restart', 'all'])
    if install or remote_cmd:
        global systemPass
        for cmd in commands:
            update_output(cmd, output)
            result = subprocess.run(cmd, input=systemPass, text=True, capture_output=True)
            if result.returncode == 0:
                content = f"Nginx configured successfully\n{result.stdout}"
                update_output(content, output)
            else:
                content = f"Error configuring Nginx:\n{result.stderr}"
                update_output(content, output)
                raise content
    else:
        from ops import CommandRunner
        import threading
        command_runner = CommandRunner(None, commands, None, None, special_commands)
        threading.Thread(target=command_runner.run_commands).start()


# in the event the mac upgrades postgres without constent
MIGRATE_SCRIPT = f'/Users/{username}/Sonet/SoNodeManager/scripts/pg_automigrate.sh'
PLIST_PATH = f'/Users/{username}/Library/LaunchAgents/com.sonet.pg_automigrate.plist'
PLIST_CONTENT = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.sonet.pg_automigrate</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>{MIGRATE_SCRIPT}</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>6</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/pg_automigrate.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/pg_automigrate.log</string>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>"""


def finalize(output=None, remote_cmd=False):
    get_variables()
    global operatorData
    global node_data
    from commands.utils import finalize_install
    finalize_install(output=output, node_data=node_data, operatorData=operatorData)

remove_for_quick_install = [
    # ['run_command', 'setup_firewall'],
    ['run_command', 'run_create_env'],
    ['install_requirements', homepath + "/Sonet/SoNodeServer/requirements.txt", homepath + f"/Sonet/.data/env/bin/pip"],
    # ["sudo", "-S", "-i", "-u", username, "psql", "-c", "DROP DATABASE so_data;"],
    ['sudo', '-S', brew_path, 'install', 'zip'],
    ['run_command', 'fetch_chrome_and_chromedriver'],
    ['unzip', '/tmp/chrome_mac64.zip', '-d', '/tmp'],
    ['sudo', '-S', 'mv', '/tmp/chrome-mac-arm64/Google Chrome for Testing.app', '/Applications/Google Chrome for Testing.app'],
    ['sudo', '-S', 'chmod', '-R', '755', '/Applications/Google Chrome for Testing.app'],
    ['rm', '/tmp/chrome_mac64.zip'],
    ['unzip', '/tmp/chromedriver_mac64.zip', '-d', '/tmp'],
    ['sudo', '-S', 'mv', '/tmp/chromedriver', '/usr/local/bin/'],
    ['sudo', '-S', 'chown', f'{username}:{username}', '/usr/local/bin/chromedriver'],
    ['sudo', '-S', 'chmod', '+x', '/usr/local/bin/chromedriver'],
    ['rm', '/tmp/chromedriver_mac64.zip'],
]

remove_for_new_database = [
    ["sudo", "-S", "-i", "-u", username, "psql", "-c", "DROP DATABASE so_data;"],
    ["sudo", "-S", "-i", "-u", username, "psql", "-c", "CREATE DATABASE so_data;"],
]

special_commands = [
    # {'cmd':'hardware_check', 'reqs':'output_display'},
    {'cmd':'run_fetch_secret_key', 'reqs':'display_content'},
    {'cmd':'run_adjust_settings', 'reqs':'output_display'},
    {'cmd':'get_local_ip'},
    # {'cmd':'setup_rqworker', 'reqs':'output_display'},
    {'cmd':'config_supervisor', 'reqs':'output_display'},
    {'cmd':'edit_worker', 'reqs':'output_display'},
    {'cmd':'write_supervisor_plist', 'reqs':'output_display'},
    {'cmd':'config_gunicorn', 'reqs':'output_display'},
    {'cmd':'setup_gunicorn', 'reqs':'output_display'},
    {'cmd':'edit_nginx_conf', 'reqs':'output_display'},
    {'cmd':'config_nginx', 'reqs':'output_display'},
    {'cmd':'run_create_env', 'reqs':'output_display'},
    {'cmd':'fetch_chrome_and_chromedriver', 'reqs':'output_display'},
    {'cmd':'update_path'},
    {'cmd':'setup_firewall', 'reqs':'output_display'},
    {'cmd':'get_variables'},
    {'cmd':'pull_git', 'reqs':'output_display'},
    {'cmd':'finalize', 'reqs':'output_display'},
    # {'cmd':'update_shell_path'},
]

action_cmds = [
    ['sudo', '-S', '/bin/bash', '-c', '"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'],
    ['run_command', 'get_variables'],
    ['run_command', 'hardware_check'],
    [brew_path, '--version'],
    ['run_command', 'pull_git'],
    ['pkill', '-f', 'tor'],
    ['sudo', '-S', 'pkill', '-f', 'nginx'],
    ['sudo', '-S', 'pkill', '-f', 'supervisord'],
    ['sudo', '-S', 'rm', '-f', f'/Users/{username}/Sonet/.data/supervisor/supervisor.sock'],
    [brew_path, 'install', 'build-essential', 'libssl', 'zlib1g', 'libbz2', 'readline', 'curl', 'ncurses', 'xz', 'tk', 'libxml2', 'libffi', 'liblzma', 'osx-cpu-temp'],
    [brew_path, "install", "tor", "cloudflared", 'wget', 'sshpass'],
    ['run_command', 'run_create_env'],
    ['install_requirements', homepath + "/Sonet/SoNodeServer/requirements.txt", homepath + f"/Sonet/.data/env/bin/pip"],
    ['run_command', 'get_local_ip'],
    [brew_path, 'install', 'postgresql'],
    ['sudo', '-S', 'chown', '-R', f'{username}:{group}', pg_data_dir],
    ['chmod', '700', pg_data_dir],
    [brew_path, 'services', 'stop', f'postgresql@{pg_version}'],
    [brew_path, 'services', 'cleanup'],
    [brew_path, 'services', 'start', f'postgresql@{pg_version}'],
    f'''/Users/{username}/Sonet/.data/env/bin/python3 {homepath}/Sonet/SoNodeServer/manage.py shell -c "from django.core.management.utils import get_random_secret_key; print('key:', get_random_secret_key())"''',
    ['run_command', 'run_fetch_secret_key'],
    ['run_command', 'run_adjust_settings'],
    ["sudo", "-S", "-u", username, psql_path, "-c", "CREATE USER queue WITH PASSWORD 'K9V43S2P1';"],
    ["sudo", "-S", "-u", username, psql_path, "-c", "ALTER USER queue WITH SUPERUSER;"],
    ["sudo", "-S", "-u", username, psql_path, "-c", "DROP DATABASE so_data;"],
    ["sudo", "-S", "-u", username, psql_path, "-c", "CREATE DATABASE so_data;"],
    [f'/Users/{username}/Sonet/.data/env/bin/python3', f'{homepath}/Sonet/SoNodeServer/manage.py', 'migrate'],
    ['sudo', '-S', 'chmod', '-R', '755', f'/Users/{username}/Sonet/.data/logs'],
    ['sudo', '-S', 'chmod', '-R', '755', f'/Users/{username}/Sonet/.data/supervisor'],
    ['chmod', 'o+x', '/Users/sozed'],
    ['chmod', 'o+x', '/Users/sozed/Sonet'],
    ['chmod', 'o+x', '/Users/sozed/Sonet/.data'],
    ['chmod', 'o+x', '/Users/sozed/Sonet/.data/supervisor'],
    ['touch', '~/Sonet/.data/logs/nginx_supervisor.log'],
    ['chmod', '644', '~/Sonet/.data/logs/nginx_supervisor.log'],
    ['sudo', '-S', 'chown', '-R', f'{username}:staff', f'/Users/{username}/Sonet/.data/logs'],
    ['sudo', '-S', 'chown', '-R', f'{username}:staff', f'/Users/{username}/Sonet/.data/supervisor'],
    ['run_command', 'setup_gunicorn'],
    [brew_path, 'install', 'supervisor', 'nginx'],
    [brew_path, 'services', 'stop', 'supervisor'],
    ['sudo', '-S', 'pkill', '-f', 'supervisord'],
    [brew_path, 'link', 'nginx'],
    ['run_command', 'config_supervisor'],
    ['sudo', '-S', 'pkill', '-f', 'supervisord'],
    ['/bin/sleep', '2'],
    ['/bin/rm', '-f', f'/Users/{username}/Sonet/.data/supervisor/supervisor.sock'],
    ['/bin/rm', '-f', f'/Users/{username}/Sonet/.data/supervisor/supervisord.pid'],
    ['/opt/homebrew/bin/supervisord', '-c', f'/Users/{username}/Sonet/.data/supervisor/supervisord.conf'],
    ["raise_if_error", f"{homepath}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "check"],
    ['run_command', 'config_nginx'],
    ['run_command', 'edit_nginx_conf'],
    ['sudo', '-S', 'rm', '-rf', '/opt/homebrew/var/nginx/client_body'],
    ['sudo', '-S', 'mkdir', '-p', '/opt/homebrew/var/nginx/client_body'],
    ['sudo', '-S', 'chown', '-R', f'{username}:wheel', '/opt/homebrew/var/nginx/client_body'],
    ['sudo', '-S', 'chmod', '755', '/opt/homebrew/var/nginx/client_body'],
    ['sudo', '-S', 'chmod', '755', '/opt/homebrew/var/nginx'],
    # Write pg_automigrate plist file
    ['sudo', '-S', '-u', username, '/bin/bash', '-c',
     f"cat > {PLIST_PATH} << 'EOF'\n{PLIST_CONTENT}\nEOF"],
    ['sudo', '-S', 'chown', f'{username}:staff', PLIST_PATH],
    ['sudo', '-S', 'chmod', '644', PLIST_PATH],
    ['sudo', '-S', '-u', username, 'launchctl', 'load', PLIST_PATH],

    ['sudo', '-S', '/opt/homebrew/bin/supervisorctl', '-c', f'/Users/{username}/Sonet/.data/supervisor/supervisord.conf', 'reread'],
    ['sudo', '-S', '/opt/homebrew/bin/supervisorctl', '-c', f'/Users/{username}/Sonet/.data/supervisor/supervisord.conf', 'update'],
    ['sudo', '-S', '/opt/homebrew/bin/supervisorctl', '-c', f'/Users/{username}/Sonet/.data/supervisor/supervisord.conf', 'start', 'gunicorn'],
    ['sudo', '-S', '/opt/homebrew/bin/supervisorctl', '-c', f'/Users/{username}/Sonet/.data/supervisor/supervisord.conf', 'restart', 'all'],
    ['sudo', '-S', 'rm', '-f', '/opt/homebrew/var/run/nginx.pid'],
    ['sudo', '-S', '/opt/homebrew/bin/nginx', '-t'],
    [brew_path, 'services', 'restart', 'nginx'],
    ['run_command', 'write_supervisor_plist'],
    ['launchctl', 'bootout', f'gui/{uid}', f'/Users/{username}/Library/LaunchAgents/com.sonet.supervisor.plist'],
    ['sudo', '-S', 'pkill', '-f', 'supervisord'],
    ['/bin/rm', '-f', f'/Users/{username}/Sonet/.data/supervisor/supervisor.sock'],
    ['/bin/rm', '-f', f'/Users/{username}/Sonet/.data/supervisor/supervisord.pid'],
    ['/bin/sleep', '2'],
    ['launchctl', 'bootstrap', f'gui/{uid}', f'/Users/{username}/Library/LaunchAgents/com.sonet.supervisor.plist'],
    [brew_path, 'autoremove'],
    [brew_path, 'cleanup'],
    ['run_command', 'finalize'],
    # ['echo', 'thats it!'],
]

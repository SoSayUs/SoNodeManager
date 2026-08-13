
from __future__ import annotations

import fnmatch
import json
import os
import posixpath
import shlex
import sys
import zlib
from pathlib import Path
from typing import Iterable

import paramiko
import importlib.util
import json
import datetime
import time
import pytz
import uuid
import random
import subprocess
import requests
import platform
import os
import sys
import getpass
import shutil
import math
from kivy.clock import Clock
from os.path import expanduser
import struct
import psutil

from .locked import encrypt, decrypt, sign, simpleSign, verify, dt_to_string, generate_id

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec


username = getpass.getuser()
homepath = expanduser("~")
sonode_version_num = 0.1


def fetch_secure_item(val_name=None, key_path=None, file_path=None):
    print('-fetch_secure_item',val_name,'path:',file_path)
    create_file = False
    if not file_path:
        file_path = homepath + f"/Sonet/.data/operator_data/{val_name}.enc"
        create_file = True
    try:
        with open(file_path, 'rb') as file:
            encrypted_data = file.read()
            data_string = decrypt(encrypted_data, key_path=key_path)
    except Exception as e:
        print('fetch item fail 1 carry_on', str(e))
        if not create_file or val_name != 'operatorData':
            return None
        try:
            server_path = Path(homepath + '/Sonet/.data/operator_data')
            server_path.mkdir(parents=True, exist_ok=True)
            new_data = {}
            
            new_data['myRemotes'] = {}
            new_data['myRemotes']['local'] = {'nickname':'local', 'address':'127.0.0.1', 'username':'self', 'password':'', 'os_type':get_device_system()}
            data_string = json.dumps(new_data, indent=4)
            encrypted_data = encrypt(data_string)
            with open(file_path, 'wb') as file:
                file.write(encrypted_data)
            import stat
            key_file = os.path.expanduser(f"~/Sonet/.data/operator_data/{val_name}.enc")
            os.chmod(key_file, stat.S_IRUSR | stat.S_IWUSR)  # 600: Owner read & write
            with open(file_path, 'rb') as file:
                encrypted_data = file.read()
                data_string = decrypt(encrypted_data)
        except Exception as e:
            print('fetch item fail 2',str(e))
            return None
    try:
        json_obj = json.loads(data_string)
    except Exception as e:
        print('not json', str(e), data_string)
        json_obj = data_string
    return json_obj

def store_secure_item(val_name, data, key_path=None, file_path=None):
    print('-store_secure_item',val_name)
    data_string = json.dumps(data, indent=4)
    encrypted_data = encrypt(data_string, key_path=key_path)
    if not file_path:
        file_path = homepath + f"/Sonet/.data/operator_data/{val_name}.enc"
    with open(file_path, 'wb') as file:
        file.write(encrypted_data)

def get_remote_opData(operatorData=None, selected_nodeId=None, fetch_data=False): # works for local node or remote node
    print('-get_remote_opData')
    if operatorData:
        return operatorData
    operatorData = get_operatorData()
    if not selected_nodeId:
        if 'selected_node' in operatorData:
            selected_nodeId = operatorData['selected_node']
    print('selected_nodeId',selected_nodeId)
    if 'local_nodeId' in operatorData and selected_nodeId == operatorData['local_nodeId']:
        file_path = homepath + f"/Sonet/.data/operator_data/operatorData.enc"
        key_path = homepath + "/Sonet/.data/special/keys/.soSecret.key"
        return operatorData
    else:
        if fetch_data:
            remote_data = get_remote(node_id=selected_nodeId, operatorData=operatorData)
            return fetch_remote_data(remote_data, operatorData=operatorData, fetch_key=False, ssh_client=None)
        else:
            file_path = homepath + f"/Sonet/.data/operator_data/{selected_nodeId}_opData.enc"
            key_path = homepath + f"/Sonet/.data/special/keys/{selected_nodeId}_key.key"
    print('file_pathA',file_path)
    print('key_pathA',key_path)

    return fetch_secure_item(val_name=None, key_path=key_path, file_path=file_path)

def write_remote_opData(opData, update_remote=False): # works for local node or remote node
    print('-write_remote_opData')
    selected_nodeId = opData['local_nodeId']
    local_nodeId = fetch_secure_item('local_nodeId')
    if local_nodeId and selected_nodeId == local_nodeId:
        write_operatorData(opData)
    elif update_remote:
        update_remote_data(remote_opData=opData, remote_data=None, operatorData=None, remote_password=None, output=None)
    else:
        file_path = homepath + f"/Sonet/.data/operator_data/{selected_nodeId}_opData.enc"
        key_path = homepath + f"/Sonet/.data/special/keys/{selected_nodeId}_key.key"
        store_secure_item(None, opData, key_path=key_path, file_path=file_path)

def get_operatorData(val=None):
    print('-get_operatorData')
    if val:
        return val
    result = fetch_secure_item("operatorData")
    return result if result else {}

def write_operatorData(data, clear_data=True):
    print('-write operatorData')
    if not clear_data:
        try:
            current_data = get_operatorData()
            data = {**current_data, **data}
        except:
            pass
    store_secure_item("operatorData", data)

def fetch_node_keys(target_nodeId=None):
    local_nodeId = fetch_secure_item('local_nodeId')
    if target_nodeId and target_nodeId != local_nodeId:
        file_path = homepath + f"/Sonet/.data/operator_data/{target_nodeId}_nodeKeys.enc"
        key_path = homepath + f"/Sonet/.data/special/keys/{target_nodeId}_key.key"
        node_keys = fetch_secure_item(file_path=file_path, key_path=key_path)
    else:
        node_keys = fetch_secure_item('node_keys')
    return node_keys

def get_temp_data():
    from commands.locked import encrypt, decrypt
    try:
        with open(homepath + "/Sonet/.data/setup.json", 'rb') as file:
            encrypted_data = file.read()
            data_string = decrypt(encrypted_data)
    except Exception as e:
        print('get_temp_data err',str(e))
        server_path = Path(homepath + '/Sonet/.data')
        server_path.mkdir(parents=True, exist_ok=True)
        data_string = json.dumps({}, indent=4)
        encrypted_data = encrypt(data_string)
        with open(homepath + "/Sonet/.data/setup.json", 'wb') as file:
            file.write(encrypted_data)
        import stat
        key_file = os.path.expanduser("~/Sonet/.data/setup.json")
        os.chmod(key_file, stat.S_IRUSR | stat.S_IWUSR)  # 600: Owner read & write
        with open(homepath + "/Sonet/.data/setup.json", 'rb') as file:
            encrypted_data = file.read()
            data_string = decrypt(encrypted_data)
    json_obj = json.loads(data_string)
    return json_obj

def write_temp_data(data):
    from commands.locked import encrypt
    data_string = json.dumps(data, indent=4)
    encrypted_data = encrypt(data_string)
    with open(homepath + "/Sonet/.data/setup.json", 'wb') as file:
        file.write(encrypted_data)

def clear_temp_data():
    file_path = "/Sonet/.data/setup.json"
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Deleted: {file_path}")
    else:
        print("File does not exist")

def to_base62(hash_bytes):
    ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    num = int.from_bytes(hash_bytes, "big")
    if num == 0:
        return ALPHABET[0]
    result = []
    while num:
        result.append(ALPHABET[num % 62])
        num //= 62
    return ''.join(reversed(result))

def from_base62(s):
    ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    num = 0
    for char in s:
        num = num * 62 + ALPHABET.index(char)
    length = max(1, (num.bit_length() + 7) // 8)
    return num.to_bytes(length, "big")

def now_utc():
    return datetime.datetime.now().astimezone(pytz.utc)    

def value_is_none(value):
    if value in ['',{},[],0,None,'Val:N']:
        return True
    if isinstance(value, list):
        if all([value_is_none(v) for v in value]):
            return True
    return False

def hash_upk_id(pubKey, length=14):
    from commands.locked import generate_id
    return 'upkSo' + generate_id(pubKey, length=length) 

def is_id(obj):
    # prefix = plugin num + 2 to 3 class chars followed by "So"
    max_length = 35 # includes ID_LENGTH of 25 - does not include prefix
    min_length = 13 # includes ID_LENGTH of 10 - does not include prefix
    if isinstance(obj, str) and 'So' in obj[:10] and any(obj[i:i+2] == 'So' and obj[i+2:].isalnum() and min_length <= len(obj[i+2:]) <= max_length for i in range(10)):
        return True
    return False

def string_to_dt(dt_str):
    if isinstance(dt_str, datetime.datetime):
        return dt_str
    if dt_str and isinstance(dt_str, str):
        if 'Z' in dt_str:
            dt = datetime.datetime.fromisoformat(dt_str.replace('Z', '0+00:00'))
            return dt
        return datetime.datetime.fromisoformat(dt_str)
    return None

def update_output(line, output):
    
    if line and isinstance(line, str):
        print('-update_output',line)
        if '-noBreak-' in line:
            line = line.replace('-noBreak-','')
        elif not line.endswith('\n'):
            line += '\n'
        if isinstance(output, str):
            output += line
        else:
            Clock.schedule_once(lambda dt, line=line: schedule(line, output))

def schedule(content, output_display):
    from ops import display_max_size
    try:
        if output_display:
            output_display.text += f'{content}'
            lines = output_display.text.splitlines()
            if display_max_size > 0 and len(lines) > display_max_size:
                last_n_lines = lines[-display_max_size:]
                result = "\n".join(last_n_lines)
                output_display.text = result
    except Exception as e:
        pass


def get_node_ips(node_list): # not used
    print('-get_node_ips')
    if 'data' in node_list:
        node_list = node_list['data']
    ip_list = [ip for addresses in node_list.values() for ip in addresses if ip]
    print('d2:',ip_list)
    random.shuffle(ip_list)
    return ip_list

def get_or_create_node_obj(operatorData=None, new_node=None, register_data=True, create_node=True):
    print('-get_or_create_node_obj',register_data)
    operatorData = get_remote_opData(operatorData)
    def set_data(node_data):
        if all(field in node_data for field in ['upk', 'nodeData']):
            signed_upkData = sign(node_data['upk'], privKey=operatorData['accnt_privKey'], pubKey=operatorData['accnt_pubKey']) # sign with user account keys
            signed_walletData = sign(node_data['wallet'], privKey=operatorData['accnt_privKey'], pubKey=operatorData['accnt_pubKey'])
            if 'privKey' in node_data['meta']:
                privkey = node_data['meta']['privKey']
                store_secure_item("node_keys", {'pubKey':node_data['meta']['pubKey'],'privKey':node_data['meta']['privKey'],'keyId':node_data['upk']['id']})
            else:
                node_keys = fetch_secure_item('node_keys')
                privkey = node_keys['privKey']
            signed_nodeData = sign(node_data['nodeData'], privKey=privkey, pubKey=node_data['meta']['pubKey']) # sign with node keys
            data = {'objData' : json.dumps([signed_upkData,signed_nodeData,signed_walletData])}
            r = connect_to_node(operatorData['seed_ip'], 'utils/set_object_data', data=data, operatorData=operatorData, self_nodeData=node_data['nodeData'], node_setup=True)
            
            if r and r.status_code == 200:
                received_json = r.json()
                print('received_json',received_json)
                if received_json['message'] == 'Success':
                    operatorData['local_nodeId'] = signed_nodeData['id']
                    node_data['meta']['node_registered'] = True
                    node_details = {'nodeData':signed_nodeData, 'location':node_data['location'], 'settings':node_data['settings'], 'meta':node_data['meta'], 'upk':signed_upkData}
                    operatorData['myNodes'][signed_nodeData['id']] = node_details
                    operatorData['selected_node'] = signed_nodeData['id']
                    if 'userPass' in operatorData:
                        del operatorData['userPass']
                    if 'accnt_privKey' in operatorData:
                        del operatorData['accnt_privKey']
                    if 'accnt_pubKey' in operatorData:
                        del operatorData['accnt_pubKey']
                    if 'pubKey' in new_node['meta']:
                        del new_node['meta']['pubKey']
                    if 'privKey' in new_node['meta']:
                        del new_node['meta']['privKey']
                    write_remote_opData(operatorData)
                    return node_details, True
        print('set node data fail',node_data)
        return node_data, False
    if 'local_nodeId' in operatorData and operatorData['local_nodeId'] and operatorData['local_nodeId'] != '' and str(operatorData['local_nodeId']) != 'None':
        print('-has self node data')
        node_data = operatorData['myNodes'][operatorData['local_nodeId']]
        if register_data:
            if 'node_registered' not in node_data['meta'] or not node_data['meta']['node_registered']:
                node_details, updated = set_data(node_data)
                return node_details, False
        return node_data, False
    elif create_node:
        # should only be done locally - during install, not activate - store_secure_item only works locally
        try:
            user_id = operatorData['user_id']
            print('create node obj')
            if not new_node:
                for node in operatorData['myNodes']:
                    if 'new_install-' in node:
                        if operatorData['myNodes'][node]['location'] == 'local':
                            new_node = operatorData['myNodes'][node]
                            break
            if new_node:
                print('new_node',new_node)
                new_nodes = []
                for node in operatorData['myNodes']:
                    if 'new_install-' in node:
                        new_nodes.append(node)
                for node in new_nodes:
                    del operatorData['myNodes'][node]

                try:
                    def get_device_id():
                        system = platform.system()
                        try:
                            if system == "Linux" or system == "Darwin":
                                paths = ["/etc/machine-id", "/var/lib/dbus/machine-id"]
                                for path in paths:
                                    if os.path.exists(path):
                                        with open(path, "r") as f:
                                            return f.read().strip()
                            elif system == "Windows":
                                import winreg
                                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                                    r"SOFTWARE\Microsoft\Cryptography")
                                value, _ = winreg.QueryValueEx(key, "MachineGuid")
                                return value
                        except Exception as e:
                            print(f"Error fetching device id: {e}", file=sys.stderr)
                        import uuid
                        return str(uuid.getnode())

                    iden_creator = str(get_device_id())+str(user_id)
                    print('iden_creator',iden_creator)

                    from commands.locked import generate_id, createKeyPair
                    new_node_id = 'nodSo' + generate_id(iden_creator, length=10)

                    data = {'obj_type' : 'Node', 'obj_id' : new_node_id, 'if_empty':True}
                    err = 1
                    r = connect_to_node(operatorData['seed_ip'], '/utils/get_object_data/Node', data=data, operatorData=operatorData, node_setup=True, timeout=(4,10))
                    err = 2
                    if r and r.status_code == 200:
                        now = now_utc()
                        received_json = r.json()
                        err = 3
                        objModel_sign = json.loads(received_json['signing_obj'])
                        err = 4
                        upkModel_sign = json.loads(received_json['upk_signing_obj'])
                        walletModel_sign = json.loads(received_json['wallet_signing_obj'])
                        domain = None
                        if 'sonet' in operatorData:
                            if 'Domain' in operatorData['sonet']:
                                domain = operatorData['sonet']['Domain']
                                if domain:
                                    new_node['meta']['domain'] = domain
                        if not domain and 'domain' in operatorData:
                            domain = operatorData['domain']
                            if domain:
                                new_node['meta']['domain'] = domain
                        err = 5

                        node_name = new_node['settings']['node_name']
                        new_node['settings']['node_type'] = 'server/maintainer'
                        new_node['settings']['node_level'] = 'standard'

                        if not objModel_sign['created']:
                            objModel_sign['created'] = dt_to_string(now)
                        if not objModel_sign['User_obj']:
                            objModel_sign['User_obj'] = user_id
                        objModel_sign['node_name'] = node_name
                        objModel_sign['activated_dt'] = None
                        
                        upkModel_sign['created'] = dt_to_string(now)
                        upkModel_sign['User_obj'] = user_id
                        upkModel_sign['nodeId'] = objModel_sign['id']
                        upkModel_sign['keyType'] = 'node'
                        upkModel_sign['algorithm'] = 'secp256k1'
                        keyPair = createKeyPair(objModel_sign['id'], new_node['meta']['password'], 'node', key_strength='secp256k1')

                        upkModel_sign['publicKey'] = keyPair[1]
                        upkModel_sign['id'] = hash_upk_id(keyPair[1])

                        store_secure_item("node_keys", {'pubKey':keyPair[1],'privKey':keyPair[0],'keyId':upkModel_sign['id']})
                        store_secure_item(f"{objModel_sign['id']}_pass", new_node['meta']['password'])
                        store_secure_item(f"local_nodeId", objModel_sign['id'])

                        del new_node['meta']['password']

                        new_node['meta']['privKey'] = keyPair[0]
                        new_node['meta']['pubKey'] = keyPair[1]

                        walletModel_sign['created'] = dt_to_string(now)
                        walletModel_sign['User_obj'] = user_id
                        walletModel_sign['Name'] = f'Rewards-{new_node_id}'

                        address = new_node['settings']['address']
                        if domain and address == 'Cloudflare Tunnel':
                            address = f"{objModel_sign['id']}.{domain}"
                        elif not address or address == 'Cloudflare Tunnel':
                            try:
                                external_ip = requests.get('https://api.ipify.org').content.decode('utf8')
                            except:
                                external_ip = '127.0.0.1'
                            if 'port' in new_node['settings'] and new_node['settings']['port']:
                                address = external_ip + ':' + new_node['settings']['port']
                            else:
                                address = external_ip

                        objModel_sign['address'] = address
                        print('address',address)
                        print('new_node_data',objModel_sign)
                        new_nodeData = {'nodeData':objModel_sign, 'location':new_node['location'], 'settings':new_node['settings'], 'meta':new_node['meta'], 'upk':upkModel_sign, 'wallet':walletModel_sign}
                        if register_data:
                            print('register_data',register_data)
                            if node in operatorData['myNodes']:
                                del operatorData['myNodes'][node]
                            operatorData['local_nodeId'] = objModel_sign['id']
                            signed_nodeData, updated = set_data(new_nodeData)
                            return signed_nodeData, updated
                        else:
                            signed_upkData = sign(upkModel_sign, privKey=operatorData['accnt_privKey'], pubKey=operatorData['accnt_pubKey']) # sign with user account keys
                            signed_walletData = sign(walletModel_sign, privKey=operatorData['accnt_privKey'], pubKey=operatorData['accnt_pubKey'])
                            signed_nodeData = sign(objModel_sign, privKey=new_node['meta']['privKey'], pubKey=new_node['meta']['pubKey']) # sign with node keys
                            created_node = {'nodeData':signed_nodeData, 'location':new_node['location'], 'settings':new_node['settings'], 'meta':new_node['meta'], 'upk':signed_upkData, 'wallet':signed_walletData}
                            print('created_node',created_node)
                            operatorData['myNodes'][signed_nodeData['id']] = created_node
                            operatorData['local_nodeId'] = signed_nodeData['id']
                            operatorData['selected_node'] = signed_nodeData['id']
                            if node in operatorData['myNodes']:
                                del operatorData['myNodes'][node]

                            if 'userPass' in operatorData:
                                del operatorData['userPass']
                            if 'accnt_privKey' in operatorData:
                                del operatorData['accnt_privKey']
                            if 'accnt_pubKey' in operatorData:
                                del operatorData['accnt_pubKey']
                            if 'pubKey' in new_node['meta']:
                                del new_node['meta']['pubKey']
                            if 'privKey' in new_node['meta']:
                                del new_node['meta']['privKey']
                            
                            write_operatorData(operatorData)
                            return created_node, True
                except Exception as e:
                    print('create node fail 1',str(e))
                    pass
        except Exception as e:
            print('create node fail 2',str(e))
    return None, None

def update_node_data(operatorData=None):
    # not used ?
    print('-update_node_data')
    operatorData = get_operatorData(operatorData)
    result = 'Update failed'
    updated = False
    for nodeId, ip in get_node_list(operatorData=operatorData).items():
        if 'local_nodeId' in operatorData:
            iden = operatorData['local_nodeId']
        else:
            iden = 'self'
        try:
            r = connect_to_node(ip, f'network/get_node_request/{iden}', operatorData=operatorData)
            if r and r.status_code == 200:
                json_response = r.json()
                print('json_response',json_response)
                result = json_response['message']
                if json_response['message'] == 'Success':
                    server_signingNodeData = json.loads(json_response['nodeData'])
                    server_nodeData = json.loads(json_response['fullNodeData'])
                    if not verify(server_signingNodeData, server_nodeData['signed']):
                        result = 'Failed to verify'
                    else:
                        local_fullNodeData = operatorData['myNodes'][server_nodeData['id']]
                        local_nodeData = local_fullNodeData['nodeData']
                        if string_to_dt(server_nodeData['lastUpdate']) > string_to_dt(local_nodeData['lastUpdate']) or 'latestVer' in server_nodeData and server_nodeData['latestVer'] > local_nodeData['modlVer']:
                            server_signingNodeData['modlVer'] = server_nodeData['latestVer']
                            signedNodeData = sign(server_signingNodeData)
                            data = {'objData' : json.dumps(signedNodeData)}
                            r = connect_to_node(local_fullNodeData['settings']['localhost'], 'utils/set_object_data', data=data, operatorData=operatorData)
                            received_json = r.json()
                            if received_json['message'] == 'Success':
                                local_fullNodeData['nodeData'] = signedNodeData
                                operatorData['myNodes'][signedNodeData['id']] = local_fullNodeData
                                write_operatorData(operatorData)
                                updated = True
                            result = received_json['message']
                            print('res',result)
                return result, updated
            else:
                print('r',r)
        except Exception as e:
            print('update node fail',str(e))
    return result, updated

def get_node_list(operatorData=None, target='master', self_node={}, exclude_self=True, refresh_list=False, return_refresh_result=False, exclude_relays=True):
    print('-get_node_list, target:',target)
    operatorData = get_remote_opData(operatorData)

    refresh_result = False
    if refresh_list:
        print('refresh_list')
        nodes = get_node_list(operatorData=operatorData)
        for iden, ip in nodes.items():
            try:
                r = connect_to_node(ip, 'network/get_current_node_list', operatorData=operatorData, timeout=10, get=True)
                if r and r.status_code == 200:
                    r_json = r.json()
                    print('r_json',r_json)
                    if r_json['message'] == 'Success':
                        refresh_result = True
                        node_data = json.loads(r_json['node_data'])
                        node_addresses = json.loads(r_json['node_addresses'])
                        operatorData['node_list'] = {'lastUpdate' : dt_to_string(now_utc()), 'node_data' : node_data, 'addresses':node_addresses}
                        operatorData['ip_master_list'] = node_addresses
                        write_remote_opData(operatorData)
                        break
                else:
                    print('r',r)
            except Exception as e:
                print('node access err',str(e))
    try:
        if self_node and 'created' in self_node and string_to_dt(self_node['created']) < now_utc() - datetime.timedelta(minutes=10) and 'seed_ip' in operatorData: # only contact seed_node until self_node has been shared with network by seed_node
            nodes = {'seed_ip' : operatorData['seed_ip']}
        elif target == 'master' and 'ip_master_list' in operatorData:
            nodes = operatorData['ip_master_list']
            if exclude_relays and 'node_list' in operatorData and 'node_data' in operatorData['node_list']:
                if isinstance(nodes, list):
                    nodes = {n['address'][:n['address'].find('.')]:n for n in nodes if n['address'][:n['address'].find('.')] not in operatorData['node_list']['node_data']['relay']}
                else:
                    nodes = {iden:addr for iden, addr in nodes.items() if iden not in operatorData['node_list']['node_data']['relay']}
        elif isinstance(target, dict) and 'node_list' in operatorData and 'node_data' in operatorData['node_list']:
            target={'category':'abilities', 'sub_cat':'cloudflare'}
            if target['category'] in operatorData['node_list']['node_data'] and target['sub_cat'] in operatorData['node_list']['node_data'][target['category']]:
                node_ids = operatorData['node_list']['node_data'][target['category']][target['sub_cat']]
                if isinstance(node_ids, list):
                    nodes = {iden:operatorData['node_list']['addresses'][iden] for iden in operatorData['node_list']['node_data'][target['category']][target['sub_cat']] if iden in node_ids}
                else:
                    nodes = {iden:addr for iden, addr in operatorData['node_list']['addresses'].items() if iden in node_ids}
                if exclude_relays:
                    nodes = {iden:addr for iden, addr in nodes.items() if iden not in operatorData['node_list']['node_data']['relay']}
        elif 'node_list' in operatorData and target in operatorData['node_list']['node_data']:
            node_ids = operatorData['node_list']['node_data'][target]['server']
            if isinstance(node_ids, list):
                addresses = operatorData['node_list']['addresses']
                nodes = {iden:addresses[iden] for iden in node_ids}
            else:
                nodes = {iden:addr for iden, addr in operatorData['node_list']['addresses'].items() if iden in node_ids}
            if exclude_relays:
                nodes = {iden:addr for iden, addr in nodes.items() if iden not in operatorData['node_list']['node_data']['relay']}
        elif 'ip_master_list' in operatorData:
            nodes = operatorData['ip_master_list']
            if exclude_relays and 'node_list' in operatorData and 'node_data' in operatorData['node_list']:
                if isinstance(nodes, list):
                    nodes = {addr[:addr.find('.')]:addr for addr in nodes if addr[:addr.find('.')] not in operatorData['node_list']['node_data']['relay']}
                else:
                    nodes = {iden:addr for iden, addr in nodes.items() if iden not in operatorData['node_list']['node_data']['relay']}
        else:
            nodes = {}
    except Exception as e:
        print('get nodes list fail',str(e))
        nodes = {}
    print('nodes result:',nodes)
    if isinstance(nodes, list):
        nodes = {str(n):n for n in nodes}

    items = list(nodes.items())
    random.shuffle(items)
    nodes = dict(items)
    if 'seed_ip' in operatorData and target == 'master' or len(nodes) == 0:
        if 'seed_ip' in operatorData and operatorData['seed_ip'] not in nodes:
            nodes['seed_ip'] = operatorData['seed_ip']
    try:
        localhost = operatorData['myNodes'][operatorData['local_nodeId']]['settings']['localhost']
    except:
        localhost = None
    if localhost:
        if operatorData['local_nodeId'] in nodes:
            if 'seed_ip' in operatorData and localhost == operatorData['seed_ip']:
                pass
            elif localhost in nodes:
                del nodes[localhost]
        if len(nodes) < 1 and localhost:
            nodes[operatorData['local_nodeId']] = localhost
    if exclude_self and 'local_nodeId' in operatorData and operatorData['local_nodeId'] in nodes:
        del nodes[operatorData['local_nodeId']]
    if refresh_list:
        if return_refresh_result:
            return nodes, operatorData, refresh_result
        return nodes, operatorData
    return nodes

def declare_self_active(activate, output=None, operatorData=None, wait_for_reload=False, broadcast_to_network=True, print_updates=True, just_activate_me=False, activate_tasker=True, remote_cmd=False):
    # only run locally, not remotely
    print('--declare_self_active', activate)
    def broadcast(peer, data, broadcast_list, syncSuccess):
        print('-broadcast declare state', activate, peer, now_utc())
        try:
            declaredStateResponse = connect_to_node(peer, 'network/declare_node_state', data=data, operatorData=operatorData, node_setup=True, timeout=10)
            if declaredStateResponse and declaredStateResponse.json()['message'].lower() == 'success':
                syncSuccess = True
            else:
                if declaredStateResponse and declaredStateResponse.status_code == 200:
                    print(declaredStateResponse.json())
                    if output:
                        update_output(f'{declaredStateResponse.json()["err"]}\n', output)
            downstream_peers = broadcast_list[peer]
            for downstream_peer in downstream_peers:
                syncSuccess = broadcast(downstream_peer, data, broadcast_list, syncSuccess)
        except Exception as e:
            print('declare_self_active err 1',str(e))
            pass
        return syncSuccess
    
    def self_activate(signedData=None, full_nodeData={}, operatorData={}, output=None):
        print('-self_activate',signedData)
        if not signedData:
            if 'abilities' in operatorData:
                full_nodeData['nodeData']['abilities'] = operatorData['abilities']
            try:
                file_path = Path.home() / "Sonet/SoNodeServer/utils/utils.py"
                spec = importlib.util.spec_from_file_location("utils", file_path)
                utils_funcs = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(utils_funcs)
                server_version = getattr(utils_funcs, "current_version")
            except Exception as e:
                print('self_activate err',str(e))
                server_version = 'err_' + str(e)
            print('server_version',server_version)
            print('sonode_version_num',sonode_version_num)  
            full_nodeData['nodeData']['software_version'] = {'node':sonode_version_num, 'server':server_version}
            
            full_nodeData['nodeData']['node_name'] = node_name
            full_nodeData['nodeData']['node_type'] = node_type
            full_nodeData['nodeData']['node_level'] = node_level
            full_nodeData['nodeData']['address'] = node_ip_address
            if broadcast_to_network:
                if activate:
                    full_nodeData['nodeData']['activated_dt'] = dt_to_string(now_utc())
                else:
                    full_nodeData['nodeData']['activated_dt'] = None
            else:
                full_nodeData['nodeData']['activated_dt'] = None
            full_nodeData['nodeData']['User_obj'] = user_id
            full_nodeData['nodeData']['chain_array'] = full_nodeData['meta']['chainData']['supported_chains']
            full_nodeData['nodeData']['region_array'] = full_nodeData['meta']['chainData']['supported_regions']
            full_nodeData['nodeData']['plugin_array'] = full_nodeData['meta']['chainData']['supported_plugins']
            print("-operatorData['chainData']['supported_regions']",full_nodeData['meta']['chainData']['supported_regions'])

            if full_nodeData['nodeData']['node_level'] == 'super':
                print('sign with super keys')
                temp_keys = fetch_secure_item('temp_keys')
                signedData = sign(full_nodeData['nodeData'], privKey=temp_keys['privKey'], pubKey=temp_keys['pubKey'], operatorData=operatorData, verify_result=True)
            else:
                print('sign with node keys')
                signedData = sign(full_nodeData['nodeData'], operatorData=operatorData, verify_result=True)
                
            full_nodeData['nodeData'] = signedData
        if output:
            if activate:
                update_output('Activating self...\n', output)
            else:
                update_output('Deactivating self...\n', output)

        data = {'source':'node4', 'is_self':True, 'objData':json.dumps(signedData), 'broadcast_to_network':broadcast_to_network}
        print('sending declare node state locally::4',full_nodeData['settings']["localhost"],now_utc())
        declaredStateResponse = connect_to_node(full_nodeData['settings']["localhost"], 'network/declare_node_state', data=data, operatorData=operatorData, node_setup=True, timeout=custom_timeout)

        if declaredStateResponse and declaredStateResponse.status_code == 200 and 'message' in declaredStateResponse.json() and declaredStateResponse.json()['message'] == 'Success':
            syncSuccess = True
            if output:
                if activate:
                    update_output('Self Activated\n\n', output)
                else:
                    update_output('Self Deactivated\n\n', output)
        else:
            syncSuccess = False
        print('syncSuccess:',syncSuccess)
        if not syncSuccess and activate:
            write_operatorData(operatorData) 
            if output:
                if declaredStateResponse and declaredStateResponse.status_code == 200:
                    update_output(f'A Problem Occured: {declaredStateResponse.json()["err"]}\nDeactivating self...\n', output)
                else:
                    update_output(f'A Problem Occured connecting to self\nDeactivating self...\n', output)
            new_command = declare_self_active(False, output=output, operatorData=operatorData, wait_for_reload=wait_for_reload, broadcast_to_network=True, print_updates=True)
            update_output(f'Self not activated.\n', output)

            # disable Tasker
            device_system = get_device_system()
            if device_system == 'mac':
                uid = os.getuid()
                commands = [                 
                    ["sudo", "-S", f"/Users/{username}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "crontab", "remove"],
                ]
            elif device_system == 'windows':
                commands = []
            else:
                from .linux.linux_deactivate_cmds import empty_supervisor
                empty_supervisor(install=False, remote_cmd=remote_cmd)
                commands = [
                    ["sudo", "-S", f"/home/{username}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "crontab", "remove"],
                ]
            
            systemPass = fetch_secure_item('sysPass')
            for cmd in commands:
                print('cmd1',cmd)
                try:
                    update_output(f'\n{str(cmd)}', output)
                except Exception as e:
                    update_output(f'\n{str(e)}', output)
                result = subprocess.run(cmd, input=systemPass, text=True, capture_output=True)
                if output:
                    try:
                        if result.returncode == 0:
                            content = f"{result.stdout}"
                            print(content)
                            update_output(content, output)
                        else:
                            print(content)
                            content = f"{result.stderr}"
                            update_output(content, output)
                    except Exception as e:
                        update_output(f'\ncmd err 961:{str(e)}', output)
            return 'deactivate'
        elif syncSuccess and activate_tasker:
            operatorData['local_nodeId'] = signedData['id']
            operatorData['myNodes'][signedData['id']] = full_nodeData
            
            if activate: # enable Tasker
                device_system = get_device_system()
                if device_system == 'mac':
                    commands = [                                               
                        ["sudo", "-S", f"/Users/{username}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "crontab", "add"],
                        ["sudo", "-S", f"/Users/{username}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "crontab", "add"],
                        ["sudo", "-S", f"/Users/{username}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "crontab", "show"],
                    ]
                elif device_system == 'windows':
                    commands = []
                else:
                    commands = [
                        ["sudo", "-S", f"/home/{username}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "crontab", "add"],
                        ["sudo", "-S", f"/home/{username}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "crontab", "add"],
                        ["sudo", "-S", f"/home/{username}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "crontab", "show"],
                    ]

                systemPass = fetch_secure_item('sysPass')
                for cmd in commands:
                    print('cmd2',cmd)
                    try:
                        update_output(f'\n{str(cmd)}', output)
                    except Exception as e:
                        update_output(f'\n{str(e)}', output)
                    result = subprocess.run(cmd, input=systemPass, text=True, capture_output=True)
                    if output:
                        try:
                            if result.returncode == 0:
                                content = f"{result.stdout}"
                                print(content)
                                update_output(content, output)
                            else:
                                print(content)
                                content = f"{result.stderr}"
                                update_output(content, output)
                        except Exception as e:
                            update_output(f'\ncmd err 962:{str(e)}', output)
        return syncSuccess

    operatorData = get_operatorData(operatorData)
    
    print("operatorData['syncingDB']",operatorData['syncingDB'])
    if activate and ('syncingDB' in operatorData and operatorData['syncingDB'] == 'Fail') and not just_activate_me:
        # disable Tasker
        # this is used above, consider making its own function
        device_system = get_device_system()
        if device_system == 'mac':
            uid = os.getuid()
            commands = [                 
                ["sudo", "-S", f"/Users/{username}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "crontab", "remove"]
            ]
        elif device_system == 'windows':
            commands = []
        else:
            from .linux.linux_deactivate_cmds import empty_supervisor
            empty_supervisor(install=False, remote_cmd=remote_cmd)
            commands = [
                ["sudo", "-S", f"/home/{username}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "crontab", "remove"],
            ]
        
        systemPass = fetch_secure_item('sysPass')
        for cmd in commands:
            print('cmd3',cmd)
            try:
                update_output(f'\n{str(cmd)}', output)
            except Exception as e:
                update_output(f'\n{str(e)}', output)
            result = subprocess.run(cmd, input=systemPass, text=True, capture_output=True)
            if output:
                try:
                    if result.returncode == 0:
                        content = f"{result.stdout}"
                        print(content)
                        update_output(content, output)
                    else:
                        print(content)
                        content = f"{result.stderr}"
                        update_output(content, output)
                except Exception as e:
                    update_output(f'\ncmd err 963:{str(e)}', output)
        return 'failed_sync'
    if activate and ('syncingDB' not in operatorData or operatorData['syncingDB'] == 'bypass') and not just_activate_me:
        return 'failed_network_contact'
    if wait_for_reload:
        custom_timeout = 25
        time.sleep(10)
    else:
        custom_timeout = (4,10)
    user_id = operatorData['user_id']
    full_nodeData, is_new = get_or_create_node_obj(operatorData)
    if activate and not is_new:
        result, updated = update_node_data()
        print('result::',result)
        if result == 'Success' and updated:
            operatorData = get_operatorData(operatorData)
            full_nodeData = operatorData['myNodes'][operatorData['local_nodeId']]
    print('starting nodeData',full_nodeData)
    if activate == True:
        if 'address' in full_nodeData['settings'] and full_nodeData['settings']['address']:
            node_ip_address = full_nodeData['settings']['address']
        elif 'domain' in full_nodeData['meta']:
            node_ip_address = f"{full_nodeData['nodeData']['id']}.{full_nodeData['meta']['domain']}"
            full_nodeData['settings']['address'] = node_ip_address
        store_secure_item("address", node_ip_address)
        onion_address = get_onion_address()
        node_name = full_nodeData['settings']['node_name']
        node_type = full_nodeData['settings']['node_type']
        node_level = full_nodeData['settings']['node_level']
    else:
        node_ip_address = ''
        onion_address = ''
        node_name = full_nodeData['settings']['node_name']
        node_type = ''
        node_level = ''
        store_secure_item("address", node_ip_address)
    print('node_ip_address',node_ip_address)
    print('node_type',node_type)
    if broadcast_to_network:
        proceed = False
        nodes = get_node_list(operatorData=operatorData, exclude_self=False)
        if full_nodeData['nodeData']['id'] in nodes:
            del nodes[full_nodeData['nodeData']['id']]
        if not any(v for k, v in nodes.items() if v == full_nodeData['settings']['localhost']):
            nodes[full_nodeData['nodeData']['id']] = full_nodeData['settings']['localhost']
    else:
        proceed = True
        nodes = {full_nodeData['nodeData']['id']: full_nodeData['settings']['localhost']}
    print('nodes---3',nodes)

    if just_activate_me:
        print('just_activate_me')
        proceed = True
        is_running = True
        syncSuccess = self_activate(full_nodeData=full_nodeData, operatorData=operatorData, output=output)
    else:
        syncSuccess = False
        is_running = False
        dummy_node_model_sign = {}
        dummy_node_model = {}
        if output:
            update_output(f'\nChecking node is running...\n', output)
        data = {'requested_address':node_ip_address,'nodeId':full_nodeData['nodeData']['id']}
        try:
            r = connect_to_node(f"{full_nodeData['settings']['localhost']}", 'utils/is_sonet', data={}, operatorData=operatorData, get=True, node_setup=True, timeout=30)
            received_json = r.json()
            print('received message', received_json['message'])
            if received_json['message'] == 'is_sonet':
                is_running = True
            else:
                err = f"This node is not running"
                if output:
                    update_output(f'{err}\n', output)
        except Exception as e:
            print('declare err 22', str(e))
        
        if output:
            update_output(f'\nEstablishing connection...\n', output)

        broadcast_json = None
        if full_nodeData['nodeData']['node_level'] == 'super':
            print('sign with super keys')
            temp_keys = fetch_secure_item('temp_keys')
            signedData = sign(full_nodeData['nodeData'], privKey=temp_keys['privKey'], pubKey=temp_keys['pubKey'], operatorData=operatorData, verify_result=True, remove_skip_fields=True)
        else:
            print('sign with node keys')
            signedData = sign(full_nodeData['nodeData'], operatorData=operatorData, verify_result=True, remove_skip_fields=True)
        if is_running or activate == False:
            for iden, ip in nodes.items():
                print('sending get_broadcast_list::',ip,now_utc())
                response = connect_to_node(ip, 'network/get_broadcast_list', data={'source':'node','obj' : json.dumps(signedData), 'dt':signedData['lastUpdate']}, operatorData=operatorData, node_setup=True, timeout=custom_timeout)
                try:
                    print('~response from get_broadcast_list',response.content)
                    broadcast_json = response.json()
                    break
                except Exception as e:
                    print('declare err 43',str(e))

        attempts = 0
        if is_running or activate == False:
            last_iden, last_ip = next(reversed(nodes.items()))
            for iden, ip in nodes.items():
                print('--for ip', ip, nodes)
                try:
                    attempts += 1
                    if attempts > 3:
                        print('max attempts')
                        if output:
                            update_output(f'External access not achieved.\nShould be accessable at {node_ip_address}.\nConsider opening the port on your router.\n', output)
                        break
                    else:
                        if activate == False:
                            proceed = True
                        if not proceed and ip != node_ip_address:
                            update_output(f'Checking for external access...\n', output)
                            data = {'requested_address':node_ip_address,'nodeId':full_nodeData['nodeData']['id']}
                            try:
                                r = connect_to_node(ip, 'utils/can_you_see_me', data=data, operatorData=operatorData, node_setup=True, timeout=custom_timeout)
                                print('r.content',r.content)
                                received_json = r.json()
                                if received_json['message'] == 'Success':
                                    if 'is_https' in received_json and not received_json['is_https']:
                                        line = 'Node has external access but not https support which is required.\n'
                                    else:
                                        line = f'External access successful\n'
                                        proceed = True
                                    update_output(line, output)
                                elif received_json['actual_address'] not in node_ip_address and '127.0.0.1' not in received_json['actual_address']:
                                    err = f"{ip} Connection to self failed"
                                    update_output(f'{err}\n', output)
                            except:
                                pass
                        if not proceed and ip == full_nodeData['settings']['localhost'] and ip == last_ip:
                            try:
                                data = {'requested_address':node_ip_address,'nodeId':full_nodeData['nodeData']['id']}
                                r = connect_to_node(ip, 'utils/can_you_see_me', data=data, operatorData=operatorData, node_setup=True, timeout=custom_timeout)
                                if r.status_code == 200:
                                    print('r.content',r.content)
                                    received_json = r.json()
                                    if received_json['message'] == 'Success':
                                        if 'is_https' in received_json and not received_json['is_https']:
                                            line = 'Node has external access but not https support which is required.\n'
                                        else:
                                            line = f'External access successful\n'
                                            proceed = True
                                        update_output(line, output)
                                    elif received_json['actual_address'] not in node_ip_address and '127.0.0.1' not in received_json['actual_address']:
                                        err = f"{ip} Connection to self failed"
                                        update_output(f'{err}\n', output)
                            except:
                                pass
                        if not proceed and ip == last_ip and len(nodes) <= 2:
                            received_ip = requests.get('https://api.ipify.org').content.decode('utf8')
                        print('proceed:',proceed, ip)
                        if proceed or ip in full_nodeData['settings']['localhost'] and ip == last_ip and len(nodes) <= 2: # or ip == full_nodeData['settings']['localhost'] and verify_super_status(operatorData=operatorData):
                            update_output(f'Connected to {ip}\n', output)
                            try:                            
                                if not dummy_node_model:
                                    data = {'obj_type' : 'Node', 'obj_id' : '0'}
                                    r = connect_to_node(ip, 'utils/get_object_data', data=data, operatorData=operatorData, node_setup=True)
                                    if r:
                                        received_json = r.json()
                                        if 'message' in received_json and received_json['message'].lower() == 'success':
                                            dummy_node_model_sign = json.loads(received_json['signing_obj'])
                                            print('dummy_node_model_sign',dummy_node_model_sign)
                                            dummy_node_model = json.loads(received_json['model_obj'])
                                            if dummy_node_model_sign and dummy_node_model_sign['objType'] == 'Node':
                                                if int(dummy_node_model_sign['modlVer']) > int(full_nodeData['nodeData']['modlVer']):
                                                    for field in dummy_node_model_sign:
                                                        if field in full_nodeData['nodeData'] and field != 'modlVer':
                                                            dummy_node_model_sign[field] = full_nodeData['nodeData'][field]
                                                    print('new node data:',dummy_node_model_sign)
                                                    full_nodeData['nodeData'] = dummy_node_model_sign

                                full_nodeData['nodeData']['node_name'] = node_name
                                full_nodeData['nodeData']['node_type'] = node_type
                                full_nodeData['nodeData']['node_level'] = node_level
                                full_nodeData['nodeData']['address'] = node_ip_address
                                full_nodeData['nodeData']['onion'] = onion_address

                                system = platform.system()
                                try:
                                    if system == "Linux":
                                        full_nodeData['nodeData']['hardware_data']['os'] = 'Linux'
                                    elif system == "Darwin":
                                        full_nodeData['nodeData']['hardware_data']['os'] = 'MacOS'
                                    elif system == "Windows":
                                        full_nodeData['nodeData']['hardware_data']['os'] = 'Windows'
                                    if 'os' not in full_nodeData['meta']:
                                        full_nodeData['meta']['os'] = full_nodeData['nodeData']['hardware_data']['os']
                                        operatorData['myNodes'][full_nodeData['nodeData']['id']] = full_nodeData

                                        full_nodeData['nodeData']['hardware_data']['results'] = full_nodeData['meta']['hardware_results']
                                except:
                                    pass

                                if 'abilities' in operatorData:
                                    full_nodeData['nodeData']['abilities'] = operatorData['abilities']

                                try:
                                    file_path = Path.home() / "Sonet/SoNodeServer/utils/utils.py"
                                    spec = importlib.util.spec_from_file_location("utils", file_path)
                                    utils_funcs = importlib.util.module_from_spec(spec)
                                    spec.loader.exec_module(utils_funcs)
                                    server_version = getattr(utils_funcs, "current_version")
                                except Exception as e:
                                    print('server_version err',str(e))
                                    server_version = 'err_' + str(e)
                                print('server_version',server_version)
                                print('sonode_version_num',sonode_version_num)  
                                full_nodeData['nodeData']['software_version'] = {'node':sonode_version_num, 'server':server_version}

                                if not full_nodeData['nodeData']['region_data']:
                                    full_nodeData['nodeData']['region_data'] = {}
                                r = requests.get("http://ip-api.com/json", timeout=15)
                                if r.status_code == 200:
                                    full_nodeData['nodeData']['region_data']['country_code'] = r.json().get("countryCode")
                                
                                if broadcast_to_network:
                                    if activate:
                                        full_nodeData['nodeData']['activated_dt'] = dt_to_string(now_utc())
                                    else:
                                        full_nodeData['nodeData']['activated_dt'] = None
                                else:
                                    full_nodeData['nodeData']['activated_dt'] = None
                                full_nodeData['nodeData']['User_obj'] = user_id
                                if node_type == 'relay':
                                    full_nodeData['nodeData']['chain_array'] = []
                                    full_nodeData['nodeData']['plugin_array'] = []
                                else:
                                    full_nodeData['nodeData']['chain_array'] = full_nodeData['meta']['chainData']['supported_chains']
                                    full_nodeData['nodeData']['region_array'] = full_nodeData['meta']['chainData']['supported_regions']
                                    full_nodeData['nodeData']['plugin_array'] = full_nodeData['meta']['chainData']['supported_plugins']
                                print('node_data',full_nodeData['nodeData'])

                                if full_nodeData['nodeData']['node_level'] == 'super':
                                    print('sign with super keys')
                                    temp_keys = fetch_secure_item('temp_keys')
                                    signedData = sign(full_nodeData['nodeData'], privKey=temp_keys['privKey'], pubKey=temp_keys['pubKey'], operatorData=operatorData, verify_result=True, remove_skip_fields=True)
                                else:
                                    print('sign with node keys')
                                    signedData = sign(full_nodeData['nodeData'], operatorData=operatorData, verify_result=True, remove_skip_fields=True)
                                    
                                full_nodeData['nodeData'] = signedData
                                if not broadcast_to_network:
                                    syncSuccess = True
                                    update_output(f'\nComplete.\n', output)
                                    print('syncSuccess complete:',syncSuccess)
                                    print('should stop here')
                                    operatorData['syncingDB'] = False
                                    write_operatorData(operatorData) 
                                    return 'successfully_activated' if syncSuccess else 'failed_activation'
                                else:

                                    if not broadcast_json and activate == False and ip == full_nodeData['settings']['localhost']:
                                        update_output(f'\nComplete.\n', output)
                                        print('syncSuccess A',syncSuccess)
                                        write_operatorData(operatorData) 
                                        return 'successfully_activated' if syncSuccess else 'failed_activation'
                                    elif broadcast_json:
                                        if broadcast_json['message'] == 'Success':
                                            broadcast_list = broadcast_json['broadcast_list']
                                            starting_node = broadcast_json['starting_node']
                                            print('starting_node',starting_node)
                                            update_output(f'Declaring state...\n', output)
                                            data = {'source':'node3','objData' : json.dumps(signedData)}
                                            
                                            if starting_node in broadcast_list and broadcast_list[starting_node]:
                                                starting_node_list = [ip for ip in broadcast_list[starting_node] if ip]
                                            else:
                                                starting_node_list = []
                                            if starting_node_list:
                                                for node_address in starting_node_list:
                                                    print('decalre to starting node address:',node_address,now_utc())
                                                    if node_address:
                                                        update_output('Broadcasting...\n', output)
                                                        syncSuccess = broadcast(node_address, data, broadcast_list, syncSuccess)
                                            else:
                                                syncSuccess = True
                                            if full_nodeData['nodeData']['id'] in broadcast_list:
                                                data = {'source':'node2','objData' : json.dumps(signedData)}
                                                for node_address in broadcast_list[full_nodeData['nodeData']['id']]:
                                                    syncSuccess = broadcast(node_address, data, broadcast_list, syncSuccess)
                                            operatorData['syncingDB'] = False
                                            declaredStateResponse = None
                                            print(f'braodcast state result, syncSuccess:{syncSuccess},ip:{ip},last_ip:{last_ip}')
                                            if syncSuccess or activate == False:

                                                d = self_activate(signedData=signedData, full_nodeData=full_nodeData, operatorData=operatorData, output=output)
                                                if not d or d == 'deactivate':
                                                    full_nodeData['nodeData']['activated_dt'] = None
                                                    operatorData['myNodes'][full_nodeData['nodeData']['id']] = full_nodeData
                                                    operatorData['syncingDB'] = False
                                                    write_operatorData(operatorData) 
                                                    return 'failed_activation'
                                            elif ip == last_ip:
                                                return 'failed_network_contact'
                                            update_output(f'\nComplete.\n', output)
                                            print('syncSuccess B',syncSuccess)
                                            print('should stop here')
                                            write_operatorData(operatorData) 
                                            return 'successfully_activated' if syncSuccess else 'failed_activation'
                                        elif ip == last_ip:
                                            update_output(f'Failed last node. {broadcast_json["message"]}\n', output)
                                            if activate == False:
                                                operatorData['myNodes'][full_nodeData['nodeData']['id']] = full_nodeData
                                                operatorData['syncingDB'] = False
                                                write_operatorData(operatorData) 
                                            return 'failed_network_contact'
                                        else:
                                            update_output(f'Failed to get broadcast list. {broadcast_json["message"]}\n', output)
                                    else:
                                        update_output(f'Failed to get broadcast list.\n', output)
                            except Exception as e:
                                print('declare err 3',str(e))
                                update_output(f'node activation fail: {str(e)}\n', output)
                except Exception as e:
                    print('node declare fail',str(e))
    if proceed and not syncSuccess and output:
        return 'failed_network_contact'
    
    elif not is_running and output:
        update_output(f'External access not achieved.\nShould be accessable at {node_ip_address}.\nConsider opening the port on your router.\n', output)
    
    operatorData['syncingDB'] = False
    write_operatorData(operatorData)   
    if syncSuccess:
        return 'successfully_activated'      
    print('this is the end of a failure')  
    return 'Failed to activate'

def sync_database(output=None, SetupScreen=None, seed=False, total_sync=False):
    print('--sync_database output',output)
    # operatorData = get_operatorData()

    # check what keys are signing
    # adjust 'localhost' in connect_to_node
    # adjust update_output, remote Clock.schedule
    # make sure connect_to_node is signing with proper keys
    operatorData = get_remote_opData(fetch_data=True)
    operatorData['syncingDB'] = dt_to_string(now_utc())
    fullNode_data = {}
    if 'local_nodeId' in operatorData and operatorData['local_nodeId'] and operatorData['local_nodeId'] != '' and str(operatorData['local_nodeId']) != 'None':
        fullNode_data = operatorData['myNodes'][operatorData['local_nodeId']]
    node_keys = fetch_node_keys(target_nodeId=operatorData['local_nodeId'])
    print('node_keys,',node_keys)
    write_remote_opData(operatorData, update_remote=True)
    update_output(f'\n\nUpdating database...\n', output)
    def get_data(data, node_list=None, output=None, target_node=None, starting_index=0, count_index=True):
        print('\n-get_data',target_node,now_utc())
        if not node_list:
            nonlocal nodes
        else:
            nodes = node_list
        time.sleep(1)
        if target_node and target_node in nodes:
            value = nodes[target_node]
            nodes.pop(target_node)
            nodes = {target_node: value, **nodes}
        err_msg = 'no responses'
        for iden, ip in nodes.items():
            if SetupScreen and hasattr(SetupScreen, 'abort_function') and SetupScreen.abort_function:
                SetupScreen.parent_screen.job_running = False
                return False
            if iden != full_nodeData['nodeData']['id']:
                try:
                    received_json = None
                    response = connect_to_node(ip, 'network/request_data', data=data, operatorData=operatorData, self_nodeData=full_nodeData['nodeData'], node_setup=True, node_keys=node_keys)
                    if SetupScreen and hasattr(SetupScreen, 'abort_function') and SetupScreen.abort_function:
                        SetupScreen.parent_screen.job_running = False
                        return False
                    if response and response.status_code == 200:
                        received_json = response.json()
                        if received_json['message'] == 'Success':
                            if received_json['type'] == 'Blockchain':
                                print('is chain')
                                if SetupScreen and hasattr(SetupScreen, 'abort_function') and SetupScreen.abort_function:
                                    SetupScreen.parent_screen.job_running = False
                                    return False
                                blockchain_dict = json.loads(received_json['blockchain_obj'])
                                update_output(f'Received {blockchain_dict["genesisType"]} Chain: {blockchain_dict["genesisName"]}\n{blockchain_dict["chain_length"]} Blocks\n', output)
                                print('send block')
                                r = connect_to_node(sync_node_address, 'network/receive_data', data={'content' : received_json['content'], 'type' : received_json['type'], 'is_self':True, 'dt':dt_to_string(now_utc())}, operatorData=operatorData, stream=True, self_nodeData=full_nodeData['nodeData'], node_setup=True, node_keys=node_keys)
                                if r and r.status_code == 200:
                                    data_has_been_processed = True
                                    r_json = r.json()
                                    print('received_json 13:',r_json)
                                    if r_json['message'] == 'Success':
                                        wait_time = 1
                                        if 'iden' in r_json and r_json['iden']:
                                            is_processing = True
                                            attempts = 1
                                            failures = 0
                                            while is_processing and attempts < 7 and failures < 5:
                                                time.sleep(wait_time)
                                                if SetupScreen and hasattr(SetupScreen, 'abort_function') and SetupScreen.abort_function:
                                                    SetupScreen.parent_screen.job_running = False
                                                    return False
                                                wait_time = 7
                                                process_response = connect_to_node(sync_node_address, f'network/is_data_processing/{r_json["iden"]}', operatorData=operatorData, timeout=(4, 10), self_nodeData=full_nodeData['nodeData'], node_setup=True, node_keys=node_keys)
                                                if process_response and process_response.status_code == 200:
                                                    process_json = process_response.json()
                                                    print('process_json',process_json)
                                                    if 'result' in process_json and process_json['result'] in ['failed', 'fail']:
                                                        is_processing = False
                                                        return {'result' : 'Failed processing', 'chainData' : blockchain_dict}
                                                    elif 'result' in process_json and process_json['result'] == 'completed':
                                                        is_processing = False
                                                        return {'result' : 'True', 'chainData' : blockchain_dict}
                                                    elif process_json['message'] != 'Success' or process_json['result'] != 'running':
                                                        is_processing = False
                                                        return {'result' : 'Failed', 'chainData' : blockchain_dict}
                                                    elif output and process_json['message'] == 'Success' and process_json['result'] == 'running':
                                                        print('waiting...')
                                                        if 'added_to_queue' in process_json and process_json['added_to_queue']:
                                                            attempts += 1
                                                            update_output(f'-noBreak-+', output)
                                                        else:
                                                            update_output(f'-noBreak-.', output)
                                                    else:
                                                        failures += 1
                                                else:
                                                    failures += 1
                                                    update_output(f'-noBreak-x', output)
                                                
                                            if failures >= 5:
                                                return {'result' : 'Failed', 'index' : index, 'message':'Node not responding'}
                                            elif attempts >= 7:
                                                return {'result' : 'Failed', 'index' : index, 'message':'Max attempts'}

                                        else:
                                            result = r_json
                                    return {'result' : r_json['message'], 'chainData' : blockchain_dict}
                                return {'result' : received_json}
                            elif received_json['type'] == 'Block':
                                if SetupScreen and hasattr(SetupScreen, 'abort_function') and SetupScreen.abort_function:
                                    SetupScreen.parent_screen.job_running = False
                                    return False
                                block_dict = json.loads(received_json['block_obj'])
                                block_content = [block_dict]
                                if 'transaction_obj' in received_json and received_json['transaction_obj']:
                                    block_content.append(json.loads(received_json['transaction_obj']))
                                index = block_dict['index']
                                content = received_json['content']
                                if output and count_index:
                                    update_output(f'-noBreak-{index}..', output)
                                print('block_dict id',block_dict['id'],'index',block_dict['index'])

                                r = connect_to_node(sync_node_address, 'network/receive_data', data={'content' : content, 'type' : received_json['type'], 'is_self':True, 'dt':dt_to_string(now_utc())}, operatorData=operatorData, stream=True, self_nodeData=full_nodeData['nodeData'], node_setup=True, node_keys=node_keys)
                                if r and r.status_code == 200:
                                    result_json = r.json()
                                    print('received_json 14:',result_json)
                                    if result_json['message'] == 'Success':
                                        wait_time = 1
                                        process_result = 'True'
                                        if 'iden' in result_json and result_json['iden']:
                                            is_processing = True
                                            process_result = 'Unknown'
                                            process_iden = result_json['iden']
                                            attempts = 1
                                            failures = 0
                                            while is_processing and failures < 5 and attempts < 5:
                                                time.sleep(wait_time)
                                                if SetupScreen and hasattr(SetupScreen, 'abort_function') and SetupScreen.abort_function:
                                                    SetupScreen.parent_screen.job_running = False
                                                    return False
                                                wait_time = 7
                                                process_response = connect_to_node(sync_node_address, f'network/is_data_processing/{process_iden}', operatorData=operatorData, timeout=(10, 20), self_nodeData=full_nodeData['nodeData'], node_setup=True, node_keys=node_keys)
                                                if not process_response:
                                                    update_output(f'-noBreak-x', output)
                                                    failures += 1
                                                    time.sleep(30)
                                                else:
                                                    process_json = process_response.json()
                                                    print('process_json 2',process_json)
                                                    if 'result' in process_json and process_json['result'] in ['failed','fail']:
                                                        is_processing = False
                                                        failures += 1
                                                    elif 'result' in process_json and process_json['result'] == 'completed':
                                                        is_processing = False
                                                    elif output and process_json['message'] == 'Success' and process_json['result'] == 'running':
                                                        print('waiting...')
                                                        if 'added_to_queue' in process_json and process_json['added_to_queue']:
                                                            attempts += 1
                                                            update_output(f'-noBreak-+', output)
                                                        else:
                                                            update_output(f'-noBreak-.', output)
                                                    else:
                                                        failures += 1
                                                    
                                                    if not is_processing:
                                                        if SetupScreen and hasattr(SetupScreen, 'abort_function') and SetupScreen.abort_function:
                                                            SetupScreen.parent_screen.job_running = False
                                                            return False
                                                        check_data = {'type' : 'Block', 'obj_id' : block_dict['id'], 'fields' : ['id','validated']}
                                                        r = connect_to_node(sync_node_address, 'network/check_if_exists', data=check_data, timeout=(10, 20), self_nodeData=full_nodeData['nodeData'], node_setup=True, node_keys=node_keys)
                                                        if not r:
                                                            update_output(f'-noBreak-err', output)
                                                            failures += 1
                                                            time.sleep(30)
                                                        elif r and r.status_code == 200:
                                                            r_json = r.json()
                                                            print('r_json 15',r_json)
                                                            if r_json['message'] != 'Success' or 'requested_fields' in r_json and str(r_json['requested_fields']['validated']).lower() != 'true' or 'obj' in r_json and str(json.loads(r_json['obj'])['validated']).lower() != 'true':
                                                                process_result = 'Failed processing'
                                                                # run again
                                                                if SetupScreen and hasattr(SetupScreen, 'abort_function') and SetupScreen.abort_function:
                                                                    SetupScreen.parent_screen.job_running = False
                                                                    return False
                                                                update_output(f'-noBreak-x', output)
                                                                print('--rerunning, pause')
                                                                time.sleep(7)
                                                                attempts += 1
                                                                if attempts <= 3:
                                                                    r = connect_to_node(sync_node_address, 'network/receive_data', data={'content' : content, 'type' : received_json['type'], 'is_self':True, 'dt':dt_to_string(now_utc())}, operatorData=operatorData, stream=True, self_nodeData=full_nodeData['nodeData'], node_setup=True, node_keys=node_keys)
                                                                    if not r:
                                                                        update_output(f'-noBreak-x', output)
                                                                    elif r and r.status_code == 200:
                                                                        result_json = r.json()
                                                                        if result_json['message'] == 'Success':
                                                                            if 'iden' in result_json and result_json['iden']:
                                                                                is_processing = True
                                                                                process_iden = result_json['iden']
                                                                else:
                                                                    return {'result' : 'Failed', 'index' : index, 'message':'Max attempts'}
                                                            else:
                                                                process_result = 'True'
                                            
                                            if failures >= 5:
                                                return {'result' : 'Failed', 'index' : index, 'message':'Node not responding'}
                                            elif attempts >= 5:
                                                return {'result' : 'Failed', 'index' : index, 'message':'Max attempts'}
                                        return {'result' : process_result, 'index' : index}
                                try:
                                    print('no success',r.json())
                                except Exception as e:
                                    print('sync fail 1',str(e),r.status_code)
                                return {'result' : 'Failed', 'index' : index, 'message':'Failed to reach self'}
                            elif 'Blocks' in received_json['type']:
                                block_ids_len = len(json.loads(received_json['block_ids']))
                                update_output(f'Processing {block_ids_len} blocks...\n', output)
                                return {'result': 'Success', 'data': received_json}
                            else:
                                print('sync else 16')
                                if SetupScreen and hasattr(SetupScreen, 'abort_function') and SetupScreen.abort_function:
                                    SetupScreen.parent_screen.job_running = False
                                    return False
                                if not 'content' in received_json:
                                    return received_json
                                try:
                                    index = received_json['index']
                                except:
                                    index = 'NA'
                                print('index',index)
                                data_has_been_processed = False
                                update_output(f'Receiving data...\n', output)
                                r = connect_to_node(sync_node_address, 'network/receive_data', data={'content' : received_json['content'], 'type' : received_json['type'], 'is_self':True, 'dt':dt_to_string(now_utc())}, stream=True, operatorData=operatorData, timeout=(4, 180), self_nodeData=full_nodeData['nodeData'], node_setup=True, node_keys=node_keys)
                                if not r:
                                    update_output(f'-noBreak-x', output)
                                    time.sleep(30)
                                elif r and r.status_code == 200:
                                    received_json = r.json()
                                    print('received_json 16',received_json)
                                    if received_json['message'] == 'Success':
                                        if 'iden' in received_json and received_json['iden']:
                                            is_processing = True
                                            wait_time = 1
                                            attempts = 1
                                            while is_processing and attempts < 7:
                                                time.sleep(wait_time)
                                                if SetupScreen and hasattr(SetupScreen, 'abort_function') and SetupScreen.abort_function:
                                                    SetupScreen.parent_screen.job_running = False
                                                    return False
                                                wait_time = 5
                                                process_response = connect_to_node(sync_node_address, f'network/is_data_processing/{received_json["iden"]}', operatorData=operatorData, timeout=(4, 10), self_nodeData=full_nodeData['nodeData'], node_setup=True, node_keys=node_keys)
                                                if not process_response:
                                                    update_output(f'-noBreak-x', output)
                                                    time.sleep(30)
                                                else:
                                                    process_json = process_response.json()
                                                    print('process_json 17',process_json)
                                                    if process_json['message'] != 'Success' or process_json['result'] in ['failed','fail']:
                                                        is_processing = False
                                                        return {'result' : 'Failed processing'}
                                                    elif output and process_json['message'] == 'Success' and process_json['result'] == 'running':
                                                        print('waiting...')
                                                        if 'added_to_queue' in process_json and process_json['added_to_queue']:
                                                            attempts += 1
                                                            update_output(f'-noBreak-+', output)
                                                        else:
                                                            update_output(f'-noBreak-.', output)
                                                    elif process_json['message'] == 'Success' and process_json['result'] == 'completed':
                                                        is_processing = False
                                                        data_has_been_processed = True
                                                    else:
                                                        failures += 1
                                            if data_has_been_processed:
                                                result = {'result' : 'True'}
                                            else:
                                                result = {'result' : 'Failed'}

                                        else:
                                            data_has_been_processed = True
                                            result = received_json
                                        if index != 'NA' and index != starting_index and index != 'end':
                                            print('running next index:',index)
                                            time.sleep(2)
                                            json_data = json.loads(data['request'])
                                            json_data['index'] = index
                                            json_data['dt'] = dt_to_string(now_utc())
                                            signedRequest = json.dumps(sign(json_data, operatorData=operatorData, node_keys=node_keys))
                                            data['request'] = signedRequest
                                            result = get_data(data, nodes, output=output, target_node=iden, starting_index=index)
                                            if data_has_been_processed:
                                                result['result'] = 'True'
                                        return result
                                    else:
                                        return received_json
                        else:
                            print('else received_json 18',received_json)
                            err_msg = received_json['message']
                    else:
                        print('response 19',response)
                except Exception as e:
                    print('sync fail 2',str(e))
                    print('received_json err', str(received_json)[:2000])
                    err_msg = str(e)
        return {'result' : 'Fail', 'message' : err_msg}

    def get_chain(genesisId, node_list=None, initialData=None, output=None, target_node=None):
        print('-get_chain',now_utc(),genesisId)
        data = initialData
        if not node_list:
            nonlocal nodes
        else:
            nodes = node_list
        result = get_data(data, nodes, output=output, target_node=target_node)
        if SetupScreen and hasattr(SetupScreen, 'abort_function') and SetupScreen.abort_function:
            SetupScreen.parent_screen.job_running = False
            return False
        if isinstance(result, dict) and result['result'] == 'True' or result['result'] == 'Success':
            if 'chainData' in result:
                print('result is chainData')
                chain_dict = result['chainData']

                signedRequest = json.dumps(sign({'type':'Blockchain','chainId':chain_dict['id'],'dt':dt_to_string(now_utc())}, operatorData=operatorData, node_keys=node_keys))
                data = {'userData':userData, 'upkData':upkData, 'nodeData':selfNode, 'request':signedRequest}
                rv = connect_to_node(sync_node_address, 'utils/remove_false_blocks', data=data, operatorData=operatorData, self_nodeData=full_nodeData['nodeData'], node_setup=True, node_keys=node_keys)
                if rv:
                    rv_json = rv.json()
                get_block = 1
                found_starting_point = False
                for block_index in range(1, int(chain_dict['chain_length'])+1):
                    print('block_index',block_index,'get_block',get_block)
                    if SetupScreen and hasattr(SetupScreen, 'abort_function') and SetupScreen.abort_function:
                        SetupScreen.parent_screen.job_running = False
                        return False
                    try: 
                        if not found_starting_point:
                            data = {'type' : 'Block', 'blockchainId' : chain_dict['id'], 'index' : block_index, 'fields' : ['id','validated']}
                            print('check_if_exists 1',data)
                            r = connect_to_node(sync_node_address, 'network/check_if_exists', data=data, operatorData=operatorData, self_nodeData=full_nodeData['nodeData'], node_setup=True, node_keys=node_keys)
                            if r and r.status_code == 200:
                                found_starting_point = True
                                r_json = r.json()
                                print('r_json 20',r_json)
                                if 'latest_index' in r_json and int(r_json['latest_index']) >= get_block:
                                    get_block = int(r_json['latest_index']) + 1
                                    data = {'type' : 'Block', 'blockchainId' : chain_dict['id'], 'index' : get_block, 'fields' : ['id','validated']}
                                    print('check_if_exists2 ',data)
                                    r = connect_to_node(sync_node_address, 'network/check_if_exists', data=data, operatorData=operatorData, self_nodeData=full_nodeData['nodeData'], node_setup=True, node_keys=node_keys)
                                    r_json = r.json()
                                    print('r_json 21',r_json)
                        if block_index == get_block:
                            print('get index 2',block_index)
                            if chain_dict['genesisId'] == 'Nodes' and block_index != int(chain_dict['chain_length']): # only get content of last Node-Block
                                signedRequest = json.dumps(sign({'type':'Block','blockchainId' : chain_dict['id'], 'include_content' : False, 'item_count':'single', 'include_validators':True, 'index' : block_index,'dt':dt_to_string(now_utc()),'obj_updated_on_node':None}, node_keys=node_keys))
                            else:
                                signedRequest = json.dumps(sign({'type':'Block','blockchainId' : chain_dict['id'], 'include_content' : False, 'item_count':'single', 'include_validators':True, 'index' : block_index,'dt':dt_to_string(now_utc()),'obj_updated_on_node':None}, node_keys=node_keys))

                            data = initialData
                            data['request'] = signedRequest
                            result = get_data(data, nodes, output=output, target_node=target_node)
                            print('get_data result 1',result)
                            if isinstance(result, dict) and 'result' in result and result['result'] == 'True':
                                print('get_block +1')
                                get_block += 1
                            else:
                                print('breaking here',result)
                                break
                    except Exception as e:
                        print('get chain fail 1',str(e))
            elif 'data' in result:
                print('result is data 1')
                received_data = result['data']
                if SetupScreen and hasattr(SetupScreen, 'abort_function') and SetupScreen.abort_function:
                    SetupScreen.parent_screen.job_running = False
                    return False
                block_ids = json.loads(received_data['block_ids'])
                index = received_data['index']
                requested_update_dt = received_data['requested_update_dt']
                req_type = received_data['type']
                if block_ids:
                    block_ids.sort(key=lambda x: list(x.keys())[0]) # sort by DateTime key
                    print('block_ids',len(block_ids), block_ids)
                    num = 0
                    for b in block_ids:
                        for dt, iden in b.items():
                            num += 1
                            update_output(f'-noBreak-{num}..', output)
                            block_completed = False
                            attempt_nodes = nodes.copy()
                            while block_completed == False and len(attempt_nodes) > 0:
                                if SetupScreen and hasattr(SetupScreen, 'abort_function') and SetupScreen.abort_function:
                                    SetupScreen.parent_screen.job_running = False
                                    return False
                                signedRequest = json.dumps(sign({'type':'Block', 'iden' : iden, 'include_content' : False, 'item_count':'single', 'include_validators':True, 'dt':dt_to_string(now_utc()),'obj_updated_on_node':None},operatorData=operatorData, node_keys=node_keys))
                                data['request'] = signedRequest
                                target_node = random.choice(list(attempt_nodes.keys()))
                                del attempt_nodes[target_node]
                                result = get_data(data, nodes, output=output, target_node=target_node, count_index=False)
                                if isinstance(result, dict) and 'result' in result and result['result'] == 'True':
                                    block_completed = True
                                    if 'index' in result:
                                        index = 'end'
                            if not block_completed:
                                return {'result': 'Fail', 'message': f'Failed to retreive block {iden}'}
                    
                if index != 'end':
                    if SetupScreen and hasattr(SetupScreen, 'abort_function') and SetupScreen.abort_function:
                        SetupScreen.parent_screen.job_running = False
                        return False
                    signedRequest = json.dumps(sign({'type':req_type,'genesisId':req_type,'dt':dt_to_string(now_utc()),'item_count':'single','requested_update_dt':requested_update_dt, 'obj_count':'x', 'index':index, 'requested_update_dt':requested_update_dt}, operatorData=operatorData, node_keys=node_keys))
                    data['request'] = signedRequest
                    result = get_chain(req_type, nodes, data, output=output, target_node=target_node)

        else:
            print('sync else 21 result',result)
        return result

    def check_latest_update(model_name):
        if total_sync:
            return None
        response = connect_to_node(sync_node_address, 'network/check_latest_data/'+model_name, operatorData=operatorData, self_nodeData=full_nodeData['nodeData'], node_setup=True, node_keys=node_keys, timeout=(20,20))
        if response and response.status_code == 200:
            r_json = response.json()
            print('-check_latest_update r_json',now_utc(),r_json)
            if r_json['message'] == 'Success':
                if 'latest_index' in r_json:
                    requested_update_dt = r_json['latest_index']
                else:
                    requested_update_dt = r_json['update_dt']
                if 'obj_count' in r_json:
                    obj_count = r_json['obj_count']
                else:
                    obj_count = 'x'
                print('requested_update_dt',requested_update_dt,model_name)
                return requested_update_dt, obj_count
        return None, 0
    
    nodes, operatorData, network_contacted = get_node_list(operatorData=operatorData, self_node=fullNode_data, refresh_list=True, return_refresh_result=True, exclude_self=True)
    print('sync nodes:',nodes)
    iden = None
    userData = json.dumps(sign(operatorData['userData'], operatorData=operatorData, node_keys=node_keys))
    if 'upkData' in operatorData:   
        upkData = json.dumps(sign(operatorData['upkData'], operatorData=operatorData, node_keys=node_keys))
    else:
        upkData = None
    full_nodeData, is_new = get_or_create_node_obj(operatorData=operatorData, register_data=True, create_node=False)

    sync_node_address = [fullNode_data['settings']['localhost']]
    local_nodeId = fetch_secure_item('local_nodeId')
    if not local_nodeId or local_nodeId != operatorData['local_nodeId']:
        remote_data = get_remote(node_id=None, operatorData=None)
        sync_node_address = []
        if remote_data['local_address'] and remote_data['port']:
            sync_node_address.append(f"{remote_data['local_address']}:{fullNode_data['settings']['port']}")
        if remote_data['remote_address'] and remote_data['remote_port']:
            sync_node_address.append(f"{fullNode_data['settings']['address']}")
        if 'address' in full_nodeData['settings'] and full_nodeData['settings']['address']:
            sync_node_address.append(full_nodeData['settings']['address'])
        print('sync_node_address',sync_node_address)

    proceed = True
    err = '0'
    if not full_nodeData:
        update_output(f'Node creation failed.\n', output)
    else:
        signedNode = sign(full_nodeData['nodeData'], operatorData=operatorData, node_keys=node_keys)
        selfNode = json.dumps(signedNode)

        def run_data_task(target, check_for_latest=True):
            print('-run_data_task',target)
            try:
                if SetupScreen and hasattr(SetupScreen, 'abort_function') and SetupScreen.abort_function:
                    SetupScreen.parent_screen.job_running = False
                    return False
                if check_for_latest:
                    requested_update_dt, obj_count = check_latest_update(target)
                else:
                    requested_update_dt = None
                    obj_count = 'x'
                signedRequest = json.dumps(sign({'type':target,'items' : 'All', 'index' : 0,'dt':dt_to_string(now_utc()),'requested_update_dt':requested_update_dt, 'obj_count':obj_count}, operatorData=operatorData, node_keys=node_keys))
                if output:
                    if target.endswith('s'):
                        print_text = f'\nUpdating {target}...\n'
                    else:
                        print_text = f'\nUpdating {target}s...\n'
                    update_output(print_text, output)
                data = {'userData':userData, 'upkData':upkData, 'nodeData':selfNode, 'request':signedRequest}
                result = get_data(data, output=output)
                if result and result == False:
                    update_output(f'Aborted\n', output)
                elif result and 'result' in result and output:
                    if result['result'] == 'True':
                        update_output(f'Success\n', output)
                        return True
                    elif 'message' in result and result["message"] == 'Not Found' and requested_update_dt:
                        update_output(f'None New\n', output)
                        return True
                    else:
                        resp = 'err'
                        if 'result' in result:
                            resp = f'{resp} -result:{result["result"]}'
                        if 'message' in result:
                            resp = f'{resp} -msg:{result["message"]}'
                        update_output(f'{resp}\n', output)
                elif 'message' in result and output:
                    if result['message'].lower() == 'success':
                        update_output(f'Success\n', output)
                        return True
                    else:
                        update_output(f"{result['message']}\n", output)
            except Exception as e:
                print('data task err',str(e))
                update_output(f'error 3: {e}\n', output)
            return False

        signedRequest = json.dumps(sign({'type':'Blockchain','chainId':'all','dt':dt_to_string(now_utc())}, operatorData=operatorData, node_keys=node_keys))
        data = {'userData':userData, 'upkData':upkData, 'nodeData':selfNode, 'request':signedRequest}
        rva = connect_to_node(sync_node_address, 'utils/remove_false_blocks', data=data, operatorData=operatorData, self_nodeData=full_nodeData['nodeData'], node_setup=True, node_keys=node_keys)

        cont = run_data_task('Users-Keys')
        if cont:
            network_contacted = True
            cont = run_data_task('Sonet')
        if 'node_type' not in full_nodeData['settings']:
            full_nodeData['settings']['node_type'] = 'server/maintainer'
        if 'start_local_install' in operatorData:
            del operatorData['start_local_install']
            write_remote_opData(operatorData, update_remote=True)
        if cont and 'maintainer' in full_nodeData['settings']['node_type']:
            cont = run_data_task('Wallet')
        if cont:
            cont = run_data_task('Node', check_for_latest=False)
        
        def run_chain_task(target, node_list=None, target_node=iden):
            if not node_list:
                nonlocal nodes
                node_list = nodes
            print('-run_chain_task',target,nodes)
            if SetupScreen and hasattr(SetupScreen, 'abort_function') and SetupScreen.abort_function:
                SetupScreen.parent_screen.job_running = False
                return False
            try:
                if '-' in target:
                    a = target.find('-')
                    genesisId = target[:a]
                    req_type = 'Blockchain'
                elif '_Blocks' in target:
                    req_type = target
                    genesisId = target
                else:
                    genesisId = target
                    req_type = 'Blockchain'
                update_output(f'\nUpdating {target}...\n', output)
                requested_update_dt, obj_count = check_latest_update(target)
                signedRequest = json.dumps(sign({'type':req_type,'genesisId':genesisId,'dt':dt_to_string(now_utc()),'item_count':'single','requested_update_dt':requested_update_dt, 'obj_count':obj_count}, operatorData=operatorData, node_keys=node_keys))
                data = {'userData':userData, 'upkData':upkData, 'nodeData':selfNode, 'request':signedRequest}
                result = get_chain(genesisId, node_list, data, output=output, target_node=target_node)
                if result and result == False:
                    update_output(f'Aborted\n', output)
                if result and 'result' in result and output:
                    if result['result'] == 'True' or result['result'] == 'Success':
                        update_output(f'Success\n', output)
                        return True
                    else:
                        resp = 'err'
                        if 'result' in result:
                            resp = f'{resp} -result:{result["result"]}'
                        if 'message' in result:
                            resp = f'{resp} -msg:{result["message"]}'
                        update_output(f'{resp}\n', output)
            except Exception as e:
                print('chain task err')
                update_output(f'error 4: {e}\n', output)
            return False
        
        if cont:
            cont = run_data_task('Plugin')
        if cont:
            cont = run_data_task('Region')
        if cont:
            cont = run_chain_task('Operations-Blocks')
        if cont:
            cont = run_chain_task('Sonet-Blocks')
        if cont:
            cont = run_chain_task('User_Blocks')
        if cont and 'maintainer' in full_nodeData['settings']['node_type']:
            operatorData['myNodes'][operatorData['local_nodeId']]['meta']['do_not_sync_block_content'] = True
            write_remote_opData(operatorData, update_remote=True)
            cont = run_chain_task('Wallet_Blocks')
            del operatorData['myNodes'][operatorData['local_nodeId']]['meta']['do_not_sync_block_content']
            operatorData['myNodes'][operatorData['local_nodeId']]['meta']['do_sync_block_content'] = True
            write_remote_opData(operatorData, update_remote=True)
            
        if cont and 'relay' not in full_nodeData['settings']['node_type']:
            if 'chainData' in full_nodeData['meta'] and 'supported_regions' in full_nodeData['meta']['chainData'] and full_nodeData['meta']['chainData']['supported_regions'] != '':
                update_output(f'\nUpdating region chains...\n', output)
                for genesisId in full_nodeData['meta']['chainData']['supported_regions']:
                    print('genesisId',genesisId)
                    if SetupScreen and hasattr(SetupScreen, 'abort_function') and SetupScreen.abort_function:
                        SetupScreen.parent_screen.job_running = False
                        return False
                    if cont and genesisId.startswith('reg'):
                        nodes = get_node_list(operatorData=operatorData, target=genesisId, exclude_self=True)
                        print('nodes::',nodes)
                        if nodes:
                            try:
                                cont = run_chain_task(genesisId+'-Blocks', node_list=nodes, target_node=None)
                            except Exception as e:
                                print('chain task err 4',str(e))
                                update_output(f'error 4: {e}\n', output)
    if cont or not network_contacted:
        operatorData['syncingDB'] = False
        update_output(f'\n\nSync Complete.\n', output)
    elif not network_contacted:
        operatorData['syncingDB'] = 'bypass'
        update_output(f'\n\nSync Failed. Bypass Option.\n', output)
    else:
        operatorData['syncingDB'] = 'Fail'
        update_output(f'\n\nSync Failed.\n', output)
    try:
        del operatorData['myNodes'][operatorData['local_nodeId']]['meta']['do_sync_block_content']
    except:
        pass
    write_remote_opData(operatorData, update_remote=True)
    if not operatorData['syncingDB']:
        return True
    return False



def get_most_recent_even_hour(dt=None):
    if not dt:
        dt = now_utc()
    dt = dt - datetime.timedelta(minutes=dt.minute, seconds=dt.second, microseconds=dt.microsecond)
    hour = dt.hour
    while hour % 2 != 0:
        hour -= 1
    dt = dt.replace(hour=hour)
    return dt

def round_time(dt=None, dir='down', amount='hour'):
    if not dt:
        dt = now_utc()
    if isinstance(dt, str):
        dt = string_to_dt(dt)
    def reduce_hours(dt, hr):
        dt = dt - datetime.timedelta(minutes=dt.minute, seconds=dt.second, microseconds=dt.microsecond)
        hour = dt.hour
        while hour % hr != 0:
            hour -= 1
        dt = dt.replace(hour=hour)
        return dt
    def round_mins(dt, mins, dir='down'):
        r = dt - datetime.timedelta(minutes=(dt.minute % mins), seconds=dt.second, microseconds=dt.microsecond)
        if dir == 'up':
            r = r  + datetime.timedelta(minutes=mins)
        return r
    if dir == 'down':
        if amount == 'hour':
            return dt - datetime.timedelta(minutes=dt.minute, seconds=dt.second, microseconds=dt.microsecond)
        elif amount == 'evenhour':
            return reduce_hours(dt, 2)
        elif amount == '10mins':
            return round_mins(dt, 10)
        elif 'hours' in amount:
            x = amount.find('-')
            hr = int(amount[:x])
            return reduce_hours(dt, hr)
        elif amount == 'week':
            return (dt - datetime.timedelta(days=dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        elif amount == 'month':
            return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif dir == 'up':
        if amount == '10mins':
            return round_mins(dt, 10, dir='up')

def get_remote(node_id=None, operatorData=None):
    print('-get_remote',node_id)
    operatorData = get_operatorData(operatorData)

    if not node_id:
        node_id = operatorData['selected_node']

    for nickname, remote_data in operatorData['myRemotes'].items():
        if 'node_id' in remote_data and remote_data['node_id'] == node_id:
            return remote_data
    return {}

def verify_super_status(operatorData=None, save_data=True):
    print('-verify_super_status...')
    from commands.locked import super_id, sign
    operatorData = get_operatorData(operatorData)
    try:
        if 'user_is_super' in operatorData and operatorData['user_is_super'] == True:
            if 'new_sonet' in operatorData and 'sonet' not in operatorData:
                print('true1')
                return True
        if 'userData' in operatorData and 'id' in operatorData['userData'] and operatorData['userData']['id'] == super_id(operatorData=operatorData):
            if save_data:
                if 'user_is_super' not in operatorData or operatorData['user_is_super'] == False:
                    operatorData['user_is_super'] = True
                    write_operatorData(operatorData)
            print('true2')
            return True
        if 'userData' in operatorData and 'id' in operatorData['userData']:
            data = {'user_id' : operatorData['userData']['id']}
            now = now_utc()
            x = {'dt':dt_to_string(now), 'lastUpdate':dt_to_string(now)}
            signed_data = sign(x)
            print('signed_data',signed_data)
            last_dt = list(signed_data['signed'])[-1]
            public_key = signed_data['signed'][last_dt]['publicKey']
            signature = signed_data['signed'][last_dt]['sig']

            data['publicKey'] = public_key
            data['signature'] = signature
            data['signed_obj'] = json.dumps(signed_data)
            nodes = get_node_list(operatorData=operatorData)
            for nodeId, ip in nodes.items():
                print('ip',ip)
                try:
                    r = connect_to_node(ip, 'accounts/verify_superuser', data=data, operatorData=operatorData, timeout=10)
                    if r and r.status_code == 200:
                        received_json = r.json()
                        if received_json['message'] == 'Success':
                            if received_json['is_super'] == True:
                                if save_data:
                                    if 'user_is_super' not in operatorData or operatorData['user_is_super'] == False:
                                        operatorData['user_is_super'] = True
                                        write_operatorData(operatorData)
                                print('true3')
                                return True
                            else:
                                if save_data:
                                    if 'user_is_super' in operatorData and operatorData['user_is_super'] == True:
                                        operatorData['user_is_super'] = False
                                        write_operatorData(operatorData)
                                print('false1')
                                return False
                        break
                except Exception as e:
                    print('verify super err',str(e))
                    pass
    except Exception as e:
        print('verify super fail',str(e))
    print('false2')
    return False

def generate_strong_password(length=32):
    uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    lowercase = 'abcdefghijklmnopqrstuvwxyz'
    numbers = '0123456789'
    special_characters = '!@#$%^&*()-_=+[]{}|;:,.<>?'
    all_characters = uppercase + lowercase + numbers + special_characters

    # Ensure at least one character from each group is in the password
    password = [
        random.choice(uppercase),
        random.choice(lowercase),
        random.choice(numbers),
        random.choice(special_characters)
    ]

    # Fill the rest of the password length with random characters
    for _ in range(length - 4):
        password.append(random.choice(all_characters))

    random.shuffle(password)
    return ''.join(password)

def pull_git_server(output=None, operatorData=None):
    print('-pull_git_server')
    operatorData = get_operatorData(operatorData)
    device_system = get_device_system()
    from os.path import expanduser
    homepath = expanduser("~")
    try:
        if 'sonet' in operatorData:
            repo_data = operatorData['sonet']['repo']
        elif 'new_sonet' in operatorData:
            repo_data = operatorData['new_sonet']['repo']

        branch = repo_data['branch'] # main
        repo = repo_data['repo'] # SoSayUs
        source = repo_data['source'] # github.com
        
        package_manager = get_package_manager()
        git_repo = f"{repo}/SoNodeServer"
        remote_url = f"https://github.com:{git_repo}.git"
        remote_url = "https://github.com/SoSayUs/SoNodeServer.git"
        commands = []

        git_path = shutil.which("git")
        print('git_path',git_path)
        project_path = homepath + "/Sonet/SoNodeServer"

        def get_remote_commit(git_path, remote_url, branch):
            if shutil.which(git_path) is None and not os.path.isfile(git_path):
                return False

            try:
                result = subprocess.run(
                    [git_path, "ls-remote", remote_url, f"refs/heads/{branch}"],
                    capture_output=True, text=True, check=True
                )
            except FileNotFoundError:
                # git_path wasn't executable
                return False
            except subprocess.CalledProcessError:
                # git ran but failed (bad remote_url, no network, auth issue, etc.)
                return False

            # output looks like: "<hash>\trefs/heads/<branch>"
            return result.stdout.split()[0] if result.stdout else None

        def get_local_commit(git_path, project_path):
            if not os.path.isdir(project_path):
                return None
            if not os.path.isdir(os.path.join(project_path, ".git")): # confirm it's actually a git repo
                return None
            if shutil.which(git_path) is None and not os.path.isfile(git_path):
                return None

            try:
                result = subprocess.run(
                    [git_path, "-C", project_path, "rev-parse", "HEAD"],
                    capture_output=True, text=True, check=True
                )
            except (FileNotFoundError, subprocess.CalledProcessError):
                return None

            return result.stdout.strip()

        remote_commit = get_remote_commit(git_path, remote_url, branch)
        local_commit = get_local_commit(git_path, project_path) if os.path.exists(os.path.join(project_path, ".git")) else None

        if remote_commit == False or local_commit == None:
            # git or project not installed
            commands = [
                ["mkdir", homepath + "/Sonet"],
                ["mkdir", homepath + "/Sonet/SoNodeServer"],
                ["mkdir", homepath + "/Sonet/.data"],
                ["mkdir", homepath + "/Sonet/.data/logs"],
                ["mkdir", homepath + "/Sonet/.data/supervisor"],
                ["mkdir", homepath + "/Sonet/.data/operator_data"],
                ["mkdir", homepath + "/Sonet/.data/special"],
                ["mkdir", homepath + "/Sonet/.data/special/keys"],
                ['sudo', '-S', 'rm', homepath + '/Sonet/.data/special/settings.py'],
                ['touch', homepath + '/Sonet/.data/special/settings.py'],
                ['touch', homepath + '/Sonet/.data/special/cors.conf'],
                ["sudo", "-S", "chown", "-R", f"{username}:{username}", homepath + "/Sonet/.data/logs"],
                ["sudo", "-S", "chmod", "-R", f"755", homepath + "/Sonet/.data/logs"],
            ]
            if package_manager:
                commands.append(["sudo", "-S", package_manager, "install", "git", "-y"])
            elif device_system == 'mac':
                commands.append(["sudo", "-S", shutil.which("brew"), "install", "git", "-y"])

        if remote_commit != local_commit:
            print("Update found, pulling and restarting...")
        
            if os.path.exists(os.path.join(project_path, ".git")):
                commands.append([git_path, "-C", project_path, "fetch", "origin", branch, "--depth", "1"])
                commands.append([git_path, "-C", project_path, "reset", "--hard", "FETCH_HEAD"])
                commands.append([git_path, "-C", project_path, "clean", "-fd"])  # wipe any stray untracked files
            else:
                commands.append([git_path, "clone", "--branch", branch, "--depth", "1", remote_url, project_path])

        else:
            print("Already up to date, no restart needed.")
            

    except Exception as e:
        print('git fail', str(e))
    if commands:
        password = fetch_secure_item("sysPass")
        for cmd in commands:
            print('cmd',cmd)
            update_output(cmd, output)
            result = subprocess.run(
                cmd,
                input=(password + "\n").encode(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            content = f"{result.stdout.decode()}\n"
            update_output(content.replace(password, '*****'), output)

        with open(homepath + "/Sonet/.data/special/cors.conf", "w") as f:
            f.write("map $http_origin $cors_origin {\n")
            f.write('    default "";\n')
            if 'seed_ip' in operatorData:
                f.write(f'    "{operatorData["seed_ip"]}" $http_origin;\n')
            f.write("}\n")
        update_requirements(output=output)
    
    return commands

def get_installed_versions(venv="~/Sonet/.data/env"):
    """Return {package_name: version} for everything installed in the venv."""
    VENV_PIP = os.path.expanduser(venv+"/bin/pip")
    result = subprocess.run(
        [VENV_PIP, "freeze"],
        capture_output=True, text=True, check=True
    )
    installed = {}
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "==" not in line:
            continue
        name, version = line.split("==", 1)
        installed[name.lower()] = version
    return installed

def update_requirements(output=None, req_location="/SoNodeServer", venv="~/Sonet/.data/env"):
    print('-update_requirements')
    VENV_PIP = os.path.expanduser(venv+"/bin/pip")
    if not os.path.exists(VENV_PIP):
        print(f"✘ venv pip not found at {VENV_PIP}")
        return

    installed = get_installed_versions(venv=venv)
    homepath = expanduser("~")
    location_path = homepath + '/Sonet' + req_location + "/requirements.txt"
    print('location_path',location_path)
    with open(location_path) as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]

    import re
    for line in lines:
        match = re.match(r"^([A-Za-z0-9_.\-]+)==([A-Za-z0-9_.\-+]+)$", line)
        if not match:
            # not a pinned requirement (e.g. uses >=, ~=, or no version) - skip or handle separately
            print(f"  ⚠ Skipping unpinned/unparsed line: {line}")
            continue

        pkg, version = match.group(1), match.group(2)
        current = installed.get(pkg.lower())

        if current == version:
            # print(f"  ✓ {pkg}=={version} already installed, skipping")
            continue

        print(f"  → Installing {pkg}=={version} (was: {current or 'not installed'})")
        result = subprocess.run(
            [VENV_PIP, "install", f"{pkg}=={version}"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            # print(f"    ✘ Failed: {result.stderr.strip()}")
            update_output(f"Failed install {pkg}=={version}", output)
        else:
            # print(f"    ✔ Installed {pkg}=={version}")
            update_output(f"Installed {pkg}=={version}", output)

def get_update_commands(device_system):
    print('-get_update_commands',device_system)
    operatorData = get_operatorData()
    debug = False
    if 'debug' in operatorData:
        debug = operatorData['debug']
    if 'syncingDB' in operatorData and operatorData['syncingDB'] != False:
        operatorData['syncingDB'] = False
        write_operatorData(operatorData)
    commands, special_commands = get_commands('update', system=device_system, extras={'debug':debug})
        
    if 'self_is_active' in operatorData and operatorData['self_is_active'] and operatorData['self_is_active'] == True and not debug:
        commands.append(["sudo", "-S", f"{homepath}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "crontab", "add"])
        commands.append(["sudo", "-S", f"{homepath}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "crontab", "add"])

    return commands, special_commands

def get_commands(task, system=None, operatorData=None, in_full=False, extras={}):
    print('-get_commands',task)
    if task == 'ready_check':
        operatorData = get_operatorData()
        return [], {}
    if not system:
        try:
            operatorData = get_operatorData(operatorData)
            if 'local_nodeId' in operatorData:
                local_nodeId = operatorData['local_nodeId']
                for nickname, node_data in operatorData['myRemotes'].items():
                    if 'node_id' in node_data and node_data['node_id'] == local_nodeId:
                        if 'os_type' in node_data:
                            system = node_data['os_type']
                        break
        except Exception as e:
            print('get_commands err', str(e))
    if not system:
        system = get_device_system()
    if task == 'get_update':
        return get_update_commands(system)

    commands = []
    special_commands = {}
    if system == 'linux':
        if task == 'install':
            import commands.linux.linux_install_cmds as cmds
        elif task == 'activate':
            import commands.linux.linux_activate_cmds as cmds
        elif task == 'deactivate':
            import commands.linux.linux_deactivate_cmds as cmds
        elif task == 'uninstall':
            import commands.linux.linux_uninstall_cmds as cmds
        elif task == 'update':
            import commands.linux.linux_update_server as cmds
        elif task == 'purgeDB':
            import commands.linux.linux_purgedb as cmds
        elif task == 'restart':
            cmds = [
                # ["raise_if_error", "sudo", "-S", f"{homepath}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "check"],
                ["sudo", "-S", "supervisorctl", "reload"],
                ["sudo", "-S", "systemctl", "daemon-reexec"],
                ["sudo", "-S", "systemctl", "daemon-reload"],
                ["sudo", "-S", "systemctl", "restart", "gunicorn"],
                ["sudo", "-S", "systemctl", "restart", "nginx"],
            ]
            return cmds, {}

    elif system == 'mac':
        if task == 'install':
            import commands.mac.mac_install_cmds as cmds
        elif task == 'activate':
            import commands.mac.mac_activate_cmds as cmds
        elif task == 'deactivate':
            import commands.mac.mac_deactivate_cmds as cmds
        elif task == 'uninstall':
            import commands.mac.mac_uninstall_cmds as cmds
        elif task == 'update':
            import commands.mac.mac_update_server as cmds
        elif task == 'purgeDB':
            import commands.mac.mac_purgedb as cmds
        elif task == 'restart':
            from commands.mac.mac_install_cmds import find_brew
            username = getpass.getuser()
            brew_path = find_brew()
            uid = os.getuid()
            cmds = [
                
                ["raise_if_error", f"{homepath}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "check"],
                ['sudo', '-S', 'chown', '-R', f'{username}:staff', f'/Users/{username}/Sonet/.data/logs'],
                ['sudo', '-S', 'chown', '-R', f'{username}:staff', f'/Users/{username}/Sonet/.data/supervisor'],
                ['/opt/homebrew/bin/supervisord', '-c', f'/Users/{username}/Sonet/.data/supervisor/supervisord.conf'],
                ['sudo', '-S', '/opt/homebrew/bin/supervisorctl', '-c', f'/Users/{username}/Sonet/.data/supervisor/supervisord.conf', 'reread'],
                ['sudo', '-S', '/opt/homebrew/bin/supervisorctl', '-c', f'/Users/{username}/Sonet/.data/supervisor/supervisord.conf', 'update'],
                ['sudo', '-S', '/opt/homebrew/bin/supervisorctl', '-c', f'/Users/{username}/Sonet/.data/supervisor/supervisord.conf', 'restart', 'all'],

                ['launchctl', 'bootout', f'gui/{uid}', f'/Users/{username}/Library/LaunchAgents/com.sonet.supervisor.plist'],
                ['sudo', '-S', 'pkill', '-f', 'supervisord'],
                ['/bin/rm', '-f', f'/Users/{username}/Sonet/.data/supervisor/supervisor.sock'],
                ['/bin/rm', '-f', f'/Users/{username}/Sonet/.data/supervisor/supervisord.pid'],
                ['/bin/sleep', '2'],
                ['launchctl', 'bootstrap', f'gui/{uid}', f'/Users/{username}/Library/LaunchAgents/com.sonet.supervisor.plist'],

            ]
            return cmds, {}

    if in_full:
        return cmds

    if 'debug' in extras:
        debug = extras['debug']
    else:
        debug = False
    if 'preserve_database' in extras:
        preserve_database = extras['preserve_database']
    else:
        preserve_database = False
    if 'preserve_dependencies' in extras:
        preserve_dependencies = extras['preserve_dependencies']
    else:
        preserve_dependencies = False
    if 'quick_uninstall' in extras:
        quick_uninstall = extras['quick_uninstall']
    else:
        quick_uninstall = False
    if 'quick_install' in extras:
        quick_install = extras['quick_install']
    else:
        quick_install = False
    if 'new_database' in extras:
        new_database = extras['new_database']
    else:
        new_database = False
    if 'enableTasker' in extras:
        enableTasker = extras['enableTasker']
    else:
        enableTasker = True

    for x in cmds.special_commands:
        func = getattr(cmds, x['cmd'])
        x['func'] = func
        special_commands[x['cmd']] = x
    for cmd in cmds.action_cmds:
        if debug and hasattr(cmds, 'remove_for_debug') and cmd in cmds.remove_for_debug:
            pass
        elif preserve_database and hasattr(cmds, 'remove_to_save_database') and cmd in cmds.remove_to_save_database:
            pass
        elif quick_uninstall and hasattr(cmds, 'remove_for_quick_uninstall') and cmd in cmds.remove_for_quick_uninstall:
            pass
        elif quick_install and hasattr(cmds, 'remove_for_quick_install') and cmd in cmds.remove_for_quick_install:
            pass
        elif new_database and hasattr(cmds, 'remove_for_new_database') and cmd in cmds.remove_for_new_database:
            pass
        elif enableTasker == False and hasattr(cmds, 'remove_for_tasker') and cmd in cmds.remove_for_tasker:
            pass
        elif cmd[0] == 'install_requirements':
            req_path = cmd[1]
            pip_path = cmd[2]
            with open(req_path, 'r') as file:
                line = [pip_path, 'install', 'wheel']
                commands.append(line)
                line = [pip_path, 'install', 'psycopg2-binary']
                commands.append(line)
                for line in file:
                    line = [pip_path, 'install', line.replace('\n', '')]
                    commands.append(line)
        
        else:
            commands.append(cmd)

    return commands, special_commands

def fetch_remote_commands(task, ssh_client, extras=None):
    print('-fetch_remote_commands...',task)
    import json
    extras_json = json.dumps(extras or {})
    python_bin = "~/Sonet/.data/nenv/bin/python"
    base = "cd ~/Sonet/SoNodeManager/commands &&"

    cmd = (
        f"{base} {python_bin} remote_get_commands.py "
        f"{task} '{extras_json}'"
    )
    stdin, stdout, stderr = ssh_client.exec_command(cmd, get_pty=True)

    output = stdout.read().decode().strip()
    error  = stderr.read().decode().strip()
    print('output---:',output)

    if error:
        print("Remote error:", error)
        return "Failed to fetch remote commands", {}

    if "ERR:" in output:
        return "Remote error: " + output.split("ERR:",1)[1].strip(), {}

    marker1 = "COMMANDS_JSON:"
    marker2 = "SPECIAL_CMDS_JSON:"

    cmd_pos = output.find(marker1)
    spec_pos = output.find(marker2)

    if cmd_pos == -1:
        return "Missing COMMANDS_JSON in remote output.\n" + output, {}

    if spec_pos == -1:
        return "Missing SPECIAL_CMDS_JSON in remote output.\n" + output, {}

    commands_json = output[cmd_pos + len(marker1):].split("\n", 1)[0].strip()
    special_json = output[spec_pos + len(marker2):].split("\n", 1)[0].strip()

    commands = json.loads(commands_json)
    special_commands = json.loads(special_json)


    return commands, special_commands


MAX_SIZE = 1024 * 1024 * 1  # 1 MB
MAX_SIZE = 40000

def send_post(url, data_str, headers=None, timeout=(5, 30)):
    print('-send_post',url)
    # print('data_str',str(data_str)[:300])
    if headers is None:
        headers = {}
    if not data_str:
        data_str = ''
    body_bytes = data_str.encode('utf-8')
    total_size = len(body_bytes)
    print(f'total_size: {total_size}/{MAX_SIZE}')
    if total_size < MAX_SIZE:
        headers['X-Last-Part'] = 'true'
        print('send in 1')
        return requests.post(url, data=body_bytes, headers=headers, timeout=timeout)

    # Multi-part upload
    upload_id = str(uuid.uuid4())
    responses = []
    total_parts = math.ceil(total_size / MAX_SIZE)
    for part_number, start in enumerate(range(0, total_size, MAX_SIZE), start=1):
        is_last = (part_number == total_parts)
        print('part_number',part_number,'start',start)
        chunk = body_bytes[start:start + MAX_SIZE]
        part_headers = headers.copy()
        part_headers['Content-Length'] = str(len(chunk))
        part_headers['X-Upload-ID'] = upload_id
        part_headers['X-Part-Number'] = str(part_number)
        part_headers['X-Last-Part'] = 'false'
        if part_number == total_parts:
            part_headers['X-Last-Part'] = 'true'

        resp = requests.post(url, data=chunk, headers=part_headers, timeout=(10, 120))
        if resp.status_code != 200:
            break
    return resp
        

def connect_to_node(ip_list, link, data={}, operatorData=None, timeout=(5,30), get=False, stream=False, self_nodeData=None, skip_self=False, privKey=None, node_keys={}, node_setup=True):
    print('---connecting...',ip_list,link, "node_setup",node_setup)
    # print('data',str(data)[:500])
    if link.startswith('/'):
        link = link[1:]
    if isinstance(ip_list, dict):
        ip_list = [ip_list[i] for i in ip_list if 'onion' not in i]
    elif not isinstance(ip_list, list):
        ip_list = [ip_list]
    try:
        local_ip = fetch_secure_item('address')
        print('local_ip:',local_ip)
        if not local_ip:
            operatorData = get_operatorData(operatorData)
            local_ip = operatorData['myNodes'][operatorData['local_nodeId']]['nodeData']['address']
        if local_ip in ip_list:
            if skip_self:
                return None
            operatorData = get_operatorData(operatorData)
            ip_list = [operatorData['myNodes'][operatorData['local_nodeId']]['settings']['localhost']]
            print('swapped ip', ip_list)

    except Exception as e:
        print('connect_to_node error1',str(e))
        pass
    if ip_list:
        for ip in ip_list:
            print('ip:',ip)
            try:
                if '127.0.0.1' in ip or ip.startswith('10.0.'):
                    http = 'http'
                else:
                    http = 'https'
                if get:
                    start_time = time.time()
                    response = requests.get(http + '://' + ip + '/' + link, timeout=timeout)
                else:
                    start_time = time.time()
                    now = dt_to_string(now_utc())
                    print('now',now)
                    sig = '0000'
                    node_id = '0'
                    if not self_nodeData:
                        self_nodeData, is_new = get_or_create_node_obj(operatorData=operatorData, register_data=False, create_node=False)
                    if self_nodeData:
                        if 'nodeData' in self_nodeData:
                            node_id = self_nodeData['nodeData']['id']
                        elif 'id' in self_nodeData:
                            node_id = self_nodeData['id']

                    pubKey = None
                    if not privKey:
                        if not node_keys:
                            node_keys = fetch_secure_item('node_keys')
                        if node_keys and 'privKey' in node_keys:
                            privKey = node_keys['privKey']
                            pubKey = node_keys['pubKey']
                    if not privKey and self_nodeData and 'meta' in self_nodeData and 'privKey' in self_nodeData['meta']:
                        privKey = self_nodeData['meta']['privKey']
                    if not privKey:
                        operatorData = get_operatorData(operatorData)
                        if 'accnt_privKey' in operatorData and operatorData['accnt_privKey']:
                            privKey = operatorData['accnt_privKey']
                        if 'accnt_pubKey' in operatorData and operatorData['accnt_pubKey']:
                            pubKey = operatorData['accnt_pubKey']
                    if privKey:
                        sign_data = f"{node_id}-{None}-{now}"
                        sig = simpleSign(privKey, sign_data)

                    if isinstance(data, dict):
                        data = json.dumps(data)

                    headers = {'Content-Type': 'application/json'}
                    headers['packet-id'] = 'dpkSo' + generate_id()
                    headers['senderid'] = node_id
                    headers['signed-dt'] = now
                    headers['dt-sig'] = sig
                    headers['upk'] = pubKey
                    headers['nodesetup'] = str(node_setup)
                    headers['dt'] = now
                    start_time = time.time()
                    response = send_post(http + '://' + ip + '/' + link, data, headers=headers, timeout=timeout)
                    elapsed_time = time.time() - start_time
                    print('post connection', f"{int(elapsed_time // 60):02}:{int(elapsed_time % 60):02}")

                print('returned resposne:',response.status_code, str(response)[:200])
                if response.status_code == 200:
                    return response
            except Exception as e:
                print('connectfail',ip,str(e))
                elapsed_time = time.time() - start_time
                print('elapsed_time',elapsed_time)
                print('post connection', f"{int(elapsed_time // 60):02}:{int(elapsed_time % 60):02}") 
    return None



def purge_database_commands(device):
    username = getpass.getuser()
    homepath = expanduser("~")
    if device == 'linux':
        commands = [
            ["sudo", "-S", "-i", "-u", "postgres", "psql", "-c", "DROP DATABASE so_data;"],
            ["sudo", "-S", "-i", "-u", "postgres", "psql", "-c", "CREATE DATABASE so_data;"],
            ["sudo", "-S", f"/home/{username}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "migrate"],
            ["echo", 'Complete'],
        ]
    elif device == 'mac':
        commands = [
            ["sudo", "-S", "-i", "-u", username, "psql", "-c", "DROP DATABASE so_data;"],
            ["sudo", "-S", "-i", "-u", username, "psql", "-c", "CREATE DATABASE so_data;"],
            [f'/Users/{username}/Sonet/.data/env/bin/python3', f'{homepath}/Sonet/SoNodeServer/manage.py', 'migrate'],
            ["echo", 'Complete'],
        ]
    return commands

def get_onion_address():
    system = platform.system()
    if system == "Darwin":
        HS_DIR = f"/Users/{username}/Sonet/.data/tor_instance/hidden_service"
    elif system == "Linux":
        HS_DIR = f"/home/{username}/Sonet/.data/tor_instance/hidden_service"

    try:
        hostname_path = os.path.join(HS_DIR, "hostname")
        with open(hostname_path, "r") as f:
            addr = f.read().strip()
        store_secure_item('onion', addr)
        return addr
    except:
        return None

def adjust_settings(nodeData=None, node_data=None, clear_data=False, output=None, operatorData=None):
    print('r-adjust_settings')

    base_path = os.path.expanduser("~/Sonet/.data/special")
    files = {
        "settings.py": "\n",
        "trusted_sources.py": "\n",
        "__init__.py": ""
    }
    os.makedirs(base_path, exist_ok=True)
    for filename, content in files.items():
        file_path = os.path.join(base_path, filename)
        if not os.path.exists(file_path):
            with open(file_path, "w") as f:
                f.write(content)
            print(f"Created: {file_path}")
        else:
            print(f"Already exists: {file_path}")

    django_secret_key = None
    domain = None
    address = None
    local_ip = None
    external_ip = None
    port = None
    debug = False
    if nodeData:
        node_data = nodeData

    fields = {}
    fields['CUSTOM_DEBUG'] = node_data['meta']['debug']
    if 'external_ip' in node_data['settings']:
        fields['EXTERNAL_IP'] = node_data['settings']['external_ip']
    else:
        fields['EXTERNAL_IP'] = ''
    fields['PORT'] = node_data['settings']['port']
    if 'local_ip' in node_data['settings'] and node_data['settings']['local_ip']:
        fields['LOCAL_IP'] = node_data['settings']['local_ip']
    else:
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                fields['LOCAL_IP'] = s.getsockname()[0] # i think this returns wrong
        except Exception as e:
            print('failed to get local ip', str(e))
            fields['LOCAL_IP'] = ''
        print("fields['LOCAL_IP']",fields['LOCAL_IP'])
    fields['CUSTOM_SECRET_KEY'] = node_data['meta']['django_secret_key']
    if 'address' in node_data['settings'] and node_data['settings']['address']:
        fields['ADDRESS'] = node_data['settings']['address']
    elif 'nodeData' in node_data and 'address' in node_data['nodeData']:
        fields['ADDRESS'] = node_data['nodeData']['address']
    else:
        fields['ADDRESS'] = ''
    if 'domain' in node_data['meta']:
        fields['DOMAIN'] = node_data['meta']['domain']
    else:
        fields['DOMAIN'] = ''
    fields['ONION'] = get_onion_address()
    domain = fields['DOMAIN']
    port = fields['PORT']

    text = {}
    for key, value in fields.items():
        if value and str(value) != 'None' and 'tunnel' not in str(value).lower():
            text[key] = value
        else:
            text[key] = ''

    data_string = json.dumps(text, indent=4)
    open(homepath + "/Sonet/.data/special/settings.py", "w").close()
    f = open(homepath + "/Sonet/.data/special/settings.py", "r+")
    f.writelines(data_string)
    f.close

    operatorData = get_operatorData(operatorData)
    if 'sonet' in operatorData:
        sonet_data = operatorData['sonet']

        # import json
        from pathlib import Path
        filename = Path.home() / "Sonet" / "SoNodeServer" / "static_cdn" / "manifest.json"

        with filename.open("r", encoding="utf-8") as f:
            manifest_dict = json.load(f)

        manifest_dict['name'] = sonet_data['Title']
        manifest_dict['short_name'] = sonet_data['Title']

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(manifest_dict, f, indent=4)



    nodes = get_node_list(operatorData=operatorData, exclude_self=False)
    conf_path = homepath + "/Sonet/.data/special/cors.conf"
    if os.path.exists(conf_path):
        with open(conf_path, "r") as f:
            existing_lines = f.read().splitlines()
    else:
        existing_lines = []
    new_lines = []
    new_lines.append("map $http_origin $cors_origin {")
    new_lines.append('    default "";')
    if 'seed_ip' in operatorData:
        new_lines.append(f'    "{operatorData["seed_ip"]}" $http_origin;')
    if 'ADDRESS' in fields:
        address = fields['ADDRESS']
        new_lines.append(f'    "{address}" $http_origin;')
    if 'EXTERNAL_IP' in fields:
        external_ip = fields['EXTERNAL_IP']
        new_lines.append(f'    "{external_ip}" $http_origin;')
    if 'LOCAL_IP' in fields:
        local_ip = fields['LOCAL_IP']
        new_lines.append(f'    "{local_ip}" $http_origin;')
    new_lines.append("}")
    print('new_lines:',new_lines)

    with open(conf_path, "w") as f:
        f.write("\n".join(new_lines) + "\n")

    if 'nodeData' in node_data and 'id' in node_data['nodeData'] and node_data['nodeData']['id'] in address:
        tunnel_name = node_data['nodeData']['id']
        cert_path = os.path.expanduser(f"~/Sonet/.data/cloudflare_registration/{tunnel_name}.json")
        if os.path.exists(cert_path):
            project_dir = Path.home() / "Sonet"
            active_dir = project_dir / ".data" / "cloudflare_registration"
            actv_json = active_dir / f"{tunnel_name}.json"

            hostname = f"{tunnel_name}.{domain}"
            config = {
                "tunnel": tunnel_name,
                "credentials-file": str(actv_json.resolve()),
                "ingress": [
                    {
                        "hostname": hostname,
                        "service": f"http://localhost:{port}",
                    },
                    {
                        "hostname": domain,
                        "service": f"http://localhost:{port}"
                    },
                    {"service": "http_status:404"}
                ]
            }
            text = f"Creating config.yaml"
            import yaml
            config_path = active_dir / "config.yml"
            with open(config_path, "w") as f:
                yaml.dump(config, f)
    return None

# not used
def config_lighthouse(is_lighthouse=None, operatorData=None):
    LIGHTHOUSE_FILE = "/etc/nebula/lighthouses.conf"

    system = platform.system()
    if system == "Darwin":
        CONFIG_FILE = f"/Users/{username}/Sonet/.data/nebula/config.yml"
    elif system == "Linux":
        CONFIG_FILE = f"/home/{username}/Sonet/.data/nebula/config.yml"

    nodeId = fetch_secure_item('local_nodeId')
    NODE_NAME = nodeId
    v_ip = fetch_secure_item('v_ip')
    if not v_ip:
        v_ip = pick_unique_ip()

    
    lighthouse_nodes = get_node_list(operatorData=operatorData, target={'category':'abilities', 'sub_cat':'lighthouse'}, exclude_relays=False, exclude_self=False, refresh_list=True)
    lighthouse_addresses = []
    for iden, address in lighthouse_nodes.items():
        lighthouse_addresses.append(address['v_ip'])

    operatorData = get_operatorData() # refresh after get_node_list refresh_list
    if is_lighthouse == None:
        is_lighthouse = False
        local_node = operatorData['myNodes'][nodeId]
        if 'abilities' in local_node['nodeData']:
            if 'lighthouse' in local_node['nodeData']['abilities'] and local_node['nodeData']['abilities']['lighthouse']:
                is_lighthouse = True
                lighthouse_addresses.append(v_ip)
    elif is_lighthouse:
        local_node = operatorData['myNodes'][nodeId]
        if 'abilities' not in local_node['nodeData']:
            local_node['nodeData']['abilities'] = {}
        if 'lighthouse' not in local_node['nodeData']['abilities'] or not local_node['nodeData']['abilities']['lighthouse']:
            local_node['nodeData']['abilities']['lighthouse'] = True
            operatorData['myNodes'][nodeId] = local_node
            write_operatorData(operatorData)
        lighthouse_addresses.append(v_ip)
    elif is_lighthouse == False:
        local_node = operatorData['myNodes'][nodeId]
        if 'abilities' in local_node['nodeData']:
            if 'lighthouse' in local_node['nodeData']['abilities'] and local_node['nodeData']['abilities']['lighthouse']:
                del local_node['nodeData']['abilities']['lighthouse']
                operatorData['myNodes'][nodeId] = local_node
                write_operatorData(operatorData)
        if v_ip in lighthouse_addresses:
            lighthouse_addresses.pop(v_ip)


    IS_LIGHTHOUSE = is_lighthouse

    with open(CONFIG_FILE, "w") as out:
        out.write("pki:\n")
        out.write(f"  ca: /etc/nebula/ca.crt\n")
        out.write(f"  cert: /etc/nebula/{NODE_NAME}.crt\n")
        out.write(f"  key: /etc/nebula/{NODE_NAME}.key\n\n")

        out.write("lighthouse:\n")
        out.write(f"  am_lighthouse: {str(IS_LIGHTHOUSE).lower()}\n")
        out.write("  hosts:\n")

        # with open(LIGHTHOUSE_FILE, "r") as lh:
        #     for line in lh:
        for line in lighthouse_addresses:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            out.write(f'    - "{line}"\n')

        out.write("\nlisten:\n")
        out.write("  host: 0.0.0.0\n")
        out.write("  port: 4242\n\n")

        out.write("\nstatic_host_map:\n")
        out.write(f"  {v_ip}: []\n")

        out.write("firewall:\n")
        out.write("  inbound:\n")
        out.write("    - port: any\n")
        out.write("      proto: any\n")
        out.write("      host: any\n")
        out.write("  outbound:\n")
        out.write("    - port: any\n")
        out.write("      proto: any\n")
        out.write("      host: any\n")

        # /etc/nebula/lighthouses.conf
        # lh1.example.net:4242
        # lh2.example.net:4242
        # 203.0.113.45:4242
    return operatorData
# not used
def pick_unique_ip(subnet="10.0.0.0/16", used_ips=None, max_attempts=5000):
    """
    Pick a unique IP from a large subnet without iterating over all addresses.
    
    Args:
        subnet (str): Subnet to pick from, e.g., "10.0.0.0/16" or "10.0.0.0/12"
        used_ips (set or list): Already assigned IPs as strings
        max_attempts (int): Max random attempts to find an unused IP
    
    Returns:
        str: A unique IP
    
    Raises:
        ValueError: If no available IP is found after max_attempts
    """
    operatorData = get_operatorData()
    used_ips = [i['v_ip'] for i in operatorData['ip_master_list']]
    import ipaddress
    import random
    used_ips = set(used_ips or [])
    net = ipaddress.ip_network(subnet)
    
    total_hosts = net.num_addresses - 2  # skip network and broadcast
    if total_hosts <= len(used_ips):
        raise ValueError("No available IPs left in the subnet")
    
    first_ip_int = int(net.network_address) + 1
    last_ip_int = int(net.broadcast_address) - 1
    
    for _ in range(max_attempts):
        candidate = random.randint(first_ip_int, last_ip_int)
        ip_str = str(ipaddress.IPv4Address(candidate))
        ip_str = f'{ip_str}:4242'
        if ip_str not in used_ips:
            store_secure_item('v_ip', ip_str)
            return ip_str
    
    # fallback: iterate if random fails (rare in large subnets)
    for ip in net.hosts():
        ip_str = f'{ip}:4242'
        if ip_str not in used_ips:
            store_secure_item('v_ip', ip_str)
            return ip_str
    
    raise ValueError("No available IPs found after random attempts")



def fetch_django_secret_key(output=None, node_data=None, node_id=None, operatorData=None):
    print('-fetch_django_secret_key start')
    print('reverse_output_text:',output[-250])
    if 'meta' in node_data and 'django_secret_key' in node_data['meta'] and node_data['meta']['django_secret_key']:
        secret_key = node_data['meta']['django_secret_key']
        print('key already saved', secret_key)
        operatorData = get_operatorData(operatorData)
        if 'myNodes' in operatorData:
            for node in operatorData['myNodes']:
                if 'new_install' in node:
                    operatorData['myNodes'][node] = node_data
        operatorData['myNodes'][node_id] = node_data
        write_operatorData(operatorData)
    else:
        lines = output.split('\n')
        position = -1
        runs = 0
        key_found = False
        while runs < 40 and key_found == False:
            runs += 1
            secret_key = lines[position]
            print('secret_key?',position,secret_key)
            if 'key:' in secret_key and 'get_random_secret_key' not in secret_key:
                x = secret_key.find('key:')+4
                secret_key = secret_key[x:].strip()
                key_found = True
            position -= 1
        print('secret_key_found:',secret_key)
        if not key_found:
            update_output("Failed to create django secret key. Please restart.", output)
            raise RuntimeError("Failed to create django secret key.")

        operatorData = get_operatorData(operatorData)
        if 'myNodes' in operatorData:
            for node in operatorData['myNodes']:
                if 'new_install' in node:
                    if 'meta' not in operatorData['myNodes'][node]:
                        operatorData['myNodes'][node]['meta'] = {}
                    operatorData['myNodes'][node]['django_secret_key'] = secret_key
        node_data['meta']['django_secret_key'] = secret_key
        operatorData['myNodes'][node_id] = node_data
        write_operatorData(operatorData)
    return operatorData
        
def setup_pyenv(output=None, node_data=None):
    import os
    import subprocess
    python_version = '3.11.9'

    home = os.path.expanduser("~")
    pyenv_dir = os.path.join(home, "Sonet", ".data", "pyenv")
    venv_path = os.path.join(home, "Sonet", ".data", "env")

    def install_dependencies():
        print("Installing required dependencies...")
        systemPass = fetch_secure_item('sysPass')
        if not systemPass:
            operatorData = get_operatorData()
            systemPass = operatorData['systemPass']

        import subprocess
        device_system = get_device_system()
        if device_system == 'mac':
            cmds = [f"echo '{systemPass}' | sudo -S brew update && sudo -S brew install build-essential libssl libbz2 readline sqlite3 curl ncurses xz tk \
                libxml2 libffi liblzma"]
            cmds = []
        elif device_system == 'windows':
            cmds = []
        else:  
            package_manager = get_package_manager()

            if package_manager == 'apt':
                cmds = []
            elif package_manager == 'dnf':
                def get_dnf_command():
                    if shutil.which("dnf5"):
                        return "dnf5"
                    elif shutil.which("dnf"):
                        return "dnf"
                    else:
                        raise RuntimeError("Neither dnf nor dnf5 found on system")
                dnf_cmd = get_dnf_command()
                group_package = "@development-tools" if dnf_cmd == "dnf5" else "groupinstall 'Development Tools'"
                cmds = [
                    f'''echo '{systemPass}' | sudo -S {dnf_cmd} install {group_package} -y''',
                    f'''echo '{systemPass}' | sudo -S {dnf_cmd} install gcc zlib-devel bzip2 bzip2-devel readline-devel sqlite sqlite-devel openssl-devel tk-devel libffi-devel xz-devel wget make -y'''
                ]

        for cmd in cmds:
            update_output(cmd.replace(systemPass,'*****'), output)
            r = subprocess.run(
                cmd,
                check=True,
                input=f"{systemPass}\n".encode(),
            )

    def install_pyenv():
        install_dependencies()
        if not os.path.isdir(pyenv_dir):
            print("Installing pyenv...")
            git_path = shutil.which("git")
            cmd = f'{git_path} clone https://github.com/pyenv/pyenv.git {pyenv_dir}'
            update_output(cmd, output)
            subprocess.run(cmd, shell=True, check=True)
            content = "Pyenv installed successfully."
            update_output(content, output)
        else:
            content = "Pyenv is already installed."
            update_output(content, output)

    def set_pyenv_env():
        pyenv_bin_path = os.path.join(pyenv_dir, "bin")
        pyenv_root_env = f"export PYENV_ROOT={pyenv_dir}"
        pyenv_path_env = f"export PATH={pyenv_bin_path}:$PATH"
        pyenv_init_commands = (
            f"{pyenv_root_env} && "
            f"{pyenv_path_env} && "
            f'eval "$({pyenv_bin_path}/pyenv init --path)" && '
            f'eval "$({pyenv_bin_path}/pyenv init -)"'
        )
        cmd = f"{pyenv_init_commands} && pyenv --version"
        update_output(cmd, output)
        result = subprocess.run(
            cmd,
            shell=True,
            text=True,
            capture_output=True,
        )
        if result.returncode == 0:
            content = f"Pyenv initialized successfully:\n{result.stdout}"
            update_output(content, output)
        else:
            content = f"Error initializing pyenv:\n{result.stderr}"
            update_output(content, output)
        
    def install_python():
        Clock.schedule_once(lambda dt, line=f'Installing python {python_version}...': update_output(line, output))
        pyenv_bin_path = os.path.join(pyenv_dir, "bin")
        pyenv_root_env = f"export PYENV_ROOT={pyenv_dir}"
        pyenv_path_env = f"export PATH={pyenv_bin_path}:$PATH"
        pyenv_install_command = (
            f"{pyenv_root_env} && {pyenv_path_env} && "
            f'''yes | {pyenv_bin_path}/pyenv install {python_version} && '''
            f"{pyenv_bin_path}/pyenv local {python_version}"
        )
        
        update_output(pyenv_install_command, output)
        subprocess.run(pyenv_install_command, shell=True, check=True)
        content = f"Python {python_version} installed and set as the active version for pyenv."
        update_output(content, output)

    def create_venv():
        pyenv_python_path = os.path.join(pyenv_dir, "versions", python_version, "bin", "python3")
        if not os.path.isfile(pyenv_python_path):
            update_output(f"Python {python_version} binary not found at {pyenv_python_path}.", output)
        
        cmd = f"{pyenv_python_path} -m venv {venv_path}"
        update_output(cmd, output)
        subprocess.run(cmd, shell=True, check=True)
        content = f"Virtual environment created at: {venv_path}"
        update_output(content, output)
        
    def install_requirements():
        subprocess.run(f'{venv_path}/bin/pip install -r requirements.txt', shell=True, check=True)
        print("Requirements installed.")

    print('**install_pyenv')
    install_pyenv()
    print('**set_pyenv_env')
    set_pyenv_env()
    print('**install_python')
    install_python()
    print('**create_venv')
    create_venv()
    print(f"all done pyenv setup")

def finalize_install(output=None, node_data=None, operatorData=None):
    app_operational = False
    external_access = False
    error_code = 'finalizing'
    result = None
    operatorData = get_operatorData(operatorData)

    print('-finalize_install:',node_data)
    node_data['meta']['is_installed'] = True
    new_node_settings = node_data['settings']
    adjust_settings(node_data)
    
    try:
        local = requests.get(f'http://{new_node_settings["localhost"]}/utils/is_sonet')
        if local.status_code == 200:
            error_code = 'active'
            app_operational = True
            text = f'\nApp is operational.\n'
            update_output(text, output)
            if 'sonet' in operatorData:
                error_code = 'continue1'
                text = f'\nCreating node object...\n'
                update_output(text, output)
                nodeData, is_new = get_or_create_node_obj(operatorData, new_node=node_data)
                if nodeData and is_new:
                    text = f'\nObject created.\n'
                    update_output(text, output)
                    clear_temp_data()
                    try:
                        operatorData = get_operatorData()
                        del operatorData['start_local_install']
                        write_operatorData(operatorData)
                    except:
                        pass
                    text = '\nSonet setup successfully!\n'
                    update_output(text, output)
                else:
                    text = '\nSonet setup failed.\n'
                    update_output(text, output)
        else:
            text = f'\nSomething went wrong. App is NOT operational.\n'
            update_output(text, output)

    except Exception as e:
        print('finalize fail', str(e))
        update_output(f'Finalize error: {e}', output)

def get_package_manager():
    # (Debian, Ubuntu)
    if os.path.exists('/etc/debian_version'):
        return 'apt'
    # (Fedora, RHEL 8+)
    if shutil.which('dnf'): # dnf not fully supported
        return 'dnf'
    # (CentOS, RHEL < 8)
    if shutil.which('yum'):
        return 'yum'
    # (openSUSE)
    if shutil.which('zypper'):
        return 'zypper'
    # Alpine (uses apk)
    if os.path.exists('/etc/alpine-release'):
        return 'apk'
    return None  # Unknown

def get_device_system():
    if platform.system() == 'Darwin':
        device_system = 'mac'
    elif platform.system() == 'Windows':
        device_system = 'windows'
    else:  # linux variants
        device_system = 'linux'
    return device_system


def fetch_remote_data(remote_data, operatorData=None, fetch_key=True, ssh_client=None, output=None):
    print('-fetch_remote_data',remote_data)
    username = remote_data['username']
    if ssh_client:
        close_connection = False
    else:
        import paramiko
        hostname = remote_data['local_address']
        port = remote_data['port']
        password = remote_data['password']
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(hostname, port, username, password)
        close_connection = True

    sftp = ssh_client.open_sftp()
    if remote_data['os_type'] == 'linux':
        remote_home = f'/home/{username}'
    elif remote_data['os_type'] == 'mac':
        remote_home = f'/Users/{username}'
    try:
        if fetch_key:
            print('fetch_key')
            remote_key_path = f"{remote_home}/Sonet/.data/special/keys/.soSecret.key"
            local_key_path = homepath + f"/Sonet/.data/special/keys/{remote_data['nickname']}_key.key"
            try:
                sftp.get(remote_key_path, local_key_path)
                print("Key downloaded successfully")
                update_output(f"Key downloaded successfully", output)
            except Exception as e:
                print('fetch_remote_data err',str(e))
                if 'No such file' in str(e):
                    if os.path.exists(local_key_path):
                        os.remove(local_key_path)
                    from commands.locked import generate_key
                    generate_key(file_path=f"/Sonet/.data/special/keys/{remote_data['nickname']}_key.key")
                    print('created new key for remote')
                    ssh_client.exec_command(f"mkdir -p ~/Sonet/.data/special/keys")
                    sftp.put(local_key_path, remote_key_path)
                    update_output(f"Created new key for remote", output)

        remote_data_path = f"{remote_home}/Sonet/.data/operator_data/operatorData.enc"
        local_data_path = homepath + f"/Sonet/.data/operator_data/{remote_data['nickname']}_opData.enc"
        sftp.get(remote_data_path, local_data_path)
        print("File downloaded successfully")
        update_output(f"File downloaded successfully", output)
        remote_opData = True
        try:
            remote_nodeKey_path = f"{remote_home}/Sonet/.data/operator_data/node_keys.enc"
            local_nodeKey_path = homepath + f"/Sonet/.data/operator_data/{remote_data['nickname']}_nodeKeys.enc"
            sftp.get(remote_nodeKey_path, local_nodeKey_path)
            print("Remote node keys downloaded successfully")
            update_output(f"Remote node keys downloaded successfully", output)
        except Exception as e:
            print("Remote node keys not found")
            update_output(f"Remote node keys not found", output)
    except Exception as e:
        print("Remote file not found", str(e))
        if 'No such file' in str(e):
            update_output(f"Remote file not found: {e}", output)
            remote_opData = {}
            ssh_client.exec_command(f"mkdir -p ~/Sonet/.data/operator_data")
    finally:
        sftp.close()
    if close_connection:
        ssh_client.close()

    print('remote_data_found',remote_opData)
    if remote_opData:
        with open(homepath + f"/Sonet/.data/operator_data/{remote_data['nickname']}_opData.enc", 'rb') as file:
            encrypted_data = file.read()
            data_string = None
            try:
                data_string = decrypt(encrypted_data, key_path=homepath+f"/Sonet/.data/special/keys/{remote_data['node_id']}_key.key")
            except:
                try:
                    data_string = decrypt(encrypted_data, key_path=homepath+f"/Sonet/.data/special/keys/{remote_data['nickname']}_key.key")
                except:
                    pass
            if not data_string:
                update_output(f"No data.", output)
                return False
            remote_opData = json.loads(data_string)
            print('remote_opData:',remote_opData)
            if 'local_nodeId' in remote_opData and 'myNodes' in remote_opData and remote_opData['local_nodeId'] in remote_opData['myNodes']:
                print('remote id:',remote_opData['local_nodeId'])
                remote_node_data = remote_opData['myNodes'][remote_opData['local_nodeId']]
                remote_node_data['location'] = remote_data['nickname']
                operatorData = get_operatorData(operatorData)

                if remote_opData and 'sonet' in remote_opData and 'id' in remote_opData['sonet']:
                    if remote_opData['sonet']['id'] == operatorData['sonet']['id']:
                        if remote_opData['local_nodeId'] not in operatorData['myNodes'] or operatorData['myNodes'][remote_opData['local_nodeId']] != remote_node_data:
                            operatorData['myNodes'][remote_opData['local_nodeId']] = remote_node_data
                            remote_data['node_id'] = remote_opData['local_nodeId']
                            write_operatorData(operatorData)
                            
            if 'node_id' in remote_data:
                from pathlib import Path
                try:
                    renamed_data_path = homepath + f"/Sonet/.data/operator_data/{remote_data['node_id']}_opData.enc"
                    old = Path(local_data_path)
                    new = Path(renamed_data_path)
                    old.rename(new)
                except:
                    pass
                try:
                    renamed_nodeKey_path = homepath + f"/Sonet/.data/operator_data/{remote_data['node_id']}_nodeKeys.enc"
                    old = Path(local_nodeKey_path)
                    new = Path(renamed_nodeKey_path)
                    old.rename(new)
                except:
                    pass
                if fetch_key:
                    try:
                        renamed_key_path = homepath + f"/Sonet/.data/special/keys/{remote_data['node_id']}_key.key"
                        old = Path(local_key_path)
                        new = Path(renamed_key_path)
                        old.rename(new)
                    except:
                        pass
    print('retrieved data:',str(remote_opData)[:300])
    return remote_opData


def update_remote_data(updated_node_data=None, remote_opData=None, remote_data=None, operatorData=None, remote_password=None, ssh_client=None, output=None):
    print('-update_remote_data')
    if updated_node_data and 'location' in updated_node_data and updated_node_data['location'] == 'local':
        print('return1')
        return True
    remote_upload_success = False
    if not remote_data:
        operatorData = get_operatorData(operatorData)
        remote_data = get_remote(node_id=operatorData['selected_node'], operatorData=operatorData)
    
    if remote_data:
        if remote_data['os_type'] == 'linux':
            remote_home = f'/home'
        elif remote_data['os_type'] == 'mac':
            remote_home = f'/Users'

        if 'node_id' in remote_data:
            label = remote_data['node_id']
        else:
            label = remote_data['nickname']

        local_remoteNode_data_path = homepath + f"/Sonet/.data/operator_data/{label}_opData.enc"
        local_remoteNode_key_path = homepath+f"/Sonet/.data/special/keys/{label}_key.key"
        print('local_remoteNode_data_path',local_remoteNode_data_path)
        print('local_remoteNode_key_path',local_remoteNode_key_path)
        if not remote_opData:
            remote_opData = fetch_secure_item(key_path=local_remoteNode_key_path, file_path=local_remoteNode_data_path)
        if not remote_opData:
            remote_opData = fetch_remote_data(remote_data, operatorData=operatorData, fetch_key=True)
        if remote_opData:
            if updated_node_data:
                remote_opData['myNodes'][updated_node_data['nodeData']['id']] = updated_node_data
            store_secure_item(None, remote_opData, key_path=local_remoteNode_key_path, file_path=local_remoteNode_data_path)

            if ssh_client:
                is_connected = True
                close_remote = False
            else:
                is_connected, ssh_client = make_remote_connection(remote_data)
                close_remote = True
            print('is_connected',is_connected,'ssh_client',ssh_client)
            if is_connected:
                try:
                    sftp = ssh_client.open_sftp()

                    remote_data_path = f"{remote_home}/{remote_data['username']}/Sonet/.data/operator_data/operatorData.enc"
                    print('remote_data_path:',remote_data_path)
                    sftp.put(local_remoteNode_data_path, remote_data_path)
                    if remote_password:
                        local_remote_sysPass_path = homepath + f"/Sonet/.data/operator_data/{remote_data['nickname']}_sysPass.enc"
                        print('local_remote_sysPass_path:',local_remote_sysPass_path)
                        store_secure_item(None, remote_password, key_path=local_remoteNode_key_path, file_path=local_remote_sysPass_path)

                        remote_sysPass_path = f"{remote_home}/{remote_data['username']}/Sonet/.data/operator_data/sysPass.enc"
                        print('remote_sysPass_path',remote_sysPass_path)
                        sftp.put(local_remote_sysPass_path, remote_sysPass_path)

                        print("File sent successfully")
                        remote_upload_success = True
                    else:
                        print("File sent successfully")
                        remote_upload_success = True
                    sftp.close()
                    if close_remote:
                        ssh_client.close()
                except Exception as e:
                    print("Remote send fail", str(e))
                    update_output(f"Remote send fail: {e}", output)
                    if close_remote:
                        ssh_client.close()
                
    return remote_upload_success



def make_remote_connection(remote_data=None, cls=None):
    print('-make_remote_connection',remote_data)
    import paramiko
    import socket
    def make_connection(hostname, port, cls):
        try:
            if cls:
                cls.ssh_client = paramiko.SSHClient()
                client = cls.ssh_client
            else:
                ssh_client = paramiko.SSHClient()
                client = ssh_client

            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=hostname,
                port=port,
                username=remote_data['username'],
                password=remote_data['password'],
            )
            print('connected')
            if cls:
                return True, cls
            return True, client
        except paramiko.ssh_exception.NoValidConnectionsError as e:
            print("Unable to connect:", e)
        except paramiko.AuthenticationException:
            print("Authentication failed.")
        except paramiko.SSHException as e:
            print("SSH protocol error:", e)
        except socket.timeout:
            print("Connection timed out.")
        except Exception as e:
            print("General error:", e)
        
        if cls:
            return False, cls
        try:
            client.close()
        except:
            pass
        return False, client

    connected = None
    if 'local_address' in remote_data and remote_data['local_address']:
        connected, cls = make_connection(remote_data['local_address'], remote_data['port'], cls=cls)
    if not connected and 'remote_address' in remote_data and remote_data['remote_address']:
        connected, cls = make_connection(remote_data['remote_address'], remote_data['remote_port'], cls=cls)
    return connected, cls

def send_manager_to_remote(remote_data, ssh_client=None, text_display=None, manager_only=False, entire_dir=False):
    print('-send_manager_to_remote')

    def sftp_put_dir(sftp, local_dir, remote_dir):
        try:
            sftp.stat(remote_dir)
        except IOError:
            sftp.mkdir(remote_dir)

        for item in os.listdir(local_dir):
            local_path = os.path.join(local_dir, item)
            remote_path = remote_dir + "/" + item

            if os.path.isfile(local_path):
                sftp.put(local_path, remote_path)
            elif item not in ['nodenv', 'nenv', 'env', 'pyenv', '__pycache__', 'media'] and not item.startswith('.'):
                # Recursively create and upload subdirectory
                sftp_put_dir(sftp, local_path, remote_path)
    
    if not isinstance(remote_data, dict):
        remote_data = get_remote(node_id=remote_data)
    if ssh_client:
        is_connected = True
        close_connection = False
    else:
        is_connected, ssh_client = make_remote_connection(remote_data)
        close_connection = True
    if is_connected:

        if remote_data['os_type'] == 'linux':
            remote_home = f'/home'
        elif remote_data['os_type'] == 'mac':
            remote_home = f'/Users'
        homepath = expanduser("~")
        remote_folder_path_manager = f"{remote_home}/{remote_data['username']}/Sonet/SoNodeManager"
        local_folder_path_manager = f"{homepath}/Sonet/SoNodeManager"

        remote_folder_path_server = f"{remote_home}/{remote_data['username']}/Sonet/SoNodeServer"
        local_folder_path_server = f"{homepath}/Sonet/SoNodeServer"

        remote_folder_path_node = f"{remote_home}/{remote_data['username']}/Sonet/SoNode"
        local_folder_path_node = f"{homepath}/Sonet/SoNode"
        if not entire_dir:
            ssh_client = remote_hash_stepper(ssh_client, local_folder=local_folder_path_manager, remote_folder=remote_folder_path_manager, text_display=text_display, ignore=None, force_reupload_script=False, delete_remote_orphans=True, dry_run=False)
            if not manager_only:
                ssh_client = remote_hash_stepper(ssh_client, local_folder=local_folder_path_server, remote_folder=remote_folder_path_server, text_display=text_display, ignore=None, force_reupload_script=False, delete_remote_orphans=True, dry_run=False)
                ssh_client = remote_hash_stepper(ssh_client, local_folder=local_folder_path_node, remote_folder=remote_folder_path_node, text_display=text_display, ignore=None, force_reupload_script=False, delete_remote_orphans=False, dry_run=False)
        else:
            sftp = ssh_client.open_sftp()
            sftp_put_dir(sftp, remote_folder_path_manager, local_folder_path_manager)

            if not manager_only:
                sftp_put_dir(sftp, local_folder_path_server, remote_folder_path_server)
                if os.path.exists(local_folder_path_node):
                    sftp_put_dir(sftp, local_folder_path_node, remote_folder_path_node)

            sftp.close()
        if close_connection:
            ssh_client.close()
        return True
    return False


def refresh_ip(instance=None, display=None, text='refreshing...', network_check=False, immediate=True):
    if display:
        display.text = text
    if immediate:
        return refresh_ip_step2(display, network_check=network_check)
    else:
        Clock.schedule_once(lambda dt: refresh_ip_step2(display, network_check=network_check))

def refresh_ip_step2(display=None, network_check=False):
    # if not network_check:
    try:
        external_ip = requests.get('https://api.ipify.org').content.decode('utf8')
    except:
        external_ip = '127.0.0.1'
    # else:
    #     try:
    #         external_ip = requests.get('https://api.ipify.org').content.decode('utf8')
    #     except:
    #         external_ip = '127.0.0.1'
    if display:
        display.text = external_ip
    # instance.text = 'Refresh'
    return external_ip
    
def setup_ssh(host, user, password, iden):
    KEY_PATH = os.path.expanduser(f"~/.ssh/node_{iden}")
    PUB_KEY = KEY_PATH + ".pub"
    def run(cmd):
        try:
            subprocess.run(cmd, check=True)
        except Exception as e:
            print(f'setup_ssh cmd err:{e} - {cmd}')
            if "No such file or directory: 'sshpass'" in str(e):
                system = get_device_system()
                if system == 'linux':
                    package_manager = get_package_manager()
                    subprocess.run(['sudo', '-S', package_manager, 'install', '-y', 'sshpass'], check=True)
                elif system == 'mac':
                    def find_brew():
                        for p in ("/opt/homebrew/bin/brew", "/usr/local/bin/brew"):
                            if os.path.exists(p):
                                return p
                        return "/opt/homebrew/bin/brew"
                    brew_path = find_brew()
                    subprocess.run([brew_path, "install", 'sshpass'], check=True)
                subprocess.run(cmd, check=True)

    # 1. Create key if missing
    if not os.path.exists(KEY_PATH):
        run([
            "ssh-keygen", "-t", "ed25519",
            "-f", KEY_PATH,
            "-N", ""
        ])

    # 1.5. clear known-host
    run([
        "sshpass", "-p", password,
        "ssh-keygen",
        "-R",
        f"{host}"
    ])
    # 2. Copy key using password (non-interactive)
    run([
        "sshpass", "-p", password,
        "ssh-copy-id",
        "-o", "StrictHostKeyChecking=no",
        "-i", PUB_KEY,
        f"{user}@{host}"
    ])

    # 3. Verify key-based login
    run([
        "ssh",
        "-i", KEY_PATH,
        "-o", "BatchMode=yes",
        f"{user}@{host}",
        "echo SSH_OK"
    ])

    print("SSH automation ready")


# seems not used
def update_nginx_settings(run_restart=False):
    print('----update_nginx_settings')
    from commands.linux.linux_install_cmds import adjust_settings, edit_sites_available
    adjust_settings(None)
    edit_sites_available(install=False, run_restart=run_restart)

def setup_encrypted_secret_B(secret_value, var_name='secret', systemPass=None, operatorData=None):

    secret_file_path = f"/etc/Sonet/{var_name}.enc"
    systemPass = fetch_secure_item('sysPass')
    print('stored systemPass',systemPass)
    if not systemPass:
        if not operatorData:
            operatorData = get_operatorData()
        systemPass = operatorData['systemPass']
        result = setup_encrypted_secret(systemPass, var_name='sys_pass')
        print("Encrypted file:", result["encrypted_file"])
        print("Keys written to:", result["env_files"])

    env_file_paths = [
        os.path.expanduser("~/Sonet/.data/env"),
        os.path.expanduser("~/Sonet/.data/nodenv")
    ]

    if os.geteuid() != 0:
        if not systemPass:
            raise PermissionError("Must provide sudo_password when not running as root.")
        command = [
            "sudo", "-S", sys.executable, sys.argv[0],
            secret_value, var_name
        ]
        subprocess.run(command, input=f"{systemPass}\n", text=True)
        return
    
    import stat
    def _secure_write_file(path: str, content: bytes | str):
        """Write a file with 600 permissions (owner read/write only)."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        mode = "wb" if isinstance(content, bytes) else "w"
        with open(path, mode) as f:
            f.write(content)
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # chmod 600 initially

    def detect_django_group():
        try:
            proc = subprocess.check_output(
                ["ps", "-o", "group=", "-p", str(os.getppid())],
                text=True
            ).strip()
            return proc if proc else None
        except Exception:
            return None
    
    django_group = detect_django_group()
    print(f"[INFO] Using Django group: {django_group}")

    key = Fernet.generate_key()
    fernet = Fernet(key)
    encrypted_value = fernet.encrypt(secret_value.encode())

    _secure_write_file(secret_file_path, encrypted_value)

    subprocess.run(["chgrp", django_group, secret_file_path], check=True)
    os.chmod(secret_file_path, stat.S_IRUSR | stat.S_IRGRP)  # chmod 640

    for env_file_path in env_file_paths:
        if not os.path.exists(env_file_path):
            _secure_write_file(env_file_path, "")

        with open(env_file_path, "r") as f:
            lines = f.readlines()

        found = False
        for i, line in enumerate(lines):
            if line.startswith(f"{var_name}="):
                lines[i] = f'{var_name}="{key.decode()}"\n'
                found = True
                break
        if not found:
            lines.append(f'{var_name}="{key.decode()}"\n')

        _secure_write_file(env_file_path, "".join(lines))

        subprocess.run(["chgrp", django_group, env_file_path], check=True)
        os.chmod(env_file_path, stat.S_IRUSR | stat.S_IRGRP)  # chmod 640

    return {
        "encrypted_file": secret_file_path,
        "env_files": env_file_paths,
        "env_var": var_name,
        "key": key.decode(),
        "group": django_group
    }

def get_encrypted_secret(var=None, var_name=None):
    if not var and var_name:
        var = var_name
    secret_file_path = f"/etc/Sonet/{var}.enc"
    env_file_paths = [
        os.path.expanduser("~/Sonet/.data/special/keys"),
    ]

    def _read_env_value(env_file, key):
        if not os.path.exists(env_file):
            return None
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        return None

    key_value = None
    for env_file in env_file_paths:
        key_value = _read_env_value(env_file, var)
        if key_value:
            break

    if not key_value:
        return None

    if not os.path.exists(secret_file_path):
        return None

    with open(secret_file_path, "rb") as f:
        encrypted_value = f.read()

    fernet = Fernet(key_value.encode())
    try:
        result = fernet.decrypt(encrypted_value).decode()
        try:
            result = json.loads(result)
        except:
            pass
        return result
    except (FileNotFoundError, EnvironmentError):
        return None



def gb(bytes_val: int) -> float:
    return bytes_val / (1024 ** 3)

def check(label: str, passed: bool, detail: str, spec=True, output=None) -> bool:
    status = "PASS" if passed else "FAIL"
    print(f"  {status}  {label:<22} {detail}")
    update_output(f"  {status}  {label:<22} {detail}", output)
    return str(spec) if passed else False

def check_bitness(output=None) -> bool:
    bits = struct.calcsize("P") * 8
    return check("64-bit OS/Python", bits == 64, f"{bits}-bit", output=output)

def check_cpu_cores(min_logical_cores: int, output=None) -> bool:
    logical = psutil.cpu_count(logical=True)
    physical = psutil.cpu_count(logical=False)
    return check(
        "CPU logical cores",
        logical >= min_logical_cores,
        f"{logical} logical ({physical} physical), need ≥ {min_logical_cores}",
        spec=f"{logical} logical ({physical} physical)",
        output=output
    )

def check_cpu_freq(min_freq_ghz: float, output=None) -> bool:
    freq = psutil.cpu_freq()
    if freq is None:
        return check("CPU frequency", False, "could not be determined")
    reported_mhz = freq.max if freq.max else freq.current
    reported_ghz = reported_mhz / 1000
    return check(
        "CPU frequency",
        reported_ghz >= min_freq_ghz,
        f"{reported_ghz:.2f} GHz, need ≥ {min_freq_ghz} GHz",
        spec=f"{reported_ghz:.2f}",
        output=output
    )

def check_ram(min_ram_gb: int, output=None) -> bool:
    total_gb = gb(psutil.virtual_memory().total)
    return check("RAM", total_gb >= min_ram_gb, f"{total_gb:.1f} GB, need ≥ {min_ram_gb} GB", spec=f"{total_gb:.1f}", output=output)

def check_disk(min_disk_gb: int, output=None) -> bool:
    root = "C:\\" if platform.system() == "Windows" else "/"
    try:
        usage = psutil.disk_usage(root)
        total_gb = gb(usage.total)
        return check(
            "Primary disk",
            total_gb >= min_disk_gb,
            f"{total_gb:.0f} GB total, need ≥ {min_disk_gb} GB",
            spec=f"{total_gb:.0f}",
            output=output
        )
    except PermissionError:
        return check("Primary disk", False, "permission denied reading disk info")

def check_os(min_linux_kernel: tuple, min_macos_minor: int, min_windows_major: int, output=None) -> bool:
    system = platform.system()

    if system == "Darwin":
        mac_ver = platform.mac_ver()[0]
        parts = [int(x) for x in mac_ver.split(".")]
        if parts[0] >= 11:
            passed = True
        else:
            passed = (parts[0] == 10 and len(parts) > 1 and parts[1] >= min_macos_minor)
        return check(
            "OS version",
            passed,
            f"macOS {mac_ver}, need 10.{min_macos_minor}+ (High Sierra) or later",
            spec=mac_ver,
            output=output
        )

    elif system == "Linux":
        supported_distros = ['debian']
        import distro
        distro_id = distro.id()
        distro_like = distro.like().split()  # e.g. "debian ubuntu" -> ["debian", "ubuntu"]
        is_debian_based = distro_id == "debian" or "debian" in distro_like
        if not is_debian_based:
            return check("OS version", False, f"distro is '{distro_id}', need Debian or a Debian-based distro", spec=distro_id, output=output)

        kernel_str = platform.release().split("-")[0]
        try:
            k_parts = tuple(int(x) for x in kernel_str.split(".")[:2])
        except ValueError:
            return check("OS version", False, f"could not parse kernel version '{kernel_str}'", output=output)
        passed = k_parts >= min_linux_kernel
        return check(
            "OS version",
            passed,
            f"Debian, kernel {kernel_str}, need kernel ≥ {'.'.join(map(str, min_linux_kernel))}",
            output=output
        )
    # elif system == "Windows":
    #     ver = sys.getwindowsversion()
    #     major = ver.major
    #     passed = major >= min_windows_major
    #     return check(
    #         "OS version",
    #         passed,
    #         f"Windows {major}.{ver.minor} (build {ver.build}), need Windows {min_windows_major}+",
            # output=output
    #     )

    else:
        return check("OS version", False, f"unknown OS: {system}")

def check_cpu_benchmark(max_seconds: float, output=None) -> bool:
    """
    Runs a single-threaded matrix multiplication benchmark using only stdlib.
    Multiplies two 400x400 matrices of floats and times it.
    A late-2010s mid-range CPU should complete this well under the threshold.
    """
    import time
    import random
 
    SIZE = 400
    random.seed(42)
 
    def make_matrix():
        return [[random.random() for _ in range(SIZE)] for _ in range(SIZE)]
 
    def matmul(A, B):
        result = [[0.0] * SIZE for _ in range(SIZE)]
        for i in range(SIZE):
            for k in range(SIZE):
                a_ik = A[i][k]
                for j in range(SIZE):
                    result[i][j] += a_ik * B[k][j]
        return result
 
    # print("  Running CPU benchmark (matrix multiplication)...")
    A, B = make_matrix(), make_matrix()
    t0 = time.perf_counter()
    matmul(A, B)
    elapsed = time.perf_counter() - t0
 
    return check(
        "CPU benchmark",
        elapsed <= max_seconds,
        f"{elapsed:.2f}s for 400×400 matmul, need ≤ {max_seconds}s",
        spec=f"{elapsed:.2f}s",
        output=output
    )
    
    
def check_internet_speed(min_download_mbps: float, min_upload_mbps: float, output=None) -> tuple[bool, bool]:
    """Returns (download_passed, upload_passed)."""
    # speedtest-cli calls FileIO(f.fileno(), 'w') on sys.stderr at import time.
    # Redirect stderr to /dev/null (which has a real fd) before importing.
    _real_stderr = sys.stderr
    _devnull = open(os.devnull, 'w')
    sys.stderr = _devnull
    try:
        import speedtest
    except ImportError:
        sys.stderr = _real_stderr
        _devnull.close()
        sys.exit("speedtest-cli is required. Install it with:  pip install speedtest-cli")
    finally:
        sys.stderr = _real_stderr
        _devnull.close()
 
    print("  Running internet speed test (this may take a moment)...")
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        download_mbps = st.download() / 1_000_000
        upload_mbps   = st.upload()   / 1_000_000
    except Exception as e:
        result = check("Internet speed", False, f"speed test failed: {e}")
        return result, result
 
    dl_passed = check(
        "Download speed",
        download_mbps >= min_download_mbps,
        f"{download_mbps:.1f} Mbps, need ≥ {min_download_mbps} Mbps",
    )
    ul_passed = check(
        "Upload speed",
        upload_mbps >= min_upload_mbps,
        f"{upload_mbps:.1f} Mbps, need ≥ {min_upload_mbps} Mbps",
    )
    return download_mbps, upload_mbps
 
def run_hardware_test(remote_cmd=None, output=None, node_data=None, operatorData=None):
    """
    Checks whether the current machine meets the baseline specs of a
    late-2010s mid-range consumer device (circa 2017-2019).

    Thresholds used:
      CPU cores  : >= 4 logical cores
      CPU freq   : >= 2.0 GHz (base/reported)
      RAM        : >= 8 GB
      Storage    : >= 256 GB total on the primary disk
      OS         : Windows 10+ / macOS 10.13+ / Linux kernel 4.15+
      64-bit     : required
    """

    MIN_LOGICAL_CORES = 4
    MIN_FREQ_GHZ      = 2.0
    MIN_RAM_GB        = 7.5
    MIN_DISK_GB       = 200
    MIN_WINDOWS_MAJOR = 10
    MIN_MACOS_MINOR   = 13
    MIN_LINUX_KERNEL  = (6, 00)
    MIN_DOWNLOAD_MBPS  = 21.0   # FCC "broadband" threshold
    MIN_UPLOAD_MBPS    = 4.0    # typical decent home upload
    MAX_BENCHMARK_SECS = 6.0    # 400x400 matmul; a decent 2017+ CPU does this in ~3-6s
    MIN_DOWNLOAD_MBPS  = 5.0   # FCC "broadband" threshold
    # edited for dev:
    MIN_UPLOAD_MBPS    = 2.0    # typical decent home upload
    MAX_BENCHMARK_SECS = 10.0    # 400x400 matmul; a decent 2017+ CPU does this in ~3-6s

    # operatorData = get_operatorData(operatorData)
    # reqs = {'MIN_LOGICAL_CORES':4,'MIN_FREQ_GHZ':2.0,'MIN_RAM_GB':7.5,'MIN_DISK_GB':200,'MIN_WINDOWS_MAJOR':10,'MIN_MACOS_MINOR':13,'MIN_LINUX_KERNEL':(6, 00),'MIN_DOWNLOAD_MBPS':21.0,'MIN_UPLOAD_MBPS':2.0,'MAX_BENCHMARK_SECS':10.0,'MIN_DOWNLOAD_MBPS':5.0}
    if 'new_sonet' in operatorData:
        sonet = operatorData['new_sonet']
    else:
        sonet = operatorData['sonet']
    reqs = sonet['node_requirements']

    MIN_LOGICAL_CORES = reqs.get('MIN_LOGICAL_CORES',MIN_LOGICAL_CORES)
    MIN_FREQ_GHZ = reqs.get('MIN_FREQ_GHZ',MIN_FREQ_GHZ)
    MIN_RAM_GB = reqs.get('MIN_RAM_GB',MIN_RAM_GB)
    MIN_DISK_GB = reqs.get('MIN_DISK_GB',MIN_DISK_GB)
    MIN_WINDOWS_MAJOR = reqs.get('MIN_WINDOWS_MAJOR',MIN_WINDOWS_MAJOR)
    MIN_MACOS_MINOR = reqs.get('MIN_MACOS_MINOR',MIN_MACOS_MINOR)
    MIN_LINUX_KERNEL = tuple(reqs.get('MIN_LINUX_KERNEL',MIN_LINUX_KERNEL))
    MIN_DOWNLOAD_MBPS = reqs.get('MIN_DOWNLOAD_MBPS',MIN_DOWNLOAD_MBPS)
    MIN_UPLOAD_MBPS = reqs.get('MIN_UPLOAD_MBPS',MIN_UPLOAD_MBPS)
    MAX_BENCHMARK_SECS = reqs.get('MAX_BENCHMARK_SECS',MAX_BENCHMARK_SECS)
    MIN_DOWNLOAD_MBPS = reqs.get('MIN_DOWNLOAD_MBPS',MIN_DOWNLOAD_MBPS)

    results = {'CPU': f"{platform.processor() or 'unknown'}"}

    update_output("\n\nHardware Check — Late 2010s Mid-Range Baseline\n", output)
    update_output(f"Machine : {platform.node()}", output)
    update_output(f"  System  : {platform.system()} {platform.release()}", output)
    update_output(f"CPU     : {platform.processor() or 'unknown'}", output)
    update_output("", output)

    passed = True

    x = check_bitness(output=output)
    if not x:
        passed = False

    x = check_cpu_cores(MIN_LOGICAL_CORES, output=output)
    if not x:
        passed = False
    results['LOGICAL_CORES'] = x

    x = check_cpu_freq(MIN_FREQ_GHZ, output=output)
    if not x:
        passed = False
    results['FREQ_GHZ'] = x

    x = check_ram(MIN_RAM_GB, output=output)
    if not x:
        passed = False
    results['RAM_GB'] = x

    x = check_disk(MIN_DISK_GB, output=output)
    if not x:
        passed = False
    results['DISK_GB'] = x

    x = check_os(MIN_LINUX_KERNEL, MIN_MACOS_MINOR, MIN_WINDOWS_MAJOR, output=output)
    if not x:
        passed = False
    results['OS'] = f"{platform.system()} {platform.release()}"

    update_output("Running CPU benchmark (matrix multiplication)...", output)
    x = check_cpu_benchmark(MAX_BENCHMARK_SECS, output=output)
    if not x:
        passed = False
    results['BENCHMARK_SECS'] = x

    update_output("Running internet speed test (this may take a moment)...", output)
    download_mbps, upload_mbps = check_internet_speed(MIN_DOWNLOAD_MBPS, MIN_UPLOAD_MBPS)
    dl_passed = check(
        "Download speed",
        download_mbps >= MIN_DOWNLOAD_MBPS,
        f"{download_mbps:.1f} Mbps, need ≥ {MIN_DOWNLOAD_MBPS} Mbps",
        output,
    )
    ul_passed = check(
        "Upload speed",
        upload_mbps >= MIN_UPLOAD_MBPS,
        f"{upload_mbps:.1f} Mbps, need ≥ {MIN_UPLOAD_MBPS} Mbps",
        output,
    )
    results['DOWNLOAD'] = f"{download_mbps:.1f} Mbps"
    results['UPLOAD'] = f"{upload_mbps:.1f} Mbps"

    print("results",results)
    node_data['meta']['hardware_results'] = results

    if not dl_passed:
        passed = False

    if not ul_passed:
        passed = False

    if passed:
        update_output("\n\nRESULT: ✅ ALL checks passed.", output)
        # print("  This machine meets or exceeds a late-2010s mid-range baseline.")
        return True, node_data
    else:
        update_output("\n\nRESULT: ❌ One or more checks failed.", output)
        update_output("This machine does NOT fully meet the hardware requirements.", output)
        update_output("Speed tests vary from test to test.\n\n", output)
        return False, node_data

def remote_hash_stepper(ssh, local_folder=None, remote_folder=None, text_display=None, ignore=None, ignore_file=".gitignore", force_reupload_script=False, delete_remote_orphans=False, dry_run=False): 
    print('-remote_hash_stepper',local_folder,remote_folder)
    if not local_folder:
        local_folder = homepath + f"~/Sonet/SoNodeManager"
    if not remote_folder:
        remote_folder = local_folder
    
    line = f"\nSyncing {local_folder} and {remote_folder}..."
    update_output(line, text_display)
    """
    sync_via_paramiko.py
    ---------------------
    Syncs a local folder tree onto a remote folder tree over an *existing*
    paramiko SSH connection, using quick content hashes to decide what needs
    updating.

    Flow:
    1. Make sure a small "remote_hasher.py" helper script exists on the remote
        host (uploaded once, reused after that).
    2. Run it remotely (via exec_command) to recursively hash every file
        under the target remote folder, skipping anything matched by the
        ignore list / .gitignore. It returns the results as JSON on stdout.
    3. Locally, walk the same folder structure and hash the corresponding
        files (same ignore rules).
    4. Any file whose local hash differs from the remote hash (or that
        doesn't exist remotely yet) gets uploaded via SFTP, overwriting the
        remote copy. Remote directories are created as needed.

    Hashing: uses zlib.crc32 (fast, stdlib, C-implemented). This is a
    non-cryptographic checksum -- great for "did this file change" style
    sync decisions, not suitable for security/integrity guarantees.

    Ignore rules: any file matching an explicit --ignore glob, OR matching a
    pattern found in a .gitignore file at the root of the folder being
    hashed, is skipped entirely (not hashed, not compared, not uploaded).
    The .gitignore parsing supports comments, blank lines, "/"-anchored
    patterns, trailing-"/" directory patterns, and "!" negation -- the
    common subset of the spec, not 100% of git's edge cases.

    Usage as a library (recommended, since you already have a connection):

        from sync_via_paramiko import sync_folder

        sync_folder(
            ssh=my_existing_sshclient,          # paramiko.SSHClient, already connected
            local_folder="/home/me/project",
            remote_folder="/home/user/project",
            ignore=["*.log", "secrets.env"],    # optional, on top of .gitignore
        )

    Usage as a standalone script (it will open its own connection):

        python sync_via_paramiko.py \
            --host 1.2.3.4 --user deploy --key ~/.ssh/id_rsa \
            --local /home/me/project --remote /home/user/project \
            --ignore "*.log"
    """

    # Always excluded, regardless of what the caller passes in `ignore` --
    # these are folders you basically never want auto-synced over SFTP.
    DEFAULT_IGNORE = [".git/*", "__pycache__/*", "*.pyc", "nodenv/*", "SoNodeApp/*", ".sync_remote_hasher.py"]


    # --------------------------------------------------------------------------
    # The helper script that gets uploaded to and executed on the remote host.
    # It has no dependencies beyond the Python 3 standard library.
    # --------------------------------------------------------------------------
    REMOTE_HASHER_SOURCE = r'''#!/usr/bin/env python3
import argparse
import fnmatch
import json
import os
import posixpath
import sys
import zlib


def parse_gitignore(gitignore_path):
    patterns = []
    if not os.path.isfile(gitignore_path):
        return patterns
    with open(gitignore_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n").rstrip("\r").strip()
            if not line or line.startswith("#"):
                continue
            patterns.append(line)
    return patterns


def _gitignore_match(relpath, pattern):
    negate = pattern.startswith("!")
    if negate:
        pattern = pattern[1:]
    dir_only = pattern.endswith("/")
    if dir_only:
        pattern = pattern[:-1]
    anchored = pattern.startswith("/")
    if anchored:
        pattern = pattern[1:]

    if anchored or "/" in pattern:
        matched = fnmatch.fnmatch(relpath, pattern) or fnmatch.fnmatch(relpath, pattern + "/*")
    else:
        base = posixpath.basename(relpath)
        matched = fnmatch.fnmatch(base, pattern)
        if not matched:
            parts = relpath.split("/")
            matched = any(fnmatch.fnmatch(p, pattern) for p in parts[:-1])
    return matched, negate


def is_ignored(relpath, glob_patterns, gitignore_patterns):
    norm = relpath.replace(os.sep, "/")
    base = os.path.basename(norm)
    for pat in glob_patterns:
        if fnmatch.fnmatch(norm, pat) or fnmatch.fnmatch(base, pat):
            return True

    ignored = False
    for pattern in gitignore_patterns:
        matched, negate = _gitignore_match(norm, pattern)
        if matched:
            ignored = not negate
    return ignored


def quick_hash(path, chunk_size=1 << 20):
    crc = 0
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            crc = zlib.crc32(chunk, crc)
    return format(crc & 0xFFFFFFFF, "08x")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", help="Folder to recursively hash")
    parser.add_argument("--ignore", action="append", default=[],
                        help="Glob pattern to ignore (repeatable)")
    parser.add_argument("--ignore-file", default=".gitignore",
                        help="Name of a gitignore-style file at the root to also honor")
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    results = {}
    errors = {}

    if not os.path.isdir(root):
        print(json.dumps({"error": "root not found: %s" % root}))
        sys.exit(1)

    gitignore_patterns = []
    if args.ignore_file:
        gitignore_patterns = parse_gitignore(os.path.join(root, args.ignore_file))

    for dirpath, dirnames, filenames in os.walk(root):
        relroot = os.path.relpath(dirpath, root)
        for fname in filenames:
            relpath = fname if relroot == "." else os.path.join(relroot, fname)
            relpath = relpath.replace(os.sep, "/")
            if is_ignored(relpath, args.ignore, gitignore_patterns):
                continue
            fullpath = os.path.join(dirpath, fname)
            try:
                results[relpath] = quick_hash(fullpath)
            except OSError as e:
                errors[relpath] = str(e)

    print(json.dumps({"hashes": results, "errors": errors}))


if __name__ == "__main__":
    main()
    '''


    # --------------------------------------------------------------------------
    # Local-side: gitignore parsing / matching (mirrors the remote logic)
    # --------------------------------------------------------------------------
    def _parse_gitignore(gitignore_path: Path) -> list[str]:
        patterns = []
        if not gitignore_path.is_file():
            return patterns
        for line in gitignore_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            patterns.append(line)
        return patterns


    def _gitignore_match(relpath: str, pattern: str) -> tuple[bool, bool]:
        negate = pattern.startswith("!")
        if negate:
            pattern = pattern[1:]
        dir_only = pattern.endswith("/")
        if dir_only:
            pattern = pattern[:-1]
        anchored = pattern.startswith("/")
        if anchored:
            pattern = pattern[1:]

        if anchored or "/" in pattern:
            matched = fnmatch.fnmatch(relpath, pattern) or fnmatch.fnmatch(relpath, pattern + "/*")
        else:
            base = posixpath.basename(relpath)
            matched = fnmatch.fnmatch(base, pattern)
            if not matched:
                parts = relpath.split("/")
                matched = any(fnmatch.fnmatch(p, pattern) for p in parts[:-1])
        return matched, negate


    def _is_ignored(relpath: str, glob_patterns: Iterable[str], gitignore_patterns: Iterable[str]) -> bool:
        norm = relpath.replace("\\", "/")
        base = posixpath.basename(norm)
        for pat in glob_patterns:
            if fnmatch.fnmatch(norm, pat) or fnmatch.fnmatch(base, pat):
                return True

        ignored = False
        for pattern in gitignore_patterns:
            matched, negate = _gitignore_match(norm, pattern)
            if matched:
                ignored = not negate
        return ignored


    def _local_quick_hash(path: Path, chunk_size: int = 1 << 20) -> str:
        crc = 0
        with open(path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                crc = zlib.crc32(chunk, crc)
        return format(crc & 0xFFFFFFFF, "08x")


    def _local_hashes(
        local_folder: Path,
        glob_patterns: Iterable[str],
        gitignore_patterns: Iterable[str],
    ) -> dict[str, str]:
        hashes = {}
        for path in local_folder.rglob("*"):
            if not path.is_file():
                continue
            relpath = path.relative_to(local_folder).as_posix()
            if _is_ignored(relpath, glob_patterns, gitignore_patterns):
                continue
            hashes[relpath] = _local_quick_hash(path)
        return hashes


    # --------------------------------------------------------------------------
    # Remote-side helpers
    # --------------------------------------------------------------------------
    def _remote_file_exists(sftp: paramiko.SFTPClient, remote_path: str) -> bool:
        try:
            sftp.stat(remote_path)
            return True
        except FileNotFoundError:
            return False


    def ensure_remote_hasher(
        sftp: paramiko.SFTPClient,
        remote_script_path: str,
        force_upload: bool = False,
    ) -> None:
        """Upload the remote hashing helper if it isn't already there."""
        if force_upload or not _remote_file_exists(sftp, remote_script_path):
            remote_dir = posixpath.dirname(remote_script_path) or "."
            _mkdir_p_absolute(sftp, remote_dir)
            with sftp.open(remote_script_path, "w") as f:
                f.write(REMOTE_HASHER_SOURCE)
            sftp.chmod(remote_script_path, 0o755)


    def _mkdir_p_absolute(sftp: paramiko.SFTPClient, remote_dir: str) -> None:
        if not remote_dir or remote_dir in (".", "/"):
            return
        is_abs = remote_dir.startswith("/")
        parts = [p for p in remote_dir.split("/") if p]
        current = "/" if is_abs else ""
        for part in parts:
            current = posixpath.join(current, part) if current else part
            try:
                sftp.stat(current)
            except FileNotFoundError:
                try:
                    sftp.mkdir(current)
                except OSError:
                    pass


    def run_remote_hasher(
        ssh: paramiko.SSHClient,
        remote_script_path: str,
        remote_folder: str,
        ignore_patterns: Iterable[str],
        ignore_file: str | None,
        python_bin: str = "python3",
    ) -> dict[str, str]:
        """Execute the remote hasher and return {relpath: crc32_hex}."""
        ignore_args = " ".join(f"--ignore {shlex.quote(p)}" for p in ignore_patterns)
        ignore_file_arg = f"--ignore-file {shlex.quote(ignore_file)}" if ignore_file else "--ignore-file ''"
        cmd = (
            f"{python_bin} {shlex.quote(remote_script_path)} "
            f"{shlex.quote(remote_folder)} {ignore_args} {ignore_file_arg}"
        )
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_status = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")

        if exit_status != 0:
            raise RuntimeError(f"Remote hasher failed (exit {exit_status}): {err or out}")

        try:
            payload = json.loads(out.strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError) as e:
            raise RuntimeError(f"Could not parse remote hasher output: {out!r}") from e

        if "error" in payload:
            raise RuntimeError(f"Remote hasher error: {payload['error']}")

        if payload.get("errors"):
            for relpath, msg in payload["errors"].items():
                print(f"  [remote read error] {relpath}: {msg}", file=sys.stderr)

        return payload.get("hashes", {})


    def upload_file(sftp: paramiko.SFTPClient, local_path: Path, remote_path: str) -> None:
        remote_dir = posixpath.dirname(remote_path)
        if remote_dir:
            _mkdir_p_absolute(sftp, remote_dir)
        sftp.put(str(local_path), remote_path)


    def _resolve_remote_path(ssh: paramiko.SSHClient, remote_path: str) -> str:
        """
        Expand a leading '~' in a remote path to the remote user's actual home
        directory. SFTP has no concept of '~', and shlex-quoting a path for
        exec_command prevents the shell from expanding it either -- so we
        resolve it ourselves once, up front, via a cheap remote command.
        """
        if not remote_path.startswith("~"):
            return remote_path
        stdin, stdout, stderr = ssh.exec_command("echo $HOME")
        exit_status = stdout.channel.recv_exit_status()
        home = stdout.read().decode("utf-8", errors="replace").strip()
        if exit_status != 0 or not home:
            raise RuntimeError(
                f"Could not resolve remote home directory to expand '{remote_path}'; "
                f"use an absolute path instead."
            )
        if remote_path == "~":
            return home
        if remote_path.startswith("~/"):
            return posixpath.join(home, remote_path[2:])
        # Something like "~otheruser/path" -- not supported, bail loudly.
        raise RuntimeError(
            f"Cannot expand '{remote_path}': only '~' and '~/...' for the "
            f"connected user are supported. Use an absolute path instead."
        )

    def _cleanup_empty_remote_dirs(
        sftp: paramiko.SFTPClient,
        remote_folder: str,
        start_dirs: Iterable[str],
    ) -> list[str]:
        """
        After deleting orphan files, their parent directories may now be
        empty. SFTP has no recursive delete, so walk up from each affected
        directory and rmdir anything that's empty, climbing toward
        remote_folder (but never removing remote_folder itself).
        """
        remote_folder_norm = remote_folder.rstrip("/")
        queue = [d.rstrip("/") for d in dict.fromkeys(start_dirs) if d]
        checked: set[str] = set()
        removed: list[str] = []
    
        while queue:
            d = queue.pop(0)
            if not d or d in checked or d == remote_folder_norm:
                continue
            if not (d == remote_folder_norm or d.startswith(remote_folder_norm + "/")):
                continue  # safety: never touch anything outside the sync root
            checked.add(d)
            try:
                entries = sftp.listdir(d)
            except (FileNotFoundError, OSError):
                continue
            if entries:
                continue
            try:
                sftp.rmdir(d)
            except OSError:
                continue
            removed.append(d)
            parent = posixpath.dirname(d)
            if parent and parent != d:
                queue.append(parent)
    
        return removed


    def _fetch_remote_gitignore(
        sftp: paramiko.SFTPClient, remote_folder: str, ignore_file: str
    ) -> list[str]:
        """Read a .gitignore that lives at the root of the remote folder, if any."""
        remote_path = posixpath.join(remote_folder, ignore_file)
        try:
            with sftp.open(remote_path, "r") as f:
                content = f.read().decode("utf-8", errors="replace")
        except (FileNotFoundError, OSError):
            return []
        patterns = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            patterns.append(line)
        return patterns


    # --------------------------------------------------------------------------
    # Main orchestration
    # --------------------------------------------------------------------------
    def sync_folder(
        ssh: paramiko.SSHClient,
        local_folder: str,
        remote_folder: str,
        ignore: list[str] | None = None,
        ignore_file: str | None = ".gitignore",
        remote_script_path: str | None = None,
        force_reupload_script: bool = False,
        delete_remote_orphans: bool = False,
        dry_run: bool = False,
    ) -> dict:
        """
        Sync local_folder -> remote_folder using quick content hashes.

        ignore: explicit glob patterns (relative path or filename), applied
            on top of whatever .gitignore contains.
        ignore_file: name of a gitignore-style file to look for at the root
            of local_folder (and remote_folder) and honor automatically.
            Pass None to disable .gitignore support entirely.
        delete_remote_orphans: if True, any file that exists on the remote
            but has no local counterpart (and isn't itself ignored) gets
            deleted remotely via SFTP. Off by default -- this is destructive.
            Ignored files are never touched, so anything covered by `ignore`
            or the .gitignore stays on the remote regardless of this flag.

        Returns a summary dict:
            {"updated": [...], "unchanged": [...], "skipped": [...], "deleted": [...]}
        """
        print('-sync_folder',local_folder,remote_folder)
        ignore = list(dict.fromkeys(DEFAULT_IGNORE + (ignore or [])))
        local_root = Path(os.path.expanduser(local_folder)).resolve()
        if not local_root.is_dir():
            raise NotADirectoryError(f"Local folder not found: {local_root}")

        remote_folder = _resolve_remote_path(ssh, remote_folder)

        if remote_script_path is None:
            remote_script_path = posixpath.join(remote_folder, ".sync_remote_hasher.py")
        else:
            remote_script_path = _resolve_remote_path(ssh, remote_script_path)

        # Local .gitignore, read once so it applies identically when we hash
        # local files ourselves.
        local_gitignore_patterns = (
            _parse_gitignore(local_root / ignore_file) if ignore_file else []
        )

        sftp = ssh.open_sftp()
        try:
            ensure_remote_hasher(sftp, remote_script_path, force_upload=force_reupload_script)


            print(f"Hashing remote folder: {remote_folder}")
            remote_hashes = run_remote_hasher(
                ssh, remote_script_path, remote_folder, ignore, ignore_file
            )
    
            print(f"Hashing local folder:  {local_root}")
            local_hashes = _local_hashes(local_root, ignore, local_gitignore_patterns)
    
            updated, unchanged, skipped, deleted = [], [], [], []
    
            all_relpaths = set(local_hashes) | set(remote_hashes)
            for relpath in sorted(all_relpaths):
                if _is_ignored(relpath, ignore, local_gitignore_patterns):
                    skipped.append(relpath)
                    continue
    
                local_hash = local_hashes.get(relpath)
                remote_hash = remote_hashes.get(relpath)
    
                if local_hash is None:
                    remote_path = posixpath.join(remote_folder, relpath)
                    if delete_remote_orphans:
                        action = "Would remove" if dry_run else "Removing"
                        line = f"{action} {relpath}..."
                        update_output(line, text_display)
                        if not dry_run:
                            sftp.remove(remote_path)
                        deleted.append(relpath)
                    else:
                        print(f"  [local missing, leaving remote as-is] {relpath}")
                    continue
    
                if local_hash == remote_hash:
                    unchanged.append(relpath)
                    continue
    
                local_path = local_root / relpath
                remote_path = posixpath.join(remote_folder, relpath)
                # action = "would upload" if dry_run else "uploading"
                # print(f"  [{action}] {relpath}")
                action = "Would send" if dry_run else "Sending"
                line = f"{action} {relpath}..."
                update_output(line, text_display)
                if not dry_run:
                    upload_file(sftp, local_path, remote_path)
                updated.append(relpath)
    
            # removed_dirs = []
            # if delete_remote_orphans and deleted and not dry_run:
            #     parent_dirs = {posixpath.dirname(posixpath.join(remote_folder, p)) for p in deleted}
            #     removed_dirs = _cleanup_empty_remote_dirs(sftp, remote_folder, parent_dirs)
            #     for d in removed_dirs:
            #         # print(f"  [removed now-empty folder] {d}")
            #         line = f"\nRemoving empty folder {d}..."
            #         update_output(line, text_display)
    
            removed_dirs = []
            if delete_remote_orphans and deleted and not dry_run:
                parent_dirs = {posixpath.dirname(posixpath.join(remote_folder, p)) for p in deleted}
                print(f"  [cleanup: checking these dirs for emptiness: {sorted(parent_dirs)}]")
                removed_dirs = _cleanup_empty_remote_dirs(sftp, remote_folder, parent_dirs)
                for d in removed_dirs:
                    # print(f"  [removed now-empty folder] {d}")
                    line = f"Removing empty folder {d}..."
                    update_output(line, text_display)
    
            print(
                f"\nDone. {len(updated)} updated, {len(unchanged)} unchanged, "
                f"{len(skipped)} skipped (ignored), {len(deleted)} deleted, "
                f"{len(removed_dirs)} empty folders removed."
            )
            return {
                "updated": updated,
                "skipped": skipped,
                "deleted": deleted,
                "removed_dirs": removed_dirs,
            }
        finally:
            sftp.close()


    # --------------------------------------------------------------------------
    # Standalone CLI entry point (opens its own connection)
    # --------------------------------------------------------------------------
    def _build_ssh_client(host, port, user, key_path, password) -> paramiko.SSHClient:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        connect_kwargs = {"hostname": host, "port": port, "username": user}
        if key_path:
            connect_kwargs["key_filename"] = key_path
        if password:
            connect_kwargs["password"] = password
        ssh.connect(**connect_kwargs)
        return ssh


    # def main():
    #     parser = argparse.ArgumentParser(description=__doc__)
    #     parser.add_argument("--host", required=True)
    #     parser.add_argument("--port", type=int, default=22)
    #     parser.add_argument("--user", required=True)
    #     parser.add_argument("--key", default=None, help="Path to private key file")
    #     parser.add_argument("--password", default=None, help="Password (if not using a key)")
    #     parser.add_argument("--local", required=True, help="Local folder to sync from")
    #     parser.add_argument("--remote", required=True, help="Remote folder to sync to")
    #     parser.add_argument(
    #         "--ignore", action="append", default=[],
    #         help="Glob pattern to ignore, relative to the folder root (repeatable)",
    #     )
    #     parser.add_argument(
    #         "--ignore-file", default=".gitignore",
    #         help="Name of a gitignore-style file at the folder root to honor "
    #             "(default: .gitignore; pass '' to disable)",
    #     )
    #     parser.add_argument(
    #         "--remote-script-path", default=None,
    #         help="Where to place the helper script on the remote host",
    #     )
    #     parser.add_argument("--force-reupload-script", action="store_true")
    #     parser.add_argument(
    #         "--delete-remote-orphans", action="store_true",
    #         help="Delete remote files that have no local counterpart (destructive)",
    #     )
    #     parser.add_argument("--dry-run", action="store_true")
    #     args = parser.parse_args()

    #     ssh = _build_ssh_client(args.host, args.port, args.user, args.key, args.password)
    #     try:
    # sync_folder(
    #     ssh=ssh,
    #     local_folder=args.local,
    #     remote_folder=args.remote,
    #     ignore=args.ignore,
    #     ignore_file=args.ignore_file or None,
    #     remote_script_path=args.remote_script_path,
    #     force_reupload_script=args.force_reupload_script,
    #     delete_remote_orphans=args.delete_remote_orphans,
    #     dry_run=args.dry_run,
    # )
        # finally:
        #     ssh.close()

    r = sync_folder(
        ssh=ssh,
        local_folder=local_folder,
        remote_folder=remote_folder,
        ignore=ignore,
        ignore_file=ignore_file,
        remote_script_path=None,
        force_reupload_script=force_reupload_script,
        delete_remote_orphans=delete_remote_orphans,
        dry_run=dry_run,
    )
    print('sync_folder result:',r)
    return ssh





import platform
import os
import ctypes
import getpass
import json
import hashlib
import datetime
import base64
from dateutil import parser
from os.path import expanduser
from cryptography.fernet import Fernet, InvalidToken


username = getpass.getuser()
homepath = expanduser("~")

# DO NOT CHANGE
# WILL BREAK ALL VALIDATIONS



skip_sign_fields = [
        'validated','is_active','proposed_modification',
        'password','keyword_array','hash','fcm_capable','ai_capable',
        'coins','last_login','Block_obj','pos',
        'suspended_dt','expelled_dt','isVerified','validators','prevVersion',
        'blockchainId','groups','user_permissions','updated_on_node',
        'Validator_obj','new','date_created','must_rename','Update_obj',
        'is_superuser','is_staff','display_hour','latestVer','enacted',
        'SenderBlock_obj','ReceiverBlock_obj','notes','activeNode',
        'commitChainType','is_modifiable','BillText_obj',
        'queued_dt','plugin_prefix','iden_length','value','added_to_node'
        ]
# fields in model.yes_sign_fields must not be included here
# this should be unnessecary because these fields should not be sent from the server to be signed


_super_id = None
ID_LENGTH = 14

def generate_id(data=None, length=ID_LENGTH):
    # print('-generate_id',len(str(data)),length, str(str(data))[:25])
    import hashlib
    import uuid
    if data is not None:
        if not isinstance(data, str):
            data = str(data)
        data = data.encode()
        digest = hashlib.sha256(data).digest()
        truncated = digest[:length]
    else:
        truncated =  uuid.uuid4().bytes[:length]
    
    from commands.utils import to_base62
    s = to_base62(truncated)
    return s


def super_id(iden=None, net=None, operatorData=None, create=None):
    print('-super_id',iden)
    from commands.utils import get_operatorData
    operatorData = get_operatorData(operatorData)
    global _super_id
    if _super_id is None:
        sonet = None
        if 'sonet' in operatorData:
            sonet = operatorData['sonet']
        if not sonet and net:
            sonet = net
        if sonet:
            if isinstance(sonet, dict):
                net_iden = sonet['id']
                net_created_dt = sonet['created']
            else:
                net_iden = sonet.id
                net_created_dt = sonet.created
            if net_iden == 'ohSohVQmm16CNAIPGbrrix8':
                _super_id = 'usrSo1KOSJaVhV6foQ'
                print('_super_id1',_super_id)
            elif net_created_dt:
                print('sonet.created',net_created_dt)
                if net and isinstance(net_created_dt, str):
                    c_dt = net_created_dt
                else:
                    c_dt = dt_to_string(net_created_dt)
                _super_id = 'usrSo' + generate_id(f'SuperSo-{c_dt}',length=14)
                print('_super_id2',_super_id)
        elif create:
            if isinstance(create, str):
                c_dt = create
            else:
                c_dt = dt_to_string(create)
            _super_id = 'usrSo' + generate_id(f'SuperSo-{c_dt}',length=14)
            print('_super_id3',_super_id)
        else:
            return True
        
    print('_super_id',_super_id, iden)
    if iden:
        return True if _super_id == iden else False
    return _super_id


def generate_key(file_path=None):
    print('-generate_key')
    if not file_path:
        file_path = homepath + "/Sonet/.data/special/keys/soSecret.key"
    else:
        file_path = homepath + file_path
    print('file_path',file_path)
    os.makedirs(homepath + "/Sonet/.data/special/keys", exist_ok=True)
    
    if not os.path.exists(file_path):
        key = Fernet.generate_key()
        with open(file_path, "wb") as key_file:
            key_file.write(key)
        print(f"Encryption key saved to '{file_path}': {key.decode()}")
        if 'soSecret.key' in file_path:
            system = platform.system()

            if system == 'Windows':
                FILE_ATTRIBUTE_HIDDEN = 0x02
                ctypes.windll.kernel32.SetFileAttributesW(file_path, FILE_ATTRIBUTE_HIDDEN)
                
                key_file = os.path.expanduser("~/Sonet/.data/special/keys/soSecret.key")
                os.chmod(key_file, stat.S_IRUSR | stat.S_IWUSR)
            elif system in ('Linux', 'Darwin'):
                hidden_file_path = os.path.join(os.path.dirname(file_path), '.' + os.path.basename(file_path))
                os.rename(file_path, hidden_file_path)

                import stat
                key_file = os.path.expanduser("~/Sonet/.data/special/keys/.soSecret.key")
                os.chmod(key_file, stat.S_IRUSR | stat.S_IWUSR)
            else:
                print(f"Unsupported operating system: {system}")

_key_cache = None
def load_key(file_path=None):
    # print('-load_key', file_path)
    global _key_cache
    if _key_cache is not None and file_path == None:
        return _key_cache
    save_cache = False
    if not file_path:
        system = platform.system()
        if system == 'Windows':
            file_path = homepath + "/Sonet/.data/special/keys/soSecret.key"
        elif system in ('Linux', 'Darwin'):
            file_path = homepath + "/Sonet/.data/special/keys/.soSecret.key"
        save_cache = True
    try:
        with open(file_path, "rb") as f:
            key = f.read()
        if save_cache:
            _key_cache = key
        return key
    except Exception as e:
        print('load_key err',str(e))
        if 'soSecret.key' in file_path:
            generate_key()
            with open(file_path, "rb") as f:
                key = f.read()
            if save_cache:
                _key_cache = key
            return key
        return None

def encrypt(text, key_path=None):
    if not text:
        return text
    key = load_key(key_path)
    
    cipher_suite = Fernet(key)
    cipher_text = cipher_suite.encrypt(text.encode())
    return cipher_text

def decrypt(text, key_path=None):
    # print('-decrypt', file_path)
    if not text:
        return text
    key = load_key(key_path)
    try:
        cipher_suite = Fernet(key)
        decrypted_text = cipher_suite.decrypt(text).decode()
    except (InvalidToken, ValueError) as e:
        print("Decryption failed:", e)
        decrypted_text = None

    return decrypted_text

def string_to_64_char_hash(s):
    hash_object = hashlib.sha256((s).encode('utf-8'))
    hex_dig = hash_object.hexdigest()
    return hex_dig

def dt_to_string(dt_input):
    if isinstance(dt_input, str):
        dt = parser.parse(dt_input)
    elif isinstance(dt_input, datetime.datetime):
        dt = dt_input
    else:
        raise TypeError("Input must be a datetime object or an ISO 8601 string")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    else:
        dt = dt.astimezone(datetime.timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-4] + "Z"

def to_base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip('=')

def from_base64url(s: str) -> bytes:
    s += '=' * (-len(s) % 4)
    return base64.urlsafe_b64decode(s)

def get_ml_dsa(key_strength):
    if key_strength == 'ML_DSA_44':
        from dilithium_py.ml_dsa import ML_DSA_44
        return ML_DSA_44
    elif key_strength == 'ML_DSA_65':
        from dilithium_py.ml_dsa import ML_DSA_65
        return ML_DSA_65
    else:
        from dilithium_py.ml_dsa import ML_DSA_87
        return ML_DSA_87

def detect_security(key, key_type='sk'):
    SK_SIZES = {32: 'secp256k1', 2560: 'ML_DSA_44', 4032: 'ML_DSA_65', 4896: 'ML_DSA_87'}
    PK_SIZES = {65: 'secp256k1', 1312: 'ML_DSA_44', 1952: 'ML_DSA_65', 2592: 'ML_DSA_87'}
    SIG_SIZES = {2420: 'ML_DSA_44', 3309: 'ML_DSA_65', 4627: 'ML_DSA_87'}
    data = from_base64url(key)
    byte_len = len(data)
    if key_type == 'pubkey' and byte_len == 65 and data[0] == 0x04:
        return 'secp256k1'
    sizes = SK_SIZES if key_type == 'privkey' else PK_SIZES if key_type == 'pubkey' else SIG_SIZES
    level = sizes.get(byte_len)
    if not level:
        print(f"DEBUG detect_security: key_type={key_type}, byte_len={byte_len}, key_preview={key[:30]}...")
        raise ValueError(f"Unknown {key_type} size: {byte_len} bytes")
    print('dectect',level)
    return level
# key generation/sign/verify

def create_keys_ml_dsa(user_id, user_pass, key_strength='ML_DSA_44'):
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    from cryptography.hazmat.backends import default_backend
    salt = hashlib.sha256(f"{user_id}:{user_pass}".encode()).digest()
    if len(user_pass) > 120:
        n = 16384
    elif len(user_pass) > 40:
        n = 65536
    else:
        n = 262144
    kdf = Scrypt(salt=salt, length=32, n=n, r=8, p=1, backend=default_backend())
    seed = kdf.derive(user_pass.encode())
    pk, sk = get_ml_dsa(key_strength)._keygen_internal(seed)
    return to_base64url(sk), to_base64url(pk)

def simpleSign_ml_dsa(secret_key, data, key_strength='ML_DSA_44'):
    sk = from_base64url(secret_key)
    message = (data).encode('utf-8')
    signature = get_ml_dsa(key_strength).sign(sk, message)
    return to_base64url(signature)

def simpleVerify_ml_dsa(data, signature, public_key, key_strength='ML_DSA_44'):
    sig_strength = detect_security(signature, key_type='sig')
    if key_strength != sig_strength:
        raise ValueError(f"Key/signature level mismatch: key={key_strength}, sig={sig_strength}")
    pk = from_base64url(public_key)
    sig = from_base64url(signature)
    message = (data).encode('utf-8')
    return get_ml_dsa(key_strength).verify(pk, message, sig)


def create_keys_secp256k1(user_id, user_pass):
    import hashlib
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ec import SECP256K1

    salt = hashlib.sha256(f"{user_id}:{user_pass}".encode()).digest()
    password = user_pass.encode()
    if len(user_pass) > 120:
        n = 16384
    elif len(user_pass) > 40:
        n = 65536
    else:
        n = 262144
    kdf = Scrypt(salt=salt, length=32, n=n, r=8, p=1, backend=default_backend())
    seed = kdf.derive(password)

    priv_int = int.from_bytes(seed, 'big')
    curve = SECP256K1()
    order = int("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141", 16)
    priv_int = priv_int % order
    if priv_int == 0:
        priv_int = 1

    private_key = ec.derive_private_key(priv_int, curve, default_backend())
    priv_key_bytes = private_key.private_numbers().private_value.to_bytes(32, 'big')
    public_key = private_key.public_key()
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    return to_base64url(priv_key_bytes), to_base64url(public_key_bytes)
    
def simpleSign_secp256k1(private_key, data):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec

    private_key_bytes = from_base64url(private_key)
    private_key = ec.derive_private_key(int.from_bytes(private_key_bytes, byteorder='big'), ec.SECP256K1())
    signature = private_key.sign((data).encode('utf-8'), ec.ECDSA(hashes.SHA256()))
    signature_hex = to_base64url(signature)
    return signature_hex

def simpleVerify_secp256k1(data, signature, public_key):
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import hashes
    from cryptography.exceptions import InvalidSignature
    try:
        pub_bytes = from_base64url(public_key)
        sig_bytes = from_base64url(signature)
        public_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), pub_bytes)
        try:
            public_key.verify(sig_bytes, (data).encode('utf-8'), ec.ECDSA(hashes.SHA256()))
            print("SECP Signature is *VALID*")
            return True
        except InvalidSignature:
            print("SECP Signature !!INVALID!!")
    except Exception as e:
        print('VERIFY SECP err',str(e))
    return False


def createKeyPair(user_id, user_pass, key_type, key_strength='ML_DSA_44'):
    user_pass = key_type + user_pass
    if key_strength == 'secp256k1':
        return create_keys_secp256k1(user_id, user_pass)
    else:
        return create_keys_ml_dsa(user_id, user_pass, key_strength)

def simpleSign(private_key, data, key_type=None):
    data = data + 'ycF3atcq61TMBvVmGwrQWZJ69fu'
    print('-simpleSign',len(str(data)),key_type)
    if key_type == None:
        key_type = detect_security(private_key, key_type='privkey')
    if key_type == 'secp256k1':
        return simpleSign_secp256k1(private_key, data)
    else:
        return simpleSign_ml_dsa(private_key, data, key_type)

def verify(data, public_key, signature=None, key_type=None, skip_sort=False):
    print('-verify', str(public_key)[:40], str(signature)[:40], key_type, len(str(data)), type(data))
    err = 0
    try:
        from commands.utils import is_id, hash_upk_id
        if isinstance(data, dict):
            print('p0')
            data = {k:v for k, v in data.items() if k not in skip_sign_fields}
            if skip_sort:
                sorted_data = data
            else:
                sorted_data = sort_for_sign(data)

            if isinstance(public_key, str):
                print('p1')
                for dt, sig_data in sorted_data['signed'].items():
                    print('p2')
                    if sig_data['pk'] == public_key or ('sig' in sig_data and sig_data['sig'] == signature) or ('publicKey' in sig_data and sig_data['publicKey'] == public_key):
                        print('p3')
                        if 'publicKey' in sig_data:
                            public_key = sig_data['publicKey']
                        public_key_hash = public_key
                        if not is_id(public_key_hash):
                            public_key_hash = hash_upk_id(public_key_hash)
                        sorted_data['signed'] = {dt: {'pk':public_key_hash}}
                        if not signature:
                            print('p4')
                            signature = sig_data['sig']
                        break
            elif isinstance(public_key, dict):
                print('p5')
                # will not work if received pk is id
                sig_data = public_key
                last_dt = list(sig_data)[-1]
                public_key = sig_data[last_dt]['pk']
                sorted_data['signed'] = {last_dt: {'pk':public_key}}
                if 'publicKey' in sig_data[last_dt]:
                    public_key = sig_data[last_dt]['publicKey']
                if not signature:
                    print('p5a')
                    if 'sig' in sig_data[last_dt]:
                        print('p5b')
                        signature = sig_data[last_dt]['sig']

            data = json.dumps(sorted_data, separators=(',', ':'))
        
        data = data + 'ycF3atcq61TMBvVmGwrQWZJ69fu'
        print('-verifying...',len(str(data)), str(data)) 

        if key_type == None:
            key_type = detect_security(public_key, key_type='pubkey')
        print('key_type',key_type)
        if key_type == 'secp256k1':
            return simpleVerify_secp256k1(data, signature, public_key)
        else:
            is_valid = simpleVerify_ml_dsa(data, signature, public_key, key_type)
            if is_valid:
                prnt("ML_DSA Signature is *VALID*")
            else:
                prnt("ML_DSA Signature is *INVALID*")
            return is_valid
    except Exception as e:
        prnt('VERIFY err4',str(e), 'code:',err)
    return False


def sign(data, privKey=None, pubKey=None, node_keys={}, clear_signed=True, operatorData=None, nodeId=None, verify_result=False, bypass_last_updated_dt=False, remove_skip_fields=False):
    print('-sign',str(privKey)[:150],str(pubKey)[:150])
    # print('data',data)
    from .utils import get_operatorData, now_utc, fetch_node_keys, hash_upk_id, is_id
    if not pubKey or not privKey:
        if not node_keys:
            node_keys = fetch_node_keys(target_nodeId=nodeId)
            print('stored node_keys',node_keys)

        if node_keys:
            privKey = node_keys['privKey']
            pubKey = node_keys['pubKey']
        else:
            operatorData = get_operatorData(operatorData)
        
            if 'accnt_pubKey' in operatorData and 'accnt_privKey' in operatorData:
                pubKey = operatorData['accnt_pubKey']
                privKey = operatorData['accnt_privKey']
            
    if not pubKey or not privKey:
        raise ValueError(f"missing pubKey:{str(pubKey)[:20]} or privKey:{str(privKey)[:20]}")
    
    inputted_public_key = pubKey
    if not is_id(pubKey):
        pubKey = hash_upk_id(pubKey)

    if clear_signed:
        if isinstance(data, dict):
            data['signed'] = {}
        else:
            data.signed = {}
    signing_dt = dt_to_string(now_utc())
    data['signed'][signing_dt] = {'pk': pubKey}

    if not bypass_last_updated_dt and 'lastUpdate' in data:
        data['lastUpdate'] = signing_dt
    if remove_skip_fields:
        data = {key:data[key] for key in data if key not in skip_sign_fields}
    copied_data = data.copy()
    sorted_data = sort_for_sign(copied_data)

    x_data = sorted_data.copy()
    json_data = json.dumps(x_data, separators=(',', ':'))

    print('-signing.....',len(json_data),str(json_data))
    signature = simpleSign(privKey, json_data)
    print('sig',str(signature)[:25])
    for field in data:
        if field in sorted_data and field != 'signed':
            data[field] = sorted_data[field]

    data['signed'][signing_dt]['sig'] = signature
    data['signed'][signing_dt]['publicKey'] = inputted_public_key
    if verify_result:
        veri_data = data.copy()
        verify(veri_data, inputted_public_key, signature)
            # raise ValueError("Signature verification failed")
    # print('return from sigingin: ',data)
    return data


def sort_dict(data):
    if isinstance(data, str):
        try:
            parsed = json.loads(data)
            return sort_dict(parsed)
        except json.JSONDecodeError:
            return data
    if isinstance(data, dict):
        return {key: sort_dict(value) for key, value in sorted(data.items(), key=lambda x: str(x[0]))}
    elif isinstance(data, (list, tuple)):
        return [sort_dict(item) for item in data]
    else:
        return data

def prnt(*args):
    msg = ','.join(f"{i}" for i in args)
    print(f'p:{msg}')

def sort_for_sign(data, print_data=False):
    def stringify_bool(val):
        if val is True or val is False:
            return str(val)
        if val is None:
            return "Val:N"
        return val

    def process_value(val):
        if isinstance(val, dict):
            return sort_for_sign(val, print_data)
        elif isinstance(val, list):
            if not val:
                return "Val:N"
            return [process_value(v) for v in val]
        elif isinstance(val, str) and is_iso_datetime(val):
            return dt_to_string(val)
        else:
            return stringify_bool(val)

    def is_iso_datetime(val):
        if not isinstance(val, str):
            return False
        try:
            from dateutil.parser import parse
            parse(val)
            return True
        except Exception:
            return False

    if isinstance(data, dict):
        data = {k: process_value(v) for k, v in data.items()}
        sorted_items = sorted(data.items(), key=lambda item: item[0].lower())
        sorted_dict = dict(sorted_items)
        id_val = {}
        sign_val = {}
        if 'id' in sorted_dict:
            id_val = {'id': sorted_dict.pop('id')}
        if 'signed' in sorted_dict:
            sign_val = {'signed': sorted_dict.pop('signed')}
        return {**id_val, **sorted_dict, **sign_val}

    elif isinstance(data, list):
        if not data:
            return "Val:N"
        return [process_value(v) for v in data]

    return stringify_bool(data)



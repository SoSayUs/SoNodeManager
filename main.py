
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Rectangle, Color
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock

import os
import requests
import json



class SplashScreen(Screen):
    def __init__(self, **kwargs):
        self.message = None
        super(SplashScreen, self).__init__(**kwargs)
        print('-SplashScreen')
        from templates import Background, splash_page_content

        folder_path = os.path.expanduser("~/Sonet")
        os.makedirs(folder_path, exist_ok=True)
        folder_path = os.path.expanduser("~/Sonet/.data")
        os.makedirs(folder_path, exist_ok=True)

        self.layout = Background(page_instance=self, content = 'splash_layout')
        self.content = 'splash_layout'
        self.add_widget(splash_page_content(self.layout, self))

    def switch_content(self, content):
        from templates import Background
        self.remove_widget(self.layout)
        self.layout = Background(page_instance=self)
        self.add_widget(content)


    def switch_to_seed_ip_page(self, instance=None, force=False):
        print('-switch_to_seed_ip_page')
        from templates import Background, seed_ip_content
        from commands.utils import get_operatorData
        operatorData = get_operatorData()
        if not force and 'userData' in operatorData and operatorData['userData'] != '':
            self.switch_to_operations(self, activate=True)
        elif not force and 'seed_ip' in operatorData and operatorData['seed_ip'] != '':
            self.switch_to_login_page()
        else:
            self.remove_widget(self.layout)
            self.layout = Background(page_instance=self, content = 'seed_layout')
            self.content = 'seed_layout'
            self.add_widget(seed_ip_content(self.layout, self))

    def switch_to_login_page(self, instance=None):
        from templates import Background, login_page_content
        self.remove_widget(self.layout)
        self.layout = Background(page_instance=self, content = 'login_layout')
        self.content = 'login_layout'
        self.add_widget(login_page_content(self.layout, self))

    def switch_to_create_user_page(self, instance=None):
        from templates import Background, create_new_user
        self.remove_widget(self.layout)
        self.layout = Background(page_instance=self, content = 'new_user_layout')
        self.content = 'new_user_layout'
        self.add_widget(create_new_user(self.layout, self))

    def switch_to_splash_page(self, instance):
        from templates import Background, splash_page_content
        self.remove_widget(self.layout)
        self.layout = Background(page_instance=self, content = 'splash_layout')
        self.content = 'splash_layout'
        self.add_widget(splash_page_content(self.layout, self))

    def create_new_database(self, instance):
        from templates import Background, create_superuser_form
        print('-switch to create new')
        self.remove_widget(self.layout)
        self.layout = Background(page_instance=self, content = 'create_superuser_form_layout')
        self.content = 'create_superuser_form_layout'
        self.add_widget(create_superuser_form(self.layout, self))

    def create_new_database_second_user(self, instance=None):
        from templates import Background, create_second_superuser_form
        print('-switch to create new 2')
        self.remove_widget(self.layout)
        self.layout = Background(page_instance=self, content = 'create_superuser_form_layout')
        self.content = 'create_superuser_form_layout'
        self.add_widget(create_second_superuser_form(self.layout, self))

    def switch_to_network_setup(self):
        from templates import Background, network_setup_form
        self.remove_widget(self.layout)
        self.layout = Background(page_instance=self, content = 'network_setup_form_layout')
        self.content = 'network_setup_form_layout'
        self.add_widget(network_setup_form(self.layout, self))

    def switch_to_install_setup(self):
        from templates import Background, new_network_install
        print('-switch_to_install_setup')
        self.remove_widget(self.layout)
        self.layout = Background(page_instance=self, content = 'network_setup_install_layout')
        self.content = 'network_setup_install_layout'
        self.add_widget(new_network_install(self.layout, self))

    def switch_to_operations(self, instance=None, refresh=True, activate=False, page='profile'):
        x = self.manager.get_screen('operator_screen')
        if activate:
            x.activate_display(default=True)
        try:
            x.switch_layout(page)
        except:
            x.switch_layout(page, x)
        if not activate:
            x.refresh_sidebar()

        self.manager.current = 'operator_screen'

    def process_seed_ip(self, seed_ip):
        self.message.text = 'Checking...'
        Clock.schedule_once(lambda dt, seed_ip=seed_ip: self.process_seed_ip_step2(seed_ip))

    def process_seed_ip_step2(self, seed_ip):
        from templates import Background, seed_ip_content
        from commands.utils import get_operatorData, write_operatorData, connect_to_node
        print('-process_seed_ip')
        print('http://' + seed_ip + '/utils/is_sonet')

        seed_ip = seed_ip.replace('https:','').replace('http:', '').replace('/','')
        operatorData = get_operatorData()
        operatorData['seed_ip'] = seed_ip
        operatorData['ip_master_list'] = {'seed':{'address':seed_ip}}
        r = connect_to_node(seed_ip, 'utils/get_sonet', operatorData=operatorData, timeout=5)
        if r:
            received_json = r.json()
            print('received_json',received_json)
            if 'message' in received_json and received_json['message'] == 'success':
                sonetData = json.loads(received_json['sonet'])
                if 'new_sonet' in operatorData:
                    del operatorData['new_sonet']
                operatorData['sonet'] = sonetData
                write_operatorData(operatorData)
                self.switch_to_login_page(self)
                return
                
        if 'sonet' in operatorData:
            del operatorData['sonet']
        if 'new_sonet' in operatorData:
            del operatorData['new_sonet']
        write_operatorData(operatorData)
        self.remove_widget(self.layout)
        self.layout = Background(page_instance=self)
        self.add_widget(seed_ip_content(self.layout, self, version='Failed'))

    def process_login(self, username, password, userId=None):
        print('-process_login', username.text)
        if len(password.text) < 10:
            if self.message:
                self.message.text = 'Please enter at least 20 characters in password'
        else:
            self.message.text = 'Checking...'
            Clock.schedule_once(lambda dt: self.process_login_step2(username, password))
    
    def process_login_step2(self, username, password):
        from commands.locked import createKeyPair, sign
        from commands.utils import get_node_list, get_operatorData, hash_upk_id
        operatorData = get_operatorData()
        data = {}
        nodes = get_node_list(operatorData=operatorData)
        err = None
        for nodeId, ip in nodes.items():
            try:
                msg = 'Failed contact'
                r = requests.post('http://' + ip['address'] + '/accounts/get_user_login', data={'username':username.text}, timeout=6)
                msg = 'Contact achieved'
                received_json = r.json()
                print('r', received_json)
                if 'message' in received_json:
                    if received_json['message']  == 'User not found':
                        if self.message:
                            self.message.text = 'Login failed'
                        return
                    elif 'sonet' in received_json:
                        sonetData = json.loads(received_json['sonet'])
                        operatorData['sonet'] = sonetData
                        message = received_json['message']
                        if message == 'User found':
                            print('user found')
                            userData = json.loads(received_json['userData'])
                            upks = received_json['upks']
                            user_id = userData['id']
                            print('user_id',user_id)
                            keyPair_accnt = createKeyPair(user_id, password.text, 'account', key_strength='ML_DSA_44')
                            privKey = keyPair_accnt[0]
                            pubKey = keyPair_accnt[1]
                            upkData = None
                            for upk in upks:
                                upk = json.loads(upk)
                                if upk['id'] == hash_upk_id(pubKey):
                                    upkData = upk
                                    break
                            operatorData['accnt_privKey'] = privKey
                            operatorData['accnt_pubKey'] = pubKey
                            operatorData['user_id'] = user_id
                            operatorData['username'] = username.text
                        elif message == 'User not found':
                            # do not use - create user in browser
                            from commands.utils import dt_to_string, now_utc
                            now = now_utc()
                        else:
                            print('received_json',received_json)
                            if self.message:
                                self.message.text = 'login fail: ' + received_json
                        if not upkData:
                            alert = 'Login failed'
                            if self.message:
                                self.message.text = alert
                        else:
                            userData = sign(userData, privKey=privKey, pubKey=pubKey)
                            # parsedData = json.loads(userData)
                            data['userData'] = json.dumps(userData)
                            print('data', data)
                            r = requests.post('http://' + ip['address'] + '/accounts/receive_user_login', data=data)
                            received_json = r.json()
                            print('message',received_json['message'])
                            if received_json['message'] == 'Valid Username and Password' or received_json['message'] == 'User Created':
                                print('success')
                                operatorData['userData'] = userData
                                operatorData['upkData'] = upkData
                                from commands.utils import verify_super_status, write_operatorData
                                write_operatorData(operatorData)
                                verify_super_status(operatorData=operatorData) # may not be correctly setting superuser on login
                                if self.message:
                                    self.message.text = received_json['message']
                                self.switch_to_operations(self)
                            elif received_json['message'] == 'Invalid Password':
                                alert = 'Username does not match password'
                                if self.message:
                                    self.message.text = alert
                            else:
                                alert = received_json['message']
                                if 'error' in received_json:
                                    print('error',received_json['error'])
                                    alert = alert + ' err: ' + received_json['error']
                                if self.message:
                                    self.message.text = alert
                        return
            except Exception as e:
                print('login fail', str(e))
                err = str(e)
                try:
                    if 'error' in received_json:
                        print('error',received_json['error'])
                except:
                    pass
        if self.message:
            if msg == 'Failed contact':
                self.message.text = 'Failed contact'
            else:
                self.message.text = f'Login failed: {err if err else msg}'

    def create_new_user(self, username, password):
        print('-creating superuser')
        if len(password.text) < 20:
            if self.message:
                self.message.text = 'Please enter at least 20 characters in passphrase'
        else:
            from commands.utils import get_operatorData, write_operatorData
            operatorData = get_operatorData()
            operatorData = {}
            operatorData['username'] = username.text
            operatorData['user_is_super'] = True
            write_operatorData(operatorData)
            print('next')
            self.switch_to_operations(page='new_network')


    def create_superuser(self, username, password):
        print('-creating superuser 1')
        if len(password.text) < 20:
            if self.message:
                self.message.text = 'Please enter at least 20 characters in passphrase'
        else:
            from commands.utils import get_operatorData, write_operatorData, store_secure_item
            operatorData = get_operatorData()
            operatorData = {}
            operatorData['userPass'] = password.text
            operatorData['username'] = username.text
            operatorData['user_is_super'] = True
            operatorData['new_sonet'] = {}
            write_operatorData(operatorData, clear_data=True)
            store_secure_item("node_keys", {})
            store_secure_item("sysPass", None)
            self.create_new_database_second_user()

    def create_second_superuser(self, username, password):
        print('-creating superuser 2')
        if len(password.text) < 20:
            if self.message:
                self.message.text = 'Please enter at least 20 characters in passphrase'
        else:
            from commands.utils import get_operatorData, write_operatorData
            operatorData = get_operatorData()
            operatorData['second_userPass'] = password.text
            operatorData['second_username'] = username.text
            write_operatorData(operatorData, clear_data=True)
            self.switch_to_operations(page='new_network')



class OperatorScreen(Screen):
    def __init__(self, **kwargs):
        super(OperatorScreen, self).__init__(**kwargs)
        print('-OperatorScreen')
        self.content = None
        self.main_layout = BoxLayout(orientation='horizontal')
        self.add_widget(self.main_layout)

        with self.main_layout.canvas.before:
            Color(0.094, 0.122, 0.176, 1)
            self.rect = Rectangle(size=self.main_layout.size, pos=self.main_layout.pos)
            self.main_layout.bind(size=self.update_rect, pos=self.update_rect)

    def activate_display(self, default=True):
        from ops import Sidebar
        self.menu_layout = Sidebar(parent=self, orientation='vertical')
        self.main_layout.add_widget(self.menu_layout)

        self.display_layout = self.get_default_layout()
        if default:
            self.display_layout.activate_display()

        self.main_layout.add_widget(self.display_layout)

    def get_default_layout(self):
        from ops import ProfileScreen
        return ProfileScreen(parent=self, orientation='vertical', size_hint=(1, 1))

    def switch_layout(self, screen, instance=None, target=None, ops=None):
        print('-switch_layout', screen, self)
        from ops import LoadScreen
        self.screen = screen
        self.target = target
        self.ops = ops
        try:
            if self.job_running:
                try:
                    Clock.schedule_once(lambda dt: self.menu_layout.flash_button(self.screen), 1)
                except:
                    pass

                return
        except:
            pass


        if screen.lower() == 'logout' or screen.lower() == 'login':
            self.logout(self)
        else:
            try:
                if hasattr(self.display_layout, 'close_screen'):
                    self.display_layout.close_screen()                    
            except Exception as e:
                print('close_screen err1',str(e))
            try:
                self.display_layout.remove_widget(self.display_layout.scroll_view)
                del self.display_layout.scroll_view
            except Exception as e:
                print('opsscreen err 1',str(e))
                pass
            try:
                self.main_layout.remove_widget(self.display_layout)
                del self.display_layout
            except Exception as e:
                print('opsscreen err 2',str(e))
                pass
            self.display_layout = LoadScreen(orientation='vertical', size_hint=(1, 1))
            self.display_layout.activate_display()
            self.main_layout.add_widget(self.display_layout)
        Clock.schedule_once(lambda dt: self.switch_layout2())


    def switch_layout2(self):
        print('-switch_layout2', self.screen)
        from ops import ProfileScreen, ChainsScreen, SetupScreen, MonitorScreen, NodesScreen, SettingsScreen

        if self.screen.lower() == 'logout' or self.screen.lower() == 'login':
            self.logout(self)
        else:
            try:
                self.display_layout.remove_widget(self.display_layout.scroll_view)
            except:
                pass
            try:
                self.main_layout.remove_widget(self.display_layout)
            except:
                pass
            if self.screen.lower() in ['regions', 'plugins']:
                self.display_layout = ChainsScreen(parent=self, option=self.screen, orientation='vertical', size_hint=(1, 1))
                self.display_layout.activate_display()
            elif self.screen.lower() in ['install', 'reinstall', 'activate', 'deactivate', 'uninstall', 'restart', 'syncdb', 'update', 'new_node_local', 'new_node_remote', 'new_network']:
                self.display_layout = SetupScreen(parent=self, option=self.screen, orientation='vertical', size_hint=(1, 1))
                if self.ops:
                    getattr(self.display_layout, self.ops['func'])(**self.ops['args'])
                else:
                    self.display_layout.activate_display()
            elif self.screen.lower() in ['new_node_local', 'new_node_remote']:
                self.display_layout = SetupScreen(parent=self, option='', orientation='vertical', size_hint=(1, 1))
                self.display_layout.activate_display()
            elif self.screen.lower() == 'monitor':
                self.display_layout = MonitorScreen(parent=self, orientation='vertical', size_hint=(1, 1))
                self.display_layout.activate_display()
            elif self.screen.lower() == 'profile':
                self.display_layout = ProfileScreen(parent=self, orientation='vertical', size_hint=(1, 1))
                self.display_layout.activate_display()
            elif self.screen.lower() == 'mynodes':
                self.display_layout = NodesScreen(parent=self, orientation='vertical', size_hint=(1, 1))
                if self.ops:
                    getattr(self.display_layout, self.ops['func'])(self.ops['args'])
                else:
                    self.display_layout.activate_display()
            elif self.screen.lower() in ['settings','node_settings','super_actions']:
                self.display_layout = SettingsScreen(parent=self, option=self.screen, orientation='vertical', size_hint=(1, 1))
                if self.target:
                    self.display_layout.show_localData(target=self.target)
                else:
                    self.display_layout.activate_display()
            else:
                self.display_layout = ProfileScreen(parent=self, orientation='vertical', size_hint=(1, 1))
                self.display_layout.activate_display()
            self.main_layout.add_widget(self.display_layout)

    def refresh_sidebar(self, instance=None, attempt=1):
        from ops import Sidebar
        print('-refresh sidebar')
        try:
            self.main_layout.remove_widget(self.menu_layout)
            del self.menu_layout
        except Exception as e:
            print('opsscreen err 3',str(e))
            pass
        try:
            self.menu_layout = Sidebar(parent=self, orientation='vertical')
            self.main_layout.add_widget(self.menu_layout, index=len(self.children))
        except Exception as e:
            print('opsscreen err 4',str(e))
            if attempt == 1:
                Clock.schedule_once(lambda dt: self.refresh_sidebar(attempt=2))

    def activate(self):
        from ops import Sidebar
        self.menu_layout = Sidebar(parent=self, orientation='vertical')
        pass
    
    def deactivate(self):
        from ops import Sidebar
        self.menu_layout = Sidebar(parent=self, orientation='vertical')
        pass
    
    def uninstall(self):
        from ops import Sidebar
        self.menu_layout = Sidebar(parent=self, orientation='vertical')
        pass

    def logout(self, instance):
        print('-logout')
        from commands.utils import get_operatorData, write_operatorData, store_secure_item
        operatorData = get_operatorData()
        operatorData['accnt_privKey'] = ''
        operatorData['accnt_pubKey'] = ''
        operatorData['userPass'] = ''
        operatorData['user_id'] = ''
        operatorData['username'] = ''
        operatorData['userData'] = ''
        operatorData['upkData'] = ''

        # other data should be removed here

        write_operatorData(operatorData)
        store_secure_item("node_keys", {})
        store_secure_item("sysPass", None)
        x = self.manager.get_screen('splash_screen')
        x.switch_to_login_page(x)
        self.manager.current = 'splash_screen'

    def update_rect(self, *args):
        self.rect.size = self.size
        self.rect.pos = self.pos

    def run_installer(self):
        self.switch_layout('Install', self)
        self.manager.current = 'operator_screen'
        self.run()

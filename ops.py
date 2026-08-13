
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.graphics import Line, Rectangle, Color
from kivy.uix.gridlayout import GridLayout
from kivy.uix.checkbox import CheckBox
from kivy.uix.scrollview import ScrollView
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.widget import Widget
from kivy.metrics import dp
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from functools import partial
from collections import deque

import pty
import os
import re
import subprocess
import threading
from kivy.clock import Clock
import requests
import json
import ast
import time
import datetime
import platform
import paramiko
from itertools import islice
from mnemonic import Mnemonic

import shutil
import random
import yaml
from pathlib import Path

from os.path import expanduser
from django_rq import get_queue
from rq.worker import Worker



from templates import Divider, HoverButton, FieldRow, DynamicTreeView, CheckBoxTreeLabel, AnimatedDropDown, FlashingButton, PaneDivider
from commands.utils import (
    fetch_secure_item, store_secure_item, get_operatorData, write_operatorData, 
    now_utc, get_node_list, get_remote, verify_super_status,
    get_commands, fetch_remote_commands, connect_to_node, get_device_system,
    fetch_remote_data, make_remote_connection, send_manager_to_remote, refresh_ip, dt_to_string, value_is_none
    )
from commands.locked import generate_id, super_id, createKeyPair, sign



BASE_WIDTH = 1440

raw = Window.width / BASE_WIDTH
w_scale = max(1.15 if Window.width < 1200 else 1.0, raw)
t_scale = max(1.15 if Window.width < 1200 else 1.0, raw)


device_system = get_device_system()
display_max_size = 0 # number of lines in readout panel
# display_max_size = 1000 # number of lines in readout panel

dark_blue = Color(0.094, 0.122, 0.176, 1)
dark_blue2 = (0.094, 0.122, 0.176, 1)

try:
    operatorData = get_operatorData()
    w_scale = operatorData.get('magnification', 1)
    print('w_scale1',w_scale)
    t_scale = operatorData.get('font_adjustment', 1)
    print('t_scale1',t_scale)
except Exception as e:
    print('scale err',str(e))
    w_scale = 1
    t_scale = 1

if platform == "linux":
    base_t_scale = 3
elif platform == "macosx":
    base_t_scale = 0
else:
    base_t_scale = 0

def is_nginx_installed(operatorData=None):
    print('--is_nginx_installed')
    try:
        operatorData = get_operatorData(operatorData)
        if 'selected_node' in operatorData:
            node_meta = operatorData['myNodes'][operatorData['selected_node']]['meta']
            if 'is_installed' in node_meta and node_meta['is_installed']: 
                return True
            else:
                return False
        else:
            return False
        
    except subprocess.CalledProcessError:
        print('is_installed fail')
        return False

def is_nginx_running(operatorData=None):
    print('--is_nginx_running')
    try:
        operatorData = get_operatorData(operatorData)
        if 'selected_node' in operatorData:
            node = operatorData['myNodes'][operatorData['selected_node']]
            if 'location' in node and node['location'] != 'local':
                try:
                    address = operatorData['myRemotes'][node['location']]['local_address'] + ':' + node['settings']['port']
                except:
                    address = node['nodeData']['address']
            else:
                address = node['settings']["localhost"]
        else:
            print('r f 1')
            return False
        
        if not 'activated_dt' in node['nodeData'] or not node['nodeData']['activated_dt'] or str(node['nodeData']['activated_dt']) == 'None':
            print('r f 2')
            return False
        if 'ip_master_list' in operatorData and len(operatorData['ip_master_list']) <= 1 and ('myRemotes' not in operatorData or len(operatorData['myRemotes']) <= 1):
            if 'activated_dt' in node['nodeData'] and not value_is_none(node['nodeData']['activated_dt']):
                print('run t 1')
                return True
        r = connect_to_node(address, 'network/get_node_request/self', data={}, operatorData=operatorData, timeout=7)
        if r and r.status_code != 200:
            print('browser fail', r.content)
            return False
        elif r and r.json()['message'] == 'Success':
            json_response = r.json()
            nodeData = json.loads(json_response['fullNodeData'])
            # print('nodeData',nodeData)
            if not value_is_none(nodeData['activated_dt']) and value_is_none(nodeData['suspended_dt']):
                print('r t 2')
                return True
        else:
            if r:
                print('r.content',r.content)
            print('r f 3')
            return False
    except Exception as e:
        print('r5', str(e))
        # return False
        try:
            if 'userData' in operatorData and 'id' in operatorData['userData'] and operatorData['userData']['id'] == super_id():
                if 'ip_master_list' in operatorData and len(operatorData['ip_master_list']) == 1:
                    if 'localhost' in operatorData and operatorData['localhost'] != '':
                        r = connect_to_node(operatorData["localhost"], 'network/get_node_request/self', data={}, operatorData=operatorData, timeout=4)
                        if r.status_code != 200:
                            print('browser fail 2', r.content)
                            return False
                        elif r.json()['message'] == 'Success':
                            json_response = r.json()
                            nodeData = json.loads(json_response['fullNodeData'])
                            if not value_is_none(nodeData['activated_dt']) and value_is_none(nodeData['suspended_dt']):
                                print('r t 3')
                                return True
            else:
                nodes = get_node_list(operatorData=operatorData)
                local_node = operatorData['myNodes'][operatorData['local_nodeId']]['nodeData']
                if not value_is_none(local_node['activated_dt']):
                    if 'suspended_dt' not in local_node or not local_node['suspended_dt']:
                        data = {'requested_address':local_node['address'],'nodeId':local_node['id']}
                        for nodeId, ip in nodes.items():
                            try:
                                r = connect_to_node(ip, 'utils/can_you_see_me', data=data, operatorData=operatorData, timeout=10)
                                if r.status_code == 200:
                                    received_json = r.json()
                                    if received_json['message'] == 'Success':
                                        if 'is_https' in received_json and not received_json['is_https']:
                                            return False
                                        else:
                                            print('r t 4')
                                            return True
                            except Exception as e:
                                print('r f 4',str(e))
                                return False
                print('r f 5')
                return False
        except Exception as e:
            print('r f 5',str(e))
        return False


class GradientBackground(BoxLayout):
    def __init__(self, **kwargs):
        super(GradientBackground, self).__init__(**kwargs)
        with self.canvas.before:
            (0.2, 0.2, 0.6, 1)
            self.rect = Rectangle(size=self.size, pos=self.pos)

        # Bind the size and pos properties to update the gradient when the widget is resized or repositioned
        self.bind(size=self._update_rect, pos=self._update_rect)

    def _update_rect(self, instance, value):
        self.rect.pos = self.pos
        self.rect.size = self.size

class Sidebar(BoxLayout):
    def __init__(self, parent, **kwargs):
        super(Sidebar, self).__init__(**kwargs)
        print('-Sidebar')
        
        operatorData = get_operatorData()
        self.size_hint_x = None  
        self.size_hint_y = 1
        self.width = dp(130) * w_scale
        with self.canvas.before:
            Color(0.043, 0.333, 0.604, 1)  
            self.rect = Rectangle(size=self.size, pos=self.pos)
            self.bind(size=self.update_rect, pos=self.update_rect)
        padding = BoxLayout(size_hint=(1, None), height=25)  
        self.add_widget(padding)
        anchor_layout = AnchorLayout(anchor_x='center', anchor_y='top', size_hint=(1, None), height=dp(65) * w_scale)
        try:
            homepath = expanduser("~")
            logoLink = f'{homepath}/Sonet/SoNodeManager/assets/img/sologo.png'
            if 'sonet' in operatorData:
                sonetData = operatorData['sonet']
                logo = sonetData['LogoLink']
                new_logoLink = homepath + '/Sonet/SoNodeServer/static_cdn/' + logo
                print('logoLink',logoLink)
                if Path(new_logoLink).exists():
                    print("File exists")
                    logoLink = new_logoLink
                else:
                    print("File does not exist (or parent folder is missing)")
        except Exception as e:
            print('logo err',str(e))
            logoLink = ''
        logo = Image(source=logoLink, size_hint=(None, None), size=(dp(65) * w_scale, dp(65) * w_scale))
        anchor_layout.add_widget(logo)
        self.add_widget(anchor_layout)
        padding = BoxLayout(size_hint=(1, None), height=25) 
        self.add_widget(padding)

        self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        self.content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=5)
        self.content.bind(minimum_height=self.content.setter("height"))

        if parent and 'username' not in operatorData or operatorData['username'] == '':
            user = 'None'
        else:
            user = operatorData['username']

        if 'userData' not in operatorData or 'sonet' not in operatorData and 'new_sonet' not in operatorData:
            print('log in')
            buttons = ['Login']
            if 'start_local_install' in operatorData and operatorData['start_local_install']:
                buttons.append('Uninstall')
                buttons.append('Reinstall')

            for button_text in buttons:
                btn = HoverButton(
                    text=button_text,
                    font_size=dp(16) * t_scale,
                    height=dp(32) * w_scale,
                    on_press=partial(parent.switch_layout, button_text)
                )
                self.content.add_widget(btn)
        else:
            print('logout')
            buttons = ['Profile', 'MyNodes']
            if 'start_local_install' in operatorData and operatorData['start_local_install']:
                buttons.append('Uninstall')
                buttons.append('Reinstall')
            
            is_active = is_nginx_running()
            if not is_active:
                buttons.append('Logout')

            for button_text in buttons:
                btn = HoverButton(
                    text=button_text,
                    font_size=dp(16) * t_scale,
                    height=dp(32) * w_scale,
                    on_press=partial(parent.switch_layout, button_text)
                )
                self.content.add_widget(btn)


            self.content.add_widget(Divider(padding=15))
            if 'selected_node' in operatorData or 'local_nodeId' in operatorData:
                if not 'selected_node' in operatorData:
                    operatorData['selected_node'] = operatorData['local_nodeId']
                    write_operatorData(operatorData)
                    is_active = is_nginx_running()

                try:
                    if operatorData['selected_node'] == 'loading':
                        node_actions = ['loading...']
                    else:
                        selected_node_name = operatorData['myNodes'][operatorData['selected_node']]['settings']['node_name']
                        print('selected_node_name',selected_node_name)
                        if is_nginx_installed():
                            if is_active: # set this to update in background, otherwise may hang while trying to connect to inactive self server
                                node_actions = [selected_node_name, 'Monitor', 'Plugins', 'Restart', 'Update', 'Deactivate']
                            else:
                                node_actions = [selected_node_name, 'Monitor', 'Plugins', 'Activate', 'Restart', 'Update', 'Uninstall']
                        else:
                            node_actions = [selected_node_name, 'Install']
                    for button_text in node_actions:
                        if button_text == 'loading...':
                            action = ''
                        elif button_text == selected_node_name:
                            action = 'node_settings'
                        else:
                            action = button_text
                        btn = HoverButton(
                            text=button_text,
                            font_size=dp(16) * t_scale,
                            height=dp(32) * w_scale,
                            on_press=partial(parent.switch_layout, action)
                        )
                        self.content.add_widget(btn)
                except Exception as e:
                    print('button fail 1',str(e))
                    btn = HoverButton(
                        text=operatorData['selected_node'],
                        font_size=dp(16) * t_scale,
                        height=dp(32) * w_scale,
                        on_press=partial(parent.switch_layout, 'node_settings')
                    )
                    self.content.add_widget(btn)
            elif not 'start_local_install' in operatorData or not operatorData['start_local_install']:
                btn1 = HoverButton(
                    text='local',
                    font_size=dp(16) * t_scale,
                    height=dp(32) * w_scale,
                )
                self.content.add_widget(btn1)
                btn = HoverButton(
                    text='Install',
                    font_size=dp(16) * t_scale,
                    height=dp(32) * w_scale,
                    on_press=partial(parent.switch_layout, 'Install')
                )
                self.content.add_widget(btn)

        spacer = BoxLayout(size_hint=(1, 1))
        self.content.add_widget(spacer)

        self.scroll_view.add_widget(self.content)
        self.add_widget(self.scroll_view)
        from commands.utils import sonode_version_num
        version = Label(text='SoNode v' + str(sonode_version_num), size_hint=(1, None), height=dp(50) * w_scale, font_size=dp(13) * t_scale)
        self.add_widget(version)

    def update_rect(self, *args):
        self.rect.size = self.size
        self.rect.pos = self.pos

    def flash_button(self, text):
        print('-flash_button', text)
        for child in self.content.children:
            if isinstance(child, HoverButton) and child.text == text:
                print('HERE',child)
                original_color = child.bg_color.rgba[:]
                child.bg_color.rgba = (1, 0.5, 0, 1)
                Clock.schedule_once(
                    lambda dt, btn=child, color=original_color: setattr(btn.bg_color, "rgba", color), 
                    0.5
                )
                break


class MonitorScreen(BoxLayout):
    def __init__(self, parent=None, **kwargs):
        super(MonitorScreen, self).__init__(**kwargs)
        self.parent_screen = parent
        self.default_commands = {"Requests": "sudo -S tail -f ~/Sonet/.data/logs/gunicorn.log",'Chatter':'sudo -S tail -f ~/Sonet/.data/logs/chat_worker.log', 'High Worker':'sudo -S tail -f ~/Sonet/.data/logs/high_worker.log', 'Main Worker':'sudo -S tail -f ~/Sonet/.data/logs/main_worker.log','Low Worker':'sudo -S tail -f ~/Sonet/.data/logs/low_worker.log'}
        self.default_presets = {'Full Logs':{'local':['Status','Requests','Chatter','new_row','High Worker','Main Worker','Low Worker']},'local:workers':{'local':['High Worker', 'Main Worker','Low Worker']},'requests/chatter':['Requests','Chatter'],'All Remotes':'all_remotes'}

        self.window_row_count = 0
        self.window_count = 0
        self.load_servers()
        self.display_rows = BoxLayout(orientation='vertical')
        self.add_widget(self.display_rows)
        from os.path import expanduser
        homepath = expanduser("~")
        global t_scale
        global w_scale
        self.w_scale = w_scale
        self.t_scale = t_scale

        with self.canvas.before:
            Color(0.094, 0.122, 0.176, 1)
            self.rect = Rectangle(size=self.size, pos=self.pos)
            self.bind(size=self.update_rect, pos=self.update_rect)

    def activate_display(self):
        self.create_new_row()

    def create_window(self, row=1, creator_window=None, super_func=None):
        self.window_count += 1
        print('-create_window', self.window_count, super_func)
        window = BoxLayout(orientation='vertical')
        window.row_num = row
        window.window_num = self.window_count
        setattr(self, f'window_{self.window_count}', window)
        if creator_window:
            window.row = creator_window.row
        else:
            window.row = getattr(self, f'row_{window.row_num}')

        window.window_num = self.window_count
        window.client = None
        window.running_thread = None
        window.running_channel = None
        window.running_printer = None
        window.system_info_thread = None
        window.network_info_thread = None
        window.utc_thread = None
        window.info_updater = False
        window.monitor_status = False
        window.network_interface = 'eth0'
        window.uptime = 'unknown'
        window.uptime_fetched = None

        window.server = None
        window.command = None
        window.output_buffer = ''

        window.button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(30) * w_scale)

        close_button = FlashingButton(text="x", size_hint_y=None, size_hint_x=0.2, height=dp(30) * w_scale,font_size=dp(16) * t_scale)
        close_button.bind(on_release=lambda btn: (self.remove_window(window), window.options_dropdown.dismiss()))
        window.button_layout.add_widget(close_button)

        window.server_dropdown = AnimatedDropDown()
        window.command_dropdown = AnimatedDropDown()

        self.add_server_options(getattr(self, f'window_{self.window_count}'))
        self.add_command_options(getattr(self, f'window_{self.window_count}'))

        new_window_button = FlashingButton(text="+", size_hint_y=None, size_hint_x=0.2, height=dp(30) * w_scale,font_size=dp(16) * t_scale)
        new_window_button.bind(on_release=lambda btn: (self.create_window(creator_window=window), window.options_dropdown.dismiss()))
        window.button_layout.add_widget(new_window_button)
        window.add_widget(window.button_layout)

        window.display = BoxLayout(orientation='horizontal')
        window.add_widget(window.display)
        
        self.add_text_display(window)
        self.add_options(getattr(self, f'window_{self.window_count}'))
        if creator_window:
            children = creator_window.row.children
            for i, widget in enumerate(children):
                if hasattr(widget, 'window_num'):
                    try:
                        if widget.window_num == creator_window.window_num:
                            
                            window.ssh_host = widget.ssh_host
                            window.ssh_user = widget.ssh_user
                            window.ssh_password = widget.ssh_password
                            window.server_button.text = widget.server_button.text
                            window.server = widget.server

                            insert_index = i
                            break
                    except Exception as e:
                        print('create window err 1',str(e))
            else:
                insert_index = 0

            if insert_index < 0:
                insert_index = 0
            window.row.add_widget(window, index=insert_index)     
        else:
            window.row.add_widget(window)
        if super_func and isinstance(super_func, dict):
            self.select_server(getattr(self, f'window_{self.window_count}'), super_func['server_name'], open_cmds=False)
            self.run_command(getattr(self, f'window_{self.window_count}'), super_func['command'])
        elif self.window_count == 1:
            self.perform_action(window=window, command='monitor_status_start', menu='commands', args=[window, ])
        
        return window

    def create_new_row(self, creator_row=None, super_func=None):
        print('-create_new_row')
        self.window_row_count += 1
        window_row = BoxLayout(orientation='horizontal')
        window_row.window_row_num = self.window_row_count
        setattr(self, f'row_{self.window_row_count}', window_row)

        if creator_row:
            children = self.display_rows.children
            for i, widget in enumerate(children):
                if hasattr(widget, 'window_num'):
                    try:
                        if widget.window_row_num == creator_row.window_row_num:
                            insert_index = i
                            break
                    except Exception as e:
                        print('create_new_row err',str(e))
            else:
                insert_index = 0
            if insert_index < 0:
                insert_index = 0
            self.display_rows.add_widget(window_row, index=insert_index)     
        else:
            self.display_rows.add_widget(window_row)

        return self.create_window(row=self.window_row_count, super_func=super_func)


    def super_open_server(self, window, server_name):
        threading.Thread(target=self.remove_menu, args=(window, 'server')).start()
        done_first = False
        for name, cmd in self.commands.items():
            if name != 'Uptime':
                if not done_first:
                    self.select_server(window, server_name, open_cmds=False)
                    self.run_command(window, name)
                    done_first = True
                else:
                    self.create_window(super_func={'server_name':server_name, 'command':name})

    def super_close_server(self, window, server_name):
        # print('-stop_all_running_commands')
        window.server_dropdown.dismiss()
        for display in self.output_displays.children:
            if display.server == server_name:
                self.output_displays.remove_widget(display)
        try:
            self.output_displays.remove_widget(window)
        except:
            pass
        if not len(self.output_displays.children):
            self.create_window()

    def edit_server(self, window, server_name): # dont use
        window.server_dropdown.dismiss()
        if server_name in self.servers:
            current_server = self.servers[server_name]
            scroll_view = ScrollView(size_hint=(1, 1))

            popup_layout = BoxLayout(orientation="vertical", size_hint_y=None, padding=10, spacing=10)
            popup_layout.bind(minimum_height=popup_layout.setter("height"))

            address_input = TextInput(text=current_server["external_address"], size_hint_y=None, height=dp(30) * w_scale, font_size=dp(16) * t_scale)
            host_input = TextInput(text=current_server["host"], size_hint_y=None, height=dp(30) * w_scale, font_size=dp(16) * t_scale)
            user_input = TextInput(text=current_server["user"], size_hint_y=None, height=dp(30) * w_scale, font_size=dp(16) * t_scale)
            password_input = TextInput(text=current_server["password"], size_hint_y=None, height=dp(30) * w_scale, font_size=dp(16) * t_scale, password=True)

            popup_layout.add_widget(address_input)
            popup_layout.add_widget(host_input)
            popup_layout.add_widget(user_input)
            popup_layout.add_widget(password_input)

            def save_updated_server(instance):
                address = address_input.text
                host = host_input.text
                user = user_input.text
                password = password_input.text
                if host and user and password:
                    self.servers[server_name] = {"external_address": address, "host": host, "user": user, "password": password}
                    self.save_data()
                    self.add_server_options(window)
                    popup.dismiss()

            def cancel_action(instance):
                popup.dismiss()

            def remove_server(server_name):
                if server_name in self.servers:
                    del self.servers[server_name]
                    self.save_data()
                self.add_server_options(window)
                window.output_display.text += f"Server {server_name} has been removed.\n"
                popup.dismiss()

            button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(25) * w_scale)
            save_button = FlashingButton(text="Save", size_hint_y=None, height=dp(25) * w_scale, font_size=dp(16) * t_scale)
            save_button.bind(on_release=save_updated_server)
            button_layout.add_widget(save_button)

            cancel_button = FlashingButton(text="Cancel", size_hint_y=None, height=dp(25) * w_scale, font_size=dp(16) * t_scale)
            cancel_button.bind(on_release=cancel_action)
            button_layout.add_widget(cancel_button)

            del_button = FlashingButton(text="Delete", size_hint_y=None, height=dp(25) * w_scale, font_size=dp(16) * t_scale)
            del_button.bind(on_release=lambda btn, server_name=server_name: remove_server(server_name))
            button_layout.add_widget(del_button)
            popup_layout.add_widget(button_layout)
            scroll_view.add_widget(popup_layout)

            popup = Popup(title=f"Edit Remote {server_name}", title_size=dp(16) * t_scale, content=scroll_view, size_hint=(0.8, 0.6))
            popup.open()
        else:
            print(f"remote {server_name} not found.")

    def add_new_server(self, window, instance=None): # dont use
        window.server_dropdown.dismiss()
        scroll_view = ScrollView(size_hint=(1, 1))

        popup_layout = BoxLayout(orientation="vertical", size_hint_y=None, padding=10, spacing=10)
        popup_layout.bind(minimum_height=popup_layout.setter("height"))
        
        name_input = TextInput(hint_text="Enter name", size_hint_y=None, height=dp(35) * w_scale, font_size=dp(16) * t_scale)
        address_input = TextInput(hint_text="Enter external address", size_hint_y=None, height=dp(30) * w_scale, font_size=dp(16) * t_scale)
        host_input = TextInput(hint_text="Enter local address", size_hint_y=None, height=dp(30) * w_scale, font_size=dp(16) * t_scale)
        user_input = TextInput(hint_text="Enter username", size_hint_y=None, height=dp(30) * w_scale, font_size=dp(16) * t_scale)
        password_input = TextInput(hint_text="Enter password", size_hint_y=None, height=dp(30) * w_scale, font_size=dp(16) * t_scale, password=True)

        popup_layout.add_widget(name_input)
        popup_layout.add_widget(address_input)
        popup_layout.add_widget(host_input)
        popup_layout.add_widget(user_input)
        popup_layout.add_widget(password_input)

        def save_new_server(instance):
            server_name = name_input.text
            address = address_input.text
            host = host_input.text
            user = user_input.text
            password = password_input.text
            if host and user and password:
                self.servers[server_name] = {"external_address": address, "host": host, "user": user, "password": password}
                self.save_data()
                self.add_server_options(window)
                popup.dismiss()

        save_button = FlashingButton(text="Save Remote", size_hint_y=None, height=dp(25) * w_scale, font_size=dp(16) * t_scale)
        popup_layout.add_widget(save_button)
        scroll_view.add_widget(popup_layout)

        popup = Popup(title="New Remote", title_size=dp(16) * w_scale, content=scroll_view, size_hint=(0.8, 0.6), height=dp(16) * w_scale)
        popup.open()

    def edit_commands(self, window):
        scroll_view = ScrollView(size_hint=(1, 1))
        popup_layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        menu_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=10)
        menu_layout.bind(minimum_height=menu_layout.setter("height"))
        commands_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=10)
        commands_layout.bind(minimum_height=commands_layout.setter("height"))
        commands_layout.label = Label(text='Commands', size_hint_y=None, height=dp(30) * t_scale, font_size=dp(16) * t_scale)  
        commands_layout.add_widget(commands_layout.label)

        for name, cmd in self.commands.items():
            cmd_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(35) * t_scale)
            cmd_layout.cmd_name_input = TextInput(text=name, size_hint_y=None, height=dp(30) * t_scale, font_size=dp(16) * t_scale)
            cmd_layout.add_widget(cmd_layout.cmd_name_input)
            cmd_layout.cmd_input = TextInput(text=cmd, size_hint_y=None, height=dp(30) * t_scale, font_size=dp(16) * t_scale)
            cmd_layout.add_widget(cmd_layout.cmd_input)
            commands_layout.add_widget(cmd_layout)
        menu_layout.add_widget(commands_layout)
        
        preset_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=10)
        preset_layout.bind(minimum_height=preset_layout.setter("height"))
        preset_layout.label = Label(text='Presets', size_hint_y=None, height=dp(30) * t_scale, font_size=dp(16) * t_scale)  
        preset_layout.add_widget(preset_layout.label)

        for name, cmd in self.preset_commands.items():
            cmd_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(35) * t_scale)
            cmd_layout.preset_name_input = TextInput(text=name, size_hint_y=None, height=dp(30) * t_scale, font_size=dp(16) * t_scale)
            cmd_layout.add_widget(cmd_layout.preset_name_input)
            cmd_layout.preset_input = TextInput(text=str(cmd), size_hint_y=None, height=dp(30) * t_scale, font_size=dp(16) * t_scale)
            cmd_layout.add_widget(cmd_layout.preset_input)
            preset_layout.add_widget(cmd_layout)
        menu_layout.add_widget(preset_layout)

        settings_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=10)
        settings_layout.bind(minimum_height=settings_layout.setter("height"))
        settings_layout.label = Label(text='Settings', size_hint_y=None, height=dp(30) * t_scale, font_size=dp(16) * t_scale)  
        settings_layout.add_widget(settings_layout.label)
        line_count_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(35) * t_scale)
        line_count_layout.lines_label = Label(text='Max Characters', size_hint_y=None, height=dp(30) * t_scale, font_size=dp(16) * t_scale)  
        line_count_layout.add_widget(line_count_layout.lines_label)
        line_count_layout.lines_input = TextInput(text=str(self.max_lines), size_hint_y=None, height=dp(30) * t_scale, font_size=dp(16) * t_scale)
        line_count_layout.add_widget(line_count_layout.lines_input)
        settings_layout.add_widget(line_count_layout)

        mag_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(35) * t_scale)
        mag_layout.font_label = Label(text='Magnification', size_hint_y=None, height=dp(30) * t_scale, font_size=dp(16) * t_scale)  
        mag_layout.add_widget(mag_layout.font_label)
        mag_layout.mag_input = TextInput(text=str(self.w_scale), size_hint_y=None, height=dp(30) * t_scale, font_size=dp(16) * t_scale)
        mag_layout.add_widget(mag_layout.mag_input)
        settings_layout.add_widget(mag_layout)

        font_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(35) * t_scale)
        font_layout.font_label = Label(text='Text Size', size_hint_y=None, height=dp(30) * t_scale, font_size=dp(16) * t_scale)  
        font_layout.add_widget(font_layout.font_label)
        font_layout.font_input = TextInput(text=str(self.t_scale), size_hint_y=None, height=dp(30) * t_scale, font_size=dp(16) * t_scale)
        font_layout.add_widget(font_layout.font_input)
        settings_layout.add_widget(font_layout)

        from commands.utils import sonode_version_num
        settings_layout.version = Label(text=f'ver. {sonode_version_num}', size_hint_y=None, height=dp(30) * t_scale, font_size=dp(16) * t_scale)  
        settings_layout.add_widget(settings_layout.version)

        menu_layout.add_widget(settings_layout)
        scroll_view.add_widget(menu_layout)

        def save_updated_commands(instance):
            # print('-save_updated_commands')
            self.commands = {}
            self.preset_commands = {}
            for box in menu_layout.children:
                for chld in box.children:
                    if isinstance(chld, BoxLayout):
                        if hasattr(chld, 'lines_input'):
                            try:
                                self.max_lines = int(chld.lines_input.text)
                            except Exception as e:
                                print('save_updated_commands err',str(e))
                        elif hasattr(chld, 'mag_input'):
                            try:
                                new_w_scale = float(chld.mag_input.text)
                                if new_w_scale >= 0.1:
                                    w_scale = new_w_scale
                                    self.w_scale = w_scale
                                print('w_scale',w_scale)
                            except Exception as e:
                                print('new_w_scale err',str(e))
                        elif hasattr(chld, 'font_input'):
                            try:
                                new_t_scale = float(chld.font_input.text)
                                print('new_t_scale',new_t_scale)
                                if new_t_scale >= 0.1:
                                    t_scale = new_t_scale
                                    self.t_scale = t_scale
                                print('t_scale',t_scale)
                            except Exception as e:
                                print('new_t_scale err',str(e))
                        elif hasattr(chld, 'cmd_name_input') and chld.cmd_name_input.text and chld.cmd_input.text:
                            if chld.cmd_name_input.text != '' and chld.cmd_input.text != '':
                                if chld.cmd_name_input.text != 'name' and chld.cmd_input.text != 'cmd' and chld.cmd_input.text != '':
                                    self.commands[chld.cmd_name_input.text] = chld.cmd_input.text
                        elif hasattr(chld, 'preset_name_input') and chld.preset_name_input.text and chld.preset_input.text:
                            if chld.preset_name_input.text != '' and chld.preset_input.text != '' and chld.preset_input.text != '[]':
                                if chld.preset_name_input.text != 'name' and chld.preset_input.text != 'cmd' and chld.preset_input.text != '':
                                    self.preset_commands[chld.preset_name_input.text] = chld.preset_input.text
                    
            self.save_data()
            self.add_command_options(window)
            popup.dismiss()

        def cancel_action(instance):
            popup.dismiss()

        def new_cmd(instance):
            cmd_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(35) * t_scale)
            cmd_layout.cmd_name_input = TextInput(text='', hint_text='Command Name', size_hint_y=None, height=dp(30) * t_scale, font_size=dp(16) * t_scale)
            cmd_layout.add_widget(cmd_layout.cmd_name_input)
            cmd_layout.cmd_input = TextInput(text='', hint_text='sudo -S tail -f ~/Sonet/.data/logs/main_worker.log', size_hint_y=None, height=dp(30) * t_scale, font_size=dp(16) * t_scale)
            cmd_layout.add_widget(cmd_layout.cmd_input)
            commands_layout.add_widget(cmd_layout)

        def new_preset(instance):
            cmd_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(35) * t_scale)
            cmd_layout.preset_name_input = TextInput(text='', hint_text='Preset Name', size_hint_y=None, height=dp(30) * t_scale, font_size=dp(16) * t_scale)
            cmd_layout.add_widget(cmd_layout.preset_name_input)
            cmd_layout.preset_input = TextInput(text='', hint_text="{'local':['status','Chat Worker], 'new_row': '', 'local:['Main Worker,'Low Worker']}", size_hint_y=None, height=dp(30) * t_scale, font_size=dp(16) * t_scale)
            cmd_layout.add_widget(cmd_layout.preset_input)
            preset_layout.add_widget(cmd_layout)

        def reset_action(instance):
            self.commands = self.default_commands
            self.preset_commands = self.default_presets
            self.save_data()
            self.add_command_options(window)
            popup.dismiss()

        def fix_scroll(self):
            """Ensures the scroll starts at the top"""
            scroll_view.scroll_y = 1.0

        line1_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(25) * t_scale, spacing=10)
        line1_layout.add_widget(Button(text="New Cmd", size_hint_y=None, height=dp(25) * t_scale, font_size=dp(16) * t_scale, on_release=new_cmd))
        line1_layout.add_widget(Button(text="Cancel", size_hint_y=None, height=dp(25) * t_scale, font_size=dp(16) * t_scale, on_release=cancel_action))
        line2_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(25) * t_scale, spacing=10)
        line2_layout.add_widget(Button(text="New Preset", size_hint_y=None, height=dp(25) * t_scale, font_size=dp(16) * t_scale, on_release=new_preset))
        line2_layout.add_widget(Button(text="Reset All", size_hint_y=None, height=dp(25) * t_scale, font_size=dp(16) * t_scale, on_release=reset_action))
        line3_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(25) * t_scale, spacing=10)
        line3_layout.add_widget(Button(text="Save", size_hint_y=None, height=dp(25) * t_scale, font_size=dp(16) * t_scale, on_release=save_updated_commands))

        popup_layout.add_widget(scroll_view)
        popup_layout.add_widget(line1_layout)
        popup_layout.add_widget(line2_layout)
        popup_layout.add_widget(line3_layout)

        popup = Popup(title="Edit Commands", title_size=dp(16), content=popup_layout, size_hint=(0.8, 0.6))
        popup.open()

        Clock.schedule_once(fix_scroll, 0.1)


    def add_server_options(self, window):
        # print('-add_server_options')
        if hasattr(window, 'server_dropdown'):
            window.server_dropdown.clear_widgets()
        for server_name in self.servers.keys():
            btn = FlashingButton(
                text=server_name, 
                size_hint_y=None, 
                height=dp(35) * w_scale,
                background_color=(0.2, 0.6, 0.2, 1),  # Green background for server buttons
                color=(1, 1, 1, 1),  # White text color
                font_size=dp(16) * t_scale
            )
            btn.bind(on_release=lambda btn, window=window, server_name=server_name: self.select_server(window, server_name))

            srvr_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(27) * w_scale)
            super_close_button = FlashingButton(
                text=f"c-all", 
                size_hint_y=None,
                size_hint_x=0.25,
                height=dp(35) * w_scale,
                background_color=(1, 0, 0, 1),
                color=(1, 1, 1, 1),
                font_size=dp(16) * t_scale
            )
            super_close_button.bind(on_release=lambda btn, window=window, server_name=server_name: self.super_close_server(window, server_name))

            srvr_layout.add_widget(btn)
            srvr_layout.add_widget(super_close_button)
            window.server_dropdown.add_widget(srvr_layout)

        if not hasattr(window, 'server_button'):
            window.server_button = FlashingButton(text="Remote", size_hint_y=None, height=dp(30) * w_scale, font_size=dp(16) * t_scale)
            window.server_button.bind(on_release=window.server_dropdown.open)
            window.button_layout.add_widget(window.server_button)
            try:
                operatorData = get_operatorData()
                for nickname, remote_data in operatorData['myRemotes'].items():
                    if 'node_id' in remote_data and remote_data['node_id'] == operatorData['selected_node']:
                        self.select_server(window, nickname)
                    else:
                        print('nickname',nickname, remote_data)
                        if operatorData['myNodes'][operatorData['selected_node']]['location'] == remote_data['nickname']:
                            self.select_server(window, nickname)
            except Exception as e:
                print('select default err',str(e))

    def add_command_options(self, window):
        # print('-add_command_options')
        window.command_dropdown.clear_widgets()
        cmd_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(35) * w_scale)
        btn = FlashingButton(
            text='Status', 
            size_hint_y=None, 
            height=dp(35) * w_scale,
            background_color=(0.2, 0.6, 0.2, 1),  # Green background for server buttons
            color=(1, 1, 1, 1),  # White text color
            font_size=dp(16) * t_scale
        )
        btn.bind(on_release=lambda btn: self.perform_action(window=window, command='monitor_status_start', menu='commands', args=[window, ]))

        cmd_layout.add_widget(btn)
        window.command_dropdown.add_widget(cmd_layout)
        for cmd_name in self.commands.keys():
            cmd_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(35) * w_scale)
            btn = FlashingButton(
                text=cmd_name, 
                size_hint_y=None, 
                height=dp(35) * w_scale,
                background_color=(0.2, 0.6, 0.2, 1),
                color=(1, 1, 1, 1),
                font_size=dp(16) * t_scale
            )
            btn.bind(on_release=lambda btn: self.perform_action(window=window, command='run_command', menu='commands', args=[window, btn.text]))

            cmd_layout.add_widget(btn)
            window.command_dropdown.add_widget(cmd_layout)

        try:
            presets = self.preset_commands
        except:
            presets = self.default_presets
            self.preset_commands = presets
        for cmd_name in self.preset_commands.keys():
            cmd_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(35) * w_scale)
            btn = FlashingButton(
                text=cmd_name, 
                size_hint_y=None, 
                height=dp(35) * w_scale,
                background_color=(0.6, 0.6, 0.2, 1),
                color=(1, 1, 1, 1),
                font_size=dp(16) * t_scale
            )
            btn.bind(on_release=lambda btn: self.perform_action(window=window, command='run_preset', menu='commands', args=[window, btn.text]))

            cmd_layout.add_widget(btn)
            window.command_dropdown.add_widget(cmd_layout)

        edit_button = FlashingButton(
            text=f"Edit", 
            size_hint_y=None, 
            height=dp(35) * w_scale,
            background_color=(0.2, 0.2, 0.6, 1),  # Yellow background for edit buttons
            color=(1, 1, 1, 1),  # White text color
            font_size=dp(16) * t_scale
        )
        edit_button.bind(on_release=lambda btn: self.perform_action(window=window, command='edit_commands', menu='commands', args=[window]))
        window.command_dropdown.add_widget(edit_button)

        if not hasattr(window, 'commands_button'):
            window.commands_button = FlashingButton(text="Command", size_hint_y=None, height=dp(30) * w_scale, font_size=dp(16) * t_scale)
            window.commands_button.bind(on_release=window.command_dropdown.open)
            window.button_layout.add_widget(window.commands_button)

    def add_options(self, window):
        # print('-add_options')
        window.options_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(30) * w_scale, spacing=0, padding=0)
        window.options_dropdown = AnimatedDropDown()

        stop_button = FlashingButton(text="Stop All", size_hint_y=None, height=dp(45) * w_scale,background_color=(1, 0, 0, 1),color=(1, 1, 1, 1),font_size=dp(16) * t_scale)
        stop_button.bind(on_release=lambda btn: self.perform_action(window=window, command='stop_all_running_commands', menu='options', args=[window]))
        window.options_dropdown.add_widget(stop_button)

        stop_button = FlashingButton(text="Clear All", size_hint_y=None, height=dp(45) * w_scale,background_color=(1, 0, 0, 1),color=(1, 1, 1, 1),font_size=dp(16) * t_scale)
        stop_button.bind(on_release=lambda btn: self.perform_action(window=window, command='clear_all_outputs', menu='options', args=[window]))
        window.options_dropdown.add_widget(stop_button)

        info_button = FlashingButton(text="UTC Time", size_hint_y=None, height=dp(45) * w_scale,background_color=(0.6, 0.6, 0.2, 1),color=(1, 1, 1, 1),font_size=dp(16) * t_scale)
        info_button.bind(on_release=lambda btn: self.perform_action(window=window, command='show_utc_time', menu='options', args=[window]))
        window.options_dropdown.add_widget(info_button)

        reconnect_button = FlashingButton(text="Reconnect", size_hint_y=None, height=dp(45) * w_scale,background_color=(0.6, 0.6, 0.2, 1),color=(1, 1, 1, 1),font_size=dp(16) * t_scale)
        reconnect_button.bind(on_release=lambda btn: self.perform_action(window=window, command='redo_connection', menu='options', args=[window]))
        window.options_dropdown.add_widget(reconnect_button)

        disconnect_button = FlashingButton(text="Disconnect", size_hint_y=None, height=dp(45) * w_scale,background_color=(0.6, 0.6, 0.2, 1),color=(1, 1, 1, 1),font_size=dp(16) * t_scale)
        disconnect_button.bind(on_release=lambda btn: self.perform_action(window=window, command='close_connection', menu='options', args=[window]))
        window.options_dropdown.add_widget(disconnect_button)

        stop_button = FlashingButton(text="Stop", size_hint_y=None, height=dp(45) * w_scale,background_color=(0.6, 0.6, 0.2, 1),color=(1, 1, 1, 1),font_size=dp(16) * t_scale)
        stop_button.bind(on_release=lambda btn: self.perform_action(window=window, command='stop_running_command', menu='options', args=[window]))
        window.options_dropdown.add_widget(stop_button)

        clear_button = FlashingButton(text="Clear", size_hint_y=None, height=dp(45) * w_scale,background_color=(0.2, 0.6, 0.2, 1),color=(1, 1, 1, 1),font_size=dp(16) * t_scale)
        clear_button.bind(on_release=lambda btn: self.perform_action(window=window, command='clear_output', menu='options', args=[window]))
        window.options_dropdown.add_widget(clear_button)

        bottom_button = FlashingButton(text="To Bottom", size_hint_y=None, height=dp(45) * w_scale,background_color=(0.2, 0.6, 0.2, 1),color=(1, 1, 1, 1),font_size=dp(16) * t_scale)
        bottom_button.bind(on_release=lambda btn: self.perform_action(window=window, command='scroll_to_bottom', menu='options', args=[window]))
        window.options_dropdown.add_widget(bottom_button)

        options_button = FlashingButton(text="Options", size_hint_y=None, size_hint_x=0.75, height=dp(30) * w_scale,font_size=dp(16) * t_scale)
        options_button.bind(on_release=window.options_dropdown.open)

        close_button = FlashingButton(text="x", size_hint_y=None, size_hint_x=0.2, height=dp(30) * w_scale,font_size=dp(16) * t_scale)
        close_button.bind(on_release=lambda btn: (self.remove_window_row(window.row), window.options_dropdown.dismiss()))
        window.options_layout.add_widget(close_button)

        window.options_layout.add_widget(options_button)

        new_window_button = FlashingButton(text="+", size_hint_y=None, size_hint_x=0.2, height=dp(30) * w_scale,font_size=dp(16) * t_scale)
        new_window_button.bind(on_release=lambda btn: (self.create_new_row(creator_row=window.row), window.options_dropdown.dismiss()))
        window.options_layout.add_widget(new_window_button)

        window.add_widget(window.options_layout)

    def add_text_display(self, window):
        # print('-add_text_display')
        if not hasattr(window, "scroll_view") or not hasattr(window.scroll_view, "output_display"):
            try:
                window.display.remove_widget(window.scroll_view)
                del window.scroll_view
            except Exception as e:
                pass

            window.scroll_view = ScrollView(
                size_hint=(1, 1),
                bar_width=dp(10) * w_scale,
                scroll_type=['bars'],
                bar_color=(0.7, 0.7, 0.7, 1),
                bar_inactive_color=(0.5, 0.5, 0.5, 1),
                effect_cls='ScrollEffect',
            )
            window.output_display = TextInput(
                size_hint=(1, None),
                readonly=True,
                background_color=dark_blue2,
                foreground_color=(1, 1, 1, 1),
                multiline=True,
                cursor_blink=False,
                font_size=dp(13) * t_scale
            )
            window.output_display.bind(minimum_height=window.output_display.setter("height"))

            window.output_display.bind(minimum_height=self.update_textinput_height)
            Window.bind(size=self.update_textinput_height)
            self.update_textinput_height()
            
            window.scroll_view.bind(width=lambda s, w: setattr(window.output_display, 'width', w))
            window.scroll_view.add_widget(window.output_display)
            window.display.add_widget(window.scroll_view)
            window.display.add_widget(PaneDivider(size_hint_x=None, width=1))

    def create_connection2(self, host, user, remote_id):
        print('-create_connection2')
        key_path = os.path.expanduser(f"~/.ssh/node_{remote_id}")

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        client.connect(
            hostname=host,
            username=user,
            key_filename=key_path,
            look_for_keys=False,
            allow_agent=False,
            timeout=10,
        )
        return client
    
    def create_connection(self, host, user, password, window=None):
        print('-create_connection')
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname=host,
                username=user,
                password=password,
            )
        except:
            return None
        if window:
            window.client = client
        return client

    def ssh(self, remote, cmd): # not used
        host = remote["local_address"]
        user = remote["username"]
        remote_id = remote["remote_id"]
        result = subprocess.run(
            # ["ssh", f"{user}@{host}", cmd],
            ["ssh",
            "-i", os.path.expanduser(f"~/.ssh/{remote_id}"),
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=no",
            f"{user}@{host}",
            cmd
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout.strip()

    def checkin(self, window): # not used
        print('-checkin',window.ssh_host)
        import time
        from concurrent.futures import ThreadPoolExecutor

        def check_node(node):
            host = node["remote_data"]["local_address"]
            user = node["remote_data"]["username"]
            nickname = node["remote_data"]["nickname"]

            redis_ping = self.ssh(
                node["remote_data"],
                "redis-cli ping"
            ).strip()

            worker_count = self.ssh(
                node["remote_data"],
                "ps aux | grep rqworker | grep -v grep | wc -l"
            ).strip()

            queue_size = self.ssh(
                node["remote_data"],
                "redis-cli llen rq:queue:high"
            ).strip()

            try:
                return f'\n"timestamp": {dt_to_string(now_utc())}, \
                \n"uptime": {self.ssh(node["remote_data"], "uptime -p")}, \
                \n"load": {self.ssh(node["remote_data"], "cat /proc/loadavg")}, \
                \n"disk": {self.ssh(node["remote_data"], "df -h / | tail -1")}, \
                \n"memory": {self.ssh(node["remote_data"], "free -m | grep Mem")}, \
                \n"redis": {redis_ping}, \
                \n"rq_workers": {worker_count}, \
                \n"rq_queue_depth": {queue_size}, \
                \n"status": "ok", \
                \n----------'
                
            except Exception as e:
                return f'"node": {nickname}, \
                \n"host": {host}, \
                \n"timestamp": {dt_to_string(now_utc())}, \
                \n"status": "error", \
                \n"error": {str(e)}, \
                \n----------'
                
        nodes = [{'host': window.ssh_host, 'user':window.ssh_user, 'name':window.remote_data['nickname'], 'remote_data':window.remote_data}]
        for n in nodes:
            r = check_node(n)
            Clock.schedule_once(lambda dt, line=r: self.update_buffer(window, line))
            time.sleep(10)

    def monitor_status_start(self, window):
        print('-monitor_status_start')
        window.commands_button.text = 'Status'
        self.add_text_display(window)

        if not window.client:
            Clock.schedule_once(lambda dt, line='connecting...\n': self.replace_output(window, line))
            window.client = paramiko.SSHClient()
            window.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                window.client.connect(
                    hostname=window.ssh_host,
                    username=window.ssh_user,
                    password=window.ssh_password,
                )
                Clock.schedule_once(lambda dt, line='connected\n': self.replace_output(window, line))
            except Exception as e:
                Clock.schedule_once(lambda dt, line=f"SSH connection failed: {e}\n": self.replace_output(window, line))
                print('failed window connection 1')
                return
            
        
        try:
            window.display.remove_widget(window.scroll_view)
            del window.scroll_view
            window.scroll_view.remove_widget(window.output_display)
            del window.output_display
        except Exception as e:
            pass

        def get_default_data(cmd):
            # print('get_default_data',cmd)
            stdin, stdout, stderr = window.client.exec_command(cmd)
            return stdout.read().decode().strip()

        if window.os_type == 'mac':
            cmd = "route get default | awk '/interface:/ {print $2}'"
        else:
            cmd = "ip route | grep default | awk '{print $5}'"
        try:
            window.network_interface = get_default_data(cmd)
        except:

            Clock.schedule_once(lambda dt, line='connecting...\n': self.replace_output(window, line))
            print('start connection')
            window.client = paramiko.SSHClient()
            window.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                window.client.connect(
                    hostname=window.ssh_host,
                    username=window.ssh_user,
                    password=window.ssh_password,
                )
                Clock.schedule_once(lambda dt, line='connected\n': self.replace_output(window, line))
                window.network_interface = get_default_data(cmd)
            except Exception as e:
                Clock.schedule_once(lambda dt, line=f"SSH connection failed: {e}\n": self.replace_output(window, line))
                print('failed window connection2')
                return

        if window.os_type == 'mac':
            cmd = "sysctl -n hw.ncpu | tr -d ' \n'"
        else:
            cmd = "nproc"
        window.cpu_cores = int(get_default_data(cmd))
        window.scroll_view = ScrollView(size_hint=(1, 1))
        window.status_cluster = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
        )
        window.status_cluster.bind(
            minimum_height=window.status_cluster.setter("height")
        )
        window.scroll_view.add_widget(window.status_cluster)
        window.scroll_view.bind(
            width=lambda *_: setattr(window.status_cluster, "width", window.scroll_view.width)
        )
        window.status_monitor_display1 = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            spacing=dp(6),
            padding=dp(6),
        )
        window.status_monitor_display1.bind(
            minimum_height=window.status_monitor_display1.setter("height")
        )
        window.status_cluster.pos_hint = {"x": 0, "top": 1}
        window.status_cluster.add_widget(window.status_monitor_display1)

        index = window.children.index(window.options_layout)
        window.display.add_widget(window.scroll_view, index=index + 1)
        window.display.add_widget(PaneDivider(size_hint_x=None, width=1))

        Clock.schedule_once(lambda dt, line='': self.add_monitor_widgets(window))

        window.running_channel = True
        window.running_thread = threading.Thread(target=self.run_status_monitor, args=(window,))
        window.running_thread.daemon = True
        window.running_thread.start()
    
    def add_monitor_widgets(self, window):
        history_len = 140
        from templates import Sparkline, TimeSparkline
        def fmt_rate(bps, dec=1):
            try:
                bps = float(bps)
            except (TypeError, ValueError):
                return "—"

            for unit in ("B/s", "KB/s", "MB/s", "GB/s"):
                if bps < 1024:
                    return f"{bps:.{dec}f} {unit}"
                bps /= 1024
            return f"{bps:.{dec}f} TB/s"
        
        def build_status_row2():
            container = GridLayout(
                cols=3,
                size_hint_y=None,
                row_default_height=dp(24) * w_scale,
                spacing=dp(6) * w_scale,
                padding=[dp(6) * w_scale, dp(0) * w_scale, dp(6) * w_scale, dp(0) * w_scale],
            )
            container.bind(minimum_height=container.setter("height"))

            # disk history (bytes since boot)
            container._disk_hist = {
                "last": None,
                "last_ts": None,
            }

            def make_col(label_text="—"):
                col = BoxLayout(
                    orientation="vertical",
                    size_hint_y=None,
                    height=dp(10) * w_scale,
                )
                lbl = Label(
                    text=label_text,
                    halign="left",
                    valign="middle",
                    size_hint_y=None,
                    font_size=dp(14) * t_scale
                )
                lbl.bind(size=lbl.setter("text_size"))
                col.add_widget(lbl)
                col.label = lbl
                return col

            container.uptime_col = make_col("Uptime: —")
            container.temp_col = make_col("Temp: —")
            container.procs_col = make_col("Procs: —")

            for col in (container.uptime_col, container.temp_col, container.procs_col):
                container.add_widget(col)

            def adjust_cols(*_):
                width = container.width
                col_width = dp(120) * w_scale
                container.cols = max(1, int(width / col_width))

            container.bind(width=adjust_cols)

            def update(system_info):
                temp_raw = system_info.get("temp_raw")
                if temp_raw is not None:
                    temp_c = float(temp_raw) / 1000
                    container.temp_col.label.text = f"Temp: {temp_c:.1f}°C"
                    if temp_c >= 95:
                        container.temp_col.label.color = (1, 0.2, 0.2, 1)   # red
                    elif temp_c >= 85:
                        container.temp_col.label.color = (1, 1, 0.2, 1)     # yellow
                    else:
                        container.temp_col.label.color = (1, 1, 1, 1)
                else:
                    container.temp_col.label.text = "Temp: —"
                    container.temp_col.label.color = (1, 1, 1, 1)

                uptime_days = system_info.get("uptime")
                if uptime_days is not None:
                    if uptime_days < 1:
                        container.uptime_col.label.text = f"Uptime: {uptime_days * 24:.1f}h"
                    else:
                        container.uptime_col.label.text = f"Uptime: {uptime_days:.1f}d"
                else:
                    container.uptime_col.label.text = "Uptime: —"

                procs = system_info.get("num_processes")
                container.procs_col.label.text = f"Procs: {procs}" if procs is not None else "Procs: —"

            container.update = update
            return container

        def build_time_sparkline(title="", history_len=history_len):
            row = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(32) * w_scale,
                spacing=dp(8) * w_scale,
                padding=[dp(0) * w_scale, dp(0) * w_scale, dp(0) * w_scale, dp(10) * w_scale],
            )
            row.history = deque(maxlen=history_len)
            row.label = Label(
                text=title,
                size_hint_x=None,
                width=dp(40) * t_scale,
                font_size=dp(14) * t_scale,
                halign="left",
                valign="middle",
            )
            row.label.bind(size=row.label.setter("text_size"))
            row.graph = TimeSparkline(
                row.history,
                size_hint_x=1,
                height=dp(12) * w_scale,
            )
            row.timestamp_label = Label(
                text="",
                size_hint_x=None,
                width=dp(50) * t_scale,
                font_size=dp(14) * t_scale,
                halign="right",
                valign="middle",
            )
            row.timestamp_label.bind(size=row.timestamp_label.setter("text_size"))
            row.add_widget(row.label)
            row.add_widget(row.graph)
            row.add_widget(row.timestamp_label)

            def update(timestamp):
                """Append a new timestamp and redraw."""
                if timestamp is None:
                    return
                row.history.append(timestamp)
                # show relative time in seconds since first sample or "now"
                if row.history:
                    latest = row.history[-1]
                row.graph.redraw()

            row.update = update
            return row
        if not hasattr(window.status_monitor_display1, "time_row"):
            window.status_monitor_display1.time_row = build_time_sparkline()
            window.status_monitor_display1.add_widget(window.status_monitor_display1.time_row)

        def build_load_widget(cpu_cores, history_len=history_len):
            row = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(28) * w_scale,
                spacing=dp(8) * w_scale,
            )

            row.history = deque(maxlen=history_len)
            row.label = Label(
                text="Load",
                size_hint_x=None,
                font_size=dp(14) * t_scale,
                width=dp(40) * t_scale,
                halign="center",
                valign="middle",
            )
            row.label.bind(size=row.label.setter("text_size"))
            row.graph = Sparkline(row.history, color=(0.4, 0.8, 1, 1))
            row.graph.size_hint_x = 1
            row.values = Label(
                text="—",
                size_hint_x=None,
                font_size=dp(14) * t_scale,
                width=dp(50) * t_scale,
                halign="center",
                valign="middle",
            )
            row.values.bind(size=row.values.setter("text_size"))
            row.add_widget(row.label)
            row.add_widget(row.graph)
            row.add_widget(row.values)

            def update(load_1m, load_5m, load_15m):
                norm = load_1m / max(cpu_cores, 1)
                row.history.append(norm)
                if norm >= 1.2:
                    row.graph.color = (1, 0.2, 0.2, 1)
                elif norm >= 0.9:
                    row.graph.color = (1, 0.7, 0.2, 1)
                else:
                    row.graph.color = (0.4, 0.8, 1, 1)

                row.values.text = (f"{load_1m:.2f}")
                row.graph.redraw()

            row.update = update
            return row
        if not hasattr(window.status_monitor_display1, "load_widget"):
            window.status_monitor_display1.load_widget = build_load_widget(cpu_cores=window.cpu_cores)
            window.status_monitor_display1.add_widget(window.status_monitor_display1.load_widget)

        def build_network_sparkline(title="Net", history_len=history_len, color=(0.4, 0.8, 1, 1)):
            row = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(28) * w_scale,
                spacing=dp(8) * w_scale,
            )
            row.history = deque(maxlen=history_len)
            row.label = Label(
                text=title,
                size_hint_x=None,
                font_size=dp(14) * t_scale,
                width=dp(40) * t_scale,
                halign="center",
                valign="middle"
            )
            row.label.bind(size=row.label.setter("text_size"))
            row.graph = Sparkline(
                row.history,
                color=color,
            )
            row.graph.size_hint_x = 1
            row.pct = Label(
                text="—",
                size_hint_x=None,
                font_size=dp(14) * t_scale,
                width=dp(50) * t_scale,
                halign="center",
                valign="middle"
            )
            row.pct.bind(size=row.pct.setter("text_size"))
            row.add_widget(row.label)
            row.add_widget(row.graph)
            row.add_widget(row.pct)

            def update(value):
                row.history.append(value)
                row.pct.text = fmt_rate(value, dec=0)
                row.graph.redraw()

            row.update = update
            return row
        if not hasattr(window, "net_history"):
            window.net_history = {
                "in": [],
                "out": [],
                "last": None,
                "last_ts": None,
            }
        if not hasattr(window.status_monitor_display1, "net_in_row"):
            window.status_monitor_display1.net_in_row = build_network_sparkline(title="Net <", color=(0.7, 0.6, 0.9, 1))
            window.status_monitor_display1.add_widget(window.status_monitor_display1.net_in_row)
        if not hasattr(window.status_monitor_display1, "net_out_row"):
            window.status_monitor_display1.net_out_row = build_network_sparkline(title="Net >", color=(0.6, 0.8, 1, 1))
            window.status_monitor_display1.add_widget(window.status_monitor_display1.net_out_row)

        def build_sparkline(title="Metric", color=(1, 0.4, 0.2), history_len=history_len, is_percent=True, unit_fmt=lambda x: f"{x:.0f}"):
            row = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(28) * w_scale,
                spacing=dp(8) * w_scale,
            )
            row.history = deque(maxlen=history_len)
            row.label = Label(
                text=title,
                size_hint_x=None,
                font_size=dp(14) * t_scale,
                width=dp(40) * t_scale,
                halign="center",
                valign="middle",
            )
            row.label.bind(size=row.label.setter("text_size"))
            if is_percent:
                row.graph = Sparkline(
                    row.history,
                    color=color,
                    y_min=0,
                    y_max=100,
                )
            else:
                row.graph = Sparkline(
                    row.history,
                    color=color,
                )
            row.graph.size_hint_x = 1
            row.pct = Label(
                text="—",
                size_hint_x=None,
                font_size=dp(14) * t_scale,
                width=dp(50) * t_scale,
                halign="center",
                valign="middle",
            )
            row.pct.bind(size=row.pct.setter("text_size"))
            row.add_widget(row.label)
            row.add_widget(row.graph)
            row.add_widget(row.pct)

            def update(value):
                if value is None:
                    value = 0
                row.history.append(value)
                row.pct.text = unit_fmt(value)
                row.graph.redraw()

            row.update = update
            return row
        if not hasattr(window.status_monitor_display1, "cpu_row"):
            window.status_monitor_display1.cpu_row = build_sparkline(
                title="CPU",
                color=(1, 1, 0.2, 1),
                unit_fmt=lambda x: f"{float(x)}%"
            )
            window.status_monitor_display1.add_widget(window.status_monitor_display1.cpu_row)

        if not hasattr(window.status_monitor_display1, "mem_row"):
            window.status_monitor_display1.mem_row = build_sparkline(
                title="Mem",
                color=(0.4, 0.8, 1, 1),
                unit_fmt=lambda x: f"{float(x)}%"
            )
            window.status_monitor_display1.add_widget(window.status_monitor_display1.mem_row)

        if not hasattr(window.status_monitor_display1, "swap_row"):
            window.status_monitor_display1.swap_row = build_sparkline(
                title="Swap",
                color=(0.4, 0.8, 1, 1),
                unit_fmt=lambda x: f"{float(x)}%"
            )
            window.status_monitor_display1.add_widget(window.status_monitor_display1.swap_row)

        def build_disk_row():
            row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40) * w_scale, spacing=dp(12) * w_scale, padding=[dp(6) * w_scale, dp(24) * w_scale, dp(6) * w_scale, dp(24) * w_scale],)
            row.label = Label(text="Disk", size_hint_x=None, width=dp(40) * t_scale, font_size=dp(14) * t_scale, halign="center", valign="middle")
            row.bar = ProgressBar(max=100, value=0, size_hint_x=1)
            row.pct = Label(text="—%", size_hint_x=None, width=dp(50) * t_scale, font_size=dp(14) * t_scale, halign="center", valign="middle")
            row.pct.bind(size=row.pct.setter("text_size"))

            row.add_widget(row.label)
            row.add_widget(row.bar)
            row.add_widget(row.pct)

            def update(disk_percent):
                if disk_percent is None:
                    return
                disk_percent = float(disk_percent)
                row.bar.value = disk_percent
                row.pct.text = f"{disk_percent:.0f}%"

            row.update = update
            return row
        if not hasattr(window.status_monitor_display1, "disk_row"):
            window.status_monitor_display1.disk_row = build_disk_row()
            window.status_monitor_display1.add_widget(window.status_monitor_display1.disk_row)
        
        def build_status_row1():
            container = GridLayout(
                cols=4,
                size_hint_y=None,
                row_default_height=dp(20) * t_scale,
                spacing=dp(6) * t_scale,
                padding=[dp(6) * t_scale, dp(15) * t_scale, dp(6) * t_scale, dp(0) * t_scale],
            )
            container.bind(minimum_height=container.setter("height"))

            def make_col(label_text="—"):
                col = BoxLayout(
                    orientation="vertical",
                    size_hint_y=None,
                    height=dp(5) * w_scale,
                )
                lbl = Label(
                    text=label_text,
                    halign="left",
                    valign="middle",
                    size_hint_y=None,
                    font_size=dp(14) * t_scale
                )
                lbl.bind(size=lbl.setter("text_size"))
                col.add_widget(lbl)
                col.label = lbl
                return col

            container.node_name = make_col(f"{window.server}")
            container.last_poll_col = make_col("Last poll: —")
            container.last_poll_col.label.color = (0.6, 0.8, 1, 1)
            container.status_indicator = make_col("Status: —")
            container.temp_col = make_col("Temp: —")
            container.uptime_col = make_col("Uptime: —")

            for col in (container.last_poll_col, container.status_indicator, container.temp_col, container.uptime_col):
                container.add_widget(col)

            def adjust_cols(*_):
                width = container.width
                col_width = dp(120) * w_scale
                n_cols = max(1, int(width / col_width))
                container.cols = n_cols

            container.bind(width=adjust_cols)

            def update(system_info):
                # print('system_info:',system_info)
                dt = system_info.get("dt")
                if isinstance(dt, datetime.datetime):
                    container.last_poll_col.label.text = dt.strftime("%a/%d %H.%M.%SZ")
                else:
                    container.last_poll_col.label.text = "Last poll: —"

                status_indicator = system_info.get("status")
                if status_indicator is not None:
                    if status_indicator:
                        container.status_indicator.label.text = f"Status: OK"
                        container.status_indicator.label.color = (0.4, 1, 0.4)
                    else:
                        container.status_indicator.label.text = f"Status: ERROR"
                        container.status_indicator.label.color = (1, 0.2, 0.2, 1)
                else:
                    container.status_indicator.label.text = "Status: —"
                    container.status_indicator.label.color = (1, 1, 1, 1)

                temp_raw = system_info.get("temp_raw")
                if temp_raw is not None:
                    temp_c = float(temp_raw) / 1000
                    container.temp_col.label.text = f"Temp: {temp_c:.1f}°C"
                    if temp_c >= 55:
                        container.temp_col.label.color = (1, 0.2, 0.2, 1)   # red
                    elif temp_c >= 45:
                        container.temp_col.label.color = (1, 0.7, 0.2, 1)
                    else:
                        container.temp_col.label.color = (1, 1, 1, 1)
                else:
                    container.temp_col.label.text = "Temp: —"
                    container.temp_col.label.color = (1, 1, 1, 1)

                uptime_days = system_info.get("uptime")
                if uptime_days is not None:
                    if uptime_days < 1:
                        container.uptime_col.label.text = f"Uptime: {uptime_days * 24:.1f}h"
                    else:
                        container.uptime_col.label.text = f"Uptime: {uptime_days:.1f}d"
                else:
                    container.uptime_col.label.text = "Uptime: —"

            container.update = update
            return container
        if not hasattr(window.status_monitor_display1, "status_row"):
            window.status_monitor_display1.status_row = build_status_row1()
            window.status_monitor_display1.add_widget(window.status_monitor_display1.status_row)

        def build_workers_row(workers):
            container = GridLayout(
                cols=len(workers),
                size_hint_y=None,
                row_default_height=dp(24) * t_scale,
                spacing=dp(8) * t_scale,
                padding=[dp(6) * t_scale, dp(0) * t_scale, dp(6) * t_scale, dp(0) * t_scale],
            )
            container.bind(minimum_height=container.setter("height"))
            container.worker_cols = []
            for name in workers:
                col = BoxLayout(
                    orientation='vertical',
                    size_hint_y=None,
                    height=dp(50) * t_scale,
                    spacing=dp(2) * t_scale,
                    padding=[dp(6) * t_scale, dp(10) * t_scale, dp(6) * t_scale, dp(0) * t_scale],
                )
                col.name_label = Label(text=name, halign='center', valign='top', size_hint_y=None, font_size=dp(14) * t_scale)
                col.name_label.bind(texture_size=col.name_label.setter("size"))
                
                col.job_label = Label(text='—', halign='center', valign='top', size_hint_y=None, font_size=dp(14) * t_scale)
                col.job_label.bind(texture_size=col.job_label.setter("size"))
                
                col.args_label = Label(text='—', halign='center', valign='top', size_hint_y=None, font_size=dp(14) * t_scale)
                col.args_label.bind(texture_size=col.args_label.setter("size"))

                for widget in (col.name_label, col.job_label, col.args_label):
                    col.add_widget(widget)

                container.add_widget(col)
                container.worker_cols.append(col)

            def adjust_cols(*args):
                width = container.width
                col_width = dp(200) * t_scale
                n_cols = max(1, int(width / col_width))
                container.cols = n_cols

            container.bind(width=adjust_cols)

            return container
        if not hasattr(window.status_monitor_display1, "workers_container"):
            window.status_monitor_display1.workers_container = build_workers_row(['main', 'high', 'low', 'chat'])
            window.status_monitor_display1.add_widget(window.status_monitor_display1.workers_container)

    def run_status_monitor(self, window):
        print('-run_status_monitor')
        if not window.monitor_status:
            window.monitor_status = True
            first_run = True
            while window.running_thread and window.monitor_status:
                data = self.get_remote_system_info(window, first_run)
                first_run = False
                if data and hasattr(window, "status_monitor_display1"):
                    Clock.schedule_once(lambda dt: self.update_status_display(window, data))
                time.sleep(7)
            window.monitor_status = False

    def update_status_display(self, window, system_info):
        print('-update_status_display', window.remote_name)
        try:
            window.status_monitor_display1.status_row.update(system_info)
        except Exception as e:
            # print('err5745',str(e))
            pass
        try:
            window.status_monitor_display1.time_row.update(system_info.get("timestamp"))
        except Exception as e:
            # print('err5434',str(e))
            pass
        try:
            window.status_monitor_display1.load_widget.update(system_info["load_1m"], system_info["load_5m"], system_info["load_15m"])
        except Exception as e:
            # print('err3243',str(e))
            pass

        try:
            now = time.time()
            net_in = int(system_info["network_in"])
            net_out = int(system_info["network_out"])
            hist = window.net_history
            if hist["last"] is not None:
                dt = max(now - hist["last_ts"], 1)  # at least 1 second
                rate_in = (net_in - hist["last"]["in"]) / dt
                rate_out = (net_out - hist["last"]["out"]) / dt
            else:
                rate_in = rate_out = 0
            hist["last"] = {"in": net_in, "out": net_out}
            hist["last_ts"] = now
            window.status_monitor_display1.net_in_row.update(rate_in)
            window.status_monitor_display1.net_out_row.update(rate_out)
        except Exception as e:
            print('net monitor update err',str(e))

        try:
            usage = int(system_info["cpu"])
            if usage > 90:
                window.status_monitor_display1.cpu_row.graph.color = (1, 0.2, 0.2, 1)
            elif usage > 75:
                window.status_monitor_display1.cpu_row.graph.color = (1, 0.6, 0.2, 1)
            else:
                window.status_monitor_display1.cpu_row.graph.color = (1, 1, 0.2, 1)
            window.status_monitor_display1.cpu_row.update(system_info["cpu"])
        except Exception as e:
            print('status_monitor_display1.cpu_row err',str(e))

        try:
            usage = int(system_info["mem_percentage"])
            if usage > 90:
                window.status_monitor_display1.mem_row.graph.color = (1, 0.2, 0.2, 1)
            elif usage > 75:
                window.status_monitor_display1.mem_row.graph.color = (1, 0.6, 0.2, 1)
            else:
                window.status_monitor_display1.mem_row.graph.color = (0.2, 1, 0.2, 1)
            window.status_monitor_display1.mem_row.update(system_info["mem_percentage"])
        except Exception as e:
            print('status_monitor_display1.mem_row err',str(e))

        try:
            swap_percent = 0
            swap_total = system_info.get("swap_total", 0)
            swap_used = system_info.get("swap_used", 0)
            if swap_total > 0:
                swap_percent = round((swap_used / swap_total) * 100, 1)
            usage = int(swap_percent)
            if usage > 90:
                window.status_monitor_display1.swap_row.graph.color = (1, 0.2, 0.2, 1)
            elif usage > 75:
                window.status_monitor_display1.swap_row.graph.color = (1, 0.6, 0.2, 1)
            else:
                window.status_monitor_display1.swap_row.graph.color = (0.13, 0.55, 0.13, 1)
            window.status_monitor_display1.swap_row.update(swap_percent)
        except Exception as e:
            print('status_monitor_display1.swap_row err',str(e))
        try:
            window.status_monitor_display1.disk_row.update(system_info["disk_usage"])
        except Exception as e:
            print('status_monitor_display1.disk_row err',str(e))

        try:
            workers = {
                'main':{'current':{},'queued':0},
                'high':{'current':{},'queued':0},
                'low':{'current':{},'queued':0},
                'chat':{'current':{},'queued':0},
                # 'super':{'current':{},'queued':0}
                }
        
            workers = system_info['queue']
            for col in window.status_monitor_display1.workers_container.worker_cols:
                label_text = col.name_label.text.split(" ", 1)[0]
                data = workers.get(label_text, {})
                current = data.get('current',{})
                jobs = data.get('queued',0) + 1 if current else 0
                col.name_label.text = f"{label_text} ({jobs})"
                if current:
                    col.job_label.text = f"{current.get('func','—')}"
                    col.args_label.text = f"{current.get('args','-')}"
                else:
                    col.job_label.text = '-'
                    col.args_label.text = '-'
        except Exception as e:
            print('workers fail',str(e))

    def stop_monitor_status(self, window):
        # print('-stop_monitor_status')
        if hasattr(window, 'running_thread') and window.running_thread and window.running_thread.is_alive():
            # print('should stop here')
            window.running_thread.join(timeout=1)
        try:
            window.running_thread = None
            window.remove_widget(window.status_monitor_display1)
        except:
            pass

    def show_utc_time(self, window):
        if hasattr(window, "utc_layout"):
            return self.stop_utc_updates(window)
            
        window.utc_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(27) * w_scale, spacing=0, padding=0)
        window.utc_label = FlashingButton(text="UTC: --", size_hint_y=None, height=dp(27) * w_scale, font_size=dp(16) * t_scale)
        window.utc_layout.add_widget(window.utc_label)
        index = window.children.index(window.options_layout)
        window.add_widget(window.utc_layout, index=index+1)

        window.utc_thread = threading.Thread(target=self.utc_updater, args=(window,))
        window.utc_thread.daemon = True
        window.utc_thread.start()
    
    def utc_updater(self, window):
        while window.utc_thread:
            now_utc = datetime.datetime.now(pytz.utc)
            window.utc_label.text = f'UTC: {now_utc.strftime("%a %d, %H:%M:%S")}'
            seconds_remaining = 59 - now_utc.second
            microseconds_remaining = 1_000_000 - now_utc.microsecond
            time_to_sleep = seconds_remaining + microseconds_remaining / 1_000_000
            time.sleep(time_to_sleep)

    def stop_utc_updates(self, window):
        if hasattr(window, 'utc_thread') and window.utc_thread.is_alive():
            window.utc_thread.join(timeout=1)
            window.utc_thread = None
        if hasattr(window, "utc_layout") and window.utc_layout in window.children:
            window.remove_widget(window.utc_layout)
            del window.utc_layout

    def remove_window(self, window, restore_last=True):
        # print('-remove_window')
        row_num = window.row_num
        row = window.row
        self.stop_running_command(window)
        self.stop_system_info_updates(window)
        self.close_connection(window)
        window.row.remove_widget(window)
        if restore_last and not len(row.children):
            self.create_window(row_num)
    
    def remove_window_row(self, row):
        # print('-remove_row')
        for window in row.children:
            if window:
                row.remove_widget(window)
                Clock.schedule_once(lambda dt, line=window: self.stop_running_command(line))
                Clock.schedule_once(lambda dt, line=window: self.stop_system_info_updates(line))
                Clock.schedule_once(lambda dt, line=window: self.close_connection(line))
        self.display_rows.remove_widget(row)
        if not len(self.display_rows.children):
            self.create_new_row()

    def close_screen(self):
        print('-close_screen')
        rows = []
        windows = []
        import threading

        for i in range(1, self.window_row_count + 1):
            windows.append(getattr(self, f'row_{i}'))
            row = getattr(self, f'window_{i}')
            if row:
                rows.append(row)
        for n in range(1, self.window_count + 1):
            try:
                windows.append(getattr(self, f'window_{n}'))
            except Exception as e:
                print('close_screen err 1',str(e))

        for window in windows:
            if window:
                Clock.schedule_once(lambda dt, line=window: self.stop_running_command(line))
                self.close_thread = threading.Thread(target=self.close_connection, args=(window,))
                self.close_thread.daemon = True
                self.close_thread.start()
        for row in rows:
            if row:
                self.display_rows.remove_widget(row)
        self.remove_widget(self.display_rows)
    
    def select_server(self, window, server_name, open_cmds=True):
        print('-select_server',server_name)
        if not server_name:
            self.update_output(window, 'Select server before command\n')
            try:
                window.server_dropdown.open(window.server_button)
            except:
                window.server_dropdown.dismiss()
                window.server_dropdown.open(window.server_button)
        else:
            self.stop_running_command(window)
            self.stop_system_info_updates(window)
            self.close_connection(window)
            # print('self.servers',self.servers)
            remote = self.servers[server_name]

            window.ssh_host = remote.get('local_address',None)
            window.ssh_user = remote.get('username',None)
            window.ssh_password = remote.get('password',None)

            if window.ssh_user == 'self':
                import getpass
                username = getpass.getuser()
                window.ssh_user = username
                window.ssh_host = '127.0.0.1'

            window.os_type = remote.get('os_type',None)
            window.remote_name = remote.get('nickname','local')
            window.remote_data = remote
            print(f"Server selected: {server_name} ({window.ssh_host})")
            window.server_button.text = server_name
            window.server = server_name
            window.server_dropdown.dismiss()

            if open_cmds:
                window.command_dropdown.open(window.commands_button)

    def run_command_in_terminal(self, window, cmd_name): # not working
        print('-run_command_in_terminal',cmd_name) 
        
        import subprocess
        ssh_command = "ssh myuser@10.0.0.51"
        command = self.commands[cmd_name]
        # print('commandxx',command)
        if 'sudo' in command:
            command = f"echo {window.ssh_password} | {command}"

        # full_command = f"echo {window.ssh_password} | {ssh_command} 'bash -c \"{command}\"'"

        # # Properly escape the command for AppleScript
        # escaped_command = full_command.replace('"', '\\"')

        import re
        if platform == "linux":
            import shutil
            if shutil.which("gnome-terminal"):
                subprocess.run(["gnome-terminal", "--", "bash", "-c", f"{command}; exec bash"])
            elif shutil.which("gnome-terminal"):
                subprocess.run(["xfce4-terminal", "--hold", "--command", escaped_command])
                command = f"echo 'Hello, Linux!'; exec bash"  # Replace with your command
                subprocess.run(["xfce4-terminal", "--hold", "--command", command])

        elif platform == "macosx":
            full_command = f"echo {window.ssh_password} | {ssh_command} 'bash -c \"{command}\"'"
            escaped_command = full_command.replace('"', '\\"')
            script = f"""
            tell application "Terminal"
                do script "{escaped_command}"
                activate
            end tell
            """
            subprocess.run(["osascript", "-e", script])
  
        else:
            terminal = "gnome-terminal"

        # text = "hello world, welcome to the world"
        # pattern = re.compile(r"hello|world")
        # result = pattern.sub(lambda match: {"hello": "hi", "world": "Earth"}[match.group(0)], text)
        
        

            # if "sudo" in command:
            #             command = f"echo {self.ssh_password} | {command} -S"
            #             command = f"echo {window.ssh_password} | {command}"

        # def build(self):
        #     button = Button(text="Run Commands in Terminal")
        #     button.bind(on_press=self.open_terminal_and_run_commands)
        #     return button

    def perform_action(self, window=None, command='', menu='commands', args=[]):
        print('-perform_action',command,args)
        if menu == 'commands':
            window.command_dropdown.dismiss()
        elif menu == 'options':
            window.options_dropdown.dismiss()
        elif menu == 'servers':
            window.server_dropdown.dismiss()
        Clock.schedule_once(lambda dt: getattr(self, command)(*args), 0)

    def run_preset(self, window, cmd_name):
        print('-run_preset',cmd_name)
        try:
            err = ''
            self.stop_running_command(window)
            self.stop_system_info_updates(window)
            self.close_connection(window)
            if not cmd_name or cmd_name not in self.preset_commands:
                self.update_output(window, 'Command not found\n')
                window.command_dropdown.dismiss()
                window.command_dropdown.open(window.commands_button)
            else:
                # # remove current windows
                # rows = []
                # windows = []
                # for i in range(1, self.window_row_count + 1):
                #     windows.append(getattr(self, f'row_{i}'))
                #     row = getattr(self, f'window_{i}')
                #     if row:
                #         rows.append(row)
                # for row in rows:
                #     if row:
                #         self.remove_window_row(row)
                print('self.preset_commands',self.preset_commands)
                err = str(cmd_name)
                commands_data = self.preset_commands[cmd_name]
                err = str(commands_data)
                commands_data = ast.literal_eval(commands_data)
            if isinstance(commands_data, dict) or commands_data == 'all_remotes':
                if commands_data == 'all_remotes':
                    commands_data = {}
                    operatorData = get_operatorData()
                    if 'myNodes' in operatorData:
                        myNodes = operatorData['myNodes']

                        # if len(myNodes) > 3:
                        #     # create 2 rows
                        # if len(myNodes) > 5:
                        #     # create 3 rows

                        for node in myNodes:
                            if myNodes[node].get('nodeData', None):
                                commands_data[myNodes[node]['location']] = ['Status']
                # print('commands_dict',commands_data)
                is_first = True
                remove_window = False
                remove_window2 = False
                for remote_name, commands in commands_data.items():
                    print('--remote_name',remote_name,commands)
                    err = str(remote_name)
                    if isinstance(commands, list):
                        first_cmd = commands[0]
                    else:
                        first_cmd = commands
                    if remove_window:
                        remove_window = False
                        self.remove_window(window, restore_last=False)
                    if is_first:
                        is_first = False
                        self.select_server(window, remote_name, open_cmds=False)
                        self.run_command(window, first_cmd)
                    elif remote_name == 'new_row':
                        window = self.create_new_row(creator_row=window.row, super_func=first_cmd)
                        remove_window = True
                    else:
                        print('else')
                        window = self.create_window(creator_window=window, super_func={'server_name':remote_name, 'command':command})
                    for command in commands:
                        print('command:',command)
                        err = str(command)
                        if command != first_cmd:
                            if remove_window2:
                                remove_window2 = False
                                self.remove_window(window, restore_last=False)
                            if command == 'new_row':
                                window = self.create_new_row(creator_row=window.row, super_func=command)
                                remove_window2 = True
                            else:
                                window = self.create_window(creator_window=window, super_func={'server_name':window.server, 'command':command})
            elif isinstance(commands_data, list):
                if not window.server:
                    self.update_output(window, 'Select server before command\n')
                    try:
                        window.server_dropdown.open(window.server_button)
                    except:
                        window.server_dropdown.dismiss()
                        window.server_dropdown.open(window.server_button)
                else:
                    commands = commands_data
                    err = str(commands)
                    first_cmd = commands[0]
                    self.run_command(window, first_cmd)
                    for command in reversed(commands):
                        err = str(command)
                        if command != first_cmd:
                            self.create_window(creator_window=window, super_func={'server_name':window.server, 'command':command})
        except Exception as e:
            print('preset err 1',str(e))
            self.add_text_display(window)
            Clock.schedule_once(lambda dt, line=f"{e} {err}": self.replace_output(window, line))


    def run_command(self, window, cmd_name):
        print('-run_command', cmd_name)
        if cmd_name.lower() == 'status':
            self.perform_action(window=window, command='monitor_status_start', menu=None, args=[window, ])
        else:
            self.add_text_display(window)
            if not window.server:
                self.update_output(window, 'Select server before command\n')
                try:
                    window.server_dropdown.open(window.server_button)
                except:
                    window.server_dropdown.dismiss()
                    window.server_dropdown.open(window.server_button)
            elif not cmd_name:
                if cmd_name:
                    self.update_output(window, f'Command not found "{cmd_name}"\n')
                else:
                    self.update_output(window, 'Command not found\n')
            else:
                if window.running_thread and window.running_thread.is_alive():
                    self.stop_running_command(window)
                if cmd_name in self.commands:
                    command = self.commands[cmd_name]
                else:
                    command = cmd_name
                window.commands_button.text = cmd_name.replace('self.','')
                window.command = cmd_name
                window.output_display.text += f"\n\nRunning command: {command.replace('self.','')}\n"
                window.scroll_view.scroll_y = 0

                if not window.client:
                    window.client = paramiko.SSHClient()
                    window.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    try:
                        window.client.connect(
                            hostname=window.ssh_host,
                            username=window.ssh_user,
                            password=window.ssh_password,
                        )
                    except Exception as e:
                        window.output_display.text += f"SSH connection failed: {e}\n"
                        return

                def execute_command(command=command):
                    print('-execute_command:',str(command))
                    if 'utils/' in command:
                        address = self.servers[window.server]['remote_address']
                        if 'http://' in address or 'https://' in address:
                            address = address.replace('http://','').replace('https://','')
                        request_link = 'http://' + address + command
                        Clock.schedule_once(lambda dt, line=request_link: self.update_output(window, line))
                        while window.running_thread:
                            r = requests.get(request_link, timeout=3)
                            if r and r.status_code == 200:
                                json_data = r.json()
                                if 'message' in json_data:
                                    Clock.schedule_once(lambda dt, line=json_data['message']: self.replace_output(window, line))
                                time.sleep(3600)
                            else:
                                time.sleep(120)
                    elif 'self.' in command:
                        while window.running_thread:
                            getattr(self, command.replace('self.',''))(window)
                    else:
                        try:
                            if "sudo" in command:
                                command = f"echo {window.ssh_password} | {command}"

                            stdin, stdout, stderr = window.client.exec_command(command)
                            window.running_channel = stdout.channel
                            for line in iter(stdout.readline, ""):
                                Clock.schedule_once(lambda dt, line=line: self.update_buffer(window, line))
                            for line in iter(stderr.readline, ""):
                                line = f"ERROR: {line}"
                                Clock.schedule_once(lambda dt, line=line: self.update_buffer(window, line))
                        except Exception as e:
                            line = f"Command execution failed: {e}\n"
                            Clock.schedule_once(lambda dt, line=line: self.update_buffer(window, line))
                        finally:
                            window.running_channel = None

                window.running_thread = threading.Thread(target=execute_command)
                window.running_thread.daemon = True
                window.running_thread.start()

                window.running_printer = threading.Thread(target=self.printer, args=(window,))
                window.running_printer.daemon = True
                window.running_printer.start()

    def stop_running_command(self, window):
        print('-stop_running_command!',window)
        if hasattr(window, "running_channel") and window.running_channel:
            try:
                window.running_channel.close()
            except Exception as e:
                pass
            window.running_channel = None
            window.monitor_status = False
            try:
                window.commands_button.text = 'Command'
                window.command = ''
            except Exception as e:
                pass
            if hasattr(window, "running_printer"):
                try:
                    window.running_printer.join(timeout=1)
                    window.running_printer = None
                except Exception as e:
                    pass
                line = "Command stopped.\n"
                Clock.schedule_once(lambda dt, line=line: self.update_output(window, line))
        
        if hasattr(window, "running_thread") and window.running_thread and window.running_thread.is_alive():
            window.running_thread.join(timeout=1)
            window.running_thread = None

    def update_buffer(self, window, text):
        window.output_buffer += text

    def printer(self, window):
        while window.running_printer:
            # print('--printer:',window.output_buffer)
            if window.output_buffer:
                text = window.output_buffer
                Clock.schedule_once(lambda _: self.append_text(window, text))
                window.output_buffer = ''
            time.sleep(1.5)

    def replace_output(self, window, text):
        # print('-replace_output',text)
        window.output_display.text = str(text)
        if window.output_display.height <= window.scroll_view.height:
            window.scroll_view.scroll_y = 0
        else:
            at_bottom = window.scroll_view.scroll_y <= 0.05
            if at_bottom:
                window.scroll_view.scroll_y = 0

    def update_output(self, window, text):
        Clock.schedule_once(lambda _: self.append_text(window, text))

    def append_text(self, window, text):
        # print('-_append_text',text)
        window.output_display.text += text
        if self.max_lines > 0:
            window.output_display.text = window.output_display.text[-self.max_lines:]
            
        if window.output_display.height <= window.scroll_view.height:
            window.scroll_view.scroll_y = 0
        else:
            at_bottom = window.scroll_view.scroll_y <= 0.05
            if at_bottom:
                window.scroll_view.scroll_y = 0
            
    def stop_all_running_commands(self, window):
        print('-stop_all_running_commands')
        rows = []
        windows = []

        for i in range(1, self.window_row_count + 1):
            windows.append(getattr(self, f'row_{i}'))
            row = getattr(self, f'window_{i}')
            if row:
                rows.append(row)
        for n in range(1, self.window_count + 1):
            try:
                windows.append(getattr(self, f'window_{n}'))
            except Exception as e:
                print('stop_all_running_commands err 1',str(e))

        for window in windows:
            if window:
                Clock.schedule_once(lambda dt, line=window: self.stop_running_command(line))
                Clock.schedule_once(lambda dt, line=window: self.close_connection(line))

    def clear_all_outputs(self, window):
        print('-clear_all_outputs')
        rows = []
        windows = []

        for i in range(1, self.window_row_count + 1):
            windows.append(getattr(self, f'row_{i}'))
            row = getattr(self, f'window_{i}')
            if row:
                rows.append(row)
        for n in range(1, self.window_count + 1):
            try:
                windows.append(getattr(self, f'window_{n}'))
            except Exception as e:
                print('clear_all_outputs err 1',str(e))

        for window in windows:
            if window:
                try:
                    window.output_buffer = ''
                    window.output_display.text = ""
                except:
                    pass

    def scroll_to_bottom(self, window):
        window.scroll_view.scroll_y = 0
        
    def clear_output(self, window):
        window.output_buffer = ''
        window.output_display.text = ""

    def close_connection(self, window):
        print('-close_connection',window)
        if hasattr(window, 'client') and window.client:
            window.client.close()
            window.client = None
            window.output_display.text += "SSH connection closed.\n"
            try:
                window.ssh_host = None
                window.ssh_user = None
                window.ssh_password = None
                window.server_button.text = 'Server'
                window.server = None
            except:
                pass

    def redo_connection(self, window):
        print('-redo_connection')
        server_name = window.server
        cmd_name = window.command
        self.close_connection(window)
        time.sleep(1.5)
        self.select_server(window, server_name, open_cmds=False)
        time.sleep(1)
        self.run_command(window, cmd_name)

    def info_updater(self, window):
        if not window.info_updater:
            window.info_updater = True
            first_run = True
            # show_system_info()
            while window.system_info_thread or window.network_info_thread:
                data = self.get_remote_system_info(window, first_run)
                first_run = False
                if data and hasattr(window, "system_info_display1"):
                    Clock.schedule_once(lambda dt: self.update_system_info_label(window, data))
                elif not data and not hasattr(window, "failure_layout"):
                    Clock.schedule_once(lambda dt: self.display_failure(window, 15))
                elif data and hasattr(window, "failure_layout"):
                    Clock.schedule_once(lambda dt: self.remove_failure(window))
                time.sleep(15)
            window.info_updater = False

    def remove_menu(self, window, menu='command'):
        if menu == 'command':
            window.command_dropdown.dismiss()
        elif menu == 'options':
            window.options_dropdown.dismiss()
        elif menu == 'server':
            window.server_dropdown.dismiss()

    def workers_status(self):
        workers = {
            'main':{'current':{},'queued':0},
            'high':{'current':{},'queued':0},
            'low':{'current':{},'queued':0},
            'chat':{'current':{},'queued':0},
            'super':{'current':{},'queued':0}
            }
        for queue_name in workers:
            queue = get_queue(queue_name)
            conn = queue.connection
            # running
            for w in Worker.all(conn):
                if queue_name in [q.name for q in w.queues]:
                    job = w.get_current_job()
                    if job:
                        data = {}
                        if '.' in job.func_name:
                            x = job.func_name.rfind('.')+1
                            data["func"] = job.func_name[x:]
                        else:
                            data["func"] = job.func_name
                        data["args"] = ''
                        for a in job.args:
                            if a:
                                try:
                                    data["args"] = a.id
                                    break
                                except:
                                    pass
                        if not data["args"]:
                            data["args"] = dt_to_string(job.started_at) if job.started_at else '-'
                        workers[queue_name]['current'] = data
                    break
            job_ids = queue.job_ids
            for job_id in job_ids:
                job = queue.fetch_job(job_id)
                if job:
                    workers[queue_name]['queued'] += 1
        return workers

    def get_remote_system_info(self, window, first_run=False):
        # print('-get_remote_system_info', window.remote_name)
        commands = {
            # "uptime": "uptime -p",
            "cpu_usage": "top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'",
            "disk_usage": "df -h / | awk 'NR==2 {print $5}' | tr -d '%'",
            "network_in": f"cat /proc/net/dev | grep {window.network_interface} | awk '{{print $2}}'",
            "network_out": f"cat /proc/net/dev | grep {window.network_interface} | awk '{{print $10}}'"
        }
        
        if not hasattr(window.client, "exec_command"):
            self.stop_monitor_status(window)
        system_info = {}
        try:
            from datetime import datetime

            def in_first_20_seconds():
                now = datetime.now()
                return now.minute == 0 and now.second < 20
 
            iface = window.network_interface
            if window.os_type == 'mac':
                if first_run or in_first_20_seconds():
                    uptime = f"$(($(date +%s) - $(sysctl -n kern.boottime | awk '{{print $4}}' | tr -d ,)))"
                    disk = f"$(df / | awk 'NR==2 {{print int($5)}}')"
                else:
                    uptime = f"''"
                    disk = f"''"
                # CPU_CORES=$(sysctl -n hw.ncpu | tr -d ' \n')

                # DISK_READ=$(iostat -d 2 1 | tail -n 1 | awk '{{print int($3*1024*1024)}}')
                # DISK_WRITE=$(iostat -d 2 1 | tail -n 1 | awk '{{print int($4*1024*1024)}}')
                cmd = f"""
                CPU=$(top -l 1 | grep "CPU usage" | awk '{{print $3 + $5}}');
                DISK={disk};
                PAGE_SIZE=$(sysctl -n hw.pagesize);
                FREE_PAGES=$(vm_stat | grep "Pages free" | awk '{{print $3}}' | tr -d '.')
                MEM_TOTAL=$(sysctl -n hw.memsize)
                MEM_USED=$((MEM_TOTAL - FREE_PAGES * PAGE_SIZE))
                SWAP_TOTAL=$(sysctl vm.swapusage | awk '{{for(i=1;i<=NF;i++){{if($i=="total"){{print int($(i+2)*1024*1024)}}}}}}');
                SWAP_USED=$(sysctl vm.swapusage | awk '{{for(i=1;i<=NF;i++){{if($i=="used"){{print int($(i+2)*1024*1024)}}}}}}');
                PROCS=$(ps -e | wc -l);
                # NET_IN=$(netstat -ib | awk -v iface="{iface}" '$1==iface && $7 ~ /^[0-9]+$/ {{in+=$7}} END{{print in+0}}')
                NET_IN=$(netstat -ib | awk -v iface="{iface}" 'BEGIN {{inbytes=0}} $1 == iface {{if($7 ~ /^[0-9]+$/) inbytes += $7}} END {{print inbytes}}')
                NET_OUT=$(netstat -ib | awk -v iface="{iface}" '$1==iface && $10 ~ /^[0-9]+$/ {{out+=$10}} END{{print out+0}}')
                UPTIME={uptime}
                LOADS=$(sysctl -n vm.loadavg | awk '{{print $2 "|" $3 "|" $4}}');
                TEMP=$(/opt/homebrew/bin/osx-cpu-temp | tr -d '°C')
                echo "$CPU|$DISK|$MEM_USED|$MEM_TOTAL|$SWAP_USED|$SWAP_TOTAL|$PROCS|$NET_IN|$NET_OUT|$UPTIME|$LOADS|$TEMP"
                """
                # brew install osx-cpu-temp
                # print('command:',cmd)
                try:
                    stdin, stdout, stderr = window.client.exec_command(cmd)
                    raw = stdout.read().decode().strip()
                    (
                        cpu, disk, mem_used, mem_total, swap_used, swap_total,
                        procs, net_in, net_out, uptime_sec,
                        load_1m, load_5m, load_15m,
                        temp_raw
                    ) = raw.split("|")
                    mem_used = int(mem_used) / 1024**3
                    mem_total = int(mem_total) / 1024**3
                except:
                    cpu, disk, mem_used, mem_total, swap_used, swap_total, procs, net_in, net_out, uptime_sec, load_1m, load_5m, load_15m, temp_raw = 0,0,0,0,0,0,0,0,0,0,0,0,0,0

            else:
                if first_run or in_first_20_seconds():
                    uptime = f"$(cut -d. -f1 /proc/uptime)"
                    disk = f"$(df / | awk 'NR==2 {{print int($5)}}')"
                else:
                    uptime = f"''"
                    disk = f"''"
                cmd = f"""
                CPU=$(top -bn1 | grep 'Cpu(s)' | awk '{{print $2 + $4}}');
                DISK={disk};
                MEM_USED=$(free -b | awk 'NR==2 {{print $3}}');
                MEM_TOTAL=$(free -b | awk 'NR==2 {{print $2}}');
                SWAP_USED=$(free -b | awk 'NR==3 {{print $3}}');
                SWAP_TOTAL=$(free -b | awk 'NR==3 {{print $2}}');
                PROCS=$(ps -e | wc -l);
                NET_IN=$(cat /proc/net/dev | grep {iface} | awk '{{print $2}}');
                NET_OUT=$(cat /proc/net/dev | grep {iface} | awk '{{print $10}}');
                UPTIME={uptime};
                LOADS=$(awk '{{print $1 "|" $2 "|" $3}}' /proc/loadavg);
                TEMP=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || echo "");
                echo "$CPU|$DISK|$MEM_USED|$MEM_TOTAL|$SWAP_USED|$SWAP_TOTAL|$PROCS|$NET_IN|$NET_OUT|$UPTIME|$LOADS|$TEMP"
                """
                try:
                    stdin, stdout, stderr = window.client.exec_command(cmd)
                    raw = stdout.read().decode().strip()
                    cpu, disk, mem_used, mem_total, swap_used, swap_total, procs, net_in, net_out, uptime_sec, load_1m, load_5m, load_15m, temp_raw = raw.split("|")
                except:
                    cpu, disk, mem_used, mem_total, swap_used, swap_total, procs, net_in, net_out, uptime_sec, load_1m, load_5m, load_15m, temp_raw = 0,0,0,0,0,0,0,0,0,0,0,0,0,0

            # print(cpu, disk, mem_used, mem_total, swap_used, swap_total, procs, net_in, net_out, uptime_sec, load_1m, load_5m, load_15m, disk_read, disk_write, temp_raw, cpu_cores)
            system_info['cpu'] = float(cpu) if cpu else 0
            system_info['disk_usage'] = disk
            system_info['mem_usage'] = mem_used
            system_info['mem_total'] = mem_total
            try:
                mem_percentage = round((int(mem_used) / int(mem_total)) * 100, 1)
            except Exception as e:
                print('mem_percentage err',str(e))
                mem_percentage = f'{mem_used}/{mem_total}'
            system_info['mem_percentage'] = mem_percentage

            try:
                system_info['swap_used'] = int(swap_used) if swap_used else None
                system_info['swap_total'] = int(swap_total) if swap_total else None
            except:
                system_info['swap_used'] = swap_used if swap_used else None
                system_info['swap_total'] = swap_total if swap_total else None

            system_info['num_processes'] = procs.strip() if procs else 0
            system_info['network_in'] = net_in if net_in else 0
            system_info['network_out'] = net_out if net_out else 0
            try:
                uptime_days = round(int(uptime_sec) / 86400, 1)
            except Exception as e:
                print('uptime_days err',str(e))
                uptime_days = str(uptime_sec)
            system_info['uptime'] = uptime_days
            try:
                system_info['load_1m'] = float(load_1m)
                system_info['load_5m'] = float(load_5m)
                system_info['load_15m'] = float(load_15m)
            except:
                system_info['load_1m'] = 0
                system_info['load_5m'] = 0
                system_info['load_15m'] = 0

            # print('disk_read',disk_read,'disk_write',disk_write)
            # system_info['disk_read'] = int(disk_read) if disk_read else None
            # system_info['disk_write'] = int(disk_write) if disk_write else None
            # print('temp_raw',temp_raw,'cpu_cores',cpu_cores)
            system_info['temp_raw'] = temp_raw if temp_raw else None
            # system_info['cpu_cores'] = int(cpu_cores) if cpu_cores else None
            system_info['dt'] = now_utc()
            system_info['timestamp'] = time.time()
            # print('system_info:',system_info)

            cmd = (
                f"curl -s http://127.0.0.1:9909/utils/workers_status"
            )
            try:
                stdin, stdout, stderr = window.client.exec_command(cmd)
                raw = stdout.read().decode().strip()
                running_jobs = json.loads(raw)
                # print("Running jobs:", running_jobs)
                system_info['queue'] = running_jobs
                system_info['status'] = True
            except Exception as e:
                print('sys info workers err 2',str(e))
                workers = {
                    'main':{'current':{},'queued':0},
                    'high':{'current':{},'queued':0},
                    'low':{'current':{},'queued':0},
                    'chat':{'current':{},'queued':0},
                    'super':{'current':{},'queued':0}
                    }
                system_info['queue'] = workers
                system_info['status'] = False
            
            def get_mem_percentage():
                stdin, stdout, stderr = window.client.exec_command("free -b")  # Fetch memory info in bytes
                output = stdout.read().decode()
                lines = output.splitlines()
                mem_info = lines[1].split()
                total_mem = int(mem_info[1])  # Total memory in bytes
                used_mem = int(mem_info[2])   # Used memory in bytes
                mem_percentage = (used_mem / total_mem) * 100
                return round(mem_percentage, 1)  # Round to two decimal places

            def get_uptime_days():
                print('-getting uptime')
                stdin, stdout, stderr = window.client.exec_command("cat /proc/uptime")
                uptime_seconds = float(stdout.read().decode().split()[0])  # First value is uptime in seconds
                uptime_days = uptime_seconds / 86400  # Convert seconds to days
                window.uptime_fetched = datetime.datetime.now()
                return round(uptime_days, 1)  # Round to two decimal places
            
            return system_info

        except Exception as e:
            print(f"Failed to get system info: {e}")
            if 'SSH session not active' in str(e):
                self.stop_monitor_status(window)
        return False

    def show_system_info(self, window):
        # print('-show_system_info')
        import psutil
        try:
            if window.system_info_thread:
                stdin, stdout, stderr = window.client.exec_command("vmstat 1 2 | tail -1")
                output = stdout.read().decode().strip()
                if output:
                    stats = output.split()
                    cpu_usage = 100 - int(stats[14]) 
                    stdin, stdout, stderr = window.client.exec_command("free -m")
                    memory_info = psutil.virtual_memory()
                    total_mem = memory_info.total / (1024 ** 3)  # Convert to GB
                    used_mem = (memory_info.total - memory_info.available) / (1024 ** 3)  # Convert to GB
                    used_mem_percent = round((used_mem / total_mem) * 100, 1)
                    process_count = len(psutil.pids())
                    uptime_seconds = time.time() - psutil.boot_time()
                    uptime_days = uptime_seconds / (24 * 3600)

                    sys_text = f"cpu:{cpu_usage}%, mem:{used_mem_percent}%, prcs:{process_count}, days:{round(uptime_days, 2)}"
                    Clock.schedule_once(lambda dt: self.update_system_info_label(window, sys_text))
            if window.network_info_thread:
                # print('update network_info_thread')
                disk_usage = psutil.disk_usage('/')
                disk_percent = disk_usage.percent
                net_io = psutil.net_io_counters()
                bytes_sent = int(net_io.bytes_sent / (1024 ** 2))  # Sent data in MB
                bytes_recv = int(net_io.bytes_recv / (1024 ** 2))  # Received data in MB
                
                net_text = f"disk:{disk_percent}%, mbs in:{bytes_recv}, out:{bytes_sent}"
                Clock.schedule_once(lambda dt: self.update_network_info_label(window, net_text))

        except Exception as e:
            try:
                info_text = f"Failed to fetch system info: {e}"
                Clock.schedule_once(lambda dt: self.update_system_info_label(window, info_text))
            except:
                pass
            try:
                info_text = f"Failed to fetch system info: {e}"
                Clock.schedule_once(lambda dt: self.update_network_info_label(window, info_text))
            except:
                pass

    def update_system_info_label(self, window, system_info):
        # print('-update_system_info_label')
        if system_info:
            sys_text1 = f"{system_info['dt'].strftime('%a/%d %H.%M.%SZ')}\ncpu: {system_info['cpu']}%\nin: {round(int(system_info['network_in'])/(1024 ** 3),2)}GBs\nhigh queue: {system_info['high_queue']}"
            sys_text2 = f"up: {system_info['uptime']} days\nmem: {system_info['mem_percentage']}%\nout: {round(int(system_info['network_out'])/(1024 ** 3),2)}GBs\nmain queue: {system_info['main_queue']}"
            sys_text3 = f"\ndisk: {system_info['disk_usage']}\nprcs: {system_info['num_processes']}\nlow queue: {system_info['low_queue']}"
            
            window.system_info_display1.text = sys_text1
            window.system_info_display2.text = sys_text2
            window.system_info_display3.text = sys_text3

    def update_network_info_label(self, window, info_text):
        # print('-update_network_info_label',info_text)
        window.network_info_label.text = info_text

    def display_failure(self, window, t=None):
        try:
            window.failure_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(27) * w_scale, spacing=0, padding=0)
            window.failure_label = FlashingButton(text=f"unresponsive {datetime.datetime.now().strftime('%a %H:%M:%S')}", color=(1, 0, 0, 1), size_hint_y=None, height=dp(27) * w_scale, font_size=dp(16) * t_scale)
            window.failure_layout.add_widget(window.failure_label)
            window.add_widget(window.failure_layout, index=1)
        except Exception as e:
            print('display_failure fail',str(e))

    def remove_failure(self, window, t=None):
        if hasattr(window, "failure_layout") and window.failure_layout in window.children:
            window.remove_widget(window.failure_layout)
            del window.failure_layout

    def start_system_info_updates(self, window):
        if hasattr(window, "info_cluster"):
            return self.stop_system_info_updates(window)
            
        if not window.client:
            window.client = paramiko.SSHClient()
            window.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                window.client.connect(
                    hostname=window.ssh_host,
                    username=window.ssh_user,
                    password=window.ssh_password,
                )
            except Exception as e:
                window.output_display.text += f"SSH connection failed: {e}\n"
                return
        def get_default_interface():
            stdin, stdout, stderr = window.client.exec_command("ip route | grep default | awk '{print $5}'")
            return stdout.read().decode().strip()
        window.network_interface = get_default_interface()
        window.info_cluster = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None),
        )

        def create_info_display():
            return TextInput(
                size_hint=(1, None),
                readonly=True,
                background_color=dark_blue2,
                foreground_color=(1, 1, 1, 1),
                multiline=True,
                cursor_blink=False,
                font_size=dp(13) * t_scale,
                padding=[0,0,0,0],
            )

        window.system_info_display1 = create_info_display()
        window.system_info_display2 = create_info_display()
        window.system_info_display3 = create_info_display()
        window.system_info_display1.bind(
            minimum_height=lambda instance, h: setattr(window.info_cluster, 'height', h)
        )

        # Make all children heights equal to cluster height
        def update_children_height(instance, height):
            for child in window.info_cluster.children:
                child.height = height

        window.info_cluster.bind(height=update_children_height)
        window.info_cluster.add_widget(window.system_info_display1)
        window.info_cluster.add_widget(window.system_info_display2)
        window.info_cluster.add_widget(window.system_info_display3)
        index = window.children.index(window.options_layout)
        window.add_widget(window.info_cluster, index=index+1)

        window.system_info_thread = threading.Thread(target=self.info_updater, args=(window,))
        window.system_info_thread.daemon = True
        window.system_info_thread.start()

    def stop_system_info_updates(self, window):
        if hasattr(window, 'system_info_thread') and window.system_info_thread and window.system_info_thread.is_alive():
            window.system_info_thread.join(timeout=1)
            window.system_info_thread = None
        if hasattr(window, "info_cluster") and window.info_cluster in window.children:
            window.remove_widget(window.info_cluster)
            del window.info_cluster
        if hasattr(window, "failure_layout") and window.failure_layout in window.children:
            window.remove_widget(window.failure_layout)
            del window.failure_layout
        self.stop_network_info_updates(window)
        if hasattr(window, "info_updater") and window.info_updater:
            if not window.system_info_thread and not window.network_info_thread:
                window.info_updater = False

    def start_network_info_updates(self, window):
        if hasattr(window, "network_info_layout"):
            return self.stop_network_info_updates(window)
            
        window.network_info_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(27) * w_scale, spacing=0, padding=0)
        window.network_info_label = FlashingButton(text="net info: --", size_hint_y=None, height=dp(27) * w_scale, font_size=dp(16) * t_scale)
        window.network_info_layout.add_widget(window.network_info_label)
        index = window.children.index(window.options_layout)
        window.add_widget(window.network_info_layout, index=index+1)

        window.network_info_thread = threading.Thread(target=self.info_updater, args=(window,))
        window.network_info_thread.daemon = True
        window.network_info_thread.start()

    def stop_network_info_updates(self, window):
        print('-stop_network_info_updates')
        if hasattr(window, 'network_info_thread') and window.network_info_thread and window.network_info_thread.is_alive():
            window.network_info_thread.join(timeout=1)
            window.network_info_thread = None
        if hasattr(window, "network_info_layout") and window.network_info_layout in window.children:
            window.remove_widget(window.network_info_layout)
            del window.network_info_layout
            window.network_info_thread = None

    def load_servers(self):
        print('-load_servers')
        try:
            operatorData = get_operatorData()
            self.servers = {}
            if 'myRemotes' in operatorData:
                for nickname, remote_data in operatorData['myRemotes'].items():
                    self.servers[nickname] = remote_data

            self.commands = operatorData.get('monitor_commands', self.default_commands)
            self.preset_commands = operatorData.get('monitor_preset_commands', self.default_presets)
            w_scale = operatorData.get('magnification', 0)
            t_scale = operatorData.get('font_adjustment', 0)
            self.max_lines = operatorData.get('max_lines', 15000)
        except:
            self.servers = {}
            self.commands = self.default_commands
            self.preset_commands = self.default_presets
            w_scale = 0
            t_scale = 0
            self.max_lines = 15000

    def save_data(self):
        print('-save_data:',self.t_scale,self.w_scale)
        operatorData = get_operatorData()
        operatorData['monitor_commands'] = self.commands
        operatorData['monitor_preset_commands'] = self.preset_commands
        operatorData['magnification'] = self.w_scale
        operatorData['font_adjustment'] = self.t_scale
        operatorData['max_lines'] = self.max_lines
        write_operatorData(operatorData)

    def update_rect(self, *args):
        self.rect.size = self.size
        self.rect.pos = self.pos
    
    def update_textinput_height(self, *args):
        try:
            self.text_input.height = max(
                self.text_input.minimum_height,
                Window.height
            )
        except:
            pass

class ChainsScreen(BoxLayout):
    def __init__(self, parent=None, option='regions', **kwargs):
        super(ChainsScreen, self).__init__(**kwargs)
        print('-ChainsScreen',option)
        self.parent_screen = parent
        self.option = option.lower()

    def activate_display(self):
        print('ChainsScreen activate_display',self.option)
        self.superuser = False
        if self.option == 'regions':
            title = 'Supported Plugins and Regions'
            url = 'get_chain_data'
            self.fetch_chain_data()
        if self.option == 'plugins':
            title = 'Supported Plugins and Regions'
            # url = 'get_plugin_data'
            url = 'get_chain_data'
            self.fetch_chain_data()
            # self.fetch_plugin_data()

    def fetch_plugin_data(self):
        print(f'-fetch_plugin_data {self.option} data')
        try:
            self.operatorData = get_operatorData()
            if verify_super_status(operatorData=self.operatorData):
                self.superuser = True
                self.title = Label(text='Plugins', size_hint_y=None, height=dp(30), halign='center')
                self.add_widget(self.title)
                self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True, scroll_type=['bars', 'content'],bar_width=17, bar_color=(1, 1, 1, 1), bar_inactive_color=(1, 1, 1, .3))
                self.content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=5)
                self.content.bind(minimum_height=self.content.setter("height"))
                self.content.add_widget(Divider(padding=0))

                self.scroll_view.add_widget(self.content)
                self.add_widget(self.scroll_view)
                
                self.current_node = None
                if 'selected_node' in self.operatorData and self.operatorData['selected_node']:
                    self.current_node = self.operatorData['myNodes'][self.operatorData['selected_node']]

                nodes = get_node_list(operatorData=self.operatorData)
                received_data = False
                for nodeId, ip in nodes.items():
                    print('ip',ip)
                    if ip:
                        try:
                            r = connect_to_node(ip, f'network/get_plugin_data', operatorData=self.operatorData, get=True, timeout=4)
                            if r.status_code == 200:
                                received_data = True
                                received_json = r.json()
                                print('received_json',received_json)
                                if self.operatorData['sonet'] != json.loads(received_json['sonet']):
                                    self.operatorData['sonet'] = json.loads(received_json['sonet'])
                                    write_operatorData(self.operatorData)
                                self.plugin_data = json.loads(received_json['plugins'])
                                try:
                                    for plugin in self.plugin_data:
                                        # print('\nplugin',plugin)
                                        for key, value in plugin.items():
                                            # print('key',key,'value',value)
                                            self.content.add_widget(FieldRow(key, value, editable=False, superuser=False))
                                        self.content.add_widget(FieldRow('Actions', [{'title':"edit",'action':partial(self.edit_plugin, plugin['id'])}], parent=self, is_button_list=True, editable=False))
                                        self.content.add_widget(FieldRow('', '', editable=False, superuser=False))
                                    break

                                except Exception as e:
                                    print('pluginfetch err 1',str(e))
                                    break
                        except Exception as e:
                            print('pluginfetch err 2', str(e))
                            pass
                        
        except Exception as e:
            print('pluginfetch err 3',str(e))
            pass

    def edit_plugin(self, iden=None, instance=None):
        print('-edit plugin:',iden)

        self.scroll_view.remove_widget(self.content)
        self.remove_widget(self.scroll_view)
        del self.content
        del self.scroll_view
        self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True, scroll_type=['bars', 'content'],bar_width=17, bar_color=(1, 1, 1, 1), bar_inactive_color=(1, 1, 1, .3))
        self.content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=5)
        self.content.bind(minimum_height=self.content.setter("height"))
        self.content.add_widget(Divider(padding=0))

        self.scroll_view.add_widget(self.content)
        self.add_widget(self.scroll_view)
        
        plugin = None
        for p in self.plugin_data:
            if p['id'] == iden:
                plugin = p
                break

        if plugin:
            # check plugin.User_obj matches self user.id
            mutable_fields = ['model_prefixes','Title','AbbrTitle','Subtitle','Description','user_facing']

            for key, value in plugin.items():
                editable = False
                if key in mutable_fields:
                    editable = True
                self.content.add_widget(FieldRow(key, value, editable=editable, superuser=False))

            button_text = 'Save'
            self.save_button = Button(text=button_text, size_hint=(1, None), height=dp(30))
            self.save_button.bind(on_press=self.save_data)
            self.add_widget(self.save_button)

    def fetch_chain_data(self):
        print(f'-fetch_chain_data {self.option} data')
        try:
            self.title = Label(text='Supported Plugins and Regions', size_hint_y=None, height=dp(30), halign='center')
            self.add_widget(self.title)
            self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True, scroll_type=['bars', 'content'],bar_width=17, bar_color=(1, 1, 1, 1), bar_inactive_color=(1, 1, 1, .3))
            self.content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=5)
            self.content.bind(minimum_height=self.content.setter("height"))
            self.content.add_widget(Divider(padding=0))

            self.operatorData = get_operatorData()
            self.current_node = None
            if 'selected_node' in self.operatorData and self.operatorData['selected_node']:
                self.current_node = self.operatorData['myNodes'][self.operatorData['selected_node']]

            nodes = get_node_list(operatorData=self.operatorData)
            received_data = False
            self.mandatoryChains = []
            specialChains = []
            regionChains = []
            for nodeId, ip in nodes.items():
                print('ip',ip)
                if ip:
                    try:
                        r = connect_to_node(ip, f'network/get_chain_data', operatorData=self.operatorData, get=True, timeout=4)
                        if r.status_code == 200:
                            received_data = True
                            received_json = r.json()
                            print('received_json',received_json)
                            if self.operatorData['sonet'] != json.loads(received_json['sonet']):
                                self.operatorData['sonet'] = json.loads(received_json['sonet'])
                                write_operatorData(self.operatorData)

                            self.plugin_data = json.loads(received_json['plugins'])
                            regionChains = json.loads(received_json['regionChains'])
                            print('regionChains',regionChains)
                            specialChains = json.loads(received_json['specialChains'])
                            self.mandatoryChains = json.loads(received_json['mandatoryChains'])
                            chainData = {'regionChains':regionChains,'specialChains':specialChains,'mandatoryChains':self.mandatoryChains}
                            if self.current_node:
                                if 'chainData' not in self.current_node['meta']:
                                    self.current_node['meta']['chainData'] = {}
                                if 'choices' not in self.current_node['meta']['chainData'] or self.current_node['meta']['choices'] != chainData:
                                    self.current_node['meta']['chainData']['choices'] = chainData
                                    self.operatorData['myNodes'][self.operatorData['selected_node']] = self.current_node
                                    write_operatorData(self.operatorData)
                            break
                    except Exception as e:
                        print('fetch chain data err 1', str(e))
                        pass
            if self.current_node and not received_data and 'chainData' in self.current_node['meta'] and 'choices' in self.current_node['meta']['chainData']:
                specialChains = self.current_node['meta']['chainData']['choices']['specialChains']
                self.mandatoryChains = self.current_node['meta']['chainData']['choices']['mandatoryChains']
                regionChains = self.current_node['meta']['chainData']['choices']['regionChains']

            self.superuser = False
            if verify_super_status(operatorData=self.operatorData):
                self.superuser = True                
            self.main_root = DynamicTreeView(root_options=dict(text='Main Chains', is_open=True), hide_root=False, size_hint=(1, None))
            self.content.add_widget(self.main_root)

            self.mandatory_tree_view = self.main_root.add_node(CheckBoxTreeLabel(text='Mandatory Chains', identifier='Mandatory', active='mandatory'))
            for sChainName, sChainId in self.mandatoryChains.items():
                self.main_root.add_node(CheckBoxTreeLabel(text=sChainName, identifier=sChainId, active='mandatory'), self.mandatory_tree_view)
            # self.special_tree_view = self.main_root.add_node(CheckBoxTreeLabel(text='Special', identifier='Special', active=self.get_active_state('Special')))
            # self.main_root.add_node(CheckBoxTreeLabel(text='All New Regions', identifier='New', active=self.get_active_state('New')), self.special_tree_view)
            # for sChain in specialChains:
            #     if sChain != 'New':
            #         self.main_root.add_node(CheckBoxTreeLabel(text=sChain, identifier=sChain, active=self.get_active_state(sChain)), self.special_tree_view)
            self.plugins_root = DynamicTreeView(root_options=dict(text='Plugins', is_open=True), hide_root=False, size_hint=(1, None))
            # self.plugins_root.is_open = True
            self.content.add_widget(self.plugins_root)

            for plugin in self.plugin_data:
                print('\nplugin',plugin)
                self.plugins_root.add_node(CheckBoxTreeLabel(text=plugin['Title'], identifier=plugin['id'], obj_type='Plugin', active=self.get_active_state(plugin['id']), parent=self, superuser=self.superuser, new_child_btn=False))
                
            self.regions_root = DynamicTreeView(root_options=dict(text='Regions', is_open=True), hide_root=False, size_hint=(1, None))
            # self.regions_root.is_open = True
            self.content.add_widget(self.regions_root)
            if regionChains:
                earthData = regionChains['Earth']
                self.earth_tree = self.regions_root.add_node(CheckBoxTreeLabel(text='Earth Chains', identifier=earthData['id'], obj_type='Region', active=self.get_active_state(earthData['id']), parent=self, superuser=self.superuser, new_child_btn=True))
                self.earth_tree.is_open = True

                for earthChild in regionChains['Earth']['children']:
                    self.add_tree_data(self.regions_root, self.earth_tree, earthChild, self.operatorData)

            self.scroll_view.add_widget(self.content)
            self.add_widget(self.scroll_view)

            if self.current_node:
                if 'nodeData' in self.current_node and 'activated_dt' in self.current_node['nodeData'] and not value_is_none(self.current_node['nodeData']['activated_dt']):
                    button_text = 'Deactivate Node Before Changing'
                    self.save_button = Button(text=button_text, size_hint=(1, None), height=dp(30))
                    self.add_widget(self.save_button)
                else:
                    if 'chainData' not in self.current_node['meta'] or 'supported_chains' not in self.current_node['meta']['chainData'] or self.current_node['meta']['chainData']['supported_chains'] == [] or self.current_node['meta']['chainData']['supported_chains'] == '[]':
                        button_text = 'Unsaved'
                    else:
                        button_text = 'Save'

                    self.save_button = Button(text=button_text, size_hint=(1, None), height=dp(30))
                    self.save_button.bind(on_press=self.save_tree_data)
                    self.add_widget(self.save_button)
        except Exception as e:
            print('fetch chain fail',str(e))
            pass
    
    def edit_object(self, instance=None, iden=None, func=None): # not currently used?
        print('-homescreen activate_display', iden, func)

        # request key passpharse, sign with guardian key
        try:
            self.remove_widget(self.title)
            self.remove_widget(self.scroll_view)
            self.remove_widget(self.content)
        except:
            pass
        operatorData = get_operatorData()
        
        self.current_node = None
        if 'selected_node' in self.operatorData and self.operatorData['selected_node']:
            self.current_node = self.operatorData['myNodes'][self.operatorData['selected_node']]

        if 'userData' in operatorData and 'id' in operatorData['userData'] and 'user_is_super' in operatorData and operatorData['user_is_super'] == True:
            self.superuser = verify_super_status(operatorData)
        else:
            self.superuser = False
        print('home-superuser',self.superuser)
        extra_fields = {}
        latest_signing_fields = {}
        if self.superuser and func == 'new_child':
            self.title = Label(text='New Region', size_hint_y=None, height=dp(30), halign='center')
            self.add_widget(self.title)
            data = {'obj_type' : 'Region', 'obj_id' : '0'}
            regionModel_sign = {}
            regionModel = {}
            nodes = get_node_list(operatorData=operatorData)
            for nodeId, ip in nodes.items():
                r = connect_to_node(ip, 'utils/get_object_data', data=data, operatorData=operatorData)
                if r:
                    received_json = r.json()
                    try:
                        regionModel_sign = json.loads(received_json['signing_obj'])
                        regionModel = json.loads(received_json['model_obj'])
                        if 'latest_signing_fields' in received_json:
                            latest_signing_fields = json.loads(received_json['latest_signing_fields'])
                        break
                    except:
                        pass
            if regionModel_sign:
                now = now_utc()
                regionModel_sign['ParentRegion_obj'] = iden
                regionModel_sign['commitChain'] = iden
                regionModel['created'] = dt_to_string(now)
                from commands.utils import get_most_recent_even_hour
                regionModel_sign['created'] = dt_to_string(get_most_recent_even_hour(dt=now))
                fields = regionModel_sign
                extra_fields = regionModel
        elif self.superuser and 'edit' in func:
            print('home edit')
            obj_type = func.replace('edit_','')
            self.title = Label(text=f'Edit {obj_type}', size_hint_y=None, height=dp(30), halign='center')
            self.add_widget(self.title)
            data = {'obj_type' : obj_type, 'obj_id' : iden}
            objModel_sign = {}
            objModel = {}
            nodes = get_node_list(operatorData=operatorData)
            for nodeId, ip in nodes.items():
                err = 1
                r = connect_to_node(ip, 'utils/get_object_data', data=data, operatorData=operatorData)
                if r:
                    err =2
                    try:
                        received_json = r.json()
                        err = 3
                        objModel_sign = json.loads(received_json['signing_obj'])
                        err = 4
                        objModel = json.loads(received_json['model_obj'])
                        if 'latest_singing_fields' in received_json:
                            latest_singing_fields = json.loads(received_json['latest_singing_fields'])
                        err = 5
                        break
                    except:
                        pass
            fields = objModel_sign
            extra_fields = objModel
        self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        self.content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=5)
        self.content.bind(minimum_height=self.content.setter("height"), minimum_width=self.content.setter("width"))

        self.skipfields = ['objType', 'id', 'modlVer', 'func', 'created', 'lastUpdate', 'DateTime', 'signed','CreatorNode_obj','validatorNodeId']

        row_index = 0
        form_fields = {}
        for key, value in fields.items():
            if value == 'None':
                value = None
            form_fields[key] = value
        print('stage3 - form_fields:',form_fields)
        print('latest_signing_fields',latest_signing_fields)
        if latest_signing_fields:
            for key, value in form_fields.items():
                if key in latest_signing_fields:
                    self.content.add_widget(FieldRow(key, value, editable=True, superuser=False if key in self.skipfields else self.superuser))
            self.content.add_widget(Label(text='New model version fields', halign='left'))
            for key, value in latest_signing_fields.items():
                if key not in form_fields:
                    self.content.add_widget(FieldRow(key, value, editable=True, superuser=False if key in self.skipfields else self.superuser))
            self.content.add_widget(Label(text='Old fields being removed', halign='left'))
            for key, value in form_fields.items():
                if key not in latest_singing_fields:
                    self.content.add_widget(FieldRow(key, value, superuser=False if key in self.skipfields else self.superuser))
        else:
            for key, value in form_fields.items():
                self.content.add_widget(FieldRow(key, value, editable=False if key in self.skipfields else True, superuser=False if key in self.skipfields else self.superuser))
        self.scroll_view.add_widget(self.content)
        self.add_widget(self.scroll_view)

        if self.superuser:
            self.save_button = Button(text='Save', size_hint=(1, None), height=dp(30))
            self.save_button.disabled = not self.superuser
            self.save_button.bind(on_press=self.save_data)
            self.parent_screen.display_layout.add_widget(self.save_button)

    def get_active_state(self, key):
        print('-get_active_state',key)
        if not self.current_node:
            return False
        active = False
        if 'chainData' in self.current_node['meta']:
            if self.current_node['meta']['chainData'].get('supported_chains', None) and key in self.current_node['meta']['chainData']['supported_chains']:
                active = True
            elif self.current_node['meta']['chainData'].get('supported_plugins', None) and key in self.current_node['meta']['chainData']['supported_plugins']:
                active = True
            elif self.current_node['meta']['chainData'].get('supported_regions', None) and key in self.current_node['meta']['chainData']['supported_regions']:
                active = True
            elif self.current_node['meta']['chainData'].get('unsupported', None) and key in self.current_node['meta']['chainData']['unsupported']:
                active = False
            elif self.current_node['meta']['chainData'].get('half_selected', None) and key in self.current_node['meta']['chainData']['half_selected']:
                active = 'half'          
        return active
        
    def add_tree_data(self, tree_view, parent_node, data, operatorData):
        # print('-add_tree_data')
        for key, value in data.items():
            # print('key',key,'value',value)
            extra = None
            if value['type'] in ['Planet','Continent','Country','Province','State','Territory']:
                if 'reqs' in value:
                    extra = value['reqs']
                node = tree_view.add_node(CheckBoxTreeLabel(text=f'{key} ({value["type"]})', title=key, obj_type=value["obj_type"], identifier=value['id'], extra=extra, active=self.get_active_state(value['id']), parent=self, superuser=self.superuser), parent_node)
            elif value['type'] == 'Government':
                node = tree_view.add_node(CheckBoxTreeLabel(text=f'{key} ({value["type"]})', identifier=value['regionId'], regionId=value['regionId'], extra=extra, obj_type=value["obj_type"], active=self.get_active_state(value['id']), parent=self, superuser=self.superuser), parent_node)
            else:
                node = tree_view.add_node(CheckBoxTreeLabel(text=f'{key} ({value["type"]})', identifier=value['id'], obj_type=value["obj_type"], extra=extra, active=self.get_active_state(value['id']), parent=self, superuser=self.superuser), parent_node)
            if value['type'] == 'Planet' or value['type'] == 'Continent':
                node.is_open = True
            if value.get('children'):
                for child in value['children']:
                    self.add_tree_data(tree_view, node, child, operatorData)

    def update_rect(self, *args):
        self.rect.size = self.size
        self.rect.pos = self.pos

    def save_data(self, instance=None):
        self.save_button.text = 'Saving...'
        objData = parse_fields(items=None, obj=self)
        self.user_passphrase_prompt(data=objData)

    def save_data_step2(self, objData):
        print('-save_data_step2')
        operatorData = get_operatorData()
        try:
            # print('objData',objData)
            full_nodeData = operatorData['myNodes'][operatorData['selected_node']]
            extra_objData = {}
            if 'func' in objData:
                objData['func'] = 'super'

            full_nodeData = operatorData['myNodes'][operatorData['selected_node']]
            if 'CreatorNode_obj' in objData:
                objData['CreatorNode_obj'] = full_nodeData['nodeData']['id']
            if 'validatorNodeId' in objData:
                objData['validatorNodeId'] = full_nodeData['nodeData']['id']

            objData = sign(objData)
            data = {'objData' : json.dumps(objData), 'nodeData' : json.dumps(full_nodeData['nodeData'])}
            # print('data',data)
            r = connect_to_node(full_nodeData['settings']['local_ip']+':'+full_nodeData['settings']['port'], 'utils/get_object_id', data=data, operatorData=operatorData)
            if r:
                received_json = r.json()
                print('message',received_json['message'])
                if received_json['message'] == 'Success':
                    received_json['message'] = 'Error'
                    newId = received_json['obj_id']
                    if not objData['id']: # only working with plugins and regions here - only new id if new object
                        objData['id'] = newId
                        if 'networkChain' in objData:
                            objData['networkChain'] = newId
                    temp_keys = fetch_secure_item('temp_keys')
                    if temp_keys:
                        new_obj = sign(objData, privKey=temp_keys['privKey'], pubKey=temp_keys['pubKey'], verify_result=True)
                    else:
                        new_obj = sign(objData)
                    store_secure_item("temp_keys", None)

                    nodes = get_node_list(operatorData=operatorData)
                    for nodeId, ip in nodes.items():
                        # super_share may need to be off for plugin, above code regarding signing_obj may need to be included?
                        data = {'objData' : json.dumps(new_obj), 'extra_objData' : json.dumps({}), 'super_share':True}
                        print('senddata:',data)
                        r = connect_to_node(ip, 'utils/set_object_data', data=data, operatorData=operatorData)
                        if r:
                            received_json = r.json()
                            print('received_json',received_json)
                            if received_json['message'] == 'Success':
                                print('All GooD!')
                                Clock.schedule_once(lambda dt, line='Saved': self.update_status(line))
                                return
                            else:
                                Clock.schedule_once(lambda dt, line=received_json['message']: self.update_status(line))
                else:
                    Clock.schedule_once(lambda dt, line=received_json['message']: self.update_status(line))
            else:
                Clock.schedule_once(lambda dt, line='Save Error': self.update_status(line))
        except Exception as e:
            Clock.schedule_once(lambda dt, line=f'Error:{e}': self.update_status(line))
            print('save_data_step2 fail',str(e))
        Clock.schedule_once(lambda dt, line='Save Error': self.update_status(line))

    def update_status(self, line):
        try:
            if not line.endswith('\n') and not line.startswith('\n'):
                line = line + '\n'
            self.text_input.text += line
        except Exception as e:
            print('update_status err 1',str(e))
            try:
                self.save_button.text = line
            except Exception as e:
                print('update_status fail',str(e))

    def save_tree_data(self, instance):
        # print('-save_tree_data')
        self.remove_widget(self.save_button)
        self.save_button = Button(text='Updating...', size_hint=(1, None), height=dp(30))
        self.save_button.bind(on_press=self.save_tree_data)
        self.add_widget(self.save_button)
        threading.Thread(target=self.save_tree_data_step2).start()

    def save_tree_data_step2(self):
        print('-save_tree_data_step2')
        from commands.utils import is_id
        from commands.locked import generate_id
        chains = []
        checked_regions = []
        checked_plugins = []
        unchecked_items = []
        half_checked_items = []
        reqs = {}
        # for i in self.mandatoryChains:
        #     checked_items.append(i)
        def sort_checkboxes(node, chains, checked_regions, checked_plugins, unchecked_items, half_checked_items):
            if isinstance(node, CheckBoxTreeLabel):
                if node.checkbox.active and not node.checkbox.group:
                    if is_id(node.identifier):
                        iden = 'chnSo' + generate_id({'genesisId': node.identifier, 'objType': 'Blockchain'})
                    else:
                        iden = node.identifier
                    if iden not in chains:
                        chains.append(iden)
                    print('node',node)
                    print('node.identifier',node.identifier)
                    try:
                        print('node.obj_type',node.obj_type)
                        if node.obj_type == 'Region' and node.identifier not in checked_regions:
                            checked_regions.append(node.identifier)
                        elif node.obj_type == 'Plugin' and node.identifier not in checked_plugins:
                            checked_plugins.append(node.identifier)
                    except Exception as e:
                        print('err 64', str(e))
                elif not node.checkbox.group:
                    if node.identifier not in unchecked_items:
                        unchecked_items.append(node.identifier)
                elif node.checkbox.group:
                    if node.identifier not in half_checked_items:
                        half_checked_items.append(node.identifier)
            return chains, checked_regions, checked_plugins, unchecked_items, half_checked_items
        
        for node in self.regions_root.iterate_all_nodes():
            if isinstance(node, CheckBoxTreeLabel):
                print('node.identifier',node.identifier)
                print('node.extra',node.extra)
                if node.extra:
                    reqs[node.identifier] = {'title':node.title,'reqs':node.extra}
            chains, checked_regions, checked_plugins, unchecked_items, half_checked_items = sort_checkboxes(node, chains, checked_regions, checked_plugins, unchecked_items, half_checked_items)

        for node in self.plugins_root.iterate_all_nodes():
            chains, checked_regions, checked_plugins, unchecked_items, half_checked_items = sort_checkboxes(node, chains, checked_regions, checked_plugins, unchecked_items, half_checked_items)

        for node in self.main_root.iterate_all_nodes():
            chains, checked_regions, checked_plugins, unchecked_items, half_checked_items = sort_checkboxes(node, chains, checked_regions, checked_plugins, unchecked_items, half_checked_items)

        # for node in self.mandatory_tree_view.iterate_all_nodes():
        #     chains, checked_regions, checked_plugins, unchecked_items, half_checked_items = sort_checkboxes(node, chains, checked_regions, checked_plugins, unchecked_items, half_checked_items)

        print('checked_regions:', checked_regions)
        print('checked_plugins:', checked_plugins)
        print('chains:', chains)
        print('Unchecked items:', unchecked_items)
        self.current_node['meta']['chainData'] = {}
        self.current_node['meta']['chainData']['supported_chains'] = chains
        self.current_node['meta']['chainData']['supported_plugins'] = checked_plugins
        self.current_node['meta']['chainData']['supported_regions'] = checked_regions
        self.current_node['meta']['chainData']['unsupported'] = unchecked_items
        self.current_node['meta']['chainData']['half_selected'] = half_checked_items
        print('updated chainData:',self.current_node['meta']['chainData'])
        print('updated chainData is dict:',isinstance(self.current_node['meta']['chainData'], dict))
        if reqs:
            self.reqs = reqs
            Clock.schedule_once(self.save_tree_data_step4, 0)
        else:
            self.operatorData['myNodes'][self.current_node['nodeData']['id']] = self.current_node
            write_operatorData(self.operatorData)
            from commands.utils import update_remote_data
            update_remote_data(self.current_node, operatorData=self.operatorData)
            try:
                # not currently allowed
                if self.current_node['nodeData']['chain_array'] != self.current_node['meta']['chainData']['supported_chains'] and self.current_node['nodeData']['activated_dt']:
                    print('send chain updates')
                    from commands.utils import declare_self_active
                    resp = declare_self_active(True, activate_tasker=False)
                    print('resp of declare state chain screen',resp)
            except Exception as e:
                print('declare state chain screen fail',str(e))
                pass
            Clock.schedule_once(self.save_tree_data_step3, 0)
    
    def save_tree_data_step3(self, instance):
        self.remove_widget(self.save_button)
        self.save_button = Button(text='Saved', size_hint=(1, None), height=dp(30))
        self.save_button.bind(on_press=self.save_tree_data)
        self.add_widget(self.save_button)

    def save_tree_data_step4(self, instance):
        self.remove_widget(self.title)
        self.scroll_view.remove_widget(self.content)
        self.remove_widget(self.scroll_view)
        self.remove_widget(self.save_button)

        self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True, scroll_type=['bars', 'content'],bar_width=17, bar_color=(1, 1, 1, 1), bar_inactive_color=(1, 1, 1, .3))
        self.content = BoxLayout(orientation="vertical", size_hint_y=None)
        self.content.bind(minimum_height=self.content.setter("height"))
        self.title = Label(text='Required', size_hint_y=None, height=dp(30), halign='center')
        self.add_widget(self.title)
        self.add_widget(Divider(padding=0))
        self.text_input = TextInput(
            text="You selected items with requirements. Make sure all fields are filled below.",
            size_hint_x=1,
            size_hint_y=None,
            halign="left",
            multiline=True, 
            background_color=dark_blue2,
            foreground_color=(1, 1, 1, 1) 
        )
        self.text_input.bind(minimum_height=self.update_textinput_height)
        Window.bind(size=self.update_textinput_height)
        self.update_textinput_height()
        self.content.add_widget(self.text_input)
        self.scroll_view.add_widget(self.content)
        self.add_widget(self.scroll_view)


        self.items = {}
        for req in self.reqs:
            print('req',req)
            for key, value in self.reqs[req]['reqs'].items():
                print('k',key,'v',value)

                layout1 = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=dp(30))
                label1 = Label(text=self.reqs[req]['title'], size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(130))
                with label1.canvas.before:
                    Color(1, 1, 1, 1)
                # field = Label(text=value, size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(130))
                field = TextInput(text=value, size_hint=(1, None), height=dp(30), readonly=True)
                layout1.add_widget(label1)
                layout1.add_widget(field)
                self.add_widget(layout1)
                
                layout2 = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=dp(30))
                label2 = Label(text=key, size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(130))
                with label2.canvas.before:
                    Color(1, 1, 1, 1)

                text = ''
                try:
                    for i, x in self.current_node['meta']['abilities'][req].items():
                        print('i',i, 'x',x)
                        if i == key:
                            text = x
                            break
                except Exception as e:
                    print('err 545',str(e))
                    pass
                input = TextInput(text=text, hint_text="Required", size_hint=(1, None), height=dp(30))
                layout2.add_widget(label2)
                layout2.add_widget(input)
                self.add_widget(layout2)
                
                self.items[req] = {'field':key, 'input':input}
            self.add_widget(Divider(padding=0))

        self.save_button = Button(text='Save', size_hint=(1, None), height=dp(30))
        self.save_button.bind(on_press=self.save_tree_data2)
        self.add_widget(self.save_button)

    def save_tree_data2(self, instance):
        # print('-save_tree_data')
        self.remove_widget(self.save_button)
        self.save_button = Button(text='Saving...', size_hint=(1, None), height=dp(30))
        self.save_button.bind(on_press=self.save_tree_data2)
        self.add_widget(self.save_button)
        threading.Thread(target=self.save_tree_data_step5).start()

    def save_tree_data_step5(self, instance=None):
        print('-save_tree_data_step5')
        complete = True
        data = {}
        new_abilities = {}

        for key, value in self.items.items():
            print('k',key,'v',value)
            if not value['input'].text:
                text = 'Please complete all fields'
                complete = False
                break
            else:
                new_abilities[f"{value['field']}s"] = []
        print('next')

        if complete:
            for key, value in self.items.items():
                print('k',key,'v',value)
                new_abilities[f"{value['field']}s"].append(key)
                data[key] = {value['field']:value['input'].text}

            print('data',data)
            print('new_abilities',new_abilities)
            if 'abilities' not in self.current_node['nodeData']:
                self.current_node['nodeData']['abilities'] = {}
            if 'abilities' not in self.current_node['meta']:
                self.current_node['meta']['abilities'] = {}
            # x = {}
            # z = {}
            for key, value in data.items():
                # x[key] = value
                self.current_node['meta']['abilities'][key] = value
            for key, value in new_abilities.items():
                # z[key] = value
                self.current_node['nodeData']['abilities'][key] = value
            # print('x',x)
            # print('z',z)
            self.operatorData['myNodes'][self.current_node['nodeData']['id']] = self.current_node
            write_operatorData(self.operatorData)
            from commands.utils import update_remote_data
            update_remote_data(self.current_node, operatorData=self.operatorData)

            Clock.schedule_once(self.save_tree_data_step6, 0)
        else:
            Clock.schedule_once(lambda dt, line=text: self.save_tree_data_step6(self, text=line))

    def save_tree_data_step6(self, instance, text='Saved'):
        self.remove_widget(self.save_button)
        self.save_button = Button(text=text, size_hint=(1, None), height=dp(30))
        self.save_button.bind(on_press=self.save_tree_data2)
        self.add_widget(self.save_button)

    def user_passphrase_prompt(self, data=None, instance=None):

        def proceed():
            self.passphrase = self.pass_input.text.lower()
            self.pass_layout.remove_widget(self.pass_label)
            self.pass_layout.remove_widget(self.pass_input)
            self.remove_widget(self.pass_layout)

            user_id = self.operatorData['user_id']
            super_keyPair = createKeyPair(user_id, self.passphrase, 'guardian', key_strength='ML_DSA_87')
            from commands.utils import hash_upk_id
            store_secure_item("temp_keys", {'pubKey':super_keyPair[1],'privKey':super_keyPair[0],'keyId':hash_upk_id(super_keyPair[1])})

            self.text_input.text = f'Generated PubKey:\n{str(super_keyPair[1])[:50]}...\n\nKeyId:\n{hash_upk_id(super_keyPair[1])}\n\nSaving Data...\n'

            threading.Thread(target=self.save_data_step2, args=(data,)).start()
            
        self.content.remove_widget(self.title)
        self.content.remove_widget(self.scroll_view)
        self.scroll_view.remove_widget(self.content)
        self.remove_widget(self.scroll_view)
        self.remove_widget(self.title)
        self.remove_widget(self.save_button)

        self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True, scroll_type=['bars', 'content'],bar_width=17, bar_color=(1, 1, 1, 1), bar_inactive_color=(1, 1, 1, .3))
        self.content = BoxLayout(orientation="vertical", size_hint_y=None)
        self.content.bind(minimum_height=self.content.setter("height"))
        self.title = Label(text='Continue', size_hint_y=None, height=dp(30), halign='center')
        self.add_widget(self.title)
        self.add_widget(Divider(padding=0))
        self.text_input = TextInput(
            text="",
            size_hint_x=1,
            size_hint_y=None,
            halign="left",
            multiline=True, 
            background_color=dark_blue2,
            foreground_color=(1, 1, 1, 1) 
        )
        self.text_input.bind(minimum_height=self.update_textinput_height)
        Window.bind(size=self.update_textinput_height)
        self.update_textinput_height()
        self.content.add_widget(self.text_input)
        self.scroll_view.add_widget(self.content)
        self.add_widget(self.scroll_view)
        
        self.text_input.text = 'The selected settings require advanced keys.\n\nAccount passphrase needed to generate required keys.\n'
        self.pass_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=dp(30))
        self.toggle_button = Button(text='Show', size_hint_x=None, width=dp(70))
        self.pass_label = Label(text="User Passphrase:", size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(130))
        with self.pass_label.canvas.before:
            Color(1, 1, 1, 1)
        self.pass_input = TextInput(text='', hint_text="passphrase removed after use", size_hint=(1, None), height=dp(30), multiline=False, password=True)
        self.pass_input.bind(on_text_validate=lambda instance: proceed())
        self.pass_input.focus = True
        self.toggle_button.bind(on_press=self.toggle_password_visibility)
        self.pass_layout.add_widget(self.pass_label)
        self.pass_layout.add_widget(self.pass_input)
        self.pass_layout.add_widget(self.toggle_button)
        self.add_widget(self.pass_layout)

    def toggle_password_visibility(self, instance):
        try:
            if self.pass_input.password:
                self.pass_input.password = False
                instance.text = 'Hide'
            else:
                self.pass_input.password = True
                instance.text = 'Show'
        except:
            pass
        try:
            if self.passphrase_input.password:
                self.passphrase_input.password = False
                instance.text = 'Hide'
            else:
                self.passphrase_input.password = True
                instance.text = 'Show'
        except:
            pass

    def update_textinput_height(self, *args):
        self.text_input.height = max(
            self.text_input.minimum_height,
            Window.height
        )
    
class NodesScreen(BoxLayout):
    def __init__(self, parent=None, parentRegionId=None, obj_type=None, obj_id=None, content=None, do_scroll_x=True, do_scroll_y=True, **kwargs):
        super(NodesScreen, self).__init__(**kwargs)
        print('-NodesScreen.parent', parent)
        self.parent_screen = parent
        self.parentRegionId = parentRegionId
        self.obj_type = obj_type
        self.obj_id = obj_id
        self.content = content

        with self.canvas.before:
            Color(0.094, 0.122, 0.176, 1)
            self.rect = Rectangle(size=self.size, pos=self.pos)
            self.bind(size=self.update_rect, pos=self.update_rect)

    def activate_display(self):
        print('-NodesScreen activate_display')
        self.header = Label(text='My Nodes', size_hint_y=None, height=dp(30) * w_scale, font_size=dp(13) * t_scale, halign='center')
        self.add_widget(self.header)

        self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True, scroll_type=['bars', 'content'],bar_width=17, bar_color=(1, 1, 1, 1), bar_inactive_color=(1, 1, 1, .3))
        self.content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(5) * w_scale)
        self.content.bind(minimum_height=self.content.setter("height"), minimum_width=self.content.setter("width"))

        self.operatorData = get_operatorData()
        if 'myNodes' in self.operatorData:
            if self.operatorData['myNodes']:
                node_list = []
                for node_id, data in self.operatorData['myNodes'].items():
                    if node_id not in node_list:
                        node_list.append(node_id)
                    commands = [{'title':"Select",'action':partial(self.select_node, node_id=node_id)}]
                    if 'location' in data:
                        if data['location'] == 'local':
                            commands.append({'title':"Local",'action':None})
                        else:
                            commands.append({'title':data['location'],'action':partial(self.edit_remote, data['location'])})
                        commands.append({'title':'Remove','action':partial(self.remove_node, node_id)})
                        self.content.add_widget(FieldRow(data['settings']['node_name'], commands, is_button_list=True))
                    else: 
                        self.content.add_widget(FieldRow(node_id, commands, is_button_list=True))
                if len(node_list) > 1:
                    commands = [{'title':"Update All",'action':partial(self.run_node_sequence, 'update')}]
                    self.content.add_widget(FieldRow('', commands, is_button_list=True))
                if len(node_list) > 1:
                    commands = [{'title':"Restart All",'action':partial(self.run_node_sequence, 'restart')}]
                    self.content.add_widget(FieldRow('', commands, is_button_list=True))
  
            else:
                commands = [{'title':"",'action':None}]
                self.content.add_widget(FieldRow("None", commands, is_button_list=True))

        else:
            self.operatorData['myNodes'] = {}

        self.title = Label(text='My Remotes', size_hint_y=None, height=dp(30) * w_scale, font_size=dp(13) * t_scale, halign='center')
        self.content.add_widget(self.title)

        if 'myRemotes' in self.operatorData:
            if self.operatorData['myRemotes']:
                for nickname, data in self.operatorData['myRemotes'].items():
                    commands = [
                        {'title':"Edit",'action':partial(self.edit_remote, nickname)}
                        ]
                    commands.append({'title':"View",'action':partial(self.view_node_data, nickname)})
                    if 'node_id' not in data:
                        commands.append({'title':"Install",'action':partial(self.remote_install, nickname)})
                    commands.append({'title':"Update",'action':partial(self.remote_update, nickname)})
                    if nickname.lower() != 'local':
                        commands.append({'title':"Delete",'action':partial(self.delete_remote, nickname)})
                    self.content.add_widget(FieldRow(nickname, commands, is_button_list=True))
            else:
                commands = [{'title':"",'action':None}]
                self.content.add_widget(FieldRow("None", commands, is_button_list=True))

        else:
            self.operatorData['myRemotes'] = {}
            write_operatorData(self.operatorData)
            commands = [{'title':"None",'action':None}]
            self.content.add_widget(FieldRow("None", commands, is_button_list=True))

        self.title = Label(text='New', size_hint_y=None, height=dp(30) * w_scale, font_size=dp(13) * t_scale, halign='center')
        self.content.add_widget(self.title)
        commands = [{'title':"New Remote",'action':partial(self.new_remote)}]
        self.content.add_widget(FieldRow('', commands, is_button_list=True))
        self.text_input = TextInput(
            text="",
            size_hint_x=1,
            size_hint_y=None,
            font_size=dp(14) * t_scale,
            halign="left",
            multiline=True, 
            background_color=dark_blue2,
            foreground_color=(1, 1, 1, 1),
        )
        self.text_input.bind(minimum_height=self.text_input.setter('height'))
        self.content.add_widget(self.text_input)

        self.scroll_view.add_widget(self.content)
        self.add_widget(self.scroll_view)

    def new_remote(self):
        self.remove_widget(self.title)
        self.remove_widget(self.scroll_view)
        self.remove_widget(self.content)

        title = Label(text='New SSH Connection', size_hint_y=None, height=dp(30) * w_scale, font_size=dp(13) * t_scale, halign='center')
        self.add_widget(title)

        self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        self.content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(5) * w_scale)
        self.content.bind(minimum_height=self.content.setter("height"), minimum_width=self.content.setter("width"))
        self.scroll_view.add_widget(self.content)
        self.add_widget(self.scroll_view)

        fields = ['nickname', 'local_address', 'port', 'remote_address', 'remote_port', 'username', 'password']
        if not fetch_secure_item("sysPass"):
            fields.append('local_password')
        for i in fields:
            if 'port' in i:
                self.content.add_widget(FieldRow(i, '22', editable=True))
            else:
                self.content.add_widget(FieldRow(i, '', editable=True))

        self.text_input = TextInput(
            text='', 
            multiline=True, 
            halign='left', 
            size_hint=(1, 1),
            background_color=dark_blue2,
            foreground_color=(1, 1, 1, 1),
            font_size=dp(13) * t_scale
        )
        self.text_input.bind(minimum_height=self.text_input.setter('height'))
        self.add_widget(self.text_input)

        self.continue_button = Button(text='Create', size_hint=(1, None), height=dp(30) * w_scale, font_size=dp(13) * t_scale)
        self.continue_button.bind(on_press=self.create_ssh)
        self.add_widget(self.continue_button)

    def edit_remote(self, node_data):
        try:
            self.remove_widget(self.title)
            self.remove_widget(self.scroll_view)
            self.remove_widget(self.content)
        except:
            pass
        print('-edit_remote',node_data)
        if isinstance(node_data, str):
            if 'myRemotes' in self.operatorData and self.operatorData['myRemotes'] and node_data in self.operatorData['myRemotes']:
                node_data = self.operatorData['myRemotes'][node_data]
            else:
                node_data = None

        title = Label(text=f"Edit Host {node_data['nickname']}", size_hint_y=None, height=dp(30) * w_scale, font_size=dp(13) * t_scale, halign='center')
        self.add_widget(title)

        self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        self.content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(5) * w_scale)
        self.content.bind(minimum_height=self.content.setter("height"), minimum_width=self.content.setter("width"))

        # remote os_type and node_id should not be editable
        if node_data:
            for key, value in node_data.items():
                self.content.add_widget(FieldRow(key, value, editable=True, superuser=True))
        else:
            self.content.add_widget(FieldRow('', 'Not Found', editable=True, superuser=True))

        self.text_input = TextInput(
            text="",
            size_hint_x=1,
            size_hint_y=None,
            font_size=dp(13) * t_scale,
            halign="left",
            multiline=True, 
            background_color=dark_blue2,
            foreground_color=(1, 1, 1, 1)
        )
        self.text_input.bind(minimum_height=self.text_input.setter('height'))
        self.content.add_widget(self.text_input)

        self.scroll_view.add_widget(self.content)
        self.add_widget(self.scroll_view)

        if node_data:
            self.continue_button = Button(text='Save', size_hint=(1, None), height=dp(30) * w_scale, font_size=dp(13) * t_scale)
            self.continue_button.bind(on_press=self.save_host_data)
            self.add_widget(self.continue_button)

    def save_host_data(self, instance):
        print('-save_host_data')
        Clock.schedule_once(lambda dt, line='Saving...': update_text(self, line))
        host_data = parse_fields(obj=self)
        print('host_data',host_data)
        if host_data:
            self.operatorData = get_operatorData(self.operatorData)
            if not 'myNodes' in self.operatorData:
                self.operatorData['myNodes'] = {}
            self.operatorData['myRemotes'][host_data['nickname']] = host_data
            write_operatorData(self.operatorData)
            text = f'\nSaved.'
            Clock.schedule_once(lambda dt, line=text: update_text(self, line))

    def delete_remote(self, node_name):
        # should ask confirmation before delete
        # should update screen
        # should remove data from "myNodes"
        # should remove key and data retrieved in fetch_remote_data()
        print('-delete_host',node_name)
        if isinstance(node_name, str):
            if 'myRemotes' in self.operatorData and self.operatorData['myRemotes'] and node_name in self.operatorData['myRemotes']:
                remote_data = self.operatorData['myRemotes'][node_name]
                if 'local_nodeId' in remote_data:
                    if 'myNodes' in self.operatorData and remote_data['local_nodeId'] in self.operatorData['myNodes']:
                        del self.operatorData['myNodes'][remote_data['local_nodeId']]
                iden = self.operatorData['myRemotes'][node_name]['remote_id']
                del self.operatorData['myRemotes'][node_name]
                write_operatorData(self.operatorData)

                from pathlib import Path
                homepath = expanduser("~")

                p = homepath + f"/Sonet/.data/special/keys/{remote_data['node_id']}_key.key"
                Path(p).unlink(missing_ok=True)
                
                p = homepath + f"/Sonet/.data/special/keys/{remote_data['nickname']}_key.key"
                Path(p).unlink(missing_ok=True)
                
                p = homepath + f"/Sonet/.data/operator_data/{remote_data['node_id']}_opData.enc"
                Path(p).unlink(missing_ok=True)
                
                p = homepath + f"/Sonet/.data/operator_data/{remote_data['node_id']}_nodeKeys.enc"
                Path(p).unlink(missing_ok=True)

                text = 'Deleted'
                Clock.schedule_once(lambda dt, line=text: update_text(self, line))
                return
        
        text = 'Not Deleted'
        Clock.schedule_once(lambda dt, line=text: update_text(self, line))
        return

    def remove_node(self, node_id):
        try:
            del self.operatorData['myNodes'][node_id]
            write_operatorData(self.operatorData)
            text = 'Removed'
        except Exception as e:
            print('fail remove_node', str(e))
            text = f'Error {str(e)}'
        Clock.schedule_once(lambda dt, line=text: update_text(self, line))
        return

    def create_ssh(self, instance=None):
        items = [child for child in reversed(self.content.children) if isinstance(child, FieldRow)]
        self.remote_data = parse_fields(items)

        try:
            self.remove_widget(self.continue_button)
        except:
            pass
        if not self.remote_data['nickname']:
            self.remote_data['nickname'] = self.remote_data['local_address']
        text = 'Contacting...'
        Clock.schedule_once(lambda dt, line=text: update_text(self, line))
        threading.Thread(target=self.create_ssh_step2).start()

    def create_ssh_step2(self, instance=None, remote_data={}):
        print('-create_ssh_step2')
        if not remote_data:
            try:
                remote_data = self.remote_data
            except:
                pass
        if remote_data:
            remote_system = self.check_remote_machine(remote_data=remote_data)
            if remote_system:
                remote_data['os_type'] = remote_system
                self.operatorData = get_operatorData(self.operatorData)
                if not 'myRemotes' in self.operatorData:
                    self.operatorData['myRemotes'] = {}
                if not fetch_secure_item("sysPass"):
                    print('remote_data',remote_data)
                    print("remote_data['local_password']",remote_data['local_password'])
                    store_secure_item('sysPass', remote_data['local_password'])
                    del remote_data['local_password']
                
                import base62
                import uuid
                uuid_int = int.from_bytes(uuid.uuid4().bytes, byteorder='big')
                encoded = base62.encode(uuid_int)
                remote_data['remote_id'] = str(encoded)[:7]

                self.operatorData['myRemotes'][remote_data['nickname']] = remote_data
                from commands.utils import setup_ssh
                setup_ssh(remote_data['local_address'], remote_data['username'], remote_data['password'], remote_data['remote_id'])
                
                text = f'Successful contact with remote {remote_system} machine.'
                Clock.schedule_once(lambda dt, line=text: update_text(self, line))
                remote_opData = self.fetch_remote_data(remote_data, False, operatorData=self.operatorData, fetch_key=True)
                if remote_opData and 'sonet' in remote_opData and 'id' in remote_opData['sonet']:
                    if remote_opData['sonet']['id'] == self.operatorData['sonet']['id']:
                        Clock.schedule_once(lambda dt, line="\nRemote install found.": update_text(self, line))
                    else:
                        Clock.schedule_once(lambda dt, line=f"\nRemote running a different network. ({remote_opData['sonet']['id']})": update_text(self, line))
                        return 'Connection failed'
                else:
                    Clock.schedule_once(lambda dt, line="\nRemote install not found.": update_text(self, line))
                Clock.schedule_once(lambda dt, line="\nRemote created.\nDone.": update_text(self, line))
                write_operatorData(self.operatorData)
                return remote_system
            else:
                text = f'Failed to contact remote machine.'
                Clock.schedule_once(lambda dt, line=text: update_text(self, line))
                Clock.schedule_once(lambda dt: self.add_button(text='Create', action=partial(self.create_ssh)))
                return 'Connection failed'
        text = f'Missing connection data.'
        Clock.schedule_once(lambda dt, line=text: update_text(self, line))
        Clock.schedule_once(lambda dt: self.add_button(text='Create', action=partial(self.create_ssh)))
        return 'Missing host data'

    def send_self_ssh(self, username, host, remote_path): # not used
        import os
        local_file = os.path.abspath(__file__)
        os.system(f"scp {local_file} {username}@{host}:{remote_path}")

        # # Example Usage:
        # self.send_self_ssh("user", "192.168.1.100", "/home/user/kivy_app.py")

    def check_remote_machine(self, instance=None, remote_data=None):
        print('-check_remote_machine')
        if remote_data:
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(hostname=remote_data['local_address'], username=remote_data['username'], password=remote_data['password'])

                stdin, stdout, stderr = client.exec_command("uname -s || cat /etc/os-release || ver")
                output = stdout.read().decode().strip()
                print(f"Command: os_type\nOutput:\n{output}\n{'-'*50}")

                client.close()
                if 'linux' in output.lower():
                    return 'linux'
                elif 'darwin' in output.lower():
                    return 'mac'
                elif 'windows' in output.lower():
                    return 'windows'
                elif 'freebsd' in output.lower():
                    return 'freebsd'
            except Exception as e:
                print('check_remote_machine fail', str(e))
        return None

    def select_node(self, instance=None, node_id='', fetch_remote=True):
        print('-select_node',node_id)
        self.operatorData['selected_node'] = 'loading'
        write_operatorData(self.operatorData)
        self.parent_screen.refresh_sidebar()
        self.operatorData['selected_node'] = node_id
        remote_data = {}
        for nickname, data in self.operatorData['myRemotes'].items():
            if 'node_id' in data and data['node_id'] == node_id:
                remote_data = data
                break
        write_operatorData(self.operatorData)
        if fetch_remote and remote_data and 'remote_address' in remote_data:
            threading.Thread(target=self.fetch_remote_data, args=(remote_data, True, self.operatorData,)).start()
        else:
            Clock.schedule_once(lambda dt, line=self: self.parent_screen.refresh_sidebar())
    
    def remote_update(self, node_id=''):
        print('-remote_update',node_id)
        for nickname, data in self.operatorData['myRemotes'].items():
            if nickname == node_id:
                send_manager_to_remote(data['node_id'])
                break

    def view_node_data(self, node_name=''):
        self.node_name = node_name
        self.text_input.text += f'Loading {self.node_name}...\n'
        self.view_node_data_step2()

    def view_node_data_step2(self, instance=None):
        remote_data = {}
        for nickname, data in self.operatorData['myRemotes'].items():
            if self.node_name and nickname == self.node_name:
                remote_data = data
                break
        if remote_data:
            if self.node_name == 'local':
                self.opData = self.operatorData
            else:
                self.opData = fetch_remote_data(remote_data, operatorData=self.operatorData, fetch_key=True)
                if not self.opData and 'node_id' in remote_data:
                    self.opData = fetch_secure_item(f"{remote_data['node_id']}_opData")
            self.view_node_tree()

    def view_node_tree(self, instance=None, target_tree=[]):
        print('-view_node_tree, target_tree:',target_tree)
        # print('self.opData',self.opData)
        try:
            self.remove_widget(self.title)
            self.remove_widget(self.save_button)
        except:
            pass
        try:
            self.remove_widget(self.text_input)
        except:
            pass
        try:
            self.remove_widget(self.content)
        except:
            pass
        try:
            self.remove_widget(self.scroll_view)
        except:
            pass

        t = ''
        if target_tree:
            top_level = self.opData
            fields = {}
            text = self.node_name
            for t in target_tree:
                if t in top_level:
                    text += f' - {t}'
                    fields = top_level[t]
                    top_level = fields
            self.title = Label(text=text, size_hint_y=None, height=dp(30) * w_scale, font_size=dp(13) * t_scale, halign='center')
            self.add_widget(self.title)
        else:
            self.title = Label(text=f'{self.node_name} Data', size_hint_y=None, height=dp(30) * w_scale, font_size=dp(13) * t_scale, halign='center')
            self.add_widget(self.title)
            fields = self.opData

        self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        self.content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(5) * w_scale)
        self.content.bind(minimum_height=self.content.setter("height"), minimum_width=self.content.setter("width"))

        self.content.add_widget(Divider(padding=0))
        if isinstance(fields, dict):
            for key, value in fields.items():
                if key not in ['systemPass', 'userPass', 'password']:
                    self.content.add_widget(FieldRow(key, value, parent=self, target_tree=target_tree, superuser=False, editable=False, click_action=self.view_node_tree))

        elif isinstance(fields, list):
            for value in fields:
                self.content.add_widget(FieldRow(t, value, parent=self, target_tree=target_tree, superuser=False, editable=False, click_action=self.view_node_tree))

        self.scroll_view.add_widget(self.content)
        self.add_widget(self.scroll_view)

    def fetch_remote_data(self, remote_data, refresh_sidebar=False, operatorData=None, fetch_key=True):
        remote_opData = fetch_remote_data(remote_data, operatorData=self.operatorData, fetch_key=fetch_key)
        if refresh_sidebar:
            self.parent_screen.refresh_sidebar()
        return remote_opData

    def remote_install(self, target_nickname):
        if 'myRemotes' in self.operatorData:
            if self.operatorData['myRemotes']:
                for nickname, data in self.operatorData['myRemotes'].items():
                    if nickname == target_nickname:
                        args = {'func':'activate_display', 'args':{'remote':data}}
                        if 'selected_node' in self.operatorData:
                            del self.operatorData['selected_node']
                            write_operatorData(self.operatorData)
                            self.parent_screen.refresh_sidebar()
                        self.parent_screen.switch_layout(screen='new_node_remote', ops=args)
                        break

    def run_node_sequence(self, cmd):
        print('-run_node_sequence')
        try:
            self.remove_widget(self.title)
            self.remove_widget(self.save_button)
        except:
            pass
        try:
            self.remove_widget(self.text_input)
        except:
            pass
        try:
            self.remove_widget(self.content)
        except:
            pass
        try:
            self.remove_widget(self.scroll_view)
        except:
            pass

        self.cmd = cmd
        self.header = Label(text='', size_hint_y=None, height=dp(30) * w_scale, font_size=dp(13) * t_scale, halign='center')
        self.add_widget(self.header)
        self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        self.content = BoxLayout(orientation="vertical", size_hint_y=1, size_hint_x=1, spacing=dp(5) * w_scale)
        self.content.bind(minimum_height=self.content.setter("height"), minimum_width=self.content.setter("width"))

        self.text_input = TextInput(
            text="Loading...",
            size_hint_x=1,
            size_hint_y=None,
            halign="left",
            font_size=dp(13) * t_scale,
            multiline=True, 
            background_color=dark_blue2,
            foreground_color=(1, 1, 1, 1) 
        )
        self.text_input.bind(minimum_height=self.text_input.setter('height'))
        self.content.add_widget(self.text_input)
        self.scroll_view.add_widget(self.content)
        self.add_widget(self.scroll_view)
        Clock.schedule_once(lambda dt, line=self: self.run_node_sequence_step2())

    def run_node_sequence_step2(self):
        print(-'run_node_sequence_step2')
        self.completed_nodes = []
        for node_id, data in self.operatorData['myNodes'].items():
            print('node_id',node_id)
            self.completed_nodes.append(node_id)
            self.select_node(node_id=node_id, fetch_remote=False)
            # send_manager_to_remote(node_id)
            self.parent_screen.node_screen = self.parent_screen.display_layout

            try:
                self.parent_screen.display_layout.remove_widget(self.parent_screen.display_layout.scroll_view)
                self.parent_screen.main_layout.remove_widget(self.parent_screen.display_layout)
            except:
                pass
            self.parent_screen.display_layout = SetupScreen(parent=self.parent_screen, option=self.cmd, following_cmd=self.update_node, orientation='vertical', size_hint=(1, 1))
            self.parent_screen.display_layout.activate_display()
            self.parent_screen.main_layout.add_widget(self.parent_screen.display_layout)
            break
    
    def update_node(self):
        print('-self.update_node')
        for node_id, data in self.operatorData['myNodes'].items():
            print('node_id',node_id, data['meta'].get('os', None),"self.completed_nodes",self.completed_nodes)
            if data['meta'].get('os', None) and data['meta'].get('os') == 'Linux':
                if node_id not in self.completed_nodes and 'nodeData' in data and 'id' in data['nodeData']:
                    self.completed_nodes.append(node_id)
                    self.select_node(node_id=node_id, fetch_remote=False)

                    if self.cmd == 'update':
                        Clock.schedule_once(lambda dt, line=self: self.parent_screen.display_layout.run_update(new_text_screen=False, operatorData=self.operatorData))
                    elif self.cmd == 'restart':
                        Clock.schedule_once(lambda dt, line=self: self.parent_screen.display_layout.run_restart(new_text_screen=False, operatorData=self.operatorData))
                    return
        
        self.parent_screen.node_screen = None
        try:
            self.parent_screen.display_layout.text_input.text += '\n\nAll node updates complete.\n\n'
        except Exception as e:
            print('display_layout.text_input err',str(e))

    def update_rect(self, *args):
        self.rect.size = self.size
        self.rect.pos = self.pos

class SettingsScreen(BoxLayout):
    def __init__(self, parent=None, option='node_settings', **kwargs):
        super(SettingsScreen, self).__init__(**kwargs)
        self.parent_screen = parent
        self.option = option
        self.selected_node = None

        with self.canvas.before:
            Color(0.094, 0.122, 0.176, 1)
            self.rect = Rectangle(size=self.size, pos=self.pos)
            self.bind(size=self.update_rect, pos=self.update_rect)

    def activate_display(self):
        print('-SettingsScreen', self.option)

        self.immutablefields = ['objType', 'id', 'created', 'lastUpdate', 'modlVer', 'publickey', 'signed','region_set_date','user_is_super','activated_dt','suspended_dt']
        self.omitfields = ['signed','supportedchains_array','user_obj']
        self.editable = ['port', 'node_name', 'open_ports', 'external_ip', 'local_ip', 'debug', 'address']

        self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True, scroll_type=['bars', 'content'],bar_width=17, bar_color=(1, 1, 1, 1), bar_inactive_color=(1, 1, 1, .3))
        self.content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=5)
        self.content.bind(minimum_height=self.content.setter("height"))
        operatorData = get_operatorData()
        self.scroll_view.add_widget(self.content)
        self.add_widget(self.scroll_view)

        if 'selected_node' in operatorData:
            self.selected_node = operatorData['myNodes'][operatorData['selected_node']]

        if self.option == 'settings': # not in use
            self.title = Label(text='Settings', size_hint_y=None, height=dp(30), halign='center')
            self.add_widget(self.title)
            try:
                from commands.utils import get_or_create_node_obj
                self_nodeData, is_new = get_or_create_node_obj(operatorData)
                if 'self_nodeData' in operatorData and operatorData['self_nodeData'] and operatorData['self_nodeData'] != 'None':
                    fields = operatorData['self_nodeData']
                    fields['systemPass'] = fetch_secure_item('sysPass')
                    fields['seed_ip'] = operatorData['seed_ip']
                else:
                    fields = {'seed_ip':''}
                    if 'seed_ip' in operatorData:
                        fields['seed_ip'] = operatorData['seed_ip']
                if 'debug' in operatorData:
                    fields['debug'] = operatorData['debug']
                else:
                    fields['debug'] = False
                for key, value in fields.items():
                    if not key in self.omitfields:
                        if key in self.immutablefields:
                            self.content.add_widget(FieldRow(key, value, superuser=False))
                        else:
                            self.content.add_widget(FieldRow(key, value, superuser=True))
            except Exception as e:
                print('settings activate err 1', str(e))
                fields = {'seed_ip':''}
                if 'seed_ip' in operatorData:
                    fields['seed_ip'] = operatorData['seed_ip']
                if 'debug' in operatorData:
                    fields['debug'] = operatorData['debug']
                else:
                    fields['debug'] = False
                self.immutablefields = ['objType', 'id', 'created', 'lastUpdate', 'modlVer', 'publicKey', 'signed','region_set_date','user_is_super']
                self.omitfields = ['signed','chain_array','plugin_array','User_obj','activated_dt','suspended_dt']
                for key, value in fields.items():
                    if not key in self.omitfields:
                        if key in self.immutablefields:
                            self.content.add_widget(FieldRow(key, value, superuser=False))
                        else:
                            self.content.add_widget(FieldRow(key, value, superuser=True))
        elif self.option == 'super_actions':
            if self.selected_node:
                title = Label(text='Super Actions', size_hint_y=None, height=dp(30), halign='center')
                self.content.add_widget(title)
                if 'userData' in operatorData and 'id' in operatorData['userData'] and 'user_is_super' in operatorData and operatorData['user_is_super'] == True:
                    if True:
                        try:
                            for key, value in self.selected_node['nodeData']['abilities'].items():
                                self.content.add_widget(FieldRow(key, value, editable=True, superuser=True))
                        except:
                            pass
                        commands = []
                        if 'abilities' not in self.selected_node['nodeData']:
                            self.selected_node['nodeData']['abilities'] = {}
                        if 'cloudflare' in self.selected_node['nodeData']['abilities'] and self.selected_node['nodeData']['abilities']['cloudflare']:
                            commands.append({'title':"Create Tunnel for Self",'action':partial(self.process_cmd, 'create_tunnel_for_self', operatorData)})
                        else:
                            commands.append({'title':"Initialize CloudFlare",'action':partial(self.process_cmd, 'cloudflare_login')})

                        # if 'lighthouse' in self.selected_node['nodeData']['abilities'] and self.selected_node['nodeData']['abilities']['lighthouse']:
                        #     commands.append({'title':"Disable Lighthouse",'action':partial(self.process_cmd, 'disable_lighthouse', operatorData)})
                        # else:
                        #     commands.append({'title':"Enable Lighthouse",'action':partial(self.process_cmd, 'enable_lighthouse', operatorData)})
                        
                        self.content.add_widget(FieldRow('Actions', commands, parent=self, is_button_list=True))
                        self.text_input = TextInput(
                            text="",
                            size_hint_x=1,
                            size_hint_y=None,
                            halign="left",
                            multiline=True, 
                            background_color=dark_blue2,
                            foreground_color=(1, 1, 1, 1) 
                        )
                        self.text_input.bind(minimum_height=self.text_input.setter('height'))
                        self.content.add_widget(self.text_input)

                        self.save_button = Button(text='Save', size_hint=(1, None), height=dp(30))
                        self.save_button.bind(on_press=lambda instance: self.process_cmd('save2'))
                        self.parent_screen.display_layout.add_widget(self.save_button)
                
        elif self.option == 'node_settings':
            if self.selected_node:
                title = Label(text='Node', size_hint_y=None, height=dp(30), halign='center')
                self.content.add_widget(title)
                try:
                    for key, value in self.selected_node['nodeData'].items():
                        if not key.lower() in self.omitfields:
                            self.content.add_widget(FieldRow(key, value, editable=False, superuser=False))
                except:
                    pass
                title = Label(text='Settings', size_hint_y=None, height=dp(30), halign='center')
                self.content.add_widget(title)
                try:
                    for key, value in self.selected_node['settings'].items():
                        if not key.lower() in self.omitfields:
                            if key.lower() in self.editable:
                                self.content.add_widget(FieldRow(key, value, editable=True, superuser=True))
                            else:
                                self.content.add_widget(FieldRow(key, value, editable=False, superuser=False))
                except:
                    pass
                title = Label(text='Location', size_hint_y=None, height=dp(30), halign='center')
                self.content.add_widget(title)
                try:
                    remote_nickname = self.selected_node['location']
                    commands = [{'title':remote_nickname,'action':None}, {'title':"Edit",'action':partial(self.parent_screen.switch_layout, ops={'func':'edit_node','args':remote_nickname})}]
                    self.content.add_widget(FieldRow('nickname', commands, is_button_list=True))
                except Exception as e:
                    print('settings activate err 2',str(e))
                title = Label(text='meta', size_hint_y=None, height=dp(30), halign='center')
                self.content.add_widget(title)
                try:
                    target = ['myNodes', operatorData['selected_node'], 'meta']
                    for key, value in self.selected_node['meta'].items():
                        if not key.lower() in self.omitfields:
                            target_tree = target + [key]
                            if key.lower() in self.editable:
                                self.content.add_widget(FieldRow(key, value, parent=self, target_tree=target_tree, editable=True, superuser=True))
                            else:
                                self.content.add_widget(FieldRow(key, value, parent=self, target_tree=target_tree, editable=False, superuser=False))
                    if 'debug' not in self.selected_node['meta']:
                        self.content.add_widget(FieldRow('debug', False, editable=True, superuser=False))

                    commands = [{'title':"SyncDB",'action':partial(self.parent_screen.switch_layout, 'syncdb')}, {'title':"Force Deactivate",'action':partial(self.parent_screen.switch_layout, 'deactivate')}, {'title':"Force Activate",'action':partial(self.parent_screen.switch_layout, 'activate')}]
                    
                    if 'userData' in operatorData and 'id' in operatorData['userData'] and 'user_is_super' in operatorData and operatorData['user_is_super'] == True:
                        commands.append({'title':"Super",'action':partial(self.parent_screen.switch_layout, 'super_actions')})
                    self.content.add_widget(FieldRow('Actions', commands, parent=self, is_button_list=True))
                    self.content.add_widget(FieldRow('', [], parent=self, is_button_list=True))
                except Exception as e:
                    print('settings activate err 3',str(e))

                self.save_button = Button(text='Save', size_hint=(1, None), height=dp(30))
                self.save_button.bind(on_press=lambda instance: self.process_cmd('save1'))
                self.parent_screen.display_layout.add_widget(self.save_button)

    def process_cmd(self, data=None, operatorData=None, instance=None):
        if data == 'save1' and self.selected_node or data == 'save2':
            self.save_button.text = 'Saving...'
            threading.Thread(target=self.save_data, args=(operatorData,)).start()
        elif data == 'cloudflare_login':
            self.save_button.text = 'Running Login...'
            threading.Thread(target=self.cloudflare_login, args=(operatorData,)).start()
        elif data == 'create_tunnel_for_self':
            self.save_button.text = 'Creating Tunnel...'
            threading.Thread(target=self.create_tunnel_for_self, args=(operatorData,)).start()
        elif 'lighthouse' in data:
            if 'enable' in data:
                self.save_button.text = 'Enabling Lighthouse...'
                threading.Thread(target=self.edit_lighthouse, args=('enable',operatorData,)).start()
            elif 'disable' in data:
                self.save_button.text = 'Disabling Lighthouse...'
                threading.Thread(target=self.edit_lighthouse, args=('disable',operatorData,)).start()

    def save_data(self, operatorData=None):
        # print('-save_data')
        if not operatorData:
            operatorData = get_operatorData()
        items = [child for child in reversed(self.content.children) if isinstance(child, FieldRow)]
        sys_pass = None
        debug = None
        local_ip = None
        external_ip = None
        address = None
        port = None
        node_name = None
        close_port = None
        seed_ip = None
        reactivate = False
        # refresh_server = False
        save_operatorData = False
        for i in items:
            if i.key.lower() in ['systempass', 'password']:
                sys_pass = i.input.text
            elif i.key.lower() == 'port':
                port = i.input.text
            elif i.key.lower() == 'external_ip':
                external_ip = i.input.text
                external_ip = external_ip.replace('https:','').replace('http:', '').replace('/','')
            elif i.key.lower() == 'address':
                address = i.input.text
                address = address.replace('https:','').replace('http:', '').replace('/','')
            elif i.key.lower() == 'node_name':
                node_name = i.input.text
            elif i.key.lower() == 'localhost':
                localhost = i.input.text
            elif i.key.lower() == 'local_ip':
                local_ip = i.input.text
            elif i.key.lower() == 'seed_ip':
                seed_ip = i.input.text
            elif i.key.lower() == 'debug':
                debug = i.input.active

        if self.selected_node:
            if localhost and self.selected_node['settings']['localhost'] != localhost:
                print('change localhost:',localhost)
                self.selected_node['settings']['localhost'] = localhost
                reactivate = True
                save_operatorData = True
            if local_ip and self.selected_node['settings']['localhost'] != local_ip:
                print('change local_ip:',local_ip)
                self.selected_node['settings']['local_ip'] = local_ip
                reactivate = True
                save_operatorData = True
            if external_ip and self.selected_node['settings']['external_ip'] != external_ip:
                print('change external_ip:',external_ip)
                self.selected_node['settings']['external_ip'] = external_ip
                save_operatorData = True
            if address and self.selected_node['settings']['address'] != address:
                print('change address:',address)
                self.selected_node['settings']['address'] = address
                reactivate = True
                save_operatorData = True
            if port != None and self.selected_node['settings']['port'] != port:
                print('change port:',port)
                close_port = self.selected_node['settings']['port']
                self.selected_node['settings']['port'] = port
                reactivate = True
                save_operatorData = True
            if 'debug' not in self.selected_node['meta'] and debug != None or debug != None and self.selected_node['meta']['debug'] != debug:
                print('change debug:',debug)
                self.selected_node['meta']['debug'] = debug
                save_operatorData = True
            if self.selected_node['settings']['node_name'] != node_name:
                print('change node_name:',node_name)
                self.selected_node['settings']['node_name'] = node_name
                reactivate = True
                save_operatorData = True
            print('save_operatorData',save_operatorData,'reactivate',reactivate)
            if save_operatorData:
                self_nodeData = self.selected_node['nodeData']
                if address:
                    self_nodeData['address'] = address
                if node_name:
                    self_nodeData['node_name'] = node_name
                signed_nodeData = sign(self_nodeData, operatorData=operatorData)
                self.selected_node['nodeData'] = signed_nodeData

                print('self.selected_node',self.selected_node)
                operatorData['myNodes'][self.selected_node['nodeData']['id']] = self.selected_node
                write_operatorData(operatorData)

                if 'local_nodeId' in operatorData and operatorData['selected_node'] == operatorData['local_nodeId']:
                    print('local node')
                    pass
                else:
                    from commands.utils import update_remote_data
                    update_remote_data(self.selected_node, operatorData=operatorData)

        if reactivate and 'activated_dt' in self.selected_node['nodeData'] and not value_is_none(self.selected_node['nodeData']['activated_dt']):
            print('reactivating')
            Clock.schedule_once(lambda dt, line=self: self.reactivate_node(self.selected_node))
        else:
            print('All GooD!')
            Clock.schedule_once(lambda dt, line='Saved': self.update_status(line))

    def sync_nodeData(self, instance=None): # appears unused
        self.syncData_button.text = 'Syncing...'
        threading.Thread(target=self.sync_nodeData_step2).start()

    def sync_nodeData_step2(self):
        from commands.utils import update_node_data
        result, updated = update_node_data()
        if result == 'Success':
            Clock.schedule_once(lambda dt, line='Updated': self.update_status(line))
            Clock.schedule_once(lambda dt, line=self: self.refresh_sidebar(line))
        else:
            Clock.schedule_once(lambda dt, line=result: self.update_status(line))
    
    def reactivate_node(self, full_nodeData=None):
        try:
            self.parent_screen.display_layout.remove_widget(self.parent_screen.display_layout.scroll_view)
            self.parent_screen.main_layout.remove_widget(self.parent_screen.display_layout)
        except:
            pass
        self.parent_screen.display_layout = SetupScreen(parent=self.parent_screen, option='activate', orientation='vertical', size_hint=(1, 1))
        self.parent_screen.display_layout.activate_display()
        self.parent_screen.main_layout.add_widget(self.parent_screen.display_layout)
        Clock.schedule_once(lambda dt, line=self: self.parent_screen.display_layout.reactivate(full_nodeData=full_nodeData, new_text_screen=False))
        
    def cloudflare_login(self, operatorData=None):
        print('-cloudflare_login')
        def login_action():
            proc = subprocess.run(["cloudflared", "tunnel", "login"], check=True)
            cert_path = os.path.expanduser("~/.cloudflared/cert.pem")
            for _ in range(60):  # wait up to 60 seconds
                if os.path.exists(cert_path):
                    print("✅ Login complete, cert.pem found.")
                    try:                
                        proc.terminate()
                    except Exception as e:
                        print('cloudflare_login err 1', str(e))
                    try:                     
                        proc.wait(timeout=5)
                    except:
                        pass
                    return True
                time.sleep(1)

            print("Login timeout or cert.pem not found.")
            try:
                proc.terminate()
            except Exception as e:
                print('cloudflare_login err 2', str(e))
            return False
        
        cert_path = os.path.expanduser("~/.cloudflared/cert.pem")
        if os.path.exists(cert_path):
            if not operatorData:
                operatorData = get_operatorData()
            if 'abilities' not in self.selected_node['nodeData']:
                self.selected_node['nodeData']['abilities'] = {}
            self.selected_node['nodeData']['abilities']['cloudflare'] = True
            operatorData['myNodes'][self.selected_node['nodeData']['id']] = self.selected_node
            write_operatorData(operatorData)
            Clock.schedule_once(lambda dt, line='Previously Completed': self.update_status(line))
        elif login_action():
            if not operatorData:
                operatorData = get_operatorData()
            if 'abilities' not in self.selected_node['nodeData']:
                self.selected_node['nodeData']['abilities'] = {}
            self.selected_node['nodeData']['abilities']['cloudflare'] = True
            operatorData['myNodes'][self.selected_node['nodeData']['id']] = self.selected_node
            write_operatorData(operatorData)
            Clock.schedule_once(lambda dt, line='Completed': self.update_status(line))
        else:
            Clock.schedule_once(lambda dt, line='Incomplete': self.update_status(line))

    def create_tunnel_for_self(self, operatorData=None):
        print('-create_tunnel_for_self')
        try:
            if not operatorData:
                operatorData = get_operatorData()
            if 'userData' in operatorData and 'id' in operatorData['userData'] and 'user_is_super' in operatorData and operatorData['user_is_super'] == True:
                if verify_super_status(operatorData):
                    port = self.selected_node['settings']['port']
                    if not port or str(port) == 'None':
                        Clock.schedule_once(lambda dt, line='port not selected.': self.update_status(line))
                        return False
                    tunnel_name = self.selected_node['nodeData']['id']
                    if 'domain' in self.selected_node['meta'] and self.selected_node['meta']['domain']:
                        DOMAIN = self.selected_node['meta']['domain']
                    elif 'sonet' in operatorData and 'info' in operatorData['sonet'] and 'Domain' in operatorData['sonet'] and operatorData['sonet']['Domain']:
                        DOMAIN = operatorData['sonet']['info']['domain']
                    if not DOMAIN or str(DOMAIN) == 'None':
                        Clock.schedule_once(lambda dt, line='DOMAIN not selected.': self.update_status(line))
                        return False

                    text = f"Creating tunnel: {tunnel_name}, port:{port}, domain:{DOMAIN}"
                    print(text)
                    Clock.schedule_once(lambda dt, line=text: self.update_text(line))
                    from pathlib import Path
                    project_dir = Path.home() / "Sonet"
                    bundle_dir = project_dir / ".data" / "cloudflare_bundles" / tunnel_name
                    active_dir = project_dir / ".data" / "cloudflare_registration"

                    hostname = f"{tunnel_name}.{DOMAIN}"
                    Clock.schedule_once(lambda dt, line=hostname: self.update_text(line))

                    bundle_dir.mkdir(parents=True, exist_ok=True)
                    active_dir.mkdir(parents=True, exist_ok=True)
                    Clock.schedule_once(lambda dt, line=str(bundle_dir): self.update_text(line))
                    Clock.schedule_once(lambda dt, line=str(active_dir): self.update_text(line))
                    
                    for path in bundle_dir.rglob("*"):
                        try:
                            os.chmod(path, 0o700 if path.is_dir() else 0o600)
                        except Exception as e:
                            print(f"Error changing permissions for {path}: {e}")
                    for path in active_dir.rglob("*"):
                        try:
                            os.chmod(path, 0o700 if path.is_dir() else 0o600)
                        except Exception as e:
                            print(f"Error changing permissions for {path}: {e}")
                    
                    Clock.schedule_once(lambda dt, line=f'Creating Tunnel {tunnel_name}': self.update_text(line))
                    try:
                        subprocess.run(["cloudflared", "tunnel", "create", tunnel_name], check=True)
                    except Exception as e:
                        Clock.schedule_once(lambda dt, line=str(e): self.update_text(line))

                    def get_tunnel_json_path(tunnel_name):
                        result = subprocess.run(
                            ["cloudflared", "tunnel", "list", "--output", "json"],
                            check=True, capture_output=True, text=True
                        )
                        tunnels = json.loads(result.stdout)
                        for tunnel in tunnels:
                            if tunnel["name"] == tunnel_name:
                                uuid = tunnel["id"]
                                return Path.home() / ".cloudflared" / f"{uuid}.json"
                        raise Exception(f"Tunnel '{tunnel_name}' not found")

                    src_path = get_tunnel_json_path(tunnel_name)
                    print("Found credentials at:", src_path)
                    Clock.schedule_once(lambda dt, line='Found credentials': self.update_text(line))

                    actv_json = active_dir / f"{tunnel_name}.json"
                    dst_json = bundle_dir / f"{tunnel_name}.json"
                    try:
                        shutil.copy(src_path, dst_json)
                    except Exception as e:
                        Clock.schedule_once(lambda dt, line=str(e): self.update_text(line))

                    config = {
                        "tunnel": tunnel_name,
                        "credentials-file": str(actv_json.resolve()),
                        "ingress": [
                            {
                                "hostname": hostname,
                                "service": f"http://localhost:{port}"
                            },
                            {"service": "http_status:404"}
                        ]
                    }
                    
                    text = f"Creating config.yaml"
                    Clock.schedule_once(lambda dt, line=text: self.update_text(line))
                    config_path = bundle_dir / "config.yml"
                    with open(config_path, "w") as f:
                        yaml.dump(config, f)

                    shutil.copy(dst_json, active_dir / f"{tunnel_name}.json")
                    shutil.copy(config_path, active_dir / "config.yml")

                    text = f"Creating DNS route: {hostname}"
                    print(text)
                    Clock.schedule_once(lambda dt, line=text: self.update_text(line))
                    try:
                        subprocess.run(["cloudflared", "tunnel", "route", "dns", tunnel_name, hostname], check=True)
                    except Exception as e:
                        Clock.schedule_once(lambda dt, line=str(e): self.update_text(line))

                    self.selected_node['nodeData']['address'] = hostname
                    operatorData['myNodes'][self.selected_node['nodeData']['id']] = self.selected_node
                    write_operatorData(operatorData)

                    text = "✅ Tunnel created, bundle stored, active config ready."
                    print(text)
                    Clock.schedule_once(lambda dt, line=text: self.update_text(line))
                    Clock.schedule_once(lambda dt, line='Completed': self.update_status(line))
                    return
        except Exception as e:
            print('create cloudflare tunnel for self fail', str(e))
            Clock.schedule_once(lambda dt, line=str(e): self.update_text(line))

        Clock.schedule_once(lambda dt, line='Incomplete': self.update_status(line))

    # not used
    def edit_lighthouse(self, action, operatorData=None):
        reactivate = False
        operatorData = get_operatorData(operatorData)
        if 'abilities' not in self.selected_node['nodeData']:
            self.selected_node['nodeData']['abilities'] = {}
        if action == 'enable':
            self.selected_node['nodeData']['abilities']['lighthouse'] = True
            reactivate = True
        elif 'lighthouse' in self.selected_node['nodeData']['abilities'] and self.selected_node['nodeData']['abilities']['lighthouse']:
            del self.selected_node['nodeData']['abilities']['lighthouse']
        operatorData['myNodes'][self.selected_node['nodeData']['id']] = self.selected_node
        write_operatorData(operatorData)

        Clock.schedule_once(lambda dt, line=f'Saving...': self.update_text(line))
        if reactivate and self.selected_node['nodeData']['activated_dt']:
            print('reactivate node')
            from commands.utils import declare_self_active, config_lighthouse
            config_lighthouse(operatorData=operatorData)
            resp = declare_self_active(True, activate_tasker=False)
            print('resp of declare state',resp)
            Clock.schedule_once(lambda dt, line=resp: self.update_text(line))
        else:
            Clock.schedule_once(lambda dt, line=f'Saved': self.update_text(line))
        

    def update_text(self, line):
        try:
            self.text_input.text += f'{line}\n'
        except Exception as e:
            print('update_text fail s',str(e))

    def refresh_sidebar(self, instance=None):
        try:
            self.parent_screen.refresh_sidebar()
        except Exception as e:
            print('settings sidebar refresh fail:',str(e))

    def update_status(self, line):
        try:
            self.save_button.text = line
        except:
            pass
        try:
            self.syncData_button.text = line
        except:
            pass

    def update_border(self, *args):
        self.border.rectangle = (self.content.x, self.content.y, self.content.width, self.content.height)

    def update_rect(self, *args):
        self.rect.size = self.size
        self.rect.pos = self.pos

class ProfileScreen(BoxLayout):
    def __init__(self, parent=None, **kwargs):
        super(ProfileScreen, self).__init__(**kwargs)
        self.parent_screen = parent

        with self.canvas.before:
            Color(0.094, 0.122, 0.176, 1)
            self.rect = Rectangle(size=self.size, pos=self.pos)
            self.bind(size=self.update_rect, pos=self.update_rect)

    def activate_display(self):
        print('-proflie activate_display')
        self.title = Label(text='Profile', size_hint_y=None, height=dp(30), halign='center')
        self.add_widget(self.title)
        self.superuser = False
        operatorData = get_operatorData()
        if 'userData' in operatorData:
            fields = operatorData['userData']
            if isinstance(fields, dict):
                if 'user_is_super' in operatorData:
                    fields['user_is_super'] = operatorData['user_is_super']
                if 'userPass' in operatorData:
                    fields['user_pass'] = operatorData['userPass']
                if 'systemPass' in operatorData:
                    fields['systemPass'] = fetch_secure_item('sysPass')
                if 'seed_ip' in operatorData:
                    fields['seed_ip'] = operatorData['seed_ip']
        else:
            fields = {}

        self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True, scroll_type=['bars', 'content'],bar_width=17, bar_color=(1, 1, 1, 1), bar_inactive_color=(1, 1, 1, .3))
        self.content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=5)
        self.content.bind(minimum_height=self.content.setter("height"))

        self.content.add_widget(Divider(padding=0))
        self.skipfields = ['objType', 'id', 'networkChain', 'commitChain', 'signkey_dt', 'created', 'lastUpdate', 'must_rename', 'modlVer', 'publicKey', 'signed','region_set_date','user_is_super','pattern','nodeCreatorId','UserData_obj','UserVerification_obj']
        self.omitfields = ['signed']
        row_index = 0
        for key, value in fields.items():
            if key not in self.omitfields:
                if key in self.skipfields:
                    self.content.add_widget(FieldRow(key, value, superuser=False, editable=False))
                else:
                    self.content.add_widget(FieldRow(key, value, superuser=True, editable=True))
        
        if 'userData' in operatorData and 'id' in operatorData['userData'] and 'user_is_super' in operatorData and operatorData['user_is_super'] == True:
            if verify_super_status(operatorData):
                self.superuser = True
                commands = []
                commands.append({'title':"Settings",'action':partial(self.settings)})
                commands.append({'title':"Local Data",'action':partial(self.show_localData)})
                commands.append({'title':"Edit Sonet",'action':partial(self.edit_object, 'sonet', operatorData)})
                
                self.content.add_widget(FieldRow('Actions', commands, parent=self, is_button_list=True))

        self.scroll_view.add_widget(self.content)
        self.add_widget(self.scroll_view)
        self.save_button = Button(text='Save', size_hint=(1, None), height=dp(30))
        self.save_button.bind(on_press=self.save_data)
        self.add_widget(self.save_button)
        # self.localData_button = Button(text='Local Data', size_hint=(1, None), height=dp(30))
        # self.localData_button.bind(on_press=self.show_localData)
        # self.parent_screen.display_layout.add_widget(self.localData_button)
    
    def settings(self):
        # save button not working
        self.remove_widget(self.title)
        self.remove_widget(self.scroll_view)
        self.remove_widget(self.content)
        self.remove_widget(self.save_button)

        title = Label(text='SoNode Settings', size_hint_y=None, height=dp(30) * w_scale, font_size=dp(13) * t_scale, halign='center')
        self.add_widget(title)

        self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        self.content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(5) * w_scale)
        self.content.bind(minimum_height=self.content.setter("height"), minimum_width=self.content.setter("width"))
        self.scroll_view.add_widget(self.content)
        self.add_widget(self.scroll_view)

        filename = Path.home() / "Sonet" / ".data" / "settings.json"
        with filename.open("r", encoding="utf-8") as f:
            data = json.load(f)

        for key, val in data.items():
            self.content.add_widget(FieldRow(key, val, editable=True))

        self.text_input = TextInput(
            text='', 
            multiline=True, 
            halign='left', 
            size_hint=(1, 1),
            background_color=dark_blue2,
            foreground_color=(1, 1, 1, 1),
            font_size=dp(13) * t_scale
        )
        self.text_input.bind(minimum_height=self.text_input.setter('height'))
        self.add_widget(self.text_input)

        self.save_button = Button(text='Save', size_hint=(1, None), height=dp(30) * w_scale, font_size=dp(13) * t_scale)
        self.save_button.bind(on_press=self.save_settings)
        self.add_widget(self.save_button)

    def save_settings(self, instance=None):
        self.save_button.text = 'Saving...'
        threading.Thread(target=self.save_settings_step2, args=(operatorData,)).start()

    def save_settings_step2(self, operatorData=None):
        filename = Path.home() / "Sonet" / ".data" / "settings.json"
        with filename.open("r", encoding="utf-8") as f:
            data = json.load(f)

        objData = [child for child in reversed(self.content.children) if isinstance(child, FieldRow)]
        for i in objData:
            label = i.title_label.text
            try:
                value = i.input.text
            except Exception as e:
                value = i.input.active
            data[label] = value
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        self.save_button.text = 'Saved'


    def save_data(self, operatorData=None, instance=None):
        self.save_button.text = 'Saving...'
        threading.Thread(target=self.save_data_step2, args=(operatorData,)).start()

    def save_data_step2(self, operatorData=None):
        # currently adjusts sonet data only, not profile data
        if not operatorData:
            operatorData = get_operatorData()

        if True: # for sonet edit
            objData = parse_fields(items=[child for child in reversed(self.content.children) if isinstance(child, FieldRow)])
            nodes = get_node_list(operatorData=operatorData)
            domain = None
            if 'info' in objData:
                for key, value in objData.items():
                    if key == 'Domain' and not value:
                        pass
                    elif key == 'Domain' and value:
                        objData[key] = value
                        domain = value
                    else:
                        objData[key] = value
            sonetData = sign(objData)
            data = {'sonetData' : json.dumps(sonetData)}
            for nodeId, ip in nodes.items():
                r = connect_to_node(ip, 'accounts/set_sonet', data=data, operatorData=operatorData)
                if r:
                    received_json = r.json()
                    break
            print('message',received_json['message'])
            if received_json['message'] == 'Success':
                operatorData = get_operatorData()
                operatorData['domain'] = domain
                operatorData['sonet'] = json.loads(received_json['sonet'])
                write_operatorData(operatorData)
                Clock.schedule_once(lambda dt, line='Saved': self.update_status(line))

            else:
                Clock.schedule_once(lambda dt, line='Error': self.update_status(line))
        else:
            full_nodeData = operatorData['myNodes'][operatorData['selected_node']]

            objData = sign(objData)

            data = {'objData' : json.dumps(objData)}
            print('senddata:',data)
            r = connect_to_node(full_nodeData['settings']['localhost'], 'utils/set_object_data', data=data, operatorData=operatorData)
            if r:
                received_json = r.json()
                print('message',received_json['message'])
                if received_json['message'] == 'Success':
                    print('All GooD!')
                    Clock.schedule_once(lambda dt, line='Saved': self.update_status(line))
                else:
                    Clock.schedule_once(lambda dt, line=received_json['message']: self.update_status(line))
            else:
                Clock.schedule_once(lambda dt, line='Save Error': self.update_status(line))

    def show_localData(self, instance=None, target_tree=[]):
        expand_user_data(self, target_tree=target_tree)

    def edit_object(self, obj=None, operatorData=None, instance=None):
        print('-profile edit_object', obj)
        try:
            self.remove_widget(self.title)
            self.remove_widget(self.scroll_view)
            self.remove_widget(self.content)
        except:
            pass
        
        extra_fields = {}
        latest_singing_fields = {}

        if self.superuser and obj == 'sonet':
            if not operatorData:
                operatorData = get_operatorData()
            obj_data = operatorData['sonet']
            obj_type = 'Sonet'
            self.title = Label(text=f'Edit Sonet', size_hint_y=None, height=dp(30), halign='center')
            self.add_widget(self.title)
            data = {'obj_type' : obj_type, 'obj_id' : obj_data['id']}
            
            self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
            self.content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=5)
            self.content.bind(minimum_height=self.content.setter("height"), minimum_width=self.content.setter("width"))

            self.skipfields = ['objType', 'id', 'modlVer', 'func', 'created', 'lastUpdate', 'DateTime', 'publicKey', 'signed', 'CreatorNode_obj', 'validatorNodeId']

            row_index = 0
            form_fields = {}
            for key, value in obj_data.items():
                if value == 'None':
                    value = None
                form_fields[key] = value
            for key, value in form_fields.items():
                self.content.add_widget(FieldRow(key, value, superuser=False if key in self.skipfields else self.superuser, editable=True))
            self.scroll_view.add_widget(self.content)
            self.add_widget(self.scroll_view)

            if self.superuser:
                self.save_button = Button(text='Save', size_hint=(1, None), height=dp(30))
                self.save_button.disabled = not self.superuser
                self.save_button.bind(on_press=lambda instance: self.save_data(operatorData))
                self.parent_screen.display_layout.add_widget(self.save_button)

    def update_status(self, line):
        self.save_button.text = line

    def update_rect(self, *args):
        self.rect.size = self.size
        self.rect.pos = self.pos

class SetupScreen(BoxLayout):
    def __init__(self, parent=None, option=None, host=None, parentRegionId=None, obj_type=None, obj_id=None, following_cmd=None, **kwargs):
        super(SetupScreen, self).__init__(**kwargs)
        print('-SetupScreen', option, parent,'host',host)
        self.option = option
        self.host = host
        self.remote_data = None
        self.parent_screen = parent
        self.parent_screen.job_running = False
        self.command_runner = None
        self.debug = False
        self.enableTasker = True
        self.broadcastState = True
        self.syncDatabase = True
        self.isTesting = False
        self.fullSync = False
        self.abort_function = False
        self.parentRegionId = parentRegionId
        self.obj_type = obj_type
        self.obj_id = obj_id
        self.following_cmd = following_cmd
        self.install_ops = ['install', 'new_node_remote', 'new_node_local']

        with self.canvas.before:
            Color(0.094, 0.122, 0.176, 1)
            self.rect = Rectangle(size=self.size, pos=self.pos)
            self.bind(size=self.update_rect, pos=self.update_rect)
    

    def activate_display(self, instance=None, remote=None):
        try:
            self.parent_screen.display_layout.remove_widget(self.field)
            self.content.remove_widget(self.text_input)
            self.scroll_view.remove_widget(self.content)
            self.remove_widget(self.scroll_view)
        except:
            pass
        try:
            self.field.remove_widget(self.back_button)
            self.parent_screen.display_layout.remove_widget(self.field)
        except:
            pass
        try:
            self.field.remove_widget(self.next_button)
            self.parent_screen.display_layout.remove_widget(self.field)
        except:
            pass
        if self.option and self.option != 'new_network':
            if self.option.lower() == 'new_node_local':
                self.host = 'local'
            elif self.option.lower() == 'new_node_remote':
                self.host = 'remote'
                self.remote_data = remote
            elif self.option.lower() == 'install':
                self.host = 'local'

            self.operatorData = get_operatorData()
            self.full_nodeData = None
            if self.option.lower() in self.install_ops:
                self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True, scroll_type=['bars', 'content'],bar_width=17, bar_color=(1, 1, 1, 1), bar_inactive_color=(1, 1, 1, .3))
                self.content = BoxLayout(orientation="vertical", size_hint_y=None)
                self.content.bind(minimum_height=self.content.setter("height"))
                self.title = Label(text='New Install', size_hint_y=None, height=dp(30), halign='center')
                self.add_widget(self.title)
                self.add_widget(Divider(padding=0))
                self.text_input = TextInput(
                    text="",
                    size_hint_x=1,
                    size_hint_y=None,
                    halign="left",
                    multiline=True, 
                    background_color=dark_blue2,
                    foreground_color=(1, 1, 1, 1) 
                )
                self.text_input.bind(minimum_height=self.update_textinput_height)
                Window.bind(size=self.update_textinput_height)
                self.update_textinput_height()
                self.content.add_widget(self.text_input)
                self.scroll_view.add_widget(self.content)
                self.add_widget(self.scroll_view)
                if self.host == 'remote' and ('sonet' not in self.operatorData or not self.operatorData['sonet']):
                    texts = [
                        '''Network setup not currently supported on remote install.''',
                    ]
                    for text in texts:
                        self.text_input.text += text + '\n\n'
                else:
                    if self.host != 'local':
                        line1 = f'''You are about to begin the process of installing a remote a SoNode on {self.remote_data["nickname"]}.'''
                        device_label = self.remote_data["nickname"]

                    else:
                        line1 = '''You are about to begin the process of creating a SoNode.'''
                        device_label = "this device"
                    if 'sonet' in self.operatorData and self.operatorData['sonet'] != '':
                        try:
                            sonet_title = self.operatorData['sonet']['Title'] + ' ' + self.operatorData['sonet']['Subtitle']
                            coin_name_plural = self.operatorData['sonet']['token_info']['plural']
                        except:
                            sonet_title = 'this new sonet'
                            coin_name_plural = 'tokens'
                    else:
                        sonet_title = 'this new sonet'
                        coin_name_plural = 'tokens'
                    texts = [
                        line1,
                        f'''As a SoNode, {device_label} will contribute to the speed and integrity of {sonet_title}. It will host and serve data to peer nodes and connected users, as well as take part in the creation of new blocks. When new blocks are created and validated by peers, a small amount of {coin_name_plural} are awarded to the block creator.''',
                        '''It is strongly recommended that you run this software on a stand alone computer that contains no personal information and has a unique password. The system password is encrypted and stored for access by this program. If you change the system password you must update it here as well to continue operations. '''
                        f'''By continuing from here, you will be required to grant system permissions to this app after which a number of requirements such as Ngnix and Django will be installed on this system. You will be able to select which regions you wish to support. The more regions you support the more {coin_name_plural} you will be eligible to receive and the more demanding it will be on this system.''',
                        f'''Keep {device_label} in a single location, plugged in and awake at all times. Repeated failures to connect to this node or poor performance will result in removal from the network.''',
                        '''Other devices will see the IP address of this node if you are not running a VPN''',
                        '''Only use quick install if you have previously used quick uninstall''',
                        '''After setup is complete and you activate this node a connection will be established with peer nodes and relevant data up to this point will be downloaded. This node will then be open to serving data and receiving rewards.''',
                    ]
                    if 'debug' in self.operatorData and self.operatorData['debug']:
                        texts.append('''\n*Notice*\nYou have debug activated, requirements will not be installed while in this state.\nTurn off debug in settings or continue.''')
                    for text in texts:
                        self.text_input.text += text + '\n\n'

                    self.add_widget(Divider(padding=0))
                    debug = False
                    if 'user_is_super' in self.operatorData:
                        debug = self.operatorData['user_is_super']
                    debug = True
                    if debug:
                        self.test_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=dp(30))
                        self.test_label = Label(text='Debug:', size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(130))
                        with self.test_label.canvas.before:
                            Color(1, 1, 1, 1)
                        self.test_input = CheckBox(size_hint=(1, None), height=dp(30), active=True)
                        self.test_layout.add_widget(self.test_label)
                        self.test_layout.add_widget(self.test_input)
                        self.add_widget(self.test_layout)
                    
                    self.new_database_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=dp(30))
                    self.new_database_label = Label(text='Reuse Database:', size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(130))
                    with self.new_database_label.canvas.before:
                        Color(1, 1, 1, 1)
                    self.new_database_input = CheckBox(size_hint=(1, None), height=dp(30), active=False)
                    self.new_database_layout.add_widget(self.new_database_label)
                    self.new_database_layout.add_widget(self.new_database_input)
                    self.add_widget(self.new_database_layout)

                    self.quick_install_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=dp(30))
                    self.quick_install_label = Label(text='Quick Install:', size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(130))
                    with self.quick_install_label.canvas.before:
                        Color(1, 1, 1, 1)
                    self.quick_install_input = CheckBox(size_hint=(1, None), height=dp(30), active=False)
                    self.quick_install_layout.add_widget(self.quick_install_label)
                    self.quick_install_layout.add_widget(self.quick_install_input)
                    self.add_widget(self.quick_install_layout)

                    self.port_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=dp(30))
                    self.port_label = Label(text="Port:", size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(130))
                    with self.port_label.canvas.before:
                        Color(1, 1, 1, 1)
                    if 'port' in self.operatorData:
                        port = self.operatorData['port']
                    else:
                        port = '9909'
                    self.port_input = TextInput(text=port, size_hint=(1, None), height=dp(30), disabled=True)

                    self.port_layout.add_widget(self.port_label)
                    self.port_layout.add_widget(self.port_input)
                    self.add_widget(self.port_layout)

                    self.open_ports_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=dp(30))
                    self.open_ports_label = Label(text="Open Ports:", size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(130))
                    with self.open_ports_label.canvas.before:
                        Color(1, 1, 1, 1)
                    if 'open_ports' in self.operatorData:
                        open_ports = self.operatorData['open_ports']
                    else:
                        open_ports = '22, 5900, 3389'
                    self.open_ports_input = TextInput(text=open_ports, size_hint=(1, None), height=dp(30))

                    self.open_ports_layout.add_widget(self.open_ports_label)
                    self.open_ports_layout.add_widget(self.open_ports_input)
                    self.add_widget(self.open_ports_layout)

                    if self.remote_data:
                        node_nickname = self.remote_data['nickname']
                    else:
                        node_nickname = platform.node()
                    # elif 'username' in self.operatorData:
                    #     node_nickname = self.operatorData['username'] + "'s Node " + str(random.randint(100, 999))
                    # else:
                    #     node_nickname = 'Node ' + str(random.randint(100, 999))

                    self.node_nickname_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=dp(30))
                    self.node_nickname_label = Label(text="Node Name:", size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(130))
                    with self.node_nickname_label.canvas.before:
                        Color(1, 1, 1, 1)
                    self.node_nickname_input = TextInput(text=node_nickname, size_hint=(1, None), height=dp(30))
                    self.node_nickname_layout.add_widget(self.node_nickname_label)
                    self.node_nickname_layout.add_widget(self.node_nickname_input)
                    self.add_widget(self.node_nickname_layout)

                    if self.remote_data:
                        self.systemPass = self.remote_data['password']
                    else:
                        self.pass_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=dp(30))
                        self.toggle_button = Button(text='Show', size_hint_x=None, width=dp(70))
                        self.pass_label = Label(text="System Password:", size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(130))
                        with self.pass_label.canvas.before:
                            Color(1, 1, 1, 1)
                        self.pass_input = TextInput(text='', hint_text="system pass needed, kept on device", size_hint=(1, None), height=dp(30), multiline=False, password=True)
                        self.pass_input.bind(on_text_validate=lambda instance: self.run_install(instance))
                        self.pass_input.focus = True
                        self.toggle_button.bind(on_press=self.toggle_password_visibility)
                        self.pass_layout.add_widget(self.pass_label)
                        self.pass_layout.add_widget(self.pass_input)
                        self.pass_layout.add_widget(self.toggle_button)
                        self.add_widget(self.pass_layout)
                    if 'userPass' not in self.operatorData or not self.operatorData['userPass']:
                        if 'accnt_privKey' not in self.operatorData or not self.operatorData['accnt_privKey'] or 'accnt_pubKey' not in self.operatorData or not self.operatorData['accnt_pubKey']:
                            self.passphrase_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=dp(30))
                            self.toggle_button = Button(text='Show', size_hint_x=None, width=dp(70))
                            self.passphrase_label = Label(text=f"{self.operatorData['username']} Passphrase:", size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(130))
                            with self.passphrase_label.canvas.before:
                                Color(1, 1, 1, 1)
                            self.passphrase_input = TextInput(text='', hint_text="passphrase not stored after install", size_hint=(1, None), height=dp(30), multiline=False, password=True)
                            self.passphrase_input.bind(on_text_validate=lambda instance: self.run_install(instance))
                            self.passphrase_input.focus = True
                            self.toggle_button.bind(on_press=self.toggle_password_visibility)
                            self.passphrase_layout.add_widget(self.passphrase_label)
                            self.passphrase_layout.add_widget(self.passphrase_input)
                            self.passphrase_layout.add_widget(self.toggle_button)
                            self.add_widget(self.passphrase_layout)

                    self.continue_button = Button(text='Install', size_hint=(1, None), height=dp(30))
                    self.continue_button.bind(on_press=self.run_install)
                    self.add_widget(self.continue_button)

            elif self.option.lower() == 'deactivate':
                self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True, scroll_type=['bars', 'content'],bar_width=17, bar_color=(1, 1, 1, 1), bar_inactive_color=(1, 1, 1, .3))
                self.content = BoxLayout(orientation="vertical", size_hint_y=None)
                self.content.bind(minimum_height=self.content.setter("height"))
                self.title = Label(text='Deactivate', size_hint_y=None, height=dp(30), halign='center')
                self.add_widget(self.title)
                self.add_widget(Divider(padding=0))
                self.text_input = TextInput(
                    text="",
                    size_hint_x=1,
                    size_hint_y=None,
                    halign="left",
                    multiline=True, 
                    background_color=dark_blue2,
                    foreground_color=(1, 1, 1, 1) 
                )
                self.text_input.bind(minimum_height=self.update_textinput_height)
                Window.bind(size=self.update_textinput_height)
                self.update_textinput_height()
                self.content.add_widget(self.text_input)
                self.scroll_view.add_widget(self.content)
                self.add_widget(self.scroll_view)
                texts = [
                    '''This will disconnect your node from the network.''',
                    '''You will no longer receive rewards.''',
                    '''Local data will remain.''',
                    '''Logout and uninstall are possible after deactivation.'''
                ]
                for text in texts:
                    self.text_input.text += text + '\n\n'
                self.add_widget(Divider(padding=0))

                self.alive_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=dp(30))
                self.alive_label = Label(text='Keep alive:', size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(130))
                with self.alive_label.canvas.before:
                    Color(1, 1, 1, 1)
                self.alive_input = CheckBox(size_hint=(1, None), height=dp(30), active=False)
                self.alive_layout.add_widget(self.alive_label)
                self.alive_layout.add_widget(self.alive_input)
                self.add_widget(self.alive_layout)
                
                self.continue_button = Button(text='Continue', size_hint=(1, None), height=dp(30))
                self.continue_button.bind(on_press=self.run_deactivate)
                self.add_widget(self.continue_button)

            elif self.option.lower() == 'activate':
                self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True, scroll_type=['bars', 'content'],bar_width=17, bar_color=(1, 1, 1, 1), bar_inactive_color=(1, 1, 1, .3))
                self.content = BoxLayout(orientation="vertical", size_hint_y=None)
                self.content.bind(minimum_height=self.content.setter("height"))
                self.title = Label(text='Activate', size_hint_y=None, height=dp(30), halign='center')
                self.add_widget(self.title)
                self.add_widget(Divider(padding=0))
                self.text_input = TextInput(
                    text="",
                    size_hint_x=1,
                    size_hint_y=None,
                    halign="left",
                    multiline=True, 
                    background_color=dark_blue2,
                    foreground_color=(1, 1, 1, 1) 
                )
                self.text_input.bind(minimum_height=self.update_textinput_height)
                Window.bind(size=self.update_textinput_height)
                self.update_textinput_height()
                self.content.add_widget(self.text_input)
                self.scroll_view.add_widget(self.content)
                self.add_widget(self.scroll_view)
                print('setup activate- self.parent_screen',self.parent_screen)
                if 'selected_node' in self.operatorData:
                    node_id = self.operatorData['selected_node']
                    full_nodeData = self.operatorData['myNodes'][self.operatorData['selected_node']]
                    if 'chainData' not in full_nodeData['meta'] or 'supported_chains' not in full_nodeData['meta']['chainData'] or full_nodeData['meta']['chainData']['supported_chains'] == [] or full_nodeData['meta']['chainData']['supported_chains'] == '[]':
                        texts = [
                        '''Please select your supported Plugins before activating.''',
                        ]
                        for text in texts:
                            self.text_input.text += text + '\n\n'
                        self.add_widget(Divider(padding=0))
                        self.continue_button = Button(text='Select Plugins', size_hint=(1, None), height=dp(30))
                        self.continue_button.bind(on_press=lambda instance: self.parent_screen.switch_layout('plugins'))
                        self.add_widget(self.continue_button)
                    else:    
                        texts = [
                            '''This will connect your node to the network.''',
                            '''Data will be synced and may take some time.''',
                            '''If this is your first activation please wait 1 hour after install.'''
                        ]
                        if 'debug' in full_nodeData['meta'] and full_nodeData['meta']['debug']:
                            texts.append('''\n*Notice*\nYou have debug activated, you will not receive rewards in this state.\nTurn off debug in settings or continue to debug.''')
                        for text in texts:
                            self.text_input.text += text + '\n\n'
                        self.add_widget(Divider(padding=0))

                        if 'debug' in full_nodeData['meta'] and full_nodeData['meta']['debug']:
                            self.debug = True
                            self.broadcast_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=dp(30))
                            self.broadcast_label = Label(text='Broadcast & Sync:', size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(130))
                            with self.broadcast_label.canvas.before:
                                Color(1, 1, 1, 1)
                            self.broadcast_input = CheckBox(size_hint=(1, None), height=dp(30), active=True)
                            self.broadcast_layout.add_widget(self.broadcast_label)
                            self.broadcast_layout.add_widget(self.broadcast_input)
                            self.add_widget(self.broadcast_layout)

                        node_types = ('Server/Maintainer', 'Relay')
                        if verify_super_status(self.operatorData):
                            node_types = ('Server','Maintainer','Server/Maintainer','Intelligence','Relay')
                        try:
                            selected_node_type = 'Server/Maintainer'
                            for n in node_types:
                                if n.lower() == full_nodeData['settings']['node_type'].lower():
                                    selected_node_type = n
                        except:
                            pass
                        self.node_type_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=dp(30))
                        self.node_type_label = Label(text='Node Type:', size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(130))
                        with self.node_type_label.canvas.before:
                            Color(1, 1, 1, 1)
                        self.node_type_input = Spinner(
                                text=selected_node_type,
                                values=node_types,
                                size_hint=(1, 1),
                                height=dp(30),
                                width=dp(130)
                            )
                        self.node_type_input.bind(text=self.spinner_select)
                        self.node_type_layout.add_widget(self.node_type_label)
                        self.node_type_layout.add_widget(self.node_type_input)
                        self.add_widget(self.node_type_layout)

                        if verify_super_status(self.operatorData):
                            node_levels = ('Standard','Super')
                            try:
                                selected_node_level = 'Standard'
                                for n in node_levels:
                                    if n.lower() == full_nodeData['settings']['node_level'].lower():
                                        selected_node_type = n
                            except:
                                pass
                            self.node_level_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=dp(30))
                            self.node_level_label = Label(text='Node Level:', size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(130))
                            with self.node_level_label.canvas.before:
                                Color(1, 1, 1, 1)
                            self.node_level_input = Spinner(
                                    text=selected_node_level,
                                    values=node_levels,
                                    size_hint=(1, 1),
                                    height=dp(30),
                                    width=dp(130)
                                )
                            self.node_level_input.bind(text=self.spinner_select)
                            self.node_level_layout.add_widget(self.node_level_label)
                            self.node_level_layout.add_widget(self.node_level_input)
                            self.add_widget(self.node_level_layout)
                        else:
                            selected_node_level = 'Standard'
                            self.node_level_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=dp(30))
                            self.node_level_label = Label(text='Node Level:', size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(130))
                            with self.node_level_label.canvas.before:
                                Color(1, 1, 1, 1)
                            self.node_level_input = Spinner(
                                    text=selected_node_level,
                                    size_hint=(1, 1),
                                    height=dp(30),
                                    width=dp(130)
                                )
                            self.node_level_input.bind(text=self.spinner_select)
                            self.node_level_layout.add_widget(self.node_level_label)
                            self.node_level_layout.add_widget(self.node_level_input)

                        self.title_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=dp(30))
                        self.title_label = Label(text='Node Name:', size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(130))
                        with self.title_label.canvas.before:
                            Color(1, 1, 1, 1)
                        self.title_input = TextInput(text=full_nodeData['settings']['node_name'], size_hint=(1, None), height=dp(30))
                        self.title_layout.add_widget(self.title_label)
                        self.title_layout.add_widget(self.title_input)
                        self.add_widget(self.title_layout)

                        self.ip_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=dp(30))
                        self.ip_label = Label(text="Address:", size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(130))
                        with self.ip_label.canvas.before:
                            Color(1, 1, 1, 1)
                        address = 'Cloudflare Tunnel'
                        if 'nodeData' in full_nodeData and 'address' in full_nodeData['settings'] and full_nodeData['settings']['address']:
                            address = full_nodeData['settings']['address']
                        self.ip_input = TextInput(text=address, size_hint=(1, None), height=dp(30))
                        self.ip_layout.add_widget(self.ip_label)
                        self.ip_layout.add_widget(self.ip_input)
                        self.add_widget(self.ip_layout)

                        self.port_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=dp(30))
                        self.port_label = Label(text="Port:", size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(130))
                        with self.port_label.canvas.before:
                            Color(1, 1, 1, 1)
                        self.port_input = TextInput(text=full_nodeData['settings']['port'], size_hint=(1, None), height=dp(30), disabled=True)
                        self.port_layout.add_widget(self.port_label)
                        self.port_layout.add_widget(self.port_input)
                        self.add_widget(self.port_layout)

                        self.open_ports_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=dp(30))
                        self.open_ports_label = Label(text="Open Ports:", size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(130))
                        with self.open_ports_label.canvas.before:
                            Color(1, 1, 1, 1)
                        if 'open_ports' in full_nodeData['settings']:
                            open_ports = full_nodeData['settings']['open_ports']
                        else:
                            open_ports = '22, 5900, 3389'
                        self.open_ports_input = TextInput(text=open_ports, size_hint=(1, None), height=dp(30))

                        self.open_ports_layout.add_widget(self.open_ports_label)
                        self.open_ports_layout.add_widget(self.open_ports_input)
                        self.add_widget(self.open_ports_layout)
                        
                        self.continue_button = Button(text='Continue', size_hint=(1, None), height=dp(30))
                        self.continue_button.bind(on_press=self.run_activate)
                        self.add_widget(self.continue_button)

            elif self.option.lower() == 'update':
                self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True, scroll_type=['bars', 'content'],bar_width=17, bar_color=(1, 1, 1, 1), bar_inactive_color=(1, 1, 1, .3))
                self.content = BoxLayout(orientation="vertical", size_hint_y=None)
                self.content.bind(minimum_height=self.content.setter("height"))
                self.title = Label(text='Update', size_hint_y=None, height=dp(30), halign='center')
                self.add_widget(self.title)
                self.add_widget(Divider(padding=0))
                self.text_input = TextInput(
                    text="",
                    size_hint_x=1,
                    size_hint_y=None,
                    halign="left",
                    multiline=True, 
                    background_color=dark_blue2,
                    foreground_color=(1, 1, 1, 1) 
                )
                self.text_input.bind(minimum_height=self.update_textinput_height)
                Window.bind(size=self.update_textinput_height)
                self.update_textinput_height()
                self.content.add_widget(self.text_input)
                self.scroll_view.add_widget(self.content)
                self.add_widget(self.scroll_view)
                self.run_update()
            elif self.option.lower() == 'restart':
                self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True, scroll_type=['bars', 'content'],bar_width=17, bar_color=(1, 1, 1, 1), bar_inactive_color=(1, 1, 1, .3))
                self.content = BoxLayout(orientation="vertical", size_hint_y=None)
                self.content.bind(minimum_height=self.content.setter("height"))
                self.title = Label(text='Restart', size_hint_y=None, height=dp(30), halign='center')
                self.add_widget(self.title)
                self.add_widget(Divider(padding=0))
                self.text_input = TextInput(
                    text="",
                    size_hint_x=1,
                    size_hint_y=None,
                    halign="left",
                    multiline=True, 
                    background_color=dark_blue2,
                    foreground_color=(1, 1, 1, 1) 
                )
                self.text_input.bind(minimum_height=self.update_textinput_height)
                Window.bind(size=self.update_textinput_height)
                self.update_textinput_height()
                self.content.add_widget(self.text_input)
                self.scroll_view.add_widget(self.content)
                self.add_widget(self.scroll_view)
                self.run_restart()
            elif self.option.lower() == 'uninstall':
                self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True, scroll_type=['bars', 'content'],bar_width=17, bar_color=(1, 1, 1, 1), bar_inactive_color=(1, 1, 1, .3))
                self.content = BoxLayout(orientation="vertical", size_hint_y=None)
                self.content.bind(minimum_height=self.content.setter("height"))
                self.title = Label(text='Uninstall', size_hint_y=None, height=dp(30), halign='center')
                self.add_widget(self.title)
                self.add_widget(Divider(padding=0))
                self.text_input = TextInput(
                    text="",
                    size_hint_x=1,
                    size_hint_y=None,
                    halign="left",
                    multiline=True, 
                    background_color=dark_blue2,
                    foreground_color=(1, 1, 1, 1) 
                )
                self.text_input.bind(minimum_height=self.update_textinput_height)
                Window.bind(size=self.update_textinput_height)
                self.update_textinput_height()
                self.content.add_widget(self.text_input)
                self.scroll_view.add_widget(self.content)
                self.add_widget(self.scroll_view)
                if is_nginx_running():
                    texts = [
                        '''Please deactivate your node from the network before uninstall.''',
                    ]
                    for text in texts:
                        self.text_input.text += text + '\n\n'

                    self.add_widget(Divider(padding=0))
                    self.continue_button = Button(text='Deactivate', size_hint=(1, None), height=dp(30))
                    self.continue_button.bind(on_press=self.run_deactivate)
                    self.add_widget(self.continue_button)
                else:
                    texts = [
                        '''This will uninstall your node software.''',
                        '''The database will be cleared and uninstalled.'''
                    ]
                    for text in texts:
                        self.text_input.text += text + '\n\n'
                    self.add_widget(Divider(padding=0))
                    operatorData = get_operatorData()
                    if 'selected_node' in operatorData:
                        node_id = operatorData['selected_node']
                        full_nodeData = operatorData['myNodes'][operatorData['selected_node']]

                    self.test_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=dp(30))
                    self.test_label = Label(text='Preserve Environment:', size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(170))
                    with self.test_label.canvas.before:
                        Color(1, 1, 1, 1)
                    self.test_input = CheckBox(size_hint=(1, None), height=dp(30))
                    self.test_layout.add_widget(self.test_label)
                    self.test_layout.add_widget(self.test_input)
                    self.add_widget(self.test_layout)

                    self.database_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=dp(30))
                    self.database_label = Label(text='Preserve Database:', size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(170))
                    with self.database_label.canvas.before:
                        Color(1, 1, 1, 1)
                    self.database_input = CheckBox(size_hint=(1, None), height=dp(30))
                    self.database_layout.add_widget(self.database_label)
                    self.database_layout.add_widget(self.database_input)
                    self.add_widget(self.database_layout)

                    self.dependencies_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=dp(30))
                    self.dependencies_label = Label(text='Preserve Dependencies:', size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(170))
                    with self.dependencies_label.canvas.before:
                        Color(1, 1, 1, 1)
                    self.dependencies_input = CheckBox(size_hint=(1, None), height=dp(30))
                    self.dependencies_layout.add_widget(self.dependencies_label)
                    self.dependencies_layout.add_widget(self.dependencies_input)
                    self.add_widget(self.dependencies_layout)

                    self.continue_button = Button(text='Continue', size_hint=(1, None), height=dp(30))
                    self.continue_button.bind(on_press=self.run_uninstall)
                    self.add_widget(self.continue_button)
            elif self.option.lower() == 'reinstall':
                self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True, scroll_type=['bars', 'content'],bar_width=17, bar_color=(1, 1, 1, 1), bar_inactive_color=(1, 1, 1, .3))
                self.content = BoxLayout(orientation="vertical", size_hint_y=None)
                self.content.bind(minimum_height=self.content.setter("height"))
                self.title = Label(text='Uninstall', size_hint_y=None, height=dp(30), halign='center')
                self.add_widget(self.title)
                self.add_widget(Divider(padding=0))
                self.text_input = TextInput(
                    text="",
                    size_hint_x=1,
                    size_hint_y=None,
                    halign="left",
                    multiline=True, 
                    background_color=dark_blue2,
                    foreground_color=(1, 1, 1, 1) 
                )
                self.text_input.bind(minimum_height=self.update_textinput_height)
                Window.bind(size=self.update_textinput_height)
                self.update_textinput_height()
                self.content.add_widget(self.text_input)
                self.scroll_view.add_widget(self.content)
                self.add_widget(self.scroll_view)
                texts = [
                    '''This will uninstall your node software.''',
                    '''The database will be cleared and uninstalled.'''
                ]
                for text in texts:
                    self.text_input.text += text + '\n\n'
                self.add_widget(Divider(padding=0))
                self.test_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=dp(30))
                self.test_label = Label(text='Quick Uninstall:', size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(170))
                with self.test_label.canvas.before:
                    Color(1, 1, 1, 1)
                self.test_input = CheckBox(size_hint=(1, None), height=dp(30), active=True)
                self.test_layout.add_widget(self.test_label)
                self.test_layout.add_widget(self.test_input)
                self.add_widget(self.test_layout)

                self.database_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=dp(30))
                self.database_label = Label(text='Preserve Database:', size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(170))
                with self.database_label.canvas.before:
                    Color(1, 1, 1, 1)
                self.database_input = CheckBox(size_hint=(1, None), height=dp(30), active=True)
                self.database_layout.add_widget(self.database_label)
                self.database_layout.add_widget(self.database_input)
                self.add_widget(self.database_layout)

                self.dependencies_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=dp(30))
                self.dependencies_label = Label(text='Preserve Dependencies:', size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(170))
                with self.dependencies_label.canvas.before:
                    Color(1, 1, 1, 1)
                self.dependencies_input = CheckBox(size_hint=(1, None), height=dp(30), active=True)
                self.dependencies_layout.add_widget(self.dependencies_label)
                self.dependencies_layout.add_widget(self.dependencies_input)
                self.add_widget(self.dependencies_layout)
                self.run_uninstall()
            elif self.option.lower() == 'syncdb':
                self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True, scroll_type=['bars', 'content'],bar_width=17, bar_color=(1, 1, 1, 1), bar_inactive_color=(1, 1, 1, .3))
                self.content = BoxLayout(orientation="vertical", size_hint_y=None)
                self.content.bind(minimum_height=self.content.setter("height"))
                self.title = Label(text='Sync Database', size_hint_y=None, height=dp(30), halign='center')
                self.add_widget(self.title)
                self.add_widget(Divider(padding=0))
                self.text_input = TextInput(
                    text="",
                    size_hint_x=1,
                    size_hint_y=None,
                    halign="left",
                    multiline=True, 
                    background_color=dark_blue2,
                    foreground_color=(1, 1, 1, 1) 
                )
                self.text_input.bind(minimum_height=self.update_textinput_height)
                Window.bind(size=self.update_textinput_height)
                self.update_textinput_height()
                self.content.add_widget(self.text_input)
                self.scroll_view.add_widget(self.content)
                self.add_widget(self.scroll_view)
                operatorData = get_operatorData()
                texts = [
                    '''This will sync new data from the network to this node.''',
                ]
                for text in texts:
                    self.text_input.text += text + '\n\n'

                debug = False
                if 'selected_node' in operatorData:
                    self.add_widget(Divider(padding=0))
                    node_id = operatorData['selected_node']
                    full_nodeData = operatorData['myNodes'][operatorData['selected_node']]
                    if 'debug' in full_nodeData['meta'] and full_nodeData['meta']['debug']:
                        debug = True
                    if debug:
                        self.total_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=dp(30))
                        self.total_label = Label(text='Total sync:', size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(130))
                        with self.total_label.canvas.before:
                            Color(1, 1, 1, 1)
                        self.total_input = CheckBox(size_hint=(1, None), height=dp(30))
                        self.total_layout.add_widget(self.total_label)
                        self.total_layout.add_widget(self.total_input)
                        self.add_widget(self.total_layout)
                        self.purge_button = Button(text='Purge DB', size_hint=(1, None), height=dp(30))
                        self.purge_button.bind(on_press=self.purgeDB)
                        self.add_widget(self.purge_button)

                    self.continue_button = Button(text='Continue', size_hint=(1, None), height=dp(30))
                    self.continue_button.bind(on_press=self.run_syncDB)
                    self.add_widget(self.continue_button)

        else:
            print('else setup')
            try:
                self.remove_widget(self.title)
                self.content.remove_widget(self.title)
            except:
                pass
            try:
                self.remove_widget(self.text_input)
                self.content.remove_widget(self.text_input)
            except:
                pass
            try:
                self.scroll_view.remove_widget(self.content)
                self.remove_widget(self.scroll_view)
                self.parent_screen.display_layout.remove_widget(self.field)
            except:
                pass

            self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True, scroll_type=['bars', 'content'],bar_width=17, bar_color=(1, 1, 1, 1), bar_inactive_color=(1, 1, 1, .3))
            self.content = BoxLayout(orientation="vertical", size_hint_y=None)
            self.content.bind(minimum_height=self.content.setter("height"))

            latest_singing_fields = None
            self.operatorData = get_operatorData()
            if self.operatorData and 'user_is_super' in self.operatorData and self.operatorData['user_is_super'] == True:
                self.superuser = verify_super_status(self.operatorData)
            else:
                self.superuser = False
            if self.option == 'new_network':
                print('network_setup_form_layout')
                self.title = Label(text='New Sonet', size_hint_y=None, height=dp(30), halign='center')
                self.add_widget(self.title)
                self.add_widget(Divider(padding=0))
                if 'sonet' in self.operatorData and self.operatorData['sonet'] != '' and self.operatorData['sonet'] != None:
                    print("operatorData['sonet']::", self.operatorData['sonet'])
                    fields = self.operatorData['sonet']
                else:
                    self.superuser = True
                    fields = {'objType' : 'Sonet', 'Title' : '', 'Subtitle' : '', 'LogoLink' : "img/default_logo.png", 'Domain':'', 'info': {}, 'token_info' : {'name':'Token','plural':'Tokens'}, 'repo' : {'source':'github.com', 'repo':'', 'branch':'main'}, 'node_requirements': {'MIN_LOGICAL_CORES':4,'MIN_FREQ_GHZ':2.0,'MIN_RAM_GB':7.5,'MIN_DISK_GB':200,'MIN_WINDOWS_MAJOR':10,'MIN_MACOS_MINOR':13,'MIN_LINUX_KERNEL':(6, 00),'MIN_DOWNLOAD_MBPS':21.0,'MIN_UPLOAD_MBPS':4.0,'MAX_BENCHMARK_SECS':6.0,'MIN_DOWNLOAD_MBPS':5.0}}
                    fields = {'objType' : 'Sonet', 'Title' : 'SoSayDev', 'Subtitle' : 'Development Branch', 'LogoLink' : "img/sologo.png", 'Domain':'sosaydev.com', 'info': {}, 'token_info' : {'name':'hoho','plural':'hohos'}, 'repo' : {'source':'github.com', 'repo':'SoSayUs', 'branch':'dev'}, 'node_requirements': {'MIN_LOGICAL_CORES':4,'MIN_FREQ_GHZ':2.0,'MIN_RAM_GB':7.5,'MIN_DISK_GB':200,'MIN_WINDOWS_MAJOR':10,'MIN_MACOS_MINOR':13,'MIN_LINUX_KERNEL':(6, 00),'MIN_DOWNLOAD_MBPS':21.0,'MIN_UPLOAD_MBPS':2.0,'MAX_BENCHMARK_SECS':10.0,'MIN_DOWNLOAD_MBPS':5.0}}
            else: # install new network
                print('else2 setup')
                fields = {} 
                if 'seed_ip' in self.operatorData:
                    nodes = get_node_list(operatorData=self.operatorData)
                    for nodeId, ip in nodes.items():
                        try:
                            r = connect_to_node(ip, '/utils/get_sonet', operatorData=self.operatorData, timeout=(4,10))
                            print('r.status_code',r.status_code)
                            if r and r.status_code == 200:
                                received_json = r.json()
                                print('received_json',received_json)
                                if 'message' in received_json and received_json['message'] == 'success':
                                    fields = json.loads(received_json['signing_obj'])
                                else:
                                    fields = {}
                            elif 'sonet' in self.operatorData and self.operatorData['sonet'] != '' and self.operatorData['sonet'] != None:
                                self.title = Label(text=self.operatorData['sonet']['Title'], size_hint_y=None, height=dp(30), halign='center')
                                self.add_widget(self.title)
                                print("operatorData['sonet']::", self.operatorData['sonet'])
                                fields = self.operatorData['sonet']
                            break
                        except:
                            pass

            self.skipfields = ['objType', 'id', 'modlVer', 'func', 'created', 'lastUpdate', 'DateTime', 'publicKey', 'signed', 'CreatorNode_obj', 'validatorNodeId']

            form_fields = {}
            for key, value in fields.items():
                if value == 'None':
                    value = None
                form_fields[key] = value
            if latest_singing_fields:
                for key, value in form_fields.items():
                    if key in latest_singing_fields:
                        self.content.add_widget(FieldRow(key, value, editable=False if key in self.skipfields else self.superuser))

                self.content.add_widget(Label(text='New model version fields', halign='left'))
                for key, value in latest_singing_fields.items():
                    if key not in form_fields:
                        self.content.add_widget(FieldRow(key, value, editable=False if key in self.skipfields else self.superuser))

                self.content.add_widget(Label(text='Old fields being removed', halign='left'))
                for key, value in form_fields.items():
                    if key not in latest_singing_fields:
                        self.content.add_widget(FieldRow(key, value, editable=False if key in self.skipfields else self.superuser))
            else:
                for key, value in form_fields.items():
                    self.content.add_widget(FieldRow(key, value, editable=False if key in self.skipfields else self.superuser))

            self.scroll_view.add_widget(self.content)
            self.add_widget(self.scroll_view)
            if self.superuser:
                if self.option == 'new_network':
                    text = 'Continue'
                else:
                    text = 'Save'
                self.save_button = Button(text=text, size_hint=(1, None), height=dp(30))
                self.save_button.disabled = not self.superuser
                self.save_button.bind(on_press=self.save_data)
                self.add_widget(self.save_button)

    def update_border(self, *args):
        self.border.rectangle = (self.content.x, self.content.y, self.content.width, self.content.height)

    def update_rect(self, *args):
        self.rect.size = self.size
        self.rect.pos = self.pos

    def update_textinput_height(self, *args):
        self.text_input.height = max(
            self.text_input.minimum_height,
            Window.height
        )
    
    def spinner_select(self, spinner, text):
        # self.node_type_input.text = text
        return text

    def abort(self, instance=None):
        try:
            self.abort_button.text = 'Aborting...'
            self.abort_function = True
        except Exception as e:
            print('abort fail 61', str(e))

    def save_data(self, instance):
        self.save_button.text = 'Saving...'
        threading.Thread(target=self.save_data_step2).start()

    def save_data_step2(self):
        print('-save_data_step2 setup', self.obj_type, self.obj_id)
        operatorData = get_operatorData()
        objData = parse_fields(items=[child for child in reversed(self.content.children) if isinstance(child, FieldRow)])
        if self.parentRegionId or self.obj_type and self.obj_id:
            extra_objData = {}
            if 'func' in objData:
                objData['func'] = 'super'
            if 'CreatorNode_obj' in objData:
                objData['CreatorNode_obj'] = operatorData['local_nodeId']
            if 'validatorNodeId' in objData:
                objData['validatorNodeId'] = operatorData['local_nodeId']
            objData = sign(objData)
            data = {'objData' : json.dumps(objData), 'nodeData' : json.dumps(operatorData['myNodes'][operatorData['local_nodeId']]['nodeData'])}
            r = connect_to_node(operatorData['localhost'], 'utils/get_object_id', data=data, operatorData=operatorData)
            if r:
                received_json = r.json()
                if received_json['message'] == 'Success':
                    received_json['message'] = 'Error'
                    newId = received_json['obj_id']
                    objData['id'] = newId
                    objData = sign(objData)

                    data = {'objData' : json.dumps(objData), 'extra_objData' : json.dumps(extra_objData), 'super_share': True}
                    r = connect_to_node(operatorData['localhost'], 'utils/set_object_data', data=data, operatorData=operatorData)
                    if r:
                        received_json = r.json()
                        if received_json['message'] == 'Success':
                            print('All GooD!')
                            Clock.schedule_once(lambda dt, line='Saved': self.update_status(line))
                        else:
                            Clock.schedule_once(lambda dt, line=received_json['message']: self.update_status(line))
                    else:
                        Clock.schedule_once(lambda dt, line='Save Error': self.update_status(line))
                else:
                    Clock.schedule_once(lambda dt, line=received_json['message']: self.update_status(line))
            else:
                Clock.schedule_once(lambda dt, line='Save Error': self.update_status(line))
        else:
            print('save setup opt 2', operatorData)
            if 'sonet' not in operatorData:
                try:
                    self.remove_widget(self.save_button)
                except:
                    pass
                operatorData['new_sonet'] = objData
                write_operatorData(operatorData)
                Clock.schedule_once(lambda dt: self.switch_to_install())
            else:
                nodes = get_node_list(operatorData=operatorData)
                domain = None
                if 'info' in objData:
                    for key, value in objData.items():
                        if key == 'Domain' and not value:
                            pass
                        elif key == 'Domain' and value:
                            objData[key] = value
                            domain = value
                        else:
                            objData[key] = value
                sonetData = sign(objData, operatorData=operatorData)
                data = {'sonetData' : json.dumps(sonetData)}
                for nodeId, ip in nodes.items():
                    r = connect_to_node(ip, 'accounts/set_sonet', data=data, operatorData=operatorData)
                    if r:
                        received_json = r.json()
                        break
                if received_json['message'] == 'Success':
                    operatorData = get_operatorData()
                    if domain:
                        operatorData['domain'] = domain
                    operatorData['sonet'] = json.loads(received_json['sonet'])
                    write_operatorData(operatorData)
                    Clock.schedule_once(lambda dt, line='Saved': self.update_status(line))
                    Clock.schedule_once(lambda dt: self.update_sonet_screen())
                else:
                    Clock.schedule_once(lambda dt, line='Error': self.update_status(line))

    def update_sonet_screen(self): # unused i think
        try:
            self.scroll_view.remove_widget(self.content)
            self.remove_widget(self.scroll_view)
            self.remove_widget(self.save_button)
        except:
            pass
        
        operatorData = get_operatorData()
        fields = operatorData['sonet']

        self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        self.content = BoxLayout(orientation="vertical", size_hint_y=None)
        self.content.bind(minimum_height=self.content.setter("height"))
    
        for key, value in fields.items():
            if key in self.skipfields:
                form = FieldRow(key, value, superuser=False)
            else:
                form = FieldRow(key, value, superuser=self.superuser)
            self.content.add_widget(form)

        self.scroll_view.add_widget(self.content)
        self.add_widget(self.scroll_view)

        if self.superuser:
            self.save_button = Button(text='Saved', size_hint=(1, None), height=dp(30))
            self.save_button.disabled = not self.superuser
            self.save_button.bind(on_press=self.save_data)
            self.add_widget(self.save_button)

    def switch_to_install(self):
        print('-switch to install')
        self.parent_screen.switch_layout('new_node_local')

    def switch_to_operations(self, instance, refresh=False):
        if refresh:
            x = self.parent_screen.manager.get_screen('operator_screen')
            x.refresh_sidebar()

        self.parent_screen.manager.current = 'operator_screen'


    def refresh_ipA(self, instance, display=None):
        print('-refresh_ip')
        if display:
            display.text = 'refreshing...'
        Clock.schedule_once(lambda dt, line='refreshing ip...\n': self.update_text(line))
    
    def refresh_ip_step2A(self, instance=None, display=None): # not in use
        external_ip = None
        operatorData = get_operatorData()
        if 'ip_master_list' in operatorData and len(operatorData['ip_master_list']) > 2:
            for ip in operatorData['ip_master_list']:
                try:
                    external_ip = requests.get('https://' + ip + '/utils/myip').content.decode('utf8')
                    break
                except:
                    pass
        if not external_ip:
            external_ip = requests.get('https://api.ipify.org').content.decode('utf8')
        print('external_ip',external_ip)
        if display:
            display.text = external_ip
        return external_ip

    def purgeDB(self, instance=None):
        self.parent_screen.job_running = True
        try:
            self.remove_widget(self.continue_button)
            self.remove_widget(self.total_layout)
            self.remove_widget(self.purge_button)
        except Exception as e:
            print('purgeDB err',str(e))

        commands = []
        special_commands = {}
        context = {'task':'purgeDB', 'system':device_system}
        
        if 'local_nodeId' in self.operatorData and self.operatorData['selected_node'] == self.operatorData['local_nodeId']:
            self.host = 'local'
            remote_node = self.operatorData['myNodes'][self.operatorData['selected_node']]
            commands, special_commands = get_commands(context['task'], system=context['system'], operatorData=None, in_full=False, extras={})
        else:
            self.host = 'remote'
            remote_node = self.operatorData['selected_node']
            send_manager_to_remote(self.operatorData['selected_node'])
            
        self.command_runner = CommandRunner(self, commands, self.content, self.text_input, special_commands, remote_data=remote_node, finish_command=self.finish_setup, main_screen=self.parent_screen, operatorData=self.operatorData, context=context)
        threading.Thread(target=self.command_runner.run_commands).start()

    def run_syncDB(self, instance=None):
        self.parent_screen.job_running = True
        try:
            self.remove_widget(self.continue_button)
            self.remove_widget(self.total_layout)
            self.fullSync = self.total_input.active
            self.remove_widget(self.purge_button)
        except Exception as e:
            print('run_syncDB err',str(e))
        
        self.abort_button = Button(text='Abort', size_hint=(1, None), height=dp(30))
        self.abort_button.bind(on_press=self.abort)
        self.add_widget(self.abort_button)
        
        self.command_runner = CommandRunner(self, [], self.content, self.text_input, {}, finish_command=self.run_syncDB_step2)
        threading.Thread(target=self.command_runner.run_commands).start()

    def run_syncDB_step2(self, instance=None):
        print('-run_syncDB_step2', now_utc())
        commands = []
        commands.append(['run_command', 'sync_database'])
        commands.append(['run_command', 'remove_abort_button'])
        from commands.utils import sync_database
        self.install2 = CommandRunner(self, commands, self.content, self.text_input, {'sync_database' :{'cmd':'sync_database', 'reqs':['output_display','parent_screen'], 'func':sync_database},'remove_abort_button' :{'cmd':'remove_abort_button', 'func':self.remove_abort_button}}, main_screen=self.parent_screen)
        threading.Thread(target=self.install2.run_commands).start()

    def toggle_password_visibility(self, instance):
        try:
            if self.pass_input.password:
                self.pass_input.password = False
                instance.text = 'Hide'
            else:
                self.pass_input.password = True
                instance.text = 'Show'
        except:
            pass
        try:
            if self.passphrase_input.password:
                self.passphrase_input.password = False
                instance.text = 'Hide'
            else:
                self.passphrase_input.password = True
                instance.text = 'Show'
        except:
            pass

    def enter_password(self, instance):
        # print('-enter_password')
        systemPass = self.pass_input.text
        if self.host == 'local':
            store_secure_item("sysPass", systemPass)
        try:
            self.field.remove_widget(self.back_button)
            self.field.remove_widget(self.pass_input)
            self.field.remove_widget(self.toggle_button)
            self.parent_screen.display_layout.remove_widget(self.field)
        except:
            pass

        threading.Thread(target=self.run_install_step2).start()
    
    def is_valid_port(self, port_str):
        try:
            port = int(port_str)
            if port > 1023 and port <= 65535 or port == 80:
                return True
            else:
                return False
        except ValueError:
            return False


    def run_install(self, instance=None):
        print('-run_install')
        self.parent_screen.job_running = True
        if self.remote_data:
            self.text_input.text = f'Installing on {self.remote_data["nickname"]} ({device_system})...\n\n'
        else:
            self.text_input.text = f'Installing on {device_system}...\n\n'
        try:
            self.test_layout.remove_widget(self.test_label)
            self.test_layout.remove_widget(self.test_input)
            self.remove_widget(self.test_layout)
        except:
            pass
        try:
            self.quick_install_layout.remove_widget(self.quick_install_label)
            self.quick_install_layout.remove_widget(self.quick_install_input)
            self.remove_widget(self.quick_install_layout)
        except:
            pass
        try:
            self.new_database_layout.remove_widget(self.new_database_label)
            self.new_database_layout.remove_widget(self.new_database_input)
            self.remove_widget(self.new_database_layout)
        except:
            pass
        try:
            self.remove_widget(self.continue_button)
        except:
            pass
        try:
            self.port_layout.remove_widget(self.port_label)
            self.port_layout.remove_widget(self.port_input)
            self.remove_widget(self.port_layout)
        except:
            pass
        try:
            self.open_ports_layout.remove_widget(self.open_ports_label)
            self.open_ports_layout.remove_widget(self.open_ports_input)
            self.remove_widget(self.open_ports_layout)
        except:
            pass
        try:
            self.ip_layout.remove_widget(self.ip_button)
            self.ip_layout.remove_widget(self.ip_input)
            self.remove_widget(self.ip_layout)
        except:
            pass
        try:
            self.node_nickname_layout.remove_widget(self.node_nickname_label)
            self.node_nickname_layout.remove_widget(self.node_nickname_input)
            self.remove_widget(self.node_nickname_layout)
        except:
            pass
        try:
            self.user_passphrase = self.passphrase_input.text
            self.passphrase_layout.remove_widget(self.passphrase_input)
            self.passphrase_layout.remove_widget(self.toggle_button)
            self.passphrase_layout.remove_widget(self.passphrase_label)
            self.remove_widget(self.passphrase_layout)
        except Exception as e:
            print('fail remove syspass box',str(e))
            if 'userPass' in self.operatorData and self.operatorData['userPass']:
                self.user_passphrase = self.operatorData['userPass']
        try:
            self.systemPass = self.pass_input.text
            store_secure_item("sysPass", self.systemPass)
            self.pass_layout.remove_widget(self.pass_input)
            self.pass_layout.remove_widget(self.toggle_button)
            self.pass_layout.remove_widget(self.pass_label)
            self.remove_widget(self.pass_layout)
        except Exception as e:
            print('fail remove syspass box 2',str(e))
            pass

        self.abort_button = Button(text='Abort', size_hint=(1, None), height=dp(30))
        self.abort_button.bind(on_press=self.abort)
        self.add_widget(self.abort_button)
        threading.Thread(target=self.run_install_step2).start()

        # check this somewhere in run_install
        # port = self.port_input.text
        # print('port',port)
        # valid_port = self.is_valid_port(port)
        # if not valid_port:
        #     r = f'\nPlease enter a valid port between 1023 and 65535. You entered {port}'
        #     Clock.schedule_once(lambda dt, line=r: self.update_text(line))
        #     Clock.schedule_once(lambda dt: self.add_button(text='Back', action=partial(self.activate_display)))
        #     # self.text_input.text ='Please enter a valid port between 1023 and 65535'
        #     return

    def run_install_step2(self, instance=None):
        context = {'task':'install', 'system':device_system, 'extras':{}}
        node_settings = {}
        try:
            context['debug'] = self.test_input.active
        except:
            context['debug'] = False
        self.debug = context['debug']
        context['extras']['debug'] = context['debug']
        try:
            node_settings['node_name'] = self.node_nickname_input.text
        except:
            node_settings['node_name'] = 'Node ' + str(random.randint(100, 999))
        try:
            context['extras']['quick_install'] = self.quick_install_input.active
        except:
            context['extras']['quick_install'] = False
        try:
            context['extras']['new_database'] = self.new_database_input.active
        except:
            context['extras']['new_database'] = True
        try:
            open_ports = self.open_ports_input.text
            node_settings['open_ports'] = open_ports
        except:
            open_ports = '' # 22, 5900, 3389
            node_settings['open_ports'] = open_ports

        if self.remote_data:
            try:
                homepath = expanduser("~")
                repo_path = homepath + "/Sonet/SoNodeServer"
                if not os.path.exists(repo_path):
                    # make sure local pass exists or is requested
                    text = f'Fetching from repo...\n'
                    Clock.schedule_once(lambda dt, line=text: self.update_text(line))
                    from commands.utils import pull_git_server
                    pull_git_server(output=self.text_input.text, operatorData=self.operatorData)

                text = f'Connecting to remote...\n'
                Clock.schedule_once(lambda dt, line=text: self.update_text(line))
                connected, self = make_remote_connection(self.remote_data, cls=self)
                if connected:
                    text = f'Sending codebase to remote...\n'
                    Clock.schedule_once(lambda dt, line=text: self.update_text(line))
                    if send_manager_to_remote(self.remote_data, ssh_client=self.ssh_client, text_display=self.text_input.text):
                        text = f'Initializing remote codebase...\n'
                        Clock.schedule_once(lambda dt, line=text: self.update_text(line))
                        fetch_remote_commands('ready_check', self.ssh_client, extras=context)

                        text = f'Fetching remote operator data...\n'
                        Clock.schedule_once(lambda dt, line=text: self.update_text(line))
                        remote_opData = fetch_remote_data(self.remote_data, operatorData=self.operatorData, fetch_key=True, ssh_client=self.ssh_client)
                        remote_opData['sonet'] = self.operatorData['sonet']
                        remote_opData['userData'] = self.operatorData['userData']
                        remote_opData['seed_ip'] = self.operatorData['seed_ip']
                        if '127.0.0.1' in remote_opData['seed_ip']:
                            remote_opData['seed_ip'] = fetch_secure_item('address')
                        remote_opData['username'] = self.operatorData['username']
                        remote_opData['user_id'] = self.operatorData['user_id']
                        remote_opData['upkData'] = self.operatorData['upkData']
                        remote_opData['user_is_super'] = self.operatorData['user_is_super']
                        remote_opData['ip_master_list'] = self.operatorData['ip_master_list']
                        remote_opData['open_ports'] = open_ports

                        if 'accnt_privKey' in self.operatorData and self.operatorData['accnt_privKey'] and 'accnt_pubKey' in self.operatorData and self.operatorData['accnt_pubKey']:
                            remote_opData['accnt_privKey'] = self.operatorData['accnt_privKey']
                            remote_opData['accnt_pubKey'] = self.operatorData['accnt_pubKey']
                        else:
                            keyPair = createKeyPair(self.operatorData['user_id'], self.user_passphrase, 'account', key_strength='ML_DSA_44')
                            privKey = keyPair[0]
                            pubKey = keyPair[1]
                            remote_opData['accnt_privKey'] = privKey
                            remote_opData['accnt_pubKey'] = pubKey

                        self.current_install = node_settings['node_name']
                        node_settings['port'] = self.port_input.text
                        remote_opData['port'] = node_settings['port']
                        node_settings['external_ip'] = ''
                        node_settings['address'] = 'Cloudflare Tunnel'
                        
                        node_settings_remote = node_settings.copy()
                        node_settings_remote['localhost'] = '127.0.0.1:' + node_settings['port']
                        node_settings['localhost'] = self.remote_data['local_address'] + ":" + node_settings['port']

                        node_meta = {'debug':self.debug, 'password':Mnemonic("english").generate(strength=256), 'install_dt':dt_to_string(now_utc()), 'node_registered': False}
                        if 'sonet' in self.operatorData and 'Domain' in self.operatorData['sonet']:
                            node_meta['domain'] = self.operatorData['sonet']['Domain']

                        new_node_data = {'settings':node_settings, 'meta':node_meta, 'location':self.remote_data['nickname']}
                        new_node_data_remote = {'settings':node_settings_remote, 'meta':node_meta, 'location':'local'}
                        if not 'myRemotes' in remote_opData:
                            remote_opData['myRemotes'] = {}
                        
                        if 'myNodes' not in remote_opData:
                            remote_opData['myNodes'] = {}

                        local_host = {'nickname':'local', 'address':'127.0.0.1', 'username':'self', 'password':self.remote_data['password'], 'os_type':self.remote_data['os_type']}
                        remote_opData['myRemotes']['local'] = local_host
                        self.operatorData['myNodes'][f'new_install-{self.current_install}'] = new_node_data
                        remote_opData['myNodes'][f'new_install-{self.current_install}'] = new_node_data_remote
                        remote_opData['start_local_install'] = True
                        self.operatorData['start_remote_install'] = True
                        write_operatorData(self.operatorData)
                        
                        text = f'Updating remote operator data...\n'
                        Clock.schedule_once(lambda dt, line=text: self.update_text(line))
                        from commands.utils import update_remote_data
                        if update_remote_data(remote_opData=remote_opData, remote_data=self.remote_data, operatorData=self.operatorData, remote_password=self.remote_data['password'], output=self.text_input):
                            stdin, stdout, stderr = self.ssh_client.exec_command(
                                'python3 ~/Sonet/SoNodeManager/scripts/venv_setup.py',
                                get_pty=True,
                            )
                            # Block until the remote process finishes, streaming output locally
                            for line in iter(stdout.readline, ''):
                                print(f'[remote] {line}', end='')
                            exit_code = stdout.channel.recv_exit_status()
                            print(f'[remote] exited with code {exit_code}')
                            self.ssh_client.close()
                            text = f'Beginning remote install...\n'
                            Clock.schedule_once(lambda dt, line=text: self.update_text(line))
                            self.command_runner = CommandRunner(self, [], self.content, self.text_input, {}, remote_data=self.remote_data, main_screen=self.parent_screen, context=context, finish_command=self.finish_setup, operatorData=self.operatorData)
                            threading.Thread(target=self.command_runner.run_commands).start()
                            print('finsihed install step 2')
                        else:
                            print('failed to update remote data')
            except Exception as e:
                text = f'\nInstall Error B: {e}\n\n'
                print('install step 2 err',text)
                Clock.schedule_once(lambda dt, line=text: self.update_text(line))

        elif self.host == 'local':
            try:
                self.operatorData['open_ports'] = open_ports
                if 'myNodes' not in self.operatorData:
                    self.operatorData['myNodes'] = {}

                self.current_install = node_settings['node_name']
                node_settings['port'] = self.port_input.text
                self.operatorData['port'] = self.port_input.text
                from commands.utils import refresh_ip
                node_settings['external_ip'] = refresh_ip()
                node_settings['address'] = 'Cloudflare Tunnel'
                node_settings['localhost'] = '127.0.0.1:' + node_settings['port']

                if 'accnt_privKey' in self.operatorData and self.operatorData['accnt_privKey'] and 'accnt_pubKey' in self.operatorData and self.operatorData['accnt_pubKey']:
                    pass
                elif 'user_id' in self.operatorData and self.operatorData['user_id']:
                    text = f'Generating quantum safe key pair...\n'
                    Clock.schedule_once(lambda dt, line=text: self.update_text(line))
                    keyPair = createKeyPair(self.operatorData['user_id'], self.user_passphrase, 'account', key_strength='ML_DSA_44')
                    privKey = keyPair[0]
                    pubKey = keyPair[1]
                    self.operatorData['accnt_privKey'] = privKey
                    self.operatorData['accnt_pubKey'] = pubKey

                node_meta = {'debug':self.debug, 'password':Mnemonic("english").generate(strength=256), 'install_dt':dt_to_string(now_utc()), 'node_registered': False}
                if 'sonet' in self.operatorData and 'Domain' in self.operatorData['sonet']:
                    node_meta['domain'] = self.operatorData['sonet']['Domain']

                new_node_data = {'settings':node_settings, 'meta':node_meta}
                if self.host == 'local':
                    if not 'myRemotes' in self.operatorData:
                        self.operatorData['myRemotes'] = {}
                    local_host = {'nickname':'local', 'address':'127.0.0.1', 'username':'self', 'password':fetch_secure_item("sysPass"), 'os_type':device_system}
                    self.operatorData['myRemotes']['local'] = local_host
                    new_node_data['location'] = 'local'
                remove = []
                for n in self.operatorData['myNodes']:
                    if 'new_install' in n:
                        remove.append(n)
                for n in remove:
                    del self.operatorData['myNodes'][n]
                self.operatorData['myNodes'][f'new_install-{self.current_install}'] = new_node_data
                self.operatorData['start_local_install'] = True
                write_operatorData(self.operatorData)
                
                from commands.utils import pull_git_server
                pull_git_server(output=self.text_input.text, operatorData=self.operatorData)

                commands, special_commands = get_commands(context['task'], system=context['system'], extras=context['extras'])
                commands.append(['run_command', 'finish_setup'])
                special_commands['finish_setup'] = {'cmd':'finish_setup', 'func':self.finish_setup}
                self.command_runner = CommandRunner(self, commands, self.content, self.text_input, special_commands, main_screen=self.parent_screen, context=context, operatorData=self.operatorData)

                threading.Thread(target=self.command_runner.run_commands).start()
            except Exception as e:
                text = f'\nInstall Error A: {e}\n\n'
                Clock.schedule_once(lambda dt, line=text: self.update_text(line))

    def run_install_step2x(self):
        print('-run_install_step2x')
        from os.path import expanduser
        import getpass
        homepath = expanduser("~")
        username = getpass.getuser()
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
        try:
            from commands.utils import get_package_manager
            package_manager = get_package_manager()
            remote_url = f"https://{git_username}:{git_password}@github.com/{git_repo}.git"
            if package_manager:
                commands.append(["sudo", "-S", package_manager, "install", "git", "-y"])
            elif device_system == 'mac':
                commands.append(["sudo", "-S", 'brew', "install", "git", "-y"])
            commands.append(["git", "init", homepath + "/Sonet/SoNodeServer"])
            commands.append(['git', '-C', homepath + "/Sonet/SoNodeServer", 'remote', 'add', 'soserver', remote_url])
            commands.append(["git", '-C', homepath + "/Sonet/SoNodeServer",  "branch", "-M", "main"])
            commands.append(["git", '-C', homepath + "/Sonet/SoNodeServer",  "reset", "--hard"])
            commands.append(["git", '-C', homepath + "/Sonet/SoNodeServer",  "pull", "soserver", "main"])
        except Exception as e:
            print('git fail', str(e))
            time.sleep(10)
            return
            pass
        print('commands:',commands)
        commands.append(['run_command', 'run_install_step3'])
        self.install2 = CommandRunner(self, commands, self.content, self.text_input, {'run_install_step3' :{'cmd':'run_install_step3', 'func':self.run_install_step3}})
        threading.Thread(target=self.install2.run_commands).start()

    def run_install_step3x(self):
        print('-run_install step3')
        from os.path import expanduser
        homepath = expanduser("~")
        if self.host == 'local':
            retreived_systemPass = fetch_secure_item('sysPass')
            print('retreived_systemPass',retreived_systemPass)
        else:
            # add password to remote device
            print('not local host')

        operatorData = get_operatorData()
        with open(homepath + "/Sonet/.data/special/cors.conf", "w") as f:
            f.write("map $http_origin $cors_origin {\n")
            f.write('    default "";\n')
            if 'seed_ip' in operatorData:
                f.write(f'    "{operatorData["seed_ip"]}" $http_origin;\n')
            f.write("}\n")
            
        node_settings = {}
        try:
            self.debug = self.test_input.active
        except:
            self.debug = False
        try:
            node_nickname = self.node_nickname_input.text
        except:
            node_nickname = 'Node ' + str(random.randint(100, 999))
        try:
            quick_install = self.quick_install_input.active
        except:
            quick_install = False
        try:
            new_database = self.new_database_input.active
        except:
            new_database = True
        try:
            open_ports = self.open_ports_input.text
            node_settings['open_ports'] = open_ports
            operatorData['open_ports'] = open_ports
        except:
            open_ports = '' # 22, 5900, 3389
            node_settings['open_ports'] = open_ports

        port = self.port_input.text
        valid_port = self.is_valid_port(port)
        if not valid_port:
            r = f'\nPlease enter a valid port between 1023 and 65535. You entered {port}'
            Clock.schedule_once(lambda dt, line=r: self.update_text(line))
            Clock.schedule_once(lambda dt: self.add_button(text='Back', action=partial(self.activate_display)))
            return
        
        if 'myNodes' not in operatorData:
            operatorData['myNodes'] = {}

        self.current_install = node_nickname
        node_settings['node_name'] = node_nickname
        node_settings['port'] = port
        operatorData['port'] = port
        node_settings['external_ip'] = refresh_ip()
        node_settings['address'] = 'Cloudflare Tunnel'
        if self.host == 'local':
            node_settings['localhost'] = '127.0.0.1:' + port
        else:
            node_settings['localhost'] = self.host['address'] + port

        new_node_data = {'settings':node_settings, 'meta':{'debug':self.debug, 'password':Mnemonic("english").generate(strength=256), 'install_dt':dt_to_string(now_utc())}}
        if self.host == 'local':
            if not 'myRemotes' in operatorData:
                operatorData['myRemotes'] = {}
            local_host = {'nickname':'local', 'address':'127.0.0.1', 'username':'self', 'password':fetch_secure_item("sysPass"), 'os_type':device_system}
            operatorData['myRemotes']['local'] = local_host
            new_node_data['location'] = 'local'
        else:
            new_node_data['location'] = self.host['nickname']
        operatorData['myNodes'][f'new_install-{self.current_install}'] = new_node_data
        operatorData['start_local_install'] = True
        write_operatorData(operatorData)
        
        context = {'task':'install', 'system':device_system, 'debug':self.debug, 'quick_install':quick_install, 'new_database':new_database}
        if self.host == 'local':
            import getpass
            import requests
            from os.path import expanduser
            username = getpass.getuser()
            homepath = expanduser("~")
            commands, special_commands = get_commands(context['task'], system=context['system'], extras={'debug':context['debug'], 'quick_install':context['quick_install'], 'new_database':context['new_database']})
            print(commands, special_commands)
            if device_system == 'linux':
                port_commands = [
                    ["sudo", "-S", "ufw", "enable"],
                    ['run_command', 'run_install_step4'],
                ]
            
            elif device_system == 'mac':
                port_commands = [
                    ['run_command', 'run_install_step4'],
                ]
            commands.append(['run_command', 'finish_setup'])
            special_commands['finish_setup'] = {'cmd':'finish_setup', 'func':self.finish_setup}
            self.command_runner = CommandRunner(self, commands, self.content, self.text_input, special_commands, main_screen=self.parent_screen, context=context)

            self.port_runner = CommandRunner(self, port_commands, self.content, self.text_input, {'open_port' :{'cmd':'open_port', 'func':self.open_port}, 'run_install_step4' :{'cmd':'run_install_step4', 'func':self.run_install_step4}}, context=context)
            threading.Thread(target=self.port_runner.run_commands).start()
            
    def run_install_step4x(self):
        threading.Thread(target=self.command_runner.run_commands).start()

    def run_finish_command(self, instance=None):
        threading.Thread(target=self.finish_setup).start()

    def open_port(self):
        try:
            print('-open port start')
            import miniupnpc
            operatorData = get_operatorData()
            port_to_open = int(operatorData['port'])
            upnp = miniupnpc.UPnP()
            upnp.discoverdelay = 200
            num_devices = upnp.discover()
            print(f"Discovered {num_devices} UPnP devices")

            # first discovered device
            upnp.selectigd()
            print('upnp.lanaddr',upnp.lanaddr)

            external_port = port_to_open   # The port on the router that will be forwarded
            internal_port = port_to_open   # The port on your machine that will receive the traffic
            internal_ip = upnp.lanaddr  # Local IP address of the machine
            protocol = 'TCP'       # Protocol type ('TCP' or 'UDP')
            description = 'SoNode'

            try:
                upnp.addportmapping(external_port, protocol, internal_ip, internal_port, description, '')
                added = [True, f"Port {external_port} {protocol} opened successfully."]
            except Exception as e:
                added = [False, f"Failed to open port {external_port} {protocol}: {e}"]

            # Verify the port mapping
            try:
                mappings = upnp.getspecificportmapping(external_port, protocol)
                if mappings:
                    map = f"Port mapping details: {mappings}"
                else:
                    map = f"No mapping found for port {external_port} {protocol}."
            except Exception as e:
                map = f"Error retrieving port mapping: {e}"
        except Exception as e:
            added = [False, 'Failed to open port. %s' %(str(e))]
            map = ''
        print('added',added)
        output = added[1] + '\n' + map + '\n'
        Clock.schedule_once(lambda dt, line=output: self.update_text(line))
        print('done')
        print('reengage ufw')
        # upnp.deleteportmapping(external_port, protocol)
        return

    def refresh_sidebar(self, instance=None, line=None):
        try:
            self.parent_screen.refresh_sidebar()
        except:
            pass
    
    def add_button(self, text='Continue', action=None):
        try:
            if text.lower() == 'back':
                self.back_button = Button(text='Back', size_hint_x=None, width=dp(70))
                self.back_button.bind(on_release=action)
                self.field.add_widget(self.back_button)
            else:
                self.next_button = Button(text=text, size_hint=(1, None), height=dp(30))
                self.next_button.bind(on_press=action)
                self.add_widget(self.next_button)
        except:
            pass

    def add_continue_button(self):
        try:
            self.next_button = Button(text='Continue', size_hint=(1, None), height=dp(30))
            self.next_button.bind(on_press=partial(self.parent_screen.switch_to_operations, refresh=True))
            self.add_widget(self.next_button)
            
        except:
            pass

    def finish_setup(self, instance=None):
        print('-finish_setup', self.option)
        try:
            self.remove_widget(self.abort_button)
        except:
            pass
        if self.option.lower() in self.install_ops:
            print('self.option.lower()',self.option.lower())
            Clock.schedule_once(lambda dt, line='\nInstall commands complete.\n': self.update_text(line))
            app_operational = False
            external_access = False
            error_code = 'finalizing'
            print('error_code',error_code)
            result = None
            operatorData = get_operatorData() # refresh operatorData after install

            if f'new_install-{self.current_install}' in operatorData['myNodes']:
                new_node = operatorData['myNodes'][f'new_install-{self.current_install}']
            else:
                for node_id, node_data in operatorData['myNodes'].items():
                    if 'location' in node_data and node_data['location'] == 'local':
                        new_node = node_data
                        break

            print('installed node~~~',new_node)
            new_node_settings = new_node['settings']
            try:
                if self.remote_data:
                    try:
                        del operatorData['start_remote_install']
                    except:
                        pass
                    Clock.schedule_once(lambda dt, line='\nSyncing operator data...\n': self.update_text(line))
                    remote_opData = fetch_remote_data(self.remote_data, operatorData=operatorData, fetch_key=True, ssh_client=None)
                    new_node = remote_opData['myNodes'][remote_opData['local_nodeId']]
                    self.remote_data['node_id'] = new_node['nodeData']['id']
                    operatorData['myRemotes'][self.remote_data['nickname']] = self.remote_data
                    write_operatorData(operatorData)
                    text = '\nRemote install finished.\n'
                    Clock.schedule_once(lambda dt, line=text: self.update_text(line))

                else:
                    local = requests.get(f'http://{new_node_settings["localhost"]}/utils/is_sonet')
                    if local.status_code == 200:
                        error_code = 'active'
                        app_operational = True
                        text = f'\nApp is operational at http://{new_node_settings["localhost"]}\n'
                        Clock.schedule_once(lambda dt, line=text: self.update_text(line))
                        if 'sonet' in operatorData:
                            error_code = 'continue1'
                            text = '\nLocal install finished.\n'
                            Clock.schedule_once(lambda dt, line=text: self.update_text(line))
                        elif 'new_sonet' in operatorData and operatorData['new_sonet'] != '':
                            error_code = 'continue2'
                            # send superuser and sonet to new database server
                            # replace 'new_sonet' with sonet data
                            now = now_utc()
                            print('----------now:',dt_to_string(now))
                            newnet = {}
                            newnet['created'] = dt_to_string(now)

                            newnet['id'] = 'ohSo' + generate_id(length=14)
                            # newnet['id'] = 'ohSohVQmm16CNAIPGbrrix8' # !!!!!!!!
                            # REMEMBER TO TURN THIS OFF IN PRODUCTION
                            # also remove earth id below
                            # also remove super user passphrase and name (and second super user)
                            # also remove default sonet data from activate_display.else
                            # also second_super_id below


                            text = '\nIntializing database...\n'
                            Clock.schedule_once(lambda dt, line=text: self.update_text(line))
                            time.sleep(1)
                            new_net = operatorData['new_sonet']

                            user_id = super_id(create=now, net=newnet, operatorData=operatorData)

                            error_code = 'continue3'

                            text = '\nCreating SuperUser...\n'
                            Clock.schedule_once(lambda dt, line=text: self.update_text(line))
                            temp_userPass_var = operatorData['userPass']
                            keyPair = createKeyPair(user_id, temp_userPass_var, 'account', key_strength='ML_DSA_44')
                            privKey = keyPair[0]
                            pubKey = keyPair[1]
                            operatorData['accnt_privKey'] = privKey
                            operatorData['accnt_pubKey'] = pubKey
                            operatorData['user_id'] = user_id
                            operatorData['user_is_super'] = True

                            result = '\nNew Sonet setup incomplete.'
                            operatorData['seed_ip'] = new_node_settings["localhost"]
                            write_operatorData(operatorData)
                            from commands.utils import get_or_create_node_obj, hash_upk_id
                            self_nodeDetails, is_new = get_or_create_node_obj(operatorData, register_data=False)
                            operatorData = get_operatorData()
                            self_nodeData = self_nodeDetails['nodeData']
                            self_node_upkData = self_nodeDetails['upk']
                            new_node_settings = self_nodeDetails['settings']
                            error_code = 'node created'
                            data = {}
                            error_code = 'get_user_login'

                            r = requests.post(f'http://{new_node_settings["localhost"]}/accounts/create_user', data={'username':operatorData['username']})
                            received_json = r.json()
                            userData = json.loads(received_json['userData'])
                            walletData = json.loads(received_json['walletData'])
                            upkData_accnt = json.loads(received_json['upkData'])
                            upkData_sign = json.loads(received_json['upkData'])
                            upkData_super = json.loads(received_json['upkData'])
                            upkData_wallet = json.loads(received_json['upkData'])
                            reward_walletData = walletData.copy()
                            walletData['User_obj'] = user_id
                            walletData['created'] = dt_to_string(now)
                            walletData['lastUpdate'] = dt_to_string(now)
                            walletData['Name'] = 'Main'
                            # walletData = sign(walletData, privKey=privKey, pubKey=pubKey, bypass_last_updated_dt=True)
                            # data['walletData'] = json.dumps(walletData)

                            # should include in get_or_create_node_obj instead of here
                            wal_id_data = {'objType':'Wallet','User_obj':user_id,'Name':'Rewards'}
                            id_len = received_json['id_len']
                            reward_walletData['id'] = '1walSo' + generate_id(wal_id_data, length=id_len)
                            reward_walletData['User_obj'] = user_id
                            reward_walletData['networkChain'] = user_id
                            reward_walletData['created'] = dt_to_string(now)
                            reward_walletData['lastUpdate'] = dt_to_string(now)
                            reward_walletData['Name'] = f"Rewards-{self_nodeData['id']}"
                            reward_walletData = sign(reward_walletData, privKey=privKey, pubKey=pubKey, bypass_last_updated_dt=True)
                            data['reward_walletData'] = json.dumps(reward_walletData)

                            upkData_accnt['id'] = hash_upk_id(pubKey)
                            upkData_accnt['User_obj'] = user_id
                            upkData_accnt['created'] = dt_to_string(now)
                            upkData_accnt['lastUpdate'] = dt_to_string(now)
                            upkData_accnt['publicKey'] = pubKey
                            upkData_accnt['keyType'] = 'account'
                            upkData_accnt['algorithm'] = 'ML_DSA_44'
                            upkData_accnt = sign(upkData_accnt, privKey=privKey, pubKey=pubKey, verify_result=True, bypass_last_updated_dt=True)
                            data['upkData_accnt'] = json.dumps(upkData_accnt)

                            keyPair = createKeyPair(user_id, f"{dt_to_string(now)}{temp_userPass_var}", 'signing', key_strength='secp256k1')
                            upkData_sign['id'] = hash_upk_id(keyPair[1])
                            upkData_sign['User_obj'] = user_id
                            upkData_sign['created'] = dt_to_string(now)
                            upkData_sign['lastUpdate'] = dt_to_string(now)
                            upkData_sign['publicKey'] = keyPair[1]
                            upkData_sign['keyType'] = 'signing'
                            upkData_sign['algorithm'] = 'secp256k1'
                            upkData_sign = sign(upkData_sign, privKey=privKey, pubKey=pubKey, verify_result=True, bypass_last_updated_dt=True)
                            data['upkData_sign'] = json.dumps(upkData_sign)

                            wallet_keyPair = createKeyPair(user_id, temp_userPass_var, f"wallet-{reward_walletData['Name']}", key_strength='secp256k1')
                            upkData_wallet['id'] = hash_upk_id(wallet_keyPair[1])
                            upkData_wallet['User_obj'] = user_id
                            upkData_wallet['created'] = dt_to_string(now)
                            upkData_wallet['lastUpdate'] = dt_to_string(now)
                            upkData_wallet['publicKey'] = wallet_keyPair[1]
                            upkData_wallet['keyType'] = 'Wallet'
                            upkData_wallet['algorithm'] = 'secp256k1'
                            upkData_wallet = sign(upkData_sign, privKey=privKey, pubKey=pubKey, verify_result=True, bypass_last_updated_dt=True)
                            data['upkData_wallet'] = json.dumps(upkData_sign)

                            super_keyPair = createKeyPair(user_id, temp_userPass_var, 'guardian', key_strength='ML_DSA_87')
                            upkData_super['id'] = hash_upk_id(super_keyPair[1])
                            upkData_super['User_obj'] = user_id
                            upkData_super['created'] = dt_to_string(now)
                            upkData_super['lastUpdate'] = dt_to_string(now)
                            upkData_super['publicKey'] = super_keyPair[1]
                            upkData_super['keyType'] = 'guardian'
                            upkData_super['algorithm'] = 'ML_DSA_87'
                            upkData_super = sign(upkData_super, privKey=super_keyPair[0], pubKey=super_keyPair[1], verify_result=True, bypass_last_updated_dt=True)
                            data['upkData_super'] = json.dumps(upkData_super)

                            userData['id'] = user_id
                            userData['username'] = operatorData['username']
                            userData['created'] = dt_to_string(now)
                            userData['networkChain'] = user_id
                            userData['lastUpdate'] = dt_to_string(now_utc())
                            userData['signkey_dt'] = dt_to_string(now)
                            for key, value in userData.items():
                                if '_array' in str(key):
                                    userData[key] = json.dumps([])

                            node_keys = fetch_secure_item('node_keys')
                            self_node_upkData['id'] = hash_upk_id(node_keys['pubKey'])
                            self_node_upkData['created'] = dt_to_string(now)
                            self_node_upkData['lastUpdate'] = dt_to_string(now)
                            self_node_upkData['publicKey'] = node_keys['pubKey']
                            self_node_upkData['keyType'] = 'node'
                            self_node_upkData['algorithm'] = 'secp256k1'
                            node_upkData = sign(self_node_upkData, privKey=privKey, pubKey=pubKey, bypass_last_updated_dt=True)
                            data['node_upkData'] = json.dumps(node_upkData)

                            self_nodeData['created'] = dt_to_string(now)
                            self_nodeData['lastUpdate'] = dt_to_string(now)
                            self_nodeData['node_level'] = 'super'
                            nodeData = sign(self_nodeData, privKey=super_keyPair[0], pubKey=super_keyPair[1], bypass_last_updated_dt=True)
                            data['nodeData'] = json.dumps(nodeData)
                            
                            import random
                            userData['pattern'] = random.randint(1, 12)
                            userData['nodeCreatorId'] = self_nodeData['id']
                            userData = sign(userData, privKey=privKey, pubKey=pubKey, verify_result=True, bypass_last_updated_dt=True)
                            data['userData'] = json.dumps(userData)
                            data['account_pubkey'] = pubKey
                            error_code = 'receive_user_login'

                            r = requests.post(f'http://{new_node_settings["localhost"]}/accounts/receive_user_login', data=data)
                            received_user_json = r.json()
                            if received_user_json['message'] != 'User Created':
                                Clock.schedule_once(lambda dt, line=f"\n{received_user_json['message']}": self.update_text(line))
                            else:
                                text = 'SuperUser created.\n'
                                Clock.schedule_once(lambda dt, line=text: self.update_text(line))
                                print('superuser success')

                                operatorData['upkData'] = upkData_accnt
                                operatorData['userData'] = userData
                                operatorData['walletData'] = walletData
                            
                                if 'userPass' in operatorData:
                                    del operatorData['userPass']
                                if 'accnt_privKey' in operatorData:
                                    del operatorData['accnt_privKey']
                                if 'accnt_pubKey' in operatorData:
                                    del operatorData['accnt_pubKey']
                                if 'systemPass' in operatorData:
                                    del operatorData['systemPass']
                                if self.host == 'local':
                                    location = 'local'
                                else:
                                    location = self.host['nickname']

                                text = 'Creating Second SuperUser...\n'
                                Clock.schedule_once(lambda dt, line=text: self.update_text(line))
                                second_super_id = 'usrSo' + generate_id(length=20)
                                second_super_id = 'usrSo3axaDYOu8v1AsM'
                                error_code = 'continue4'
                                keyPair = createKeyPair(second_super_id, operatorData['second_userPass'], 'account', key_strength='ML_DSA_44')
                                second_privKey = keyPair[0]
                                second_pubKey = keyPair[1]
                                r = requests.post(f'http://{new_node_settings["localhost"]}/accounts/create_user', data={'username':operatorData['second_username']})
                                received_json = r.json()
                                userData = json.loads(received_json['userData'])
                                walletData = json.loads(received_json['walletData'])
                                upkData_accnt = json.loads(received_json['upkData'])
                                upkData_sign = json.loads(received_json['upkData'])
                                upkData_super = json.loads(received_json['upkData'])
                                data = {}

                                walletData['id'] = 'walSo' + generate_id(length=id_len)
                                walletData['User_obj'] = second_super_id
                                walletData['created'] = dt_to_string(now)
                                walletData['lastUpdate'] = dt_to_string(now)
                                walletData['Name'] = 'Main'
                                # walletData = sign(walletData, privKey=second_privKey, pubKey=second_pubKey, bypass_last_updated_dt=True)
                                # data['walletData'] = json.dumps(walletData)

                                # print('4')
                                # upkData['User_obj'] = second_super_id
                                # upkData['created'] = dt_to_string(now)
                                # upkData['lastUpdate'] = dt_to_string(now)
                                # upkData['publicKey'] = second_pubKey

                                upkData_accnt['id'] = hash_upk_id(second_pubKey)
                                upkData_accnt['User_obj'] = second_super_id
                                upkData_accnt['created'] = dt_to_string(now)
                                upkData_accnt['lastUpdate'] = dt_to_string(now)
                                upkData_accnt['publicKey'] = second_pubKey
                                upkData_accnt['keyType'] = 'account'
                                upkData_accnt['algorithm'] = 'ML_DSA_44'
                                upkData_accnt = sign(upkData_accnt, privKey=second_privKey, pubKey=second_pubKey, verify_result=True, bypass_last_updated_dt=True)
                                data['upkData_accnt'] = json.dumps(upkData_accnt)

                                keyPair = createKeyPair(second_super_id, f"{dt_to_string(now)}{operatorData['second_userPass']}", 'signing', key_strength='secp256k1')
                                upkData_sign['id'] = hash_upk_id(keyPair[1])
                                upkData_sign['User_obj'] = second_super_id
                                upkData_sign['created'] = dt_to_string(now)
                                upkData_sign['lastUpdate'] = dt_to_string(now)
                                upkData_sign['publicKey'] = keyPair[1]
                                upkData_sign['keyType'] = 'signing'
                                upkData_sign['algorithm'] = 'secp256k1'
                                upkData_sign = sign(upkData_sign, privKey=second_privKey, pubKey=second_pubKey, verify_result=True, bypass_last_updated_dt=True)
                                data['upkData_sign'] = json.dumps(upkData_sign)

                                wallet_keyPair = createKeyPair(second_super_id, operatorData['second_userPass'], f"wallet-{reward_walletData['Name']}", key_strength='secp256k1')
                                upkData_wallet['id'] = hash_upk_id(wallet_keyPair[1])
                                upkData_wallet['User_obj'] = second_super_id
                                upkData_wallet['created'] = dt_to_string(now)
                                upkData_wallet['lastUpdate'] = dt_to_string(now)
                                upkData_wallet['publicKey'] = wallet_keyPair[1]
                                upkData_wallet['keyType'] = 'Wallet'
                                upkData_wallet['algorithm'] = 'secp256k1'
                                upkData_wallet = sign(upkData_sign, privKey=second_privKey, pubKey=second_pubKey, verify_result=True, bypass_last_updated_dt=True)
                                data['upkData_wallet'] = json.dumps(upkData_sign)
                                
                                keyPair = createKeyPair(second_super_id, operatorData['second_userPass'], 'guardian', key_strength='ML_DSA_87')
                                upkData_super['id'] = hash_upk_id(keyPair[1])
                                upkData_super['User_obj'] = second_super_id
                                upkData_super['created'] = dt_to_string(now)
                                upkData_super['lastUpdate'] = dt_to_string(now)
                                upkData_super['publicKey'] = keyPair[1]
                                upkData_super['keyType'] = 'guardian'
                                upkData_super['algorithm'] = 'ML_DSA_87'
                                upkData_super = sign(upkData_super, privKey=keyPair[0], pubKey=keyPair[1], verify_result=True, bypass_last_updated_dt=True)
                                data['upkData_super'] = json.dumps(upkData_super)

                                userData['id'] = second_super_id
                                userData['username'] = operatorData['second_username']
                                userData['created'] = dt_to_string(now)
                                userData['networkChain'] = second_super_id
                                userData['lastUpdate'] = dt_to_string(now_utc())
                                userData['signkey_dt'] = dt_to_string(now)
                                for key, value in userData.items():
                                    if '_array' in str(key):
                                        userData[key] = json.dumps([])

                                userData['pattern'] = random.randint(1, 12)
                                userData['nodeCreatorId'] = self_nodeData['id']
                                userData = sign(userData, privKey=second_privKey, pubKey=second_pubKey, verify_result=True, bypass_last_updated_dt=True)
                                data['userData'] = json.dumps(userData)
                                error_code = 'receive_user_login2'

                                r = requests.post(f'http://{new_node_settings["localhost"]}/accounts/receive_user_login', data=data)
                                received_user_json = r.json()
                                if received_user_json['message'] != 'User Created':
                                    Clock.schedule_once(lambda dt, line=f"\n{received_user_json['message']}": self.update_text(line))
                                else:
                                    text = 'Second SuperUser created.\n'
                                    Clock.schedule_once(lambda dt, line=text: self.update_text(line))
                                    print('superuser 2 success')

                                    if 'second_userPass' in operatorData:
                                        del operatorData['second_userPass']
                                    if 'second_username' in operatorData:
                                        del operatorData['second_username']
                                
                                    new_node_meta = self_nodeDetails['meta']
                                    if 'info' in new_net and 'Domain' in new_net and new_net['Domain']:
                                        new_node_meta['domain'] = new_net['Domain']
                                    new_node_meta['is_installed'] = True
                                    operatorData['myNodes'][self_nodeData['id']] = {'nodeData':self_nodeData, 'location':location, 'settings':new_node_settings, 'meta':new_node_meta}
                                    if self.host == 'local':
                                        operatorData['local_nodeId'] = self_nodeData['id']
                                    else:
                                        ...
                                        # add basic data to remote host (profile info, seed_ip...)
                                        # remote network creation not currently supported
                                    
                                    operatorData['user_is_super'] = True
                                    sonet = {}
                                    sonetModel = json.loads(received_user_json['sonet'])
                                    for key, value in sonetModel.items():
                                        try:
                                            sonet[key] = new_net[key]
                                        except:
                                            sonet[key] = value

                                    sonet['created'] = newnet['created']
                                    sonet['lastUpdate'] = dt_to_string(now)
                                    sonet['id'] = newnet['id']

                                    # import json
                                    # from pathlib import Path
                                    filename = Path.home() / "Sonet" / ".data" / "settings.json"

                                    with open(filename, "r", encoding="utf-8") as f:
                                        data = json.load(f)

                                    data['branch'] = sonet['repo']['branch']
                                
                                    with open(filename, "w", encoding="utf-8") as f:
                                        json.dump(data, f, indent=4)

                                    sonetSigned = sign(sonet, privKey=super_keyPair[0], pubKey=super_keyPair[1], verify_result=True, operatorData=operatorData, bypass_last_updated_dt=True)
                                    sonetData = {'sonetData' : json.dumps(sonetSigned)}
                                    error_code = 'set_sonet'
                                    r = connect_to_node(f'{new_node_settings["localhost"]}', 'accounts/set_sonet', data=sonetData, node_setup=True, operatorData=operatorData)
                                    received_sonet_json = r.json()
                                    if received_sonet_json['message'] != 'Success':
                                        Clock.schedule_once(lambda dt, line=f"\n{received_sonet_json['message']}": self.update_text(line))
                                    else:
                                        text = '\nSonet created.\n'
                                        Clock.schedule_once(lambda dt, line=text: self.update_text(line))
                                        print('almost done')

                                        accountsPlugin = json.loads(received_sonet_json['accounts'])
                                        networkPlugin = json.loads(received_sonet_json['network'])
                                        postsPlugin = json.loads(received_sonet_json['posts'])
                                        transactionsPlugin = json.loads(received_sonet_json['transactions'])
                                        sovotePlugin = None
                                        if 'legis' in received_sonet_json:
                                            sovotePlugin = json.loads(received_sonet_json['legis'])

                                        earthModel = json.loads(received_sonet_json['earth'])
                                        operatorData['sonet'] = json.loads(received_sonet_json['sonet'])
                                        del operatorData['new_sonet']

                                        operatorData['ip_master_list'] = {self_nodeDetails['nodeData']['id']:{'address':self_nodeData['address']}}
                                        print('really almost done')
                                        models = {'Earth':earthModel, 'Accounts Plugin':accountsPlugin, 'Network Plugin':networkPlugin, 'Posts Plugin':postsPlugin, 'Transactions Plugin':transactionsPlugin}
                                        if sovotePlugin:
                                            models['SoVote Plugin'] = sovotePlugin
                                            # models['Wallet'] = reward_walletData
                                        
                                        def set_obj(objModel, msg, keys='super'):
                                            print('objModel',objModel)
                                            objModel['created'] = dt_to_string(now)
                                            if 'lastUpdate' in objModel:
                                                objModel['lastUpdate'] = dt_to_string(now)
                                            if 'func' in objModel:
                                                objModel['func'] = 'super'
                                            if 'User_obj' in objModel:
                                                objModel['User_obj'] = user_id
                                            if 'CreatorNode_obj' in objModel:
                                                objModel['CreatorNode_obj'] = self_nodeData['id']
                                            if 'commitChain' in objModel:
                                                objModel['commitChain'] = sonet['id']
                                            if 'validatorNodeId' in objModel:
                                                objModel['validatorNodeId'] = self_nodeData['id']
                                            if keys == 'super':
                                                objData = sign(objModel, privKey=super_keyPair[0], pubKey=super_keyPair[1], verify_result=True, operatorData=operatorData, bypass_last_updated_dt=True)
                                            else:
                                                objData = sign(objModel, privKey=privKey, pubKey=pubKey, bypass_last_updated_dt=True)

                                            if objModel['objType'] == 'Region':
                                                super_share = True
                                            else:
                                                super_share = False
                                            data = {'objData': json.dumps(objData), 'super_share': super_share}
                                            try:
                                                r = connect_to_node(new_node_settings["localhost"], 'utils/set_object_data', data=data, operatorData=operatorData, node_setup=True)
                                                received_json = r.json()
                                                print('received_json',received_json)
                                                if received_json['message'] == 'Success':
                                                    text = f'{msg} created.'
                                                    Clock.schedule_once(lambda dt, line=text: self.update_text(line))
                                                    return True
                                                return received_json['message']
                                            except Exception as e:
                                                return f'Error creating {msg} - {e}\n'
                                        

                                        for msg, model in models.items():
                                            if msg == 'Wallet':
                                                keys = 'account'
                                            else:
                                                keys = 'super'
                                            z = set_obj(model, msg, keys)
                                            if z != True:
                                                Clock.schedule_once(lambda dt, line=z: self.update_text(line))
                                                app_operational = False
                                                break
                                            else:
                                                print('contine to next')

                                        if app_operational:
                                            print('All GooD!')
                                            result = '\nSonet setup successfully!\n'
                                            Clock.schedule_once(lambda dt, line=result: self.update_text(line))
                                            result = None
                                            from commands.utils import clear_temp_data
                                            clear_temp_data()
                                        try:
                                            del operatorData['start_local_install']
                                        except:
                                            pass
                            write_operatorData(operatorData)

                    else:
                        text = f'\nA problem occured connecting to the app. It should be reachable in your local browser at http://{new_node_settings["localhost"]}\n'
                        Clock.schedule_once(lambda dt, line=text: self.update_text(line))
                        if result:
                            Clock.schedule_once(lambda dt, line=result: self.update_text(line))
                        text = '\nConsider uninstall/reinstall or manual troubleshooting.'
                        Clock.schedule_once(lambda dt, line=text: self.update_text(line))
                    if app_operational:
                        if 'local_nodeId' not in operatorData or operatorData['local_nodeId'] not in operatorData['myNodes']:
                            text = '\nFailed to register node on network.'
                            Clock.schedule_once(lambda dt, line=text: self.update_text(line))
                        else:
                            try:
                                del operatorData['start_local_install']
                                write_operatorData(operatorData)
                            except:
                                pass
                            node_ip_address = operatorData['myNodes'][operatorData['local_nodeId']]['nodeData']['address']
                            if node_ip_address != 'Cloudflare Tunnel':
                                text = '\nChecking for external access...'
                                Clock.schedule_once(lambda dt, line=text: self.update_text(line))
                                data = {'requested_address':node_ip_address}
                                nodes = get_node_list(operatorData=operatorData)
                                for iden, ip in islice(nodes.items(), 3):
                                    print('--for ip', ip, nodes)
                                    r = connect_to_node(ip, 'utils/can_you_see_me', data=data, operatorData=operatorData, node_setup=True)
                                    received_json = r.json()
                                    if received_json['message'] == 'Success':
                                        text = '\n\nNode has external access.\nInstallation successful. You may activate now.\n'
                                        external_access = True
                                        break
                                    else:
                                        text = f'\n\nNode has NOT achieved external access at {node_ip_address}'
                                Clock.schedule_once(lambda dt, line=text: self.update_text(line))
                                if result:
                                    Clock.schedule_once(lambda dt, line=result: self.update_text(line))
                Clock.schedule_once(lambda dt: self.add_continue_button())
            except Exception as e:
                print('finish setup err',str(e), error_code)
                text = '\n\nA problem occured.\n'
                Clock.schedule_once(lambda dt, line=text: self.update_text(line))
                if result:
                    Clock.schedule_once(lambda dt, line=result: self.update_text(line))
                if not self.remote_data:
                    self.restart_setup()
                if error_code:
                    text = f'\nError code: {error_code} -- {str(e)}.'
                    Clock.schedule_once(lambda dt, line=text: self.update_text(line))
                text = '\nConsider uninstall/reinstall or manually troubleshooting.'
                Clock.schedule_once(lambda dt, line=text: self.update_text(line))

                Clock.schedule_once(lambda dt: self.add_continue_button())
            self.refresh_sidebar(self)

        elif self.option.lower() == 'deactivate':
            if self.host == 'remote':
                fetch_remote_data(self.remote_data, operatorData=None, fetch_key=True, ssh_client=self.ssh_client, output=None)
                self.ssh_client.close()
            from commands.utils import get_or_create_node_obj
            full_nodeData, is_new = get_or_create_node_obj()
            if not value_is_none(full_nodeData['nodeData']['activated_dt']):
                response = '\nA problem occured\n' 
            else:
                response = '\nNode status synced and deactivated\n' 
            Clock.schedule_once(lambda dt, line=response: self.update_text(line))
            self.refresh_sidebar(self)
        elif self.option.lower() == 'activate':
            if self.host == 'remote':
                fetch_remote_data(self.remote_data, operatorData=None, fetch_key=True, ssh_client=self.ssh_client, output=None)
                self.ssh_client.close()
            store_secure_item("temp_keys", None)
        elif self.option.lower() == 'update':
            operatorData = get_operatorData()
            operatorData['last_server_update'] = dt_to_string(now_utc())
            write_operatorData(operatorData)
            response = '\nUpdate finished.\n'
            Clock.schedule_once(lambda dt, line=response: self.update_text(line))
            Clock.schedule_once(lambda dt, line=self: self.refresh_sidebar(line))
        elif self.option.lower() == 'restart':
            response = '\nRestart finished.\n'
            Clock.schedule_once(lambda dt, line=response: self.update_text(line))
            Clock.schedule_once(lambda dt, line=self: self.refresh_sidebar(line))
        elif self.option.lower() in ['uninstall','reinstall']:
            operatorData = get_operatorData()
            if 'is_installed' in operatorData:
                del operatorData['is_installed']
            if 'start_local_install' in operatorData:
                del operatorData['start_local_install']
            newData = {}
            if 'clearOperatorData' in operatorData and operatorData['clearOperatorData']:
                if 'seed_ip' in operatorData:
                    newData['seed_ip'] = operatorData['seed_ip']
            else:
                retainItems = ['sonet','seed_ip','userData','recent_ip_accessed','upkData','privKey',
                            'pubKey','userPass','user_id','username','accnt_privKey','accnt_pubKey']
                for i in retainItems:
                    if i in operatorData:
                        newData[i] = operatorData[i]
            
            write_operatorData(newData, clear_data=True)
            text = '\nUninstall of node software complete\n'
            Clock.schedule_once(lambda dt, line=text: self.update_text(line))
            Clock.schedule_once(lambda dt, line=self: self.refresh_sidebar(line))
            if self.option.lower() == 'reinstall':
                Clock.schedule_once(lambda dt, line='install': self.parent_screen.switch_layout(line))

        elif self.option.lower() == 'reinstall_old':
            operatorData = get_operatorData()
            if 'is_installed' in operatorData:
                del operatorData['is_installed']
            if 'start_local_install' in operatorData:
                del operatorData['start_local_install']
            newData = {}
            if 'clearOperatorData' in operatorData and operatorData['clearOperatorData']:
                if 'seed_ip' in operatorData:
                    newData['seed_ip'] = operatorData['seed_ip']
            else:
                retainItems = ['sonet','seed_ip','userData','recent_ip_accessed','upkData','privKey',
                            'pubKey','userPass','user_id','username']
                for i in retainItems:
                    if i in operatorData:
                        newData[i] = operatorData[i]
            
            write_operatorData(newData)
            text = '\nUninstall of node software complete\n'
            Clock.schedule_once(lambda dt, line=text: self.update_text(line))
            Clock.schedule_once(lambda dt, line='install': self.parent_screen.switch_layout(line))

        self.parent_screen.job_running = False
        if self.following_cmd:
            
            Clock.schedule_once(lambda dt, line=self: self.following_cmd())
        else:
            try:
                self.command_runner.content.remove_widget(self.command_runner.text_input)
            except:
                pass
        print('done finish_setp() p9')

    def restart_setup(self, instance=None, attempt=1):
        try:
            self.remove_widget(self.abort_button)
        except Exception as e:
            print('fail remove abort 8963',str(e))
        try:
            self.continue_button = Button(text='Restart', size_hint=(1, None), height=dp(30))
            self.continue_button.bind(on_press=self.run_install)
            self.add_widget(self.continue_button)
        except Exception as e:
            print('restart_setup err',str(e))
            if attempt == 1:
                Clock.schedule_once(lambda dt: self.restart_setup(attempt=2))
            pass

    def update_text(self, line):
        # print('setup update_text:', line)
        try:
            if not line.endswith('\n') and not line.startswith('\n'):
                line = line + '\n'
            self.text_input.text += line
        except Exception as e:
            print('update_text err',str(e))

    def run_deactivate(self, instance=None):
        self.remove_widget(self.continue_button)
        try:
            self.remove_widget(self.alive_layout)
        except:
            pass
        from commands.utils import get_or_create_node_obj
        full_nodeData, is_new = get_or_create_node_obj()
        
        if full_nodeData['nodeData']['node_level'].lower() == 'super':
            self.user_passphrase_prompt(next_cmd=self.run_deactivate_step2a)
        else:
            self.run_deactivate_step2a()

    def run_deactivate_step2a(self):
        print('-run_deactivate_step2a')
        self.parent_screen.job_running = True
        self.text_input.text = 'Deactivating...\n'
        threading.Thread(target=self.run_deactivate_step2b).start()

    def run_deactivate_step2b(self):
        debug = False
        try:
            debug = self.alive_input.active
        except:
            debug = False

        self.remote_data = {}
        if 'local_nodeId' in self.operatorData and self.operatorData['local_nodeId'] == self.operatorData['selected_node']:
            self.host = 'local'
        else:
            self.host = 'remote'
            self.remote_data = get_remote(node_id=self.operatorData['selected_node'], operatorData=self.operatorData)

        self.context = {}
        if self.host == 'local':
            commands = []
            special_commands = {}
            commands, special_commands = get_commands('deactivate', system=device_system, extras={'debug':debug})
        else:
            connected, self = make_remote_connection(remote_data=self.remote_data, cls=self)
            if not connected:
                Clock.schedule_once(lambda dt, line='\nFailed remote contact 1.\n': self.update_text(line))
                return
            if not send_manager_to_remote(self.remote_data, ssh_client=self.ssh_client, text_display=self.text_input.text):
                Clock.schedule_once(lambda dt, line='\nFailed send manager to remote.\n': self.update_text(line))
                return

            self.context = {'fetch_cmds': False, 'task': 'deactivate', 'extras': {'debug': debug}}
            commands, special_commands = fetch_remote_commands(self.context["task"], self.ssh_client, extras=self.context["extras"])
            self.special_commands = special_commands

        # should followup with check utils/is_sonet to make sure self is inactive

        self.command_runner = CommandRunner(self, commands, self.content, self.text_input, special_commands, remote_data=self.remote_data, finish_command=self.finish_setup, main_screen=self.parent_screen, operatorData=self.operatorData, context=self.context)
        threading.Thread(target=self.command_runner.run_commands).start()
    
    def user_passphrase_prompt(self, instance=None, next_cmd=None):
        def proceed():
            self.passphrase = self.pass_input.text.lower()
            self.pass_layout.remove_widget(self.pass_label)
            self.pass_layout.remove_widget(self.pass_input)
            self.remove_widget(self.pass_layout)

            user_id = self.operatorData['user_id']
            super_keyPair = createKeyPair(user_id, self.passphrase, 'guardian', key_strength='ML_DSA_87')
            from commands.utils import hash_upk_id
            store_secure_item("temp_keys", {'pubKey':super_keyPair[1],'privKey':super_keyPair[0],'keyId':hash_upk_id(super_keyPair[1])})
            if next_cmd:
                next_cmd()

        self.text_input.text = 'The selected settings require advanced keys.\n\nPassphrase needed to generate required keys.\n'
        self.pass_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=dp(30))
        self.toggle_button = Button(text='Show', size_hint_x=None, width=dp(70))
        self.pass_label = Label(text="User Passphrase:", size_hint=(1, 1), height=dp(30), size_hint_x=None, width=dp(130))
        with self.pass_label.canvas.before:
            Color(1, 1, 1, 1)
        self.pass_input = TextInput(text='', hint_text="passphrase removed after use", size_hint=(1, None), height=dp(30), multiline=False, password=True)
        self.pass_input.bind(on_text_validate=lambda instance: proceed())
        self.pass_input.focus = True
        self.toggle_button.bind(on_press=self.toggle_password_visibility)
        self.pass_layout.add_widget(self.pass_label)
        self.pass_layout.add_widget(self.pass_input)
        self.pass_layout.add_widget(self.toggle_button)
        self.add_widget(self.pass_layout)

    def run_activate(self, instance=None):
        self.parent_screen.job_running = True
        port = self.port_input.text

        # node should check that its upk is on chain before proceeding

        try:
            self.remove_widget(self.broadcast_layout)
            self.broadcastState = self.broadcast_input.active
            if not self.broadcastState:
                self.isTesting = True
                self.syncDatabase = False
        except Exception as e:
            print('run_activate err 1',str(e))
            pass
        self.node_type = 'server/maintainer'
        try:
            self.node_type = self.node_type_input.text.lower()
            self.node_type_layout.remove_widget(self.node_type_label)
            self.node_type_layout.remove_widget(self.node_type_input)
            self.remove_widget(self.node_type_layout)
        except Exception as e:
            print('run_activate err 2',str(e))
            pass
        self.node_level = 'standard'
        try:
            self.node_level = self.node_level_input.text.lower()
            self.node_level_layout.remove_widget(self.node_level_label)
            self.node_level_layout.remove_widget(self.node_level_input)
            self.remove_widget(self.node_level_layout)
        except Exception as e:
            print('run_activate err 3',str(e))
            pass
        try:
            self.open_ports_layout.remove_widget(self.open_ports_label)
            self.open_ports_layout.remove_widget(self.open_ports_input)
            self.remove_widget(self.open_ports_layout)
        except:
            pass
        self.title_layout.remove_widget(self.title_label)
        self.title_layout.remove_widget(self.title_input)
        self.remove_widget(self.title_layout)

        self.port_layout.remove_widget(self.port_label)
        self.port_layout.remove_widget(self.port_input)
        self.remove_widget(self.port_layout)
        self.ip_layout.remove_widget(self.ip_label)
        self.ip_layout.remove_widget(self.ip_input)
        self.remove_widget(self.ip_layout)

        self.remove_widget(self.continue_button)

        if self.node_level.lower() == 'super':
            self.user_passphrase_prompt(next_cmd=self.run_activate_step2a)
        else:
            self.run_activate_step2a()

    def run_activate_step2a(self):
        self.abort_button = Button(text='Abort', size_hint=(1, None), height=dp(30))
        self.abort_button.bind(on_press=self.abort)
        self.add_widget(self.abort_button)
        
        self.text_input.text = 'Activating...\n'
        commands = [['run_local_command', 'run_activate_step2b']]
        self.activate2 = CommandRunner(self, commands, self.content, self.text_input, {'run_activate_step2b' :{'cmd':'run_activate_step2b', 'func':self.run_activate_step2b}}, main_screen=self.parent_screen)
        threading.Thread(target=self.activate2.run_commands).start()

    def run_activate_step2b(self, run_syncDatabase=True):
        print('-run activate step2b',now_utc())
        self.remote_data = {}
        if 'local_nodeId' in self.operatorData and self.operatorData['local_nodeId'] == self.operatorData['selected_node']:
            self.host = 'local'
        else:
            self.host = 'remote'
            print('is remote')
            send_manager_to_remote(self.operatorData['selected_node'], manager_only=True, text_display=self.text_input.text)

            self.remote_data = get_remote(node_id=self.operatorData['selected_node'], operatorData=self.operatorData)

        if self.full_nodeData:
            full_nodeData = self.full_nodeData
            self.syncDatabase = False
            self.isTesting = False
            self.enableTasker = True
            self.debug = False
            if 'debug' in full_nodeData['meta'] and full_nodeData['meta']['debug']:
                self.debug = True
        else:
            full_nodeData = self.operatorData['myNodes'][self.operatorData['selected_node']]

            node_title = self.title_input.text
            port = self.port_input.text
            address = self.ip_input.text
            address = address.replace('https:','').replace('http:', '').replace('/','')
            full_nodeData['settings']['node_type'] = self.node_type.lower()
            full_nodeData['settings']['node_level'] = self.node_level.lower()
            full_nodeData['settings']['node_name'] = node_title
            full_nodeData['settings']['address'] = address
            if port:
                full_nodeData['settings']['localhost'] = '127.0.0.1:' + port
            else:
                port = '80'
                full_nodeData['settings']['localhost'] = '127.0.0.1:' + port
            full_nodeData['settings']['port'] = port
            full_nodeData['settings']['isTesting'] = self.isTesting
            self.operatorData['myNodes'][self.operatorData['selected_node']] = full_nodeData
            write_operatorData(self.operatorData)
            if self.isTesting:
                self.enableTasker = False

        self.context = {}
        if self.host == 'local':
            git_commands = []
            update_commands, update_special_commands = [], {}
            commands, special_commands = get_commands('activate', system=device_system, extras={'enableTasker':self.enableTasker})
            commands = git_commands + update_commands + commands
            special_commands = {**special_commands, **update_special_commands}

            if run_syncDatabase and self.syncDatabase and not self.isTesting:
                commands.append(['run_local_command', 'sync_database'])
                from commands.utils import sync_database
                special_commands['sync_database'] = {'cmd':'sync_database', 'reqs':['output_display','parent_screen'], 'func':sync_database}

        else:
            connected, self = make_remote_connection(remote_data=self.remote_data, cls=self)
            print('self.ssh_client',self.ssh_client)
            if not connected:
                Clock.schedule_once(lambda dt, line='\nFailed remote contact 1.\n': self.update_text(line))
                return
            if not send_manager_to_remote(self.remote_data, ssh_client=self.ssh_client, text_display=self.text_input.text):
                Clock.schedule_once(lambda dt, line='\nFailed send manager to remote.\n': self.update_text(line))
                return
            from commands.utils import update_remote_data
            if update_remote_data(full_nodeData, remote_opData=None, remote_data=self.remote_data, operatorData=self.operatorData, remote_password=None, ssh_client=self.ssh_client, output=self.text_input):

                self.context = {'fetch_cmds': False, 'task': 'activate', 'extras': {'enableTasker': self.enableTasker, 'debug': self.debug}}
                commands, special_commands = fetch_remote_commands(self.context["task"], self.ssh_client, extras=self.context["extras"])
                self.special_commands = special_commands

                if run_syncDatabase and self.syncDatabase and not self.isTesting:
                    commands.append(['run_local_command', 'sync_database'])
                    from commands.utils import sync_database
                    special_commands['sync_database'] = {'cmd':'sync_database', 'reqs':['output_display','parent_screen'], 'func':sync_database}

                if self.broadcastState:
                    commands.append(['run_command', 'declare_active'])
                else:
                    commands.append(['run_command', 'declare_active_no_broadcast'])
                print('returned commands:',commands)
                print('returned special_commands:',special_commands)
            else:
                Clock.schedule_once(lambda dt, line='\nFailed remote contact 2.\n': self.update_text(line))
                return

        commands.append(['run_local_command', 'run_activate_step3'])
        special_commands['run_activate_step3'] = {'cmd':'run_activate_step3', 'func':self.run_activate_step3}
        self.command_runner = CommandRunner(self, commands, self.content, self.text_input, special_commands, main_screen=self.parent_screen, context=self.context, remote_data=self.remote_data)
        threading.Thread(target=self.command_runner.run_commands).start()

    def run_activate_step3(self, instance=None):
        print('-run_activate_step3', now_utc())

        def add_proceed_button():
            self.field = BoxLayout(orientation='horizontal', size_hint=(1, None), height=dp(30))
            self.proceed_button = Button(text='Proceed Anyway', size_hint=(1, None), height=dp(30))
            self.proceed_button.bind(on_press=self.proceed_activation)
            self.add_widget(self.proceed_button)

        if self.host == 'local':
            from commands.utils import declare_self_active
            response = declare_self_active(True, output=self.text_input, wait_for_reload=False, broadcast_to_network=self.broadcastState)
            print('returned resposne',response)
            resp, request_proceed = self.parse_activation_resp(response)
            self.proceed_commands = CommandRunner(self, [['run_local_command', 'proceed_activation_step2']], self.content, self.text_input, {'proceed_activation_step2':{'cmd':'proceed_activation_step2','func':self.proceed_activation_step2}}, main_screen=self.parent_screen)

        else:
            # declare_self_active already ran remotely
            time.sleep(2.5)
            resp, request_proceed = self.parse_activation_resp(self.text_input.text[-500:])

            if self.broadcastState:
                commands = ['run_command', 'force_active']
            else:
                commands = ['run_command', 'force_active_no_broadcast']
            self.proceed_commands = CommandRunner(self, commands, self.content, self.text_input, self.special_commands, finish_command=self.proceed_activation_step2, main_screen=self.parent_screen, context=self.context)
        if request_proceed:
            Clock.schedule_once(lambda dt: add_proceed_button())
        else:
            self.finish_setup()

        Clock.schedule_once(lambda dt: self.remove_abort_button())
        Clock.schedule_once(lambda dt, line=resp: self.update_text(line))
        Clock.schedule_once(lambda dt, line=self: self.refresh_sidebar(line))
        self.parent_screen.job_running = False
        
    def remove_abort_button(self):
        try:
            self.remove_widget(self.abort_button)
        except Exception as e:
            print('remove abort button fail 486', str(e))
        try:
            self.parent_screen.job_running = False
        except:
            pass

    def parse_activation_resp(self, result):
        # print('-parse_activation_resp:', result)
        request_proceed = False
        if 'Sync success' in result:
            resp = '\n\nNode status synced and activated\n'
        elif 'failed_sync' in result:
            resp = '\n\nFailed sync. No activation.\n'
        elif 'failed_activation' in result:
            resp = '\n\nFailed to declare activation.\n'
        elif 'successfully_activated' in result:
            resp = '\n\nSuccessfully activated.\n'
        elif 'failed_network_contact' in result:
            resp = f'\n\nFailed to contact outside network. Continuing with activation could lead to unintended results.\n'
            request_proceed = True
        else:
            resp = f'\n\nUnknown response:\n{result}\n'
        return resp, request_proceed
    
    def proceed_activation(self, instance=None):
        # print('-proceed_activation')
        self.remove_widget(self.proceed_button)
        self.abort_button = Button(text='Abort', size_hint=(1, None), height=dp(30))
        self.abort_button.bind(on_press=self.abort)
        self.add_widget(self.abort_button)
        threading.Thread(target=self.proceed_commands.run_commands).start()

    def proceed_activation_step2(self, instance=None): # this needs to show an immediate response when clicked, currently nothing changes until entire process completes
        print('-proceed_activation step2')
        if self.host == 'local':
            from commands.utils import declare_self_active
            response = declare_self_active(True, output=self.text_input, wait_for_reload=False, broadcast_to_network=self.broadcastState, just_activate_me=True)
            resp, request_proceed = self.parse_activation_resp(response)
        else:
            resp, request_proceed = self.parse_activation_resp(self.text_input.text[-500:])
        try:
            self.remove_widget(self.proceed_button)
        except Exception as e:
            print('remove proceed_button button err 632', str(e))
        try:
            self.remove_widget(self.abort_button)
        except Exception as e:
            print('remove abort button err 721', str(e))
        Clock.schedule_once(lambda dt, line=resp: self.update_text(line))
        Clock.schedule_once(lambda dt, line=self: self.refresh_sidebar(line))
        self.finish_setup()

    def reactivate(self, instance=None, full_nodeData=None, new_text_screen=True):
        print('-reactivate')
        self.full_nodeData = full_nodeData
        self.parent_screen.job_running = True
        if operatorData:
            self.operatorData = operatorData
        t = f'\Reactivating {self.operatorData["selected_node"]}...\n'
        if new_text_screen:
            self.text_input.text = t
        else:
            self.text_input.text += t

        try:
            self.remove_widget(self.broadcast_layout)
            self.broadcastState = self.broadcast_input.active
            if not self.broadcastState:
                self.isTesting = True
                self.syncDatabase = False
        except Exception as e:
            print('reactivate err 1',str(e))
            pass
        self.node_type = 'server/maintainer'
        try:
            self.node_type = self.node_type_input.text.lower()
            self.node_type_layout.remove_widget(self.node_type_label)
            self.node_type_layout.remove_widget(self.node_type_input)
            self.remove_widget(self.node_type_layout)
        except Exception as e:
            print('reactivate err 2',str(e))
            pass
        self.node_level = 'standard'
        try:
            self.node_level = self.node_level_input.text.lower()
            self.node_level_layout.remove_widget(self.node_level_label)
            self.node_level_layout.remove_widget(self.node_level_input)
            self.remove_widget(self.node_level_layout)
        except Exception as e:
            print('reactivate err 3',str(e))
            pass
        try:
            self.open_ports_layout.remove_widget(self.open_ports_label)
            self.open_ports_layout.remove_widget(self.open_ports_input)
            self.remove_widget(self.open_ports_layout)
        except:
            pass
        self.title_layout.remove_widget(self.title_label)
        self.title_layout.remove_widget(self.title_input)
        self.remove_widget(self.title_layout)

        self.port_layout.remove_widget(self.port_label)
        self.port_layout.remove_widget(self.port_input)
        self.remove_widget(self.port_layout)
        self.ip_layout.remove_widget(self.ip_label)
        self.ip_layout.remove_widget(self.ip_input)
        self.remove_widget(self.ip_layout)

        self.remove_widget(self.continue_button)
        
        self.abort_button = Button(text='Abort', size_hint=(1, None), height=dp(30))
        self.abort_button.bind(on_press=self.abort)
        self.add_widget(self.abort_button)
        
        self.text_input.text = 'Activating...\n'
        commands = [['run_local_command', 'run_activate_step2a']]
        self.activate2 = CommandRunner(self, commands, self.content, self.text_input, {'run_activate_step2a' :{'cmd':'run_activate_step2a', 'func':self.run_activate_step2a}}, main_screen=self.parent_screen)
        threading.Thread(target=self.activate2.run_commands).start()

    def run_update(self, new_text_screen=True, operatorData=None):
        print('-run_update')
        self.parent_screen.job_running = True
        if operatorData:
            self.operatorData = operatorData
        t = f'\nUpdating {self.operatorData["selected_node"]}...\n'
        if new_text_screen:
            self.text_input.text = t
        else:
            self.text_input.text += t
        git_commands = []
        special_commands = {}

        context = {'task':'get_update', 'system':device_system}
        
        if 'local_nodeId' in self.operatorData and self.operatorData['selected_node'] == self.operatorData['local_nodeId']:
            self.host = 'local'
            remote_node = {}
            commands, special_commands = get_commands(context['task'], system=context['system'], operatorData=None, in_full=False, extras={})
        else:
            self.host = 'remote'
            remote_node = self.operatorData['selected_node']
            self.text_input.text += "\nUpdating remote manager...\n"
            
            git_commands = [['run_local_command', 'send_manager_to_remote']]
            special_commands = {'send_manager_to_remote':{'cmd':'send_manager_to_remote', 'func':partial(send_manager_to_remote, self.operatorData['selected_node'], text_display=self.text_input, manager_only=True)}}

        if self.host == 'local':
            commands = git_commands + commands
        else:
            commands = git_commands

        self.command_runner = CommandRunner(self, commands, self.content, self.text_input, special_commands, remote_data=remote_node, finish_command=self.finish_setup, main_screen=self.parent_screen, operatorData=self.operatorData, context=context)
        threading.Thread(target=self.command_runner.run_commands).start()

    def run_restart(self, new_text_screen=True, operatorData=None):
        print('-run_restart')
        self.parent_screen.job_running = True
        if operatorData:
            self.operatorData = operatorData
        t = f'\nRestarting {self.operatorData["selected_node"]}...\n'
        if new_text_screen:
            self.text_input.text = t
        else:
            self.text_input.text += t
        git_commands = []
        special_commands = {}

        context = {'task':'restart', 'system':device_system}
        
        if 'local_nodeId' in self.operatorData and self.operatorData['selected_node'] == self.operatorData['local_nodeId']:
            self.host = 'local'
            remote_node = {}
            commands, special_commands = get_commands(context['task'], system=context['system'], operatorData=None, in_full=False, extras={})
        else:
            self.host = 'remote'
            remote_node = self.operatorData['selected_node']
            self.text_input.text += "\nUpdating remote manager and server...\n"
            git_commands = [['run_local_command', 'send_manager_to_remote']]
            special_commands = {'send_manager_to_remote':{'cmd':'send_manager_to_remote', 'func':partial(send_manager_to_remote, self.operatorData['selected_node'], text_display=self.text_input)}}
            

        if self.host == 'local':
            commands = git_commands + commands
        else:
            commands = git_commands

        self.command_runner = CommandRunner(self, commands, self.content, self.text_input, special_commands, remote_data=remote_node, finish_command=self.finish_setup, main_screen=self.parent_screen, operatorData=self.operatorData, context=context)
        threading.Thread(target=self.command_runner.run_commands).start()

    def finish_instructions(self, instance=None):
        try:
            self.continue_button = Button(text='Finish', size_hint=(1, None), height=dp(30))
            self.continue_button.bind(on_press=self.run_install)
            self.add_widget(self.continue_button)
        except:
            pass

    def run_uninstall(self, instance=None):
        print('-run_uninstall')
        self.parent_screen.job_running = True
        self.text_input.text = 'Uninstalling...\n'
        try:
            self.remove_widget(self.continue_button)
        except:
            pass
        if 'debug' in self.operatorData:
            self.debug = self.operatorData['debug']
        try:
            quick_uninstall = self.test_input.active
            self.remove_widget(self.test_layout)
        except:
            quick_uninstall = False
        try:
            self.remove_widget(self.database_layout)
            preserve_database = self.database_input.active
        except:
            preserve_database = False
        try:
            self.remove_widget(self.dependencies_layout)
            preserve_dependencies = self.dependencies_input.active
        except:
            preserve_dependencies = False
        try:
            self.remove_widget(self.data_layout)
            clearOperatorData = self.data_input.active
            self.operatorData['clearOperatorData'] = clearOperatorData
            write_operatorData(self.operatorData)
        except:
            clearOperatorData = False

        self.context = {'fetch_cmds': False, 'task': 'uninstall', 'extras': {'quick_uninstall': quick_uninstall, 'preserve_database': preserve_database,'preserve_dependencies': preserve_dependencies, 'debug': self.debug}}
        
        self.remote_data = {}
        if 'start_local_install' in self.operatorData and self.operatorData['start_local_install'] or 'local_nodeId' in self.operatorData and self.operatorData['local_nodeId'] == self.operatorData['selected_node']:
            self.host = 'local'
            self.commands, self.special_commands = get_commands('uninstall', system=device_system, extras={'preserve_database':preserve_database, 'preserve_dependencies':preserve_dependencies, 'quick_uninstall':quick_uninstall, 'debug':self.debug})

        else:
            self.host = 'remote'
            self.remote_data = get_remote(node_id=self.operatorData['selected_node'], operatorData=self.operatorData)
            self.context = {'fetch_cmds': False, 'task': 'activate', 'extras': {'enableTasker': self.enableTasker, 'debug': self.debug}}

            connected, self = make_remote_connection(remote_data=self.remote_data, cls=self)
            if not connected:
                Clock.schedule_once(lambda dt, line='\nFailed remote contact 1.\n': self.update_text(line))
                return
            self.commands, self.special_commands = fetch_remote_commands(self.context["task"], self.ssh_client, extras=self.context["extras"])

        upk_deactivated = True
        from commands.utils import get_or_create_node_obj, get_remote_opData, value_is_none
        selected_opData = get_remote_opData()
        if selected_opData and 'start_local_install' not in selected_opData:
            full_nodeData, is_new = get_or_create_node_obj(selected_opData, register_data=False, create_node=False)
            if full_nodeData and 'upk' in full_nodeData and value_is_none(full_nodeData['upk']['end_life_dt']):
                response = f'Deactivating node keys on network...'
                Clock.schedule_once(lambda dt, line=response: self.update_text(line))
                from commands.utils import fetch_node_keys
                node_keys = fetch_node_keys(target_nodeId=selected_opData['local_nodeId'])
                upk_deactivated = False
                upk = full_nodeData['upk']
                upk['end_life_dt'] = dt_to_string(now_utc())
                signed_upkData = sign(upk, node_keys=node_keys)
                data = {'upkData':signed_upkData}
                nodes = get_node_list(operatorData=selected_opData, exclude_self=True)
                for node_id, node_addresses in nodes.items():
                    print('node',node_id, node_addresses)
                    r = connect_to_node(node_addresses, 'accounts/deactivate_upk', data=data, operatorData=self.operatorData, node_keys=node_keys, timeout=10)
                    if r and r.status_code == 200:
                        received_json = r.json()
                        if received_json['message'] == 'Success':
                            upk_deactivated = True
                            Clock.schedule_once(lambda dt, line='Completed': self.update_text(line))
                            break
                        else:
                            Clock.schedule_once(lambda dt, line=received_json['err']: self.update_text(line))

        if not upk_deactivated:
            def add_proceed_button():
                self.field = BoxLayout(orientation='horizontal', size_hint=(1, None), height=dp(30))
                self.proceed_commands = CommandRunner(self, [['run_command', 'run_uninstall_step2']], self.content, self.text_input, {'run_uninstall_step2':{'cmd':'run_uninstall_step2','func':self.run_uninstall_step2}}, main_screen=self.parent_screen)
                self.proceed_button = Button(text='Proceed Anyway', size_hint=(1, None), height=dp(30))
                self.proceed_button.bind(on_press=self.proceed_uninstall)
                self.add_widget(self.proceed_button)

            response = f'\nFailed to contact network. Continuing with uninstall could cause a security concern with this node keys.\n'
            Clock.schedule_once(lambda dt: add_proceed_button())
            Clock.schedule_once(lambda dt, line=response: self.update_text(line))
            
        else:
            commands = [['run_command', 'run_uninstall_step2']]
            special_commands = {}
            special_commands['run_uninstall_step2'] = {'cmd':'run_uninstall_step2', 'func':self.run_uninstall_step2}
            self.command_runner = CommandRunner(self, commands, self.content, self.text_input, special_commands, main_screen=self.parent_screen)
            threading.Thread(target=self.command_runner.run_commands).start()
    
    def proceed_uninstall(self, instance=None):
        print('-proceed_uninstall')
        self.remove_widget(self.proceed_button)
        threading.Thread(target=self.proceed_commands.run_commands).start()
    
    def run_uninstall_step2(self, instance=None):
        try:
            self.remove_widget(self.proceed_button)
        except Exception as e:
            print('remove proceed_button button err 632', str(e))
        self.command_runner = CommandRunner(self, self.commands, self.content, self.text_input, self.special_commands, finish_command=self.run_finish_command, main_screen=self.parent_screen)
        threading.Thread(target=self.command_runner.run_commands).start()

    def read_output_remote(self):
        channel = self.stdout.channel
        last_data_time = time.time()
        while True:
            if time.time() - last_data_time > 150:
                print("Timeout: command produced no output for 2.5 mins")
                break

            if channel.recv_ready() or channel.recv_stderr_ready():
                last_data_time = time.time()
                
            if channel.exit_status_ready() and not channel.recv_ready() and not channel.recv_stderr_ready():
                break
            if channel.recv_ready():
                output = channel.recv(1024).decode()

                if output:
                    if output.startswith("<<<RPC ") and output.endswith(" >>>\n"):
                        try:
                            import json
                            json_part = output[len("<<<RPC "):-len(" >>>\n")]
                            payload = json.loads(json_part)

                            if payload.get("type") == "result":
                                Clock.schedule_once(
                                    lambda dt, line=f"\nResult: {payload['value']}": self.update_text(line)
                                )
                                continue

                            if payload.get("type") == "error":
                                Clock.schedule_once(
                                    lambda dt, line=f"\nError: {payload['value']}": self.update_text(line)
                                )
                                continue

                        except Exception:
                            pass  # fall through to normal handling

                    cleaned = self.clean_output(output)
                    cleaned = cleaned.replace(self.remote_data["password"], '*****')

                    if self.should_auto_confirm(cleaned):
                        try:
                            self.stdin.write("y\n")
                            self.stdin.flush()
                        except Exception:
                            pass

                    time_str = self.make_timestamp()
                    Clock.schedule_once(
                        lambda dt, l=f"{time_str} {cleaned}": self.update_text(l)
                    )

            if channel.recv_stderr_ready():
                output = channel.recv_stderr(1024).decode()
                if output:
                    if output.startswith("<<<RPC ") and output.endswith(" >>>\n"):
                        try:
                            import json
                            json_part = output[len("<<<RPC "):-len(" >>>\n")]
                            payload = json.loads(json_part)

                            if payload.get("type") == "result":
                                Clock.schedule_once(
                                    lambda dt, line=f"\nResult: {payload['value']}": self.update_text(line)
                                )
                                continue

                            if payload.get("type") == "error":
                                Clock.schedule_once(
                                    lambda dt, line=f"\nError: {payload['value']}": self.update_text(line)
                                )
                                continue

                        except Exception:
                            pass  # ignore parsing errors
                    cleaned = self.clean_output(output)
                    cleaned = cleaned.replace(self.remote_data["password"], '*****')

                    if self.should_auto_confirm(cleaned):
                        try:
                            self.stdin.write("y\n")
                            self.stdin.flush()
                        except Exception:
                            pass

                    print('remote error-%s--:%s' %(datetime.datetime.now(),output))
                    time_str = self.make_timestamp()
                    Clock.schedule_once(
                        lambda dt, l=f"{time_str} {cleaned}": self.update_text(l)
                    )

            time.sleep(0.02)

    def update_rect(self, *args):
        self.rect.size = self.size
        self.rect.pos = self.pos

def expand_user_data(screen, instance=None, target_tree=[]):
    print('-expand_user_data, target_tree:',target_tree)
    try:
        screen.remove_widget(screen.title)
        screen.remove_widget(screen.save_button)
    except:
        pass
    try:
        screen.parent_screen.display_layout.remove_widget(screen.localData_button)
    except:
        pass
    try:
        screen.remove_widget(screen.content)
    except:
        pass
    try:
        screen.remove_widget(screen.scroll_view)
    except:
        pass

    t = ''
    text = ''
    if target_tree:
        operatorData = get_operatorData()
        top_level = operatorData
        fields = {}
        text += f'Local data'
        for t in target_tree:
            if t in top_level:
                text += f' - {t}'
                fields = top_level[t]
                top_level = fields
        screen.title = Label(text=text, size_hint_y=None, height=dp(30), halign='center')
        screen.add_widget(screen.title)
    else:
        screen.title = Label(text='Local Data', size_hint_y=None, height=dp(30), halign='center')
        screen.add_widget(screen.title)
        fields = get_operatorData()
    screen.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
    screen.content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=5)
    screen.content.bind(minimum_height=screen.content.setter("height"), minimum_width=screen.content.setter("width"))

    screen.content.add_widget(Divider(padding=0))
    if isinstance(fields, dict):
        for key, value in fields.items():
            if key not in ['systemPass', 'userPass', 'password']:
                screen.content.add_widget(FieldRow(key, value, parent=screen, target_tree=target_tree, superuser=False, editable=False))
    elif isinstance(fields, list):
        for value in fields:
            screen.content.add_widget(FieldRow(t, value, parent=screen, target_tree=target_tree, superuser=False, editable=False))

    screen.scroll_view.add_widget(screen.content)
    screen.add_widget(screen.scroll_view)

def parse_fields(items=None, obj=None):
    if obj:
        items = [child for child in reversed(obj.content.children) if isinstance(child, FieldRow)]
    field_data = {}
    if items:
        for i in items:
            if i.input:
                if '_array' in i.key and i.input.text and str(i.input.text) != 'None':
                    x = []
                    for y in ast.literal_eval(i.input.text):
                        x.append(y)
                else:
                    try:
                        x = i.input.text
                    except:
                        x = str(i.input.active)
                if not x or x == 'None':
                    field_data[i.key] = None
                elif i.key == 'modlVer':
                    field_data[i.key] = int(x)
                elif isinstance(x, str) and x.startswith('{'):
                    field_data[i.key] = ast.literal_eval(x)
                else:
                    field_data[i.key] = x
    return field_data

def update_text(obj, line):
    # print('-update_text', line, obj)
    try:
        obj.text_input.text += line
    except Exception as e:
        print('update_text fail 523',str(e))

import threading
from kivy.clock import Clock

def run_commands(commands, on_finished=None):
    index = [0]  # use a list so the nested function can mutate it

    def run_next():
        if index[0] >= len(commands):
            if on_finished:
                on_finished()
            return

        cmd = commands[index[0]]
        print(f"command {index[0]} running")

        def worker():
            cmd()
            Clock.schedule_once(advance)

        threading.Thread(target=worker, daemon=True).start()

    def advance(dt):
        index[0] += 1
        run_next()

    run_next()

class CommandRunner:
    def __init__(self, parent, command_queue, content, output_display, special_commands, remote_data={}, main_screen=None, finish_command=None, end_of_line=False, operatorData=None, context={}):
        self.command_queue = command_queue
        self.parent = parent
        self.operator_screen = main_screen
        self.operatorData = operatorData
        self.content = content
        self.special_commands = special_commands
        self.output_display = output_display
        self.current_process = None
        self.total_steps = len(command_queue)
        self.user_input = None
        self.waiting_for_input = False
        self.master_fd = None
        self.resp = None
        self.lock = threading.Lock()
        self.command_index = 0
        self.start_time = datetime.datetime.now()
        self.end_of_line = end_of_line
        self.finish_command = finish_command
        self.prev_line = ''
        self.looping_lines = 0
        self.systemPass = None
        self.context = context
        self.remote_data = remote_data
        self.stdout = None

        if self.remote_data:
            if not isinstance(self.remote_data, dict):
                if 'local_nodeId' not in self.operatorData or self.operatorData['selected_node'] != self.operatorData['local_nodeId']:
                    remote_node = self.operatorData['myNodes'][self.operatorData['selected_node']]
                    self.remote_data = get_remote(node_id=self.operatorData['selected_node'], operatorData=self.operatorData)
            if self.connect_remote():
                if 'fetch_cmds' not in self.context or self.context['fetch_cmds'] == True:
                    extras = {}
                    if 'extras' in self.context:
                        extras = self.context['extras']
                    commands, special_commands = fetch_remote_commands(
                        self.context["task"],
                        self.ssh_client,
                        extras=extras
                    )
                    if isinstance(commands, list) and len(commands) > 0:
                        self.command_queue = self.command_queue + commands
                        self.special_commands = self.special_commands | special_commands
                    else:
                        self.command_queue = []
                    print('returned commands!:',commands)
                    print('returned special_commands!:',special_commands)
                    self.total_steps = len(self.command_queue)
                        
    def connect_remote(self):
        if not self.remote_data:
            return

        connected, self = make_remote_connection(self.remote_data, cls=self)
        return connected
    
    def close_remote(self):
        # print('-close remote connection')
        if self.ssh_client:
            self.ssh_client.close()

    def add_viewable_input(self, line):
        self.text_input = TextInput(hint_text="Enter your input", size_hint=(1, None), height=dp(30), multiline=False)
        self.content.add_widget(self.text_input)
        self.text_input.bind(on_text_validate=lambda instance: self.execute_after_input(self))
        self.text_input.focus = True
        self.update_output(line)

    def add_secure_input(self, line):
        # print('-add_secure_input')
        self.text_input = TextInput(hint_text="Enter your password", size_hint=(1, None), height=dp(30), multiline=False, password=True)
        self.content.add_widget(self.text_input)
        self.text_input.bind(on_text_validate=lambda instance: self.execute_after_secure_input(instance))
        self.text_input.focus = True
        self.update_output(line)

    def remove_input(self, line=None):
        self.content.remove_widget(self.text_input)

    def run_commands(self):
        print('-self.command_index',self.command_index)
        if self.parent and hasattr(self.parent, 'abort_function') and self.parent.abort_function:
            Clock.schedule_once(lambda dt, line=f'Aborted at {now_utc().strftime("%Y-%m-%d %H:%M:%S")}\n': self.update_output(line))
            try:
                self.parent.remove_widget(self.parent.abort_button)
            except Exception as e:
                pass
            if self.operator_screen:
                self.operator_screen.job_running = False
            if self.remote_data:
                self.close_remote()
        elif self.looping_lines >= 10:
            Clock.schedule_once(lambda dt, line='\n\nAn error occured. Aborting.': self.update_output(line))
            try:
                self.parent.remove_widget(self.parent.abort_button)
            except Exception as e:
                pass
            if self.operator_screen:
                self.operator_screen.job_running = False
            if self.remote_data:
                self.close_remote()
        elif self.end_of_line:
            Clock.schedule_once(lambda dt, line='\n\n': self.update_output(line))
            if self.finish_command:
                Clock.schedule_once(self.finish_command, 0.1)
            if self.operator_screen:
                self.operator_screen.job_running = False
            if self.remote_data:
                self.close_remote()
            Clock.schedule_once(lambda dt, line=f'{now_utc().strftime("%Y-%m-%d %H:%M:%S")}\n': self.update_output(line))
            print("All commands completed1")
        elif self.command_index < len(self.command_queue):
            cmd = self.command_queue[self.command_index]
            self.command_index += 1
            self.run_command(cmd)
        else:
            Clock.schedule_once(lambda dt, line='\n\n': self.update_output(line))
            if self.finish_command:
                Clock.schedule_once(self.finish_command, 0.1)
            elif self.operator_screen:
                self.operator_screen.job_running = False
            if self.remote_data:
                self.close_remote()
            Clock.schedule_once(lambda dt, line=f'{now_utc().strftime("%Y-%m-%d %H:%M:%S")}\n': self.update_output(line))
            print("All commands completed2")

    def run_command(self, command):
        # print('-run_command__')
        now = datetime.datetime.now() - self.start_time
        cmd_text = '\n\n(%s/%s)- ' %(self.command_index, self.total_steps)
        try:
            print('-command:', command, cmd_text.replace('\n',''))
            if isinstance(command, list):
                for c in command:
                    cmd_text += c + ' '
            else:
                cmd_text = command
                if 'get_random_secret_key()' in cmd_text:
                    cmd_text = '\n\n' + cmd_text + '\n\n'
            Clock.schedule_once(lambda dt, line=cmd_text: self.update_output(line))
            if command[0] in ['run_command','run_local_command']:
                if self.remote_data and command[0] == 'run_command':
                    import json, base64

                    cmd_name = command[1]
                    reqs = self.special_commands[cmd_name].get("reqs", None)
                    clean_reqs = self.serialize_reqs_for_remote(reqs)
                    task = self.context['task']

                    args_json = json.dumps(clean_reqs)
                    args_cleaned = base64.b64encode(args_json.encode()).decode()

                    python_bin = "~/Sonet/.data/nenv/bin/python"
                    base = "cd ~/Sonet/SoNodeManager/commands &&"
                    print('task',task, 'cmd_name',cmd_name)
                    cmd = (
                        f"{base} {python_bin} remote_run_command.py "
                        f"{task} {cmd_name} '{args_cleaned}'"
                    )

                    self.stdin, self.stdout, self.stderr = self.ssh_client.exec_command(cmd, get_pty=True)
                    threading.Thread(target=self.read_output_remote, daemon=True).start()
                    return

                else:
                    func = self.special_commands[command[1]]['func']
                    print(func)
                    if 'reqs' in self.special_commands[command[1]]:
                        print('has reqs')
                        reqs = self.special_commands[command[1]]['reqs']
                        err = None
                        if reqs == 'display_content':
                            try:
                                self.resp = func(self.output_display.text)
                                if 'fail' in str(self.resp).lower() or 'error' in str(self.resp).lower():
                                    err = str(self.resp)
                            except Exception as e:
                                print('self.resp fail 1',str(e))
                                err = f'self.resp fail 1 {e}'
                        elif reqs == 'output_display':
                            try:
                                self.resp = func(output=self.output_display)
                                if 'fail' in str(self.resp).lower() or 'error' in str(self.resp).lower():
                                    err = str(self.resp)
                            except Exception as e:
                                print('function fail',str(e))
                                err = f'Function Fail: {e}'
                        elif reqs == 'None':
                            try:
                                self.resp = func(None)
                                if 'fail' in str(self.resp).lower() or 'error' in str(self.resp).lower():
                                    err = str(self.resp)
                            except Exception as e:
                                print('self.resp fail 2',str(e))
                                err = f'self.resp fail 2 {e}'
                        elif isinstance(reqs, list):
                            try:
                                if 'output_display' in reqs:
                                    reqs[reqs.index('output_display')] = self.output_display
                                if 'display_content' in reqs:
                                    reqs[reqs.index('display_content')] = self.output_display.text
                                if 'parent_screen' in reqs:
                                    reqs[reqs.index('parent_screen')] = self.parent
                                self.resp = func(*reqs)
                                if 'fail' in str(self.resp).lower() or 'error' in str(self.resp).lower():
                                    err = str(self.resp)
                            except Exception as e:
                                print('self.resp fail 3',str(e))
                                err = f'self.resp fail 3 {e}'

                        if err:
                            self.end_of_line = True
                            Clock.schedule_once(lambda dt, line=f'err:{err}': self.update_output(line))
                    else:
                        print('no reqs')
                        func()
            elif command[0] == 'raise_if_error':
                command.pop(0)
                if self.remote_data:
                    if isinstance(command, list):
                        cmd_str = ' '.join(command)
                    else:
                        cmd_str = command
                    print('remote cmd:', cmd_str)
                    self.stdin, self.stdout, self.stderr = self.ssh_client.exec_command(
                        cmd_str,
                        get_pty=True
                    )

                    if cmd_str.strip().startswith("sudo"):
                        pw = self.systemPass or self.remote_data["password"]
                        self.stdin.write(pw + "\n")
                        self.stdin.flush()

                    exit_status = self.stdout.channel.recv_exit_status()
                    if exit_status != 0:
                        self.end_of_line = True
                        Clock.schedule_once(
                            lambda dt, line=(
                                f"\nRemote command failed (exit {exit_status}):\n"
                                f"{cmd_str}\n"
                            ): self.update_output(line)
                        )
                        self.operator_screen.job_running = False
                        raise RuntimeError("Updater halted due to remote command failure")
                else:
                    with self.lock:
                        try:
                            if 'shell' in command or ' | ' in cmd_text:
                                self.current_process = subprocess.Popen(
                                    command,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True,
                                    shell=True
                                )
                            else:
                                self.master_fd, slave_fd = pty.openpty()
                                self.current_process = subprocess.Popen(
                                    command,
                                    stdin=slave_fd,
                                    stdout=slave_fd,
                                    stderr=slave_fd,
                                    text=True
                                )
                                os.close(slave_fd)

                            self.current_process.wait()
                            rc = self.current_process.returncode

                            if rc != 0:
                                self.end_of_line = True
                                Clock.schedule_once(
                                    lambda dt, line=(
                                        f"\nCommand failed (exit {rc}):\n"
                                        f"{' '.join(command) if isinstance(command, list) else command}\n"
                                    ): self.update_output(line)
                                )
                                self.operator_screen.job_running = False
                                raise RuntimeError("Updater halted due to command failure")

                        except Exception as e:
                            self.end_of_line = True
                            Clock.schedule_once(
                                lambda dt, line=f'An error occurred: {e}'
                            : self.update_output(line))
                            return
            else:
                print('else resp')
                if 'self.resp' in command:
                    index = command.index('self.resp')
                    command[index] = self.resp

                if self.remote_data:
                    if isinstance(command, list):
                        cmd_str = ' '.join(command)
                    else:
                        cmd_str = command
                    print('remote cmd:',cmd_str)

                    if 'input_pass' in cmd_str:
                        cmd_str = cmd_str.replace('input_pass', self.systemPass or self.remote_data["password"])
                    self.stdin, self.stdout, self.stderr = self.ssh_client.exec_command(cmd_str, get_pty=True)

                    if cmd_str.strip().startswith("sudo"):
                        pw = self.systemPass or self.remote_data["password"]
                        self.stdin.write(pw + "\n")
                        self.stdin.flush()
                else:
                    if any(i == 'input_pass' for i in command):
                        index = command.index('input_pass')
                        command[index] = self.systemPass or self.remote_data["password"]
                    with self.lock:
                        try:
                            if 'shell' in command or ' | ' in cmd_text:
                                self.current_process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
                            else:
                                self.master_fd, slave_fd = pty.openpty()
                                self.current_process = subprocess.Popen(command, stdin=slave_fd, stdout=slave_fd, stderr=slave_fd, text=True)
                                os.close(slave_fd)
                        except Exception as e:
                            self.end_of_line = True
                            Clock.schedule_once(lambda dt, line=f'An error occurred: {e}': self.update_output(line))
            if self.remote_data and self.stdout:
                threading.Thread(target=self.read_output_remote, daemon=True).start()
            else:
                threading.Thread(target=self.read_output_local, daemon=True).start()
        except Exception as e:
                Clock.schedule_once(lambda dt, line=f'\n\ncommand err 823:{e}\nattempted command: {command}': self.update_output(line))
                return

    def read_output_local(self):
        def make_timestamp():
            now = datetime.datetime.now() - self.start_time
            total = int(now.total_seconds())
            hours = total // 3600
            minutes = (total % 3600) // 60
            seconds = total % 60

            time_str = f"{hours:02}:{minutes:02}:{seconds:02}s"
            if time_str.startswith("00:"):
                time_str = time_str[3:]
            time_str = "\n" + time_str
            return time_str
        
        while True:
            if not self.current_process or self.current_process.poll() is not None:
                print('-has break')
                break
            try:
                output = self.current_process.stdout.readline()
                if not output:
                    output = self.read_from_fd(self.master_fd)
            except Exception as e:
                output = self.read_from_fd(self.master_fd)
            if output:
                cleaned_output = self.clean_output(output)
                time_str = make_timestamp()

                print('output--%s--:%s' %(datetime.datetime.now(),output))
                if output in self.prev_line:
                    self.looping_lines += 1
                elif self.looping_lines != 0:
                    self.looping_lines = 0
                self.prev_line = output

                if 'Waiting for cache lock' in output and 'It is held by process' in output:
                    x = output.find('It is held by process ')+len('It is held by process ')
                    y = output.find(' (apt)')
                    prcs_num = output[x:y]
                    if prcs_num:
                        try:
                            subprocess.run(["sudo", "-S", 'kill', '-9', prcs_num])
                        except Exception as e:
                            pass

                elif '(Y/n)?' in output or '[Y/n]' in output or '?' in output:
                    input = 'y\n'
                    os.write(self.master_fd, input.encode())
                elif any(word in output.lower() for word in ['password:','password for','[sudo]']):
                    if 'try again' in output.lower():
                        Clock.schedule_once(lambda dt, line=f'{time_str} {output.lower()}': self.update_output(line))
                        self.waiting_for_input = True
                        Clock.schedule_once(lambda dt, line=f'{time_str} {cleaned_output}': self.add_secure_input(line))
                        return  # Wait for user input before continuing
                    
                    if not self.systemPass:
                        if self.remote_data:
                            self.systemPass = self.remote_data['password']
                        else:
                            self.systemPass = fetch_secure_item('sysPass')
                    if self.systemPass:
                        if self.remote_data:
                            self.stdin.write(self.systemPass + "\n")
                        else:
                            input = self.systemPass + '\n'
                            os.write(self.master_fd, input.encode())
                    else:
                        operatorData = get_operatorData()
                        if 'sysPass' in operatorData and operatorData['sysPass']:
                            self.systemPass = operatorData['sysPass']
                            input = self.systemPass + '\n'
                            os.write(self.master_fd, input.encode())
                        else:
                            self.waiting_for_input = True
                            Clock.schedule_once(lambda dt, line=f'{time_str} {cleaned_output}': self.add_secure_input(line))
                            return  # Wait for user input before continuing
                elif '[' in output or 'eta' in output or output.strip() == 'y':
                    # print('[eta]')
                    pass
                elif 'incorrect password' in output.lower():
                    Clock.schedule_once(lambda dt, line=f'{time_str} {output.lower()}': self.update_output(line))
                    self.waiting_for_input = True
                    Clock.schedule_once(lambda dt, line=f'{time_str} {cleaned_output}': self.add_secure_input(line))
                    return  # Wait for user input before continuing
                elif cleaned_output:
                    Clock.schedule_once(lambda dt, line=f'{time_str} {cleaned_output}': self.update_output(line))

        self.run_commands()

    def read_output_remote(self):
        channel = self.stdout.channel
        last_data_time = time.time()

        while True:
            if time.time() - last_data_time > 150:
                print("Timeout: command produced no output for 2.5 mins")
                break

            if channel.recv_ready() or channel.recv_stderr_ready():
                last_data_time = time.time()
                
            if channel.exit_status_ready() and not channel.recv_ready() and not channel.recv_stderr_ready():
                break
            if channel.recv_ready():
                try:
                    output = channel.recv(1024).decode()
                except Exception as e:
                    print('output err 531',str(e))
                    output = None

                if output:
                    if output.startswith("<<<RPC ") and output.endswith(" >>>\n"):
                        try:
                            import json
                            json_part = output[len("<<<RPC "):-len(" >>>\n")]
                            payload = json.loads(json_part)

                            if payload.get("type") == "result":
                                Clock.schedule_once(
                                    lambda dt, line=f"\nResult: {payload['value']}": self.update_output(line)
                                )
                                continue

                            if payload.get("type") == "error":
                                Clock.schedule_once(
                                    lambda dt, line=f"\nError: {payload['value']}": self.update_output(line)
                                )
                                continue

                        except Exception:
                            pass  # fall through to normal handling

                    cleaned = self.clean_output(output)
                    cleaned = cleaned.replace(self.remote_data["password"], '*****')

                    if any(word in output.lower() for word in ['password:','password for','[sudo]']):
                        pw = self.systemPass or self.remote_data["password"]
                        try:
                            self.stdin.write(pw + "\n")
                            self.stdin.flush()
                            pw_sent = True
                            print('pw inputted')
                        except Exception as e:
                            print('pass err 3', str(e))

                    if self.should_auto_confirm(cleaned):
                        try:
                            self.stdin.write("y\n")
                            self.stdin.flush()
                        except Exception:
                            pass

                    print('remote output--%s--:%s' %(datetime.datetime.now(),output))
                    time_str = self.make_timestamp()
                    Clock.schedule_once(
                        lambda dt, l=f"{time_str} {cleaned}": self.update_output(l)
                    )
                    if 'raise' in output or 'RuntimeError' in output:
                        raise RuntimeError("Updater halted due to remote command failure")

            if channel.recv_stderr_ready():
                output = channel.recv_stderr(1024).decode()

                if output:
                    if output.startswith("<<<RPC ") and output.endswith(" >>>\n"):
                        try:
                            import json
                            json_part = output[len("<<<RPC "):-len(" >>>\n")]
                            payload = json.loads(json_part)

                            if payload.get("type") == "result":
                                Clock.schedule_once(
                                    lambda dt, line=f"\nResult: {payload['value']}": self.update_output(line)
                                )
                                continue

                            if payload.get("type") == "error":
                                Clock.schedule_once(
                                    lambda dt, line=f"\nError: {payload['value']}": self.update_output(line)
                                )
                                continue

                        except Exception:
                            pass  # ignore parsing errors
                    cleaned = self.clean_output(output)
                    cleaned = cleaned.replace(self.remote_data["password"], '*****')

                    if self.should_auto_confirm(cleaned):
                        try:
                            self.stdin.write("y\n")
                            self.stdin.flush()
                        except Exception:
                            pass

                    print('remote error-%s--:%s' %(datetime.datetime.now(),output))
                    time_str = self.make_timestamp()
                    Clock.schedule_once(
                        lambda dt, l=f"{time_str} {cleaned}": self.update_output(l)
                    )
                    if 'raise' in output or 'RuntimeError' in output:
                        raise RuntimeError("Updater halted due to remote command failure")

            time.sleep(0.02)

        self.run_commands()

    def read_from_fd(self, fd):
        try:
            return os.read(fd, 1024).decode('utf-8')
        except:
            return ''
        
    def make_timestamp(self):
        now = datetime.datetime.now() - self.start_time
        total = int(now.total_seconds())
        hours = total // 3600
        minutes = (total % 3600) // 60
        seconds = total % 60

        time_str = f"{hours:02}:{minutes:02}:{seconds:02}s"
        if time_str.startswith("00:"):
            time_str = time_str[3:]
        time_str = "\n" + time_str
        return time_str
    
    def clean_output(self, output):
        txt = re.sub(r'[^\x09\x0A\x20-\x7E]', '', output)
        return txt.strip("\n")
        
    def should_auto_confirm(self, text):
        lower = text.lower()
        if "password" in lower:
            return False
        if "(y/n" in lower or "[y/n" in lower:
            return True
        QUESTION_KEYWORDS = [
            "continue",
            "proceed",
            "confirm",
            "install",
            "upgrade",
            "overwrite",
            "replace",
            "remove",
            "clean",
            "delete",
            '[y]es',
            '(y|n)',
        ]

        if lower.strip().endswith("?") and any(k in lower for k in QUESTION_KEYWORDS):
            return True
        return False

    def update_output(self, output):
        try:
            if self.output_display:
                if not output.endswith('\n') and not output.startswith('\n'):
                    output = output + '\n'
                self.output_display.text += output
                lines = self.output_display.text.splitlines()
                if display_max_size > 0 and len(lines) > display_max_size:
                    last_n_lines = lines[-display_max_size:]
                    result = "\n".join(last_n_lines)
                    self.output_display.text = result
        except Exception as e:
            print('command output err1:', str(e))
            pass
        try:
            if self.command_index < 5:
                self.parent.scroll_view.scroll_y = 0
            else:
                at_bottom = self.parent.scroll_view.scroll_y <= 0.1
                if at_bottom:
                    self.parent.scroll_view.scroll_y = 0
        except Exception as e:
            print('command output err2',str(e))

    def execute_after_input(self, instance):
        if self.waiting_for_input:
            # print(-'execute_after_input')
            user_input = self.text_input.text + '\n'
            self.text_input.text = ''
            self.waiting_for_input = False
            os.write(self.master_fd, user_input.encode())
            threading.Thread(target=self.read_output_local).start()
            Clock.schedule_once(lambda dt, line=None: self.remove_input())

    def execute_after_secure_input(self, instance):
        if self.waiting_for_input:
            # print('-execute_after_secure_input')
            systemPass = self.text_input.text
            store_secure_item("sysPass", systemPass)
            user_input = systemPass + '\n'
            self.text_input.text = ''
            self.waiting_for_input = False
            os.write(self.master_fd, user_input.encode())
            threading.Thread(target=self.read_output_local).start()
            Clock.schedule_once(lambda dt, line=None: self.remove_input())

    def serialize_reqs_for_remote(self, reqs):
        if reqs == 'None' or reqs is None:
            return []

        if isinstance(reqs, str):
            if reqs == 'display_content':
                return [str(self.output_display.text)[-1000:]]

            if reqs == 'output_display':
                return ["__IGNORED__"]

            if reqs == 'parent_screen':
                return ["__IGNORED__"]

            return [reqs]

        if isinstance(reqs, list):
            out = []
            for r in reqs:
                if r == 'display_content':
                    out.append(self.output_display.text)
                elif r == 'output_display':
                    out.append("__IGNORED__")
                elif r == 'parent_screen':
                    out.append("__IGNORED__")
                else:
                    out.append(r)
            return out

        return [reqs]


class LoadScreen(BoxLayout):
    def __init__(self, **kwargs):
        super(LoadScreen, self).__init__(**kwargs)

        with self.canvas.before:
            Color(0.094, 0.122, 0.176, 1)
            self.rect = Rectangle(size=self.size, pos=self.pos)
            self.bind(size=self.update_rect, pos=self.update_rect)

    def activate_display(self):
        print('-LoadScreen activate_display')
        
        self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        self.content = BoxLayout(orientation="vertical", size_hint_y=None, size_hint_x=None)
        self.content.bind(minimum_height=self.content.setter("height"))
        self.add_widget(Divider(padding=0))

        self.text_input = TextInput(
            text="",
            size_hint_x=None,
            size_hint_y=None,
            halign="left",
            multiline=True, 
            background_color=dark_blue2,
            foreground_color=(1, 1, 1, 1) 
        )
        self.text_input.bind(minimum_height=self.text_input.setter('height'))
        self.content.add_widget(self.text_input)
        self.scroll_view.add_widget(self.content)
        self.add_widget(self.scroll_view)
        texts = [
            '''Loading...''',
        ]
        for text in texts:
            self.text_input.text += text + '\n\n'

    def update_status(self, line):
        self.save_button.text = line

    def switch_to_install(self):
        # print('-switch to install')
        self.parent_screen.switch_to_install_setup()

    def switch_to_operations(self, instance, refresh=False):
        if refresh:
            x = self.parent_screen.manager.get_screen('operator_screen')
            x.refresh_sidebar()
        self.parent_screen.manager.current = 'operator_screen'

    def update_rect(self, *args):
        self.rect.size = self.size
        self.rect.pos = self.pos






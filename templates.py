
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.checkbox import CheckBox
from kivy.uix.treeview import TreeView, TreeViewNode
from kivy.uix.behaviors import ButtonBehavior
from kivy.animation import Animation
from kivy.uix.dropdown import DropDown
from kivy.core.text import Label as CoreLabel
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Line, Rectangle, Color

from mnemonic import Mnemonic
import json
from os.path import expanduser
from functools import partial


class Background(BoxLayout):
    def __init__(self, content=None, **kwargs):
        page_instance = kwargs.pop('page_instance', None)
        super(Background, self).__init__(**kwargs)
        self.page_instance = page_instance
        self.content = content
        self.orientation='vertical'
        self.size_hint=(1, 1)
        self.width = Window.width
        self.height = Window.height
        self.initial_color = Color(rgba=[int(x, 16) / 255.0 for x in ('01', '21', '3f', 'ff')])
        self.canvas.add(self.initial_color)
        self.gradient_rect = Line(points=[0, 0, self.width, 0], width=self.height)
        self.canvas.add(self.gradient_rect)

        self.gradient_color = None
        self.gradient_points = None

        Window.bind(on_resize=self.update_on_resize)

        self.add_gradient()

    def update_gradient(self, instance, value):
        self.width = Window.width
        self.height = Window.height
        try:
            self.gradient_rect.points = [0, 0, self.width, 0]
        except:
            pass

    def update_on_resize(self, window, width, height):
        self.clear_widgets()
        self.canvas.remove(self.gradient_rect)
        self.gradient_rect = None
        self.canvas.remove(self.initial_color)
        self.initial_color = None
        self.width = Window.width
        self.height = Window.height
        self.initial_color = Color(rgba=[int(x, 16) / 255.0 for x in ('01', '21', '3f', 'ff')])
        self.canvas.add(self.initial_color)
        self.gradient_rect = Line(points=[0, 0, self.width, 0], width=self.height)
        self.canvas.add(self.gradient_rect)

        self.gradient_rect.points = [0, 0, self.width, 0]

        if self.content == 'splash_layout':
            self.page_instance.switch_to_splash_page(self.page_instance)
        elif self.content == 'login_layout':
            self.page_instance.switch_to_login_page(self.page_instance)
        elif self.content == 'new_user_layout':
            self.page_instance.switch_to_create_user_page(self.page_instance)
        elif self.content == 'create_superuser_form_layout':
            self.page_instance.create_superuser_form(self.page_instance)
        elif self.content == 'seed_layout':
            self.page_instance.switch_to_seed_ip_page(self.page_instance)

    def add_gradient(self):
        alpha_channel_rate = 0
        increase_rate = 1 / self.height

        for sep in range(int(self.height)):
            self.gradient_color = Color(rgba=(11/255, 85/255, 154/255, alpha_channel_rate))
            self.canvas.add(self.gradient_color)

            self.gradient_points = Line(points=[0, sep, self.width, sep], width=1)
            self.canvas.add(self.gradient_points)
            alpha_channel_rate += increase_rate

def splash_logo(layout):
    topSection = RelativeLayout()
    layout.add_widget(topSection)
    logoSection = RelativeLayout()
    logoSection.center_x = layout.width / 2
    logoSection.center_y = layout.height / 2  # Draw the border
    homepath = expanduser("~")
    logoSection.logo = Image(source=f'{homepath}/Sonet/SoNodeManager/assets/img/sologo.png') 
    logoSection.add_widget(logoSection.logo)
    layout.add_widget(logoSection)
    return layout

def splash_page_content(layout, page_instance):
    welcomeText = 'So, You Want To Be A Hero?'
    problem = False
    import subprocess, os, platform
    if platform.system() == 'Darwin':
        device_system = 'mac'
    elif platform.system() == 'Windows':
        device_system = 'windows'
    else:
        device_system = 'linux'
        try:
            homepath = expanduser("~")
        except Exception as e:
            welcomeText = 'A problem has occured: %s' %(str(e))
            problem = True

    from ops import w_scale, t_scale

    page_instance.content = 'splash_layout'
    layout = splash_logo(layout)

    centerSection = RelativeLayout()
    centerSection.center_x = layout.width / 2
    centerSection.center_y = layout.height / 2
    centerSection.title = Label(size_hint=(1, 0.5), text=welcomeText, font_size=dp(20)* t_scale)
    centerSection.add_widget(centerSection.title)
    layout.add_widget(centerSection)
    if not problem:
        bottomSection = RelativeLayout()
        bottomSection.center_x = layout.width / 2
        bottomSection.center_y = layout.height / 2
        bottomSection.nextButton = Button(text='Start',
            background_color=(1, 1, 1, 1),  
            background_normal='',
            color=(0, 0, 0, 1),  
            size_hint=(None, None), size=(dp(100)* w_scale, dp(50)* w_scale), pos_hint={'center_x': 0.5},
            on_press=page_instance.switch_to_seed_ip_page,
            font_size=dp(16)* t_scale
        )
        bottomSection.add_widget(bottomSection.nextButton)
        layout.add_widget(bottomSection)
    tailSection = RelativeLayout()
    layout.add_widget(tailSection)
    
    return layout


def seed_ip_content(layout, page_instance, version=None):
    print('-seed_ip_content')
    page_instance.content = 'seed_layout'
    layout = splash_logo(layout)
    if version == 'Failed':

        centerSection = RelativeLayout()
        centerSection.center_x = layout.width / 2
        centerSection.center_y = layout.height / 2
        centerSection.title = Label(size_hint=(1, 0.5), text='Network not found, create new?', font_size='20sp')
        centerSection.add_widget(centerSection.title)
        layout.add_widget(centerSection)
        bottomSection = RelativeLayout()
        bottomSection.backButton = Button(text='Back',
            background_color=(1, 1, 1, 1),  
            background_normal='',
            color=(0, 0, 0, 1),  
            size_hint=(None, None), size=(dp(100), dp(50)), pos_hint={'center_x': 0.4},
            on_press=page_instance.switch_to_seed_ip_page
        )
        bottomSection.nextButton = Button(text='Continue',
            background_color=(1, 1, 1, 1),  
            background_normal='',
            color=(0, 0, 0, 1),  
            size_hint=(None, None), size=(dp(100), dp(50)), pos_hint={'center_x': 0.6},
            on_press=page_instance.create_new_database
        )
        bottomSection.add_widget(bottomSection.backButton)
        bottomSection.add_widget(bottomSection.nextButton)
        layout.add_widget(bottomSection)
    else:
        from commands.utils import get_operatorData
        operatorData = get_operatorData()
        if 'seed_ip' in operatorData:
            seed_ip = operatorData['seed_ip']
        else:
            seed_ip = 'SoSayUs.com'
        centerSection = RelativeLayout()
        userInput = BoxLayout(orientation='horizontal', size_hint=(0.70, None), height=100, pos_hint={'center_x': 0.5})
        centerSection.add_widget(userInput)
        field1 = BoxLayout(orientation='horizontal', size_hint=(1, None), height=dp(30))
        label1 = Label(text='Sonet seed:')
        layout.seed_ip_input = TextInput(text=seed_ip, multiline=False, input_type='text')
        field1.add_widget(label1)
        field1.add_widget(layout.seed_ip_input)
        userInput.add_widget(field1)
        layout.add_widget(centerSection)

        bottomSection = RelativeLayout()

        bottomSection.backButton = Button(text='Back',
            background_color=(1, 1, 1, 1),  
            background_normal='',
            color=(0, 0, 0, 1),  
            size_hint=(None, None), size=(dp(100), dp(50)), pos_hint={'center_x': 0.4},
            on_press=page_instance.switch_to_splash_page
        )
        
        bottomSection.nextButton = Button(text='Continue',
            background_color=(1, 1, 1, 1),  
            background_normal='',
            color=(0, 0, 0, 1),  
            size_hint=(None, None), size=(dp(100), dp(50)), pos_hint={'center_x': 0.6},
            on_press=lambda instance: page_instance.process_seed_ip(layout.seed_ip_input.text)
        )
        bottomSection.add_widget(bottomSection.backButton)
        bottomSection.add_widget(bottomSection.nextButton)
        layout.add_widget(bottomSection)

    
    layout.field4 = BoxLayout(orientation='horizontal', size_hint=(1, None), height=100)
    message = Label(text='')
    page_instance.message = message

    layout.field4.add_widget(message)
    tailSection = RelativeLayout()
    tailSection.add_widget(layout.field4)

    layout.add_widget(tailSection)

    return layout


def toggle_password_visibility(self, key=None, btn=None, instance=None):
    if key.password:
        key.password = False
        btn.text = 'Hide'
    else:
        key.password = True
        btn.text = 'Show'


def login_page_content(layout, page_instance):
    from commands.utils import get_operatorData
    operatorData = get_operatorData()
    if 'username' in operatorData:
        user_name = operatorData['username']
    else:
        user_name = ''
    page_instance.content = 'login_layout'

    layout = splash_logo(layout)

    centerSection = RelativeLayout()
    label1 = Label(text='Restore User')
    centerSection.add_widget(label1)

    userInput = BoxLayout(orientation='horizontal', size_hint=(0.85, None), height=100, pos_hint={'center_x': 0.5})
    centerSection.add_widget(userInput)
    userFields = BoxLayout(orientation='vertical', pos_hint={'center_y': 0.25})
    userInput.add_widget(userFields)

    field2 = BoxLayout(orientation='horizontal', size_hint=(1, None), height=dp(30))
    label2 = Label(text='Username:')
    username = TextInput(hint_text='', text=user_name, multiline=False, input_type='text')
    blank_button = Button(text='', size_hint_x=None, width=dp(70))
    field2.add_widget(label2)
    field2.add_widget(username)
    field2.add_widget(blank_button)
    userFields.add_widget(field2)

    field3 = BoxLayout(orientation='horizontal', size_hint=(1, None), height=dp(30))
    label3 = Label(text='Passphrase:')
    passtext = TextInput(text='', multiline=False, password=True, input_type='text')
    toggle_button = Button(text='Show', size_hint_x=None, width=dp(70))
    toggle_button.bind(on_press=partial(toggle_password_visibility, key=passtext, btn=toggle_button))
    field3.add_widget(label3)
    field3.add_widget(passtext)
    field3.add_widget(toggle_button)
    userFields.add_widget(field3)

    layout.add_widget(centerSection)

    bottomSection = RelativeLayout()

    bottomSection.backButton = Button(text='Set Seed',
        background_color=(1, 1, 1, 1),  
        background_normal='',
        color=(0, 0, 0, 1),  
        size_hint=(None, None), size=(dp(100), dp(50)), pos_hint={'center_x': 0.4},
        on_press=lambda instance: page_instance.switch_to_seed_ip_page(force=True)
    )
    
    bottomSection.nextButton = Button(text='Continue',
        background_color=(1, 1, 1, 1),  
        background_normal='',
        color=(0, 0, 0, 1),  
        size_hint=(None, None), size=(dp(100), dp(50)), pos_hint={'center_x': 0.6},
        on_press=lambda instance: page_instance.process_login(username, passtext)
    )
    bottomSection.add_widget(bottomSection.backButton)
    bottomSection.add_widget(bottomSection.nextButton)
    layout.add_widget(bottomSection)

    field4 = BoxLayout(orientation='horizontal', size_hint=(1, None), height=100)
    message = Label(text='Keep it Secret.\nKeep it Safe.\n')
    page_instance.message = message

    field4.add_widget(message)
    tailSection = RelativeLayout()
    tailSection.add_widget(field4)

    layout.add_widget(tailSection)

    return layout


def create_new_user(layout, page_instance):
    from ops import w_scale, t_scale
    # passphrase = '1234567890'
    passphrase = Mnemonic("english").generate(strength=256)

    layout = splash_logo(layout)

    centerSection = RelativeLayout()
    label1 = Label(text='New User',font_size=dp(16)* t_scale)
    centerSection.add_widget(label1)
    userInput = BoxLayout(orientation='horizontal', size_hint=(0.85, None), height=dp(50)* w_scale, pos_hint={'center_x': 0.5})
    centerSection.add_widget(userInput)

    userFields = BoxLayout(orientation='vertical', pos_hint={'center_y': 0.25})
    userInput.add_widget(userFields)

    field2 = BoxLayout(orientation='horizontal', size_hint=(1, None), height=dp(30)* w_scale)
    label2 = Label(text='Username:',font_size=dp(16)* t_scale)
    username = TextInput(hint_text='', text='Sozed', multiline=False, input_type='text',font_size=dp(16)* t_scale)
    blank_button = Button(text='Restore', size_hint_x=None, width=dp(70)* w_scale, on_press=lambda instance: page_instance.switch_to_login_page())
    field2.add_widget(label2)
    field2.add_widget(username)
    field2.add_widget(blank_button)
    userFields.add_widget(field2)

    field3 = BoxLayout(orientation='horizontal', size_hint=(1, None), height=dp(30)* w_scale)
    label3 = Label(text='Passphrase:',font_size=dp(16)* t_scale)
    
    passtext = TextInput(text=passphrase, multiline=False, password=True, input_type='text',font_size=dp(16)* t_scale)
    toggle_button = Button(text='Show', size_hint_x=None, width=dp(70)* w_scale,font_size=dp(16)* t_scale)
    toggle_button.bind(on_press=partial(toggle_password_visibility, key=passtext, btn=toggle_button))
    field3.add_widget(label3)
    field3.add_widget(passtext)
    field3.add_widget(toggle_button)
    userFields.add_widget(field3)
    layout.add_widget(centerSection)

    bottomSection = RelativeLayout()
    bottomSection.backButton = Button(text='Back',
        background_color=(1, 1, 1, 1),  
        background_normal='',
        color=(0, 0, 0, 1),  
        size_hint=(None, None), size=(dp(100)* w_scale, dp(50)* w_scale), pos_hint={'center_x': 0.4},
        font_size=dp(16)* t_scale,
        on_press=page_instance.switch_to_login_page
    )
    
    bottomSection.nextButton = Button(text='Continue',
        background_color=(1, 1, 1, 1),  
        background_normal='',
        color=(0, 0, 0, 1),  
        size_hint=(None, None), size=(dp(100)* w_scale, dp(50)* w_scale), pos_hint={'center_x': 0.6},
        font_size=dp(16)* t_scale,
        on_press=lambda instance: page_instance.create_new_user(username, passtext)
    )
    bottomSection.add_widget(bottomSection.backButton)
    bottomSection.add_widget(bottomSection.nextButton)
    layout.add_widget(bottomSection)

    field4 = BoxLayout(orientation='horizontal', size_hint=(1, None), height=dp(50)* w_scale)
    message = Label(text='Store username and 24 word passphrase in a secure place.\nPassphrase is not saved.\nPassphrase cannot be reset if lost.',font_size=dp(16)* t_scale)
    page_instance.message = message

    field4.add_widget(message)
    tailSection = RelativeLayout()
    tailSection.add_widget(field4)

    layout.add_widget(tailSection)

    return layout


def create_superuser_form(layout, page_instance):
    print('-create_superuser_form 1', page_instance)
    from ops import w_scale, t_scale
    passphrase = Mnemonic("english").generate(strength=128)
    # passphrase = ''

    layout = splash_logo(layout)

    centerSection = RelativeLayout()
    label1 = Label(text='Create First Superuser')
    centerSection.add_widget(label1)

    userInput = BoxLayout(orientation='horizontal', size_hint=(0.85, None), height=100, pos_hint={'center_x': 0.5})
    centerSection.add_widget(userInput)

    userFields = BoxLayout(orientation='vertical', pos_hint={'center_y': 0.25})
    userInput.add_widget(userFields)

    field2 = BoxLayout(orientation='horizontal', size_hint=(1, None), height=dp(30)* w_scale)
    label2 = Label(text='Username:',font_size=dp(16)* t_scale)
    username = TextInput(hint_text='', text='Sozed', multiline=False, input_type='text')
    blank_button = Button(text='', size_hint_x=None, width=dp(70)* w_scale)
    field2.add_widget(label2)
    field2.add_widget(username)
    field2.add_widget(blank_button)
    userFields.add_widget(field2)

    field3 = BoxLayout(orientation='horizontal', size_hint=(1, None), height=dp(30)* w_scale)
    label3 = Label(text='Passphrase:',font_size=dp(16)* t_scale)
    
    passtext = TextInput(text=passphrase, multiline=False, password=True, input_type='text')
    toggle_button = Button(text='Show', size_hint_x=None, width=dp(70)* w_scale)
    toggle_button.bind(on_press=partial(toggle_password_visibility, key=passtext, btn=toggle_button))
    field3.add_widget(label3)
    field3.add_widget(passtext)
    field3.add_widget(toggle_button)
    userFields.add_widget(field3)
    layout.add_widget(centerSection)

    bottomSection = RelativeLayout()
    bottomSection.backButton = Button(text='Back',
        background_color=(1, 1, 1, 1),  
        background_normal='',
        color=(0, 0, 0, 1),  
        size_hint=(None, None), size=(dp(100)* w_scale, dp(50)* w_scale), pos_hint={'center_x': 0.4},
        font_size=dp(16)* t_scale,
        on_press=page_instance.switch_to_seed_ip_page
    )
    
    bottomSection.nextButton = Button(text='Continue',
        background_color=(1, 1, 1, 1),  
        background_normal='',
        color=(0, 0, 0, 1),  
        size_hint=(None, None), size=(dp(100)* w_scale, dp(50)* w_scale), pos_hint={'center_x': 0.6},
        font_size=dp(16)* t_scale,
        on_press=lambda instance: page_instance.create_superuser(username, passtext)

    )
    bottomSection.add_widget(bottomSection.backButton)
    bottomSection.add_widget(bottomSection.nextButton)
    layout.add_widget(bottomSection)

    field4 = BoxLayout(orientation='horizontal', size_hint=(1, None), height=dp(50)* w_scale)
    message = Label(text='Store username and 24 word passphrase in a secure place.\nPassphrase is not saved.\nPassphrase cannot be reset if lost.',font_size=dp(16)* t_scale)
    page_instance.message = message

    field4.add_widget(message)
    tailSection = RelativeLayout()
    tailSection.add_widget(field4)

    layout.add_widget(tailSection)

    return layout

def create_second_superuser_form(layout, page_instance):
    print('-create_second_superuser_form 2', page_instance)
    from ops import w_scale, t_scale
    passphrase = Mnemonic("english").generate(strength=128)
    # passphrase = ''

    layout = splash_logo(layout)

    centerSection = RelativeLayout()
    label1 = Label(text='Create Second Superuser')
    centerSection.add_widget(label1)

    userInput = BoxLayout(orientation='horizontal', size_hint=(0.85, None), height=100, pos_hint={'center_x': 0.5})
    centerSection.add_widget(userInput)

    userFields = BoxLayout(orientation='vertical', pos_hint={'center_y': 0.25})
    userInput.add_widget(userFields)

    field2 = BoxLayout(orientation='horizontal', size_hint=(1, None), height=dp(30)* w_scale)
    label2 = Label(text='Username:',font_size=dp(16)* t_scale)
    username = TextInput(hint_text='', text='Sorah', multiline=False, input_type='text')
    blank_button = Button(text='', size_hint_x=None, width=dp(70)* w_scale)
    field2.add_widget(label2)
    field2.add_widget(username)
    field2.add_widget(blank_button)
    userFields.add_widget(field2)

    field3 = BoxLayout(orientation='horizontal', size_hint=(1, None), height=dp(30)* w_scale)
    label3 = Label(text='Passphrase:',font_size=dp(16)* t_scale)
    
    passtext = TextInput(text=passphrase, multiline=False, password=True, input_type='text')
    toggle_button = Button(text='Show', size_hint_x=None, width=dp(70)* w_scale)
    toggle_button.bind(on_press=partial(toggle_password_visibility, key=passtext, btn=toggle_button))
    field3.add_widget(label3)
    field3.add_widget(passtext)
    field3.add_widget(toggle_button)
    userFields.add_widget(field3)
    layout.add_widget(centerSection)

    bottomSection = RelativeLayout()
    bottomSection.backButton = Button(text='Back',
        background_color=(1, 1, 1, 1),  
        background_normal='',
        color=(0, 0, 0, 1),  
        size_hint=(None, None), size=(dp(100)* w_scale, dp(50)* w_scale), pos_hint={'center_x': 0.4},
        font_size=dp(16)* t_scale,
        on_press=page_instance.switch_to_seed_ip_page
    )
    
    bottomSection.nextButton = Button(text='Continue',
        background_color=(1, 1, 1, 1),  
        background_normal='',
        color=(0, 0, 0, 1),  
        size_hint=(None, None), size=(dp(100)* w_scale, dp(50)* w_scale), pos_hint={'center_x': 0.6},
        font_size=dp(16)* t_scale,
        on_press=lambda instance: page_instance.create_second_superuser(username, passtext)
    )
    bottomSection.add_widget(bottomSection.backButton)
    bottomSection.add_widget(bottomSection.nextButton)
    layout.add_widget(bottomSection)

    field4 = BoxLayout(orientation='horizontal', size_hint=(1, None), height=dp(50)* w_scale)
    message = Label(text='Store username and 24 word passphrase in a secure place.\nPassphrase is not saved.\nPassphrase cannot be reset if lost.',font_size=dp(16)* t_scale)
    page_instance.message = message

    field4.add_widget(message)
    tailSection = RelativeLayout()
    tailSection.add_widget(field4)

    layout.add_widget(tailSection)

    return layout

def network_setup_form(layout, page_instance, version=None):
    print('-network_setup_content')
    from ops import SetupScreen
    page_instance.content = 'network_setup_form_layout'
    layout.data_layout = SetupScreen(parent=page_instance, option='')
    layout.data_layout.activate_display()
    layout.add_widget(layout.data_layout)
    return layout


def new_network_install(layout, page_instance):
    print('-new_network_install', page_instance)
    from ops import SetupScreen
    page_instance.content = 'network_setup_install_layout'
    layout.data_layout = SetupScreen(parent=page_instance, option='new_node_local')
    layout.data_layout.activate_display()
    layout.add_widget(layout.data_layout)
    return layout


class HoverButton(ButtonBehavior, Label):
    def __init__(self, text="", height=None, **kwargs):
        super().__init__(**kwargs)
        from ops import w_scale
        if not height:
            height = dp(40)
        self.text = text
        self.size_hint_y = None
        self.height = height* w_scale

        with self.canvas.before:
            self.bg_color = Color(0.043, 0.333, 0.604, 1)  # Default color
            self.rect = Rectangle(size=self.size, pos=self.pos)

        self.bind(size=self.update_graphics, pos=self.update_graphics)
        Window.bind(mouse_pos=self.on_mouse_move)

    def update_graphics(self, *args):
        self.rect.size = self.size
        self.rect.pos = self.pos

    def on_mouse_move(self, window, pos):
        local_pos = self.to_widget(*pos)
        if self.collide_point(*local_pos):
            self.bg_color.rgba = (0.2, 0.5, 0.8, 1)  #  on hover
        else:
            self.bg_color.rgba = (0.043, 0.333, 0.604, 1)  # Reset on leave

class PaneDivider(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0.7, 0.7, 0.7, 0.4)  # Gray divider color
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

class FlashingButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(on_press=self.flash)
        self.default_color = self.background_color

    def flash(self, *args):
        self.background_color = (0.1176, 0.7647, 1.0, 1)  # Red
        Clock.schedule_once(self.reset_color, 0.1)

    def reset_color(self, *args):
        self.background_color = self.default_color
        
class AnimatedDropDown(DropDown):
    def open(self, *largs):
        super().open(*largs)
        self.opacity = 0
        anim = Animation(opacity=1, d=0.15)
        anim.start(self)

    def dismiss(self, *largs):
        anim = Animation(opacity=0, d=0.15)
        anim.bind(on_complete=lambda *args: DropDown.dismiss(self, *largs))
        anim.start(self)

class Divider(Widget):
    def __init__(self, padding=0, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_x = 1
        self.size_hint_y = None
        self.height = 2
        self.padding = padding

        with self.canvas:
            Color(1, 1, 1, 1)
            self.line = Line(points=[])

        self.bind(size=self.update_line, pos=self.update_line)

    def update_line(self, *args):
        container_width = self.width
        x1 = self.x + self.padding
        x2 = self.x + container_width - self.padding
        y = self.center_y
        self.line.points = [x1, y, x2, y]


class CheckBoxTreeLabel(BoxLayout, TreeViewNode):
    def __init__(self, text, identifier=0, regionId=None, title=None, obj_type=None, extra=None, active=True, parent=None, button=False, superuser=False, new_child_btn=True, **kwargs):
        super(CheckBoxTreeLabel, self).__init__(orientation='horizontal', **kwargs)
        from ops import w_scale, t_scale
        self.identifier = identifier
        self.obj_type = obj_type
        self.extra = extra
        self.title = title
        self.padding = [10, 10, 10, 10]
        self.spacing = 20 
        self.checkbox = None 

        if title:
            x = title
        elif regionId:
            x = regionId
        else:
            x = identifier
        if active == 'mandatory':
            self.checkbox = CustomCheckBox(size_hint=(None, None), height=dp(15)* w_scale, identifier=x, active=active)
            self.checkbox.bind(active=self.checkbox.stay_active)
            self.add_widget(self.checkbox)
        else:
            self.checkbox = CustomCheckBox(size_hint=(None, None), height=dp(15)* w_scale, identifier=x, active=active)
            self.checkbox.bind(active=self.on_checkbox_active)
            self.add_widget(self.checkbox)

        self.label = Label(text=text, valign='middle', halign='left', size_hint_x=None)
        self.label.bind(texture_size=self.label.setter('size'))
        self.add_widget(self.label)
        if superuser:
            self.button = Button(text='edit', size_hint=(1, 1), height=dp(15)* w_scale, size_hint_x=None, width=dp(35)* w_scale, font_size=dp(14)* t_scale)
            self.button.bind(on_press=partial(parent.edit_object, iden=self.identifier, func=f'edit_{obj_type}'))
            self.add_widget(self.button)
            if new_child_btn:
                self.new_button = Button(text='new child', size_hint=(1, 1), height=dp(15)* w_scale, size_hint_x=None, width=dp(75)* w_scale, font_size=dp(14)* t_scale)
                self.new_button.bind(on_press=partial(parent.edit_object, iden=self.identifier, func='new_child'))
                self.add_widget(self.new_button)

        self.size_hint_y = None 
        self.height = dp(30)

    def on_checkbox_active(self, checkbox, value):
        if not value:
            self.deactivate_children()
        else:
            try:
                if not self.checkbox.group:
                    self.activate_children()
            except:
                pass
        self.activate_parent_if_all_checked()

    def activate_children(self):
        # print('-activate_children')
        for child in self.nodes:
            if isinstance(child, CheckBoxTreeLabel):
                if len(child.children) > 1:
                    for box in child.children:
                        if isinstance(box, CustomCheckBox):
                            box.active = True
                            box.group = None

    def deactivate_children(self):
        for child in self.nodes:
            if isinstance(child, CheckBoxTreeLabel):
                for box in child.children:
                    if isinstance(box, CustomCheckBox):
                        box.active = False
                        box.group = None

    def deactivate_parent(self):
        if self.parent_node:
            try:
                self.parent_node.checkbox.unbind(active=self.parent_node.on_checkbox_active)
                self.parent_node.checkbox.active = False
                self.parent_node.checkbox.bind(active=self.parent_node.on_checkbox_active)
                self.parent_node.deactivate_parent()
            except:
                pass

    def activate_parent_if_all_checked(self):
        if self.parent_node:
            all_checked = all(child.checkbox.active for child in self.parent_node.nodes if child.checkbox and child.checkbox.group == None)
            if all_checked and not self.checkbox.group:
                try:
                    self.parent_node.checkbox.unbind(active=self.parent_node.on_checkbox_active)
                    self.parent_node.checkbox.active = True
                    self.parent_node.checkbox.group = None
                    self.parent_node.checkbox.bind(active=self.parent_node.on_checkbox_active)
                    self.parent_node.activate_parent_if_all_checked()
                except Exception as e:
                    # print(str(e))
                    pass
            else:
                try:
                    some_checked = len([child.checkbox.active for child in self.parent_node.nodes if child.checkbox and child.checkbox.active])
                    if some_checked > 0 and some_checked < len(self.parent_node.nodes):
                        self.parent_node.checkbox.group = self.parent_node.checkbox.identifier
                        self.parent_node.checkbox.active = True
                    elif some_checked == 0:
                        pass
                    elif [child.checkbox.identifier for child in self.parent_node.nodes if child.checkbox.group]:
                        self.parent_node.checkbox.group = self.parent_node.checkbox.identifier
                        self.parent_node.checkbox.active = True
                    self.parent_node.activate_parent_if_all_checked()
                except Exception as e:
                    # print(str(e))
                    pass

class CustomCheckBox(CheckBox):
    def __init__(self, text='', identifier=1, active=True, **kwargs):
        super(CustomCheckBox, self).__init__(**kwargs)
        if active == 'half' and identifier != 'New':
            self.group = identifier
            self.active = True
        else:
            self.active = active
            self.group = None
        self.identifier = identifier
        self.color = [255,255,255,1]

    def stay_active(self, instance, value):
        self.active = True

    def on_active_change(self, instance, value):
        print('-on_active_change')
        if not self.parent:
            return
        parent = self.parent.parent
        children_checked = 0
        children_unchecked = 0
        for child in parent.children:
            for box in child.children:
                if isinstance(box, CheckBox):
                    print('id', box.identifier, box.active)
                    if box.active:
                        children_checked += 1
                    else:
                        children_unchecked += 1

class DynamicTreeView(TreeView):
    def __init__(self, **kwargs):
        super(DynamicTreeView, self).__init__(**kwargs)
        self.bind(minimum_height=self.setter('height'))

class ColoredBoxLayout(BoxLayout):
    def __init__(self, bg_color=(1, 1, 1, 1), **kwargs):
        super().__init__(**kwargs)
        self.size_hint_x = 1
        self.bg_color = bg_color
        with self.canvas.before:
            Color(*self.bg_color)
            self.rect = Rectangle(size=self.size, pos=self.pos)

        self.bind(size=self.update_rect, pos=self.update_rect)

    def update_rect(self, *args):
        self.rect.size = self.size
        self.rect.pos = self.pos
    
    def update_width(self, *args):
        self.width = sum(child.width for child in self.children) + self.spacing * (len(self.children) - 1)

class ExpandingLabel(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_x = None  # Don't stretch horizontally
        self.bind(texture_size=self.update_width)  # Adjust width based on text

        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.border = Line(rectangle=(self.x, self.y, self.width, self.height), width=1)
        self.bind(size=self.update_rect, pos=self.update_rect)

    def update_width(self, instance, *args):
        instance.width = instance.texture_size[0] + 10  # Ensure label expands

    def update_rect(self, instance, value):
        self.border.rectangle = (self.x, self.y, self.width, self.height)
    

class FieldRow(BoxLayout):
    def __init__(self, text, field_content, parent=None, target_tree=[], is_button_list=False, superuser=False, editable=False, click_action=None, **kwargs):
        super().__init__(**kwargs)
        from ops import w_scale, t_scale
        self.size_hint_y = None
        self.height = dp(30) * t_scale
        self.padding = [dp(15) * w_scale, dp(0) * w_scale]
        self.spacing = 25
        self.key = text
        self.input = None
        self.parent_screen = parent

        with self.canvas.after:
            Color(1, 1, 1, 1) 
            self.border_line = Line(rectangle=(self.x, self.y, self.width, self.height), width=0.5)

        self.title_label = Label(text=text, size_hint_x=None, width=dp(150)* w_scale, text_size=(dp(150)* t_scale, None))
        self.title_label.padding_right = 10
        self.title_label._line = None
        self.title_label.bind(size=self.on_size_title, pos=self.on_size_title)
        self.bind(size=self.on_size_title, pos=self.on_size_title)
        self.add_widget(self.title_label)

        if is_button_list and isinstance(field_content, list):
            self.field_container = BoxLayout(orientation="horizontal", spacing=5, size_hint_x=None)
            for field in field_content:
                if isinstance(field, dict) and 'action' in field:
                    item = Button(text=str(field['title']), size_hint_x=None, padding_x=10, height=dp(35)* t_scale, font_size=dp(20)* t_scale)
                    if field['action']:
                        item.on_press=field['action']
                    item.texture_update()
                    item.width = item.texture_size[0] + 20
                    self.field_container.add_widget(item)
            self.add_widget(self.field_container)
        else:
            user_customizable = ['port', 'local_ip']
            if field_content == 'new_input':
                if 'pass' in text.lower():
                    self.input = TextInput(text='', password=True, size_hint_x=1, height=dp(30)* t_scale, font_size=dp(15)* t_scale, input_type='text')
                    self.toggle_button = Button(text='Show', size_hint_x=None, width=dp(70)* w_scale)
                    self.toggle_button.bind(on_release=self.toggle_password_visibility)
                    self.add_widget(self.input)
                    self.add_widget(self.toggle_button)
                else:
                    self.input = TextInput(text='', size_hint_x=1, height=dp(30)* t_scale, font_size=dp(15)* t_scale, input_type='text', readonly=False)
                    self.add_widget(self.input)
            elif 'pass' in text.lower() or 'password' in text.lower() or 'privkey' in text.lower():
                if field_content == 'Val:N':
                    field_content = None
                self.input = TextInput(text=str(field_content), password=True, size_hint_x=1, height=dp(30)* t_scale, font_size=dp(15)* t_scale, input_type='text', readonly=not editable)
                self.toggle_button = Button(text='Show', size_hint_x=None, width=dp(70)* w_scale)
                self.toggle_button.bind(on_release=self.toggle_password_visibility)
                self.add_widget(self.input)
                self.add_widget(self.toggle_button)
            elif editable and 'external_ip' in text:
                from ops import refresh_ip
                if field_content == 'Val:N':
                    field_content = None
                self.input = TextInput(text=str(field_content), height=dp(30)* t_scale, font_size=dp(15)* t_scale, readonly=False, size_hint_x=1, input_type='text')
                self.toggle_button = Button(text='Refresh', size_hint_x=None, width=dp(70)* w_scale)
                self.toggle_button.bind(on_press=partial(refresh_ip, display=self.input))
                self.add_widget(self.input)
                self.add_widget(self.toggle_button)
            elif editable and text == 'debug' or editable and str(field_content).lower() in ['true','false']:
                if isinstance(field_content, str):
                    field_content = json.loads(field_content.lower())
                self.input = CheckBox(size_hint=(1, None), height=dp(30)* t_scale, active=field_content)
                self.add_widget(self.input)
            elif editable and superuser or editable and text in user_customizable:
                if field_content == 'Val:N':
                    field_content = None
                self.input = TextInput(text=str(field_content), size_hint_x=1, height=dp(30)* t_scale, font_size=dp(15)* t_scale, input_type='text', readonly=not superuser)
                self.add_widget(self.input)
            elif text not in ['systemPass', 'userPass', 'password']:
                if self.parent_screen and isinstance(field_content, dict) and len(field_content) > 0 or self.parent_screen and isinstance(field_content, list) and len(field_content) > 1:
                    newTree = target_tree+[text]
                    field = RelativeLayout()
                    self.input = Button(text='expand', size_hint_x=None, height=dp(30)* t_scale, pos_hint={'center_x': 0.5})
                    if click_action:
                        self.input.bind(on_press=partial(click_action, target_tree=target_tree+[text]))
                    else:
                        from ops import expand_user_data
                        self.input.bind(on_press=partial(expand_user_data, self.parent_screen, target_tree=target_tree+[text]))
                    field.add_widget(self.input)
                    self.add_widget(field)
                elif editable:
                    if field_content == 'Val:N':
                        field_content = None
                    self.input = TextInput(text=str(field_content), size_hint_x=1, height=dp(30)* t_scale, input_type='text', font_size=dp(15)* t_scale, readonly=False)
                    self.add_widget(self.input)
                else:
                    if field_content == 'Val:N':
                        field_content = None
                    self.input = Label(
                        text=str(field_content),
                        size_hint_x=None,
                        height=dp(30) * t_scale,
                        font_size=dp(16) * t_scale,
                        halign='left',
                        valign='middle'
                    )

                    self.input.bind(texture_size=lambda instance, value: setattr(instance, 'width', value[0]))
                    self.input.text_size = (None, dp(30) * t_scale)
                    self.input_scroll = ScrollView(
                        size_hint=(1, None),
                        height=dp(30) * t_scale,
                        do_scroll_x=True,
                        do_scroll_y=False
                    )

                    self.input_scroll.add_widget(self.input)
                    self.add_widget(self.input_scroll)

        self.bind(size=self.update_graphics, pos=self.update_graphics)


    def expand_field(self, instance, key=None):
        # print('-expand_field', key)
        try:
            if self.parent_screen:
                self.parent_screen.switch_layout('Settings', target=key)
        except:
            pass

    def toggle_password_visibility(self, instance):
        if self.input.password:
            self.input.password = False
            instance.text = 'Hide'
        else:
            self.input.password = True
            instance.text = 'Show'

    def refresh_field(self, display):
        display.text = 'refreshing...'

    def update_graphics(self, *args):
        self.border_line.rectangle = (self.x, self.y, self.width, self.height)

    def on_size_title(self, *args):
        if self.title_label._line is None:
            with self.title_label.canvas.after:
                Color(1, 1, 1, 1)
                self.title_label._line = Line(width=1)

        x = self.title_label.right + self.title_label.padding_right
        parent = self.title_label.parent

        self.title_label._line.points = [
            x, parent.y + 4,
            x, parent.top - 4
        ]

class Sparkline(Widget):
    def __init__(self, data, color=(0, 1, 0), y_min=None, y_max=None, **kwargs):
        super().__init__(**kwargs)
        self.data = data
        self.color = color
        self.y_min = y_min
        self.y_max = y_max
        self.bind(pos=self.redraw, size=self.redraw)

    def redraw(self, *args):
        self.canvas.clear()
        if len(self.data) < 2:
            return

        min_val = self.y_min if self.y_min is not None else min(self.data)
        max_val = self.y_max if self.y_max is not None else max(self.data)

        range_val = max_val - min_val
        if range_val == 0:
            range_val = 1

        with self.canvas:
            Color(*self.color)
            points = []
            for i, v in enumerate(self.data):
                x = self.x + i * (self.width / (len(self.data) - 1))
                y = self.y + ((v - min_val) / range_val) * self.height
                points.extend([x, y])
            Line(points=points, width=1.2)
            
class Sparkline_old(Widget):
    def __init__(self, data, color=(0, 1, 0), **kwargs):
        super().__init__(**kwargs)
        self.data = data
        self.color = color
        self.bind(pos=self.redraw, size=self.redraw)

    def redraw(self, *args):
        self.canvas.clear()
        if len(self.data) < 2:
            return
        max_val = max(self.data) or 1
        min_val = min(self.data)

        with self.canvas:
            Color(*self.color)
            points = []
            for i, v in enumerate(self.data):
                x = self.x + i * (self.width / (len(self.data) - 1))
                y = self.y + ((v - min_val) / (max_val - min_val or 1)) * self.height
                points.extend([x, y])
            Line(points=points, width=1.2)

class TimeSparkline(Widget):
    def __init__(self, history, **kwargs):
        super().__init__(**kwargs)
        from ops import w_scale, t_scale
        self.history = history
        self.color = (0.6, 0.6, 0.6, 0.9)
        self.text_color = (0.9, 0.9, 0.9, 0.9)
        self.font_size = dp(10) * t_scale
        self.max_span = 60  # seconds

        self.bind(size=self.redraw, pos=self.redraw)

    def redraw(self, *args):
        self.canvas.clear()
        n = len(self.history)
        if n < 2:
            return

        x0, y0 = self.pos
        w, h = self.size
        baseline = y0 + h / 2
        tick_height = h * 0.25

        earliest = self.history[0]
        latest = self.history[-1]
        span = max(latest - earliest, 1e-3)  # prevent division by zero

        with self.canvas:
            Color(*self.color)
            Line(points=[x0, baseline, x0 + w, baseline], width=1)

            # --- MAX TICKS CONTROL ---
            max_ticks = 5
            tick_times = [earliest + i * (span / (max_ticks - 1)) for i in range(max_ticks)]

            for t in tick_times:
                rel_frac = (t - earliest) / span
                x = x0 + rel_frac * w

                # vertical tick
                Line(points=[x, baseline - tick_height, x, baseline + tick_height], width=1)

                # label
                rel_time = latest - t
                if rel_time < 1:
                    text = "now"
                elif rel_time < 60:
                    text = f"-{int(rel_time)}s"
                else:
                    text = f"-{rel_time / 60:.1f}m"

                lbl = CoreLabel(text=text, font_size=self.font_size)
                lbl.refresh()
                tex = lbl.texture

                Color(*self.text_color)
                
                # label on top
                # Rectangle(texture=tex, size=tex.size, pos=(x - tex.width/2, baseline + tick_height + 2))

                # label on bottom
                label_y = baseline - tick_height - tex.height - 2
                Rectangle(texture=tex, size=tex.size, pos=(x - tex.width/2, label_y))


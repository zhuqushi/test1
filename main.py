import os
import time
import requests
import json
import re
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.checkbox import CheckBox
from kivy.uix.modalview import ModalView
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.properties import StringProperty, ListProperty, ObjectProperty
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from datetime import datetime, timedelta
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from base64 import b64encode
import yagmail
from threading import Thread

# 常量定义
SCHOOL_ID = 614
MONTHLY_USER_DATA_FILE = "monthly_users.json"
SINGLE_USER_DATA_FILE = "single_users.json"

# 加密函数
def encrypt(t, e):
    t = str(t)
    key = e.encode('utf-8')
    cipher = AES.new(key, AES.MODE_ECB)
    padded_text = pad(t.encode('utf-8'), AES.block_size)
    encrypted_text = cipher.encrypt(padded_text)
    return b64encode(encrypted_text).decode('utf-8')

# 登录函数
def login(headers_login, username, password, infolog):
    key = (str(username) + "0000000000000000")[:16]
    encrypted_text = encrypt(password, key)
    login_url = 'https://wzxy.chaoxing.com/basicinfo/mobile/login/username'
    params = {
        "schoolId": SCHOOL_ID,
        "username": username,
        "password": encrypted_text
    }
    try:
        login_req = requests.post(login_url, params=params, headers=headers_login)
        text = json.loads(login_req.text)
        if text['code'] == 0:
            infolog(f"{username}账号登陆成功！")
            set_cookie = login_req.headers['Set-Cookie']
            jws = re.search(r'JWSESSION=(.*?);', str(set_cookie)).group(1)
            return jws
        else:
            infolog(f"{username}登陆失败，请检查账号密码！")
            return False
    except Exception as e:
        infolog(f"登录过程中发生错误: {str(e)}")
        return False

# 上传蓝牙数据函数
def upload_blue_data(blue1, headers_sign, id, signid, infolog):
    data = {
        "blue1": blue1,
        "blue2": [],
        "location": {
            "latitude": 43.80555609809028,
            "longitude": 125.40834988064236,
            "nationcode": "",
            "country": "中国",
            "province": "吉林省",
            "citycode": "",
            "city": "长春市",
            "adcode": "220102",
            "district": "南关区",
            "towncode": "220102121",
            "township": "净月街道",
            "streetcode": "",
            "street": "博学街"}
    }
    try:
        response = requests.post(
            url=f"https://wzxy.chaoxing.com/dormSign/mobile/receive/doSignByDevice?id={id}&signId={signid}",
            headers=headers_sign, json=data)
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get("code") == 0:
                infolog("打卡成功")
                return 0
            elif response_data.get("code") == 1:
                infolog("打卡已结束")
                return 1
            else:
                infolog("打卡失败")
                return 1
        else:
            return 1
    except Exception as e:
        infolog(f"上传蓝牙数据过程中发生错误: {str(e)}")
        return 1

# 执行蓝牙打卡函数
def do_blue_punch(headers, headers_sign, infolog):
    sign_logs_url = "https://wzxy.chaoxing.com/dormSign/mobile/receive/getMySignLogs"
    sign_logs_params = {
        "page": 1,
        "size": 10
    }
    try:
        response = requests.get(sign_logs_url, headers=headers, params=sign_logs_params)
        data_ids = response.json()
        location_id = data_ids["data"][0]["locationId"]
        sign_id = data_ids["data"][0]["signId"]
        major = data_ids["data"][0]["deviceList"][0]["major"]
        uuid = data_ids["data"][0]["deviceList"][0]["uuid"]
        blue1 = [uuid.replace("-", "") + str(major)]
        return upload_blue_data(blue1, headers_sign, location_id, sign_id, infolog)
    except Exception as e:
        infolog(f"获取签到日志失败: {str(e)}")
        return 1

# 时间判断函数
def time_judge(stop_time, infolog):
    if not stop_time:
        infolog("未设置stoptime，永久订阅！")
        return True

    try:
        time_format = "%Y-%m-%d"
        stop_time_struct = time.strptime(stop_time, time_format)
        stop_timestamp = time.mktime(stop_time_struct)
        current_timestamp = time.time()

        if current_timestamp < stop_timestamp:
            infolog("订阅时间未过期！")
            return True
        else:
            infolog("订阅时间已过期！")
            return False
    except Exception as e:
        infolog(f"时间判断错误: {str(e)}")
        return False

# 邮件日志函数
def mail_log(log):
    if 'infoemail' in os.environ and 'smtppass' in os.environ:
        try:
            yag = yagmail.SMTP(user=os.environ.get("infoemail"), password=os.environ.get("smtppass"),
                               host="smtp.qq.com")
            yag.send(to=os.environ.get("infoemail"), subject=f"{time.strftime('%Y-%m-%d', time.localtime())} 运行日志",
                     contents=log)
            return "邮件发送成功！"
        except Exception as e:
            return f"邮件发送失败，异常原因为: {str(e)}"
    else:
        return "邮件通知配置错误，请检查!"

# 检查即将过期的用户
def check_expiring_users(users, days=3):
    expiring_users = []
    today = datetime.now()

    for i, user in enumerate(users):
        if not user.get("stoptime"):
            continue

        try:
            expire_date = datetime.strptime(user["stoptime"], "%Y-%m-%d")
            days_until_expire = (expire_date - today).days

            if 0 <= days_until_expire <= days:
                formatted_index = f"{i:03d}"
                expiring_users.append((formatted_index, user["username"], user["stoptime"], days_until_expire))
        except ValueError:
            continue

    return expiring_users

# 月卡玩家批量签到函数
def execute_monthly_sign_in(users, infolog, update_status):
    headers_login = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; WLZ-AN00 Build/HUAWEIWLZ-AN00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.99 XWEB/4343 MMWEBSDK/20220903 Mobile Safari/537.36 MMWEBID/4162 MicroMessenger/8.0.28.2240(0x28001C35) WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64 miniProgram/wxce6d08f781975d91'}

    run_log = "月卡玩家批量签到\n---------------------------------\n"

    def custom_infolog(message):
        infolog(message)
        nonlocal run_log
        run_log += message + "\n"

    for item in users:
        custom_infolog(f"进入用户{item['username']}签到流程")

        if not time_judge(item["stoptime"], custom_infolog):
            custom_infolog("---------------------------------")
            continue

        jws = login(headers_login, item["user"], item["password"], custom_infolog)
        if not jws:
            custom_infolog("---------------------------------")
            continue

        headers = {
            'sec-ch-ua-platform': '"Android"',
            'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Android WebView";v="134"',
            'sec-ch-ua-mobile': '?1',
            'Host': 'wzxy.chaoxing.com',
            'Connection': 'keep-alive',
            'Accept': 'application/json, text/plain, */*',
            'jwsession': jws,
            "cookie": f'JWSESSION={jws}; WZXYSESSION={jws}',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 12; RTE-AL00 Build/HUAWEIRNA-AL00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/134.0.6998.136 Mobile Safari/537.36 XWEB/1340095 MMWEBSDK/20250201 MMWEBID/7220 MicroMessenger/8.0.58.2841(0x28003A3C) WeChat/arm64 Weixin NetType/4G Language/zh_CN ABI/arm64 miniProgram/wx252bd59b6381cfc1',
            'Content-Type': 'application/json;charset=UTF-8',
            'X-Requested-With': 'com.tencent.mm',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'https://wzxy.chaoxing.com/h5/mobile/dormSign/index/message ',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9,en-CN;q=0.8,en-US;q=0.7,en;q=0.6'
        }

        headers_sign = {
            'Host': 'wzxy.chaoxing.com',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'JWSESSION': f"{jws}",
            'Accept-Encoding': 'gzip,compress,br,deflate',
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.59(0x18003b2a) NetType/WIFI Language/zh_CN',
            'Referer': 'https://servicewechat.com/wx252bd59b6381cfc1/1/page-frame.html '
        }

        do_blue_punch(headers, headers_sign, custom_infolog)
        custom_infolog("---------------------------------")

    custom_infolog("月卡玩家批量签到结束！")
    custom_infolog("正在发送日志邮件...")
    mail_result = mail_log(run_log)
    custom_infolog(mail_result)

    # 检查即将过期的用户
    expiring_users = check_expiring_users(users)
    update_status("月卡玩家批量签到完成", expiring_users)

# 单次玩家批量签到函数
def execute_single_sign_in(users, selected_indices, infolog, update_status):
    headers_login = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; WLZ-AN00 Build/HUAWEIWLZ-AN00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.99 XWEB/4343 MMWEBSDK/20220903 Mobile Safari/537.36 MMWEBID/4162 MicroMessenger/8.0.28.2240(0x28001C35) WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64 miniProgram/wxce6d08f781975d91'}

    run_log = "单次玩家批量签到\n---------------------------------\n"

    def custom_infolog(message):
        infolog(message)
        nonlocal run_log
        run_log += message + "\n"

    for index in selected_indices:
        if index < 0 or index >= len(users):
            custom_infolog(f"无效的用户序号: {index}")
            continue

        item = users[index]
        custom_infolog(f"进入用户{item['username']}签到流程")

        jws = login(headers_login, item["user"], item["password"], custom_infolog)
        if not jws:
            custom_infolog("---------------------------------")
            continue

        headers = {
            'sec-ch-ua-platform': '"Android"',
            'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Android WebView";v="134"',
            'sec-ch-ua-mobile': '?1',
            'Host': 'wzxy.chaoxing.com',
            'Connection': 'keep-alive',
            'Accept': 'application/json, text/plain, */*',
            'jwsession': jws,
            "cookie": f'JWSESSION={jws}; WZXYSESSION={jws}',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 12; RTE-AL00 Build/HUAWEIRNA-AL00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/134.0.6998.136 Mobile Safari/537.36 XWEB/1340095 MMWEBSDK/20250201 MMWEBID/7220 MicroMessenger/8.0.58.2841(0x28003A3C) WeChat/arm64 Weixin NetType/4G Language/zh_CN ABI/arm64 miniProgram/wx252bd59b6381cfc1',
            'Content-Type': 'application/json;charset=UTF-8',
            'X-Requested-With': 'com.tencent.mm',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'https://wzxy.chaoxing.com/h5/mobile/dormSign/index/message ',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9,en-CN;q=0.8,en-US;q=0.7,en;q=0.6'
        }

        headers_sign = {
            'Host': 'wzxy.chaoxing.com',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'JWSESSION': f"{jws}",
            'Accept-Encoding': 'gzip,compress,br,deflate',
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.59(0x18003b2a) NetType/WIFI Language/zh_CN',
            'Referer': 'https://servicewechat.com/wx252bd59b6381cfc1/1/page-frame.html '
        }

        do_blue_punch(headers, headers_sign, custom_infolog)
        custom_infolog("---------------------------------")

    custom_infolog("单次玩家批量签到结束！")
    custom_infolog("正在发送日志邮件...")
    mail_result = mail_log(run_log)
    custom_infolog(mail_result)
    update_status("单次玩家批量签到完成")

# 测试签到函数
def test_sign_in(username, password, infolog, update_status):
    headers_login = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; WLZ-AN00 Build/HUAWEIWLZ-AN00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.99 XWEB/4343 MMWEBSDK/20220903 Mobile Safari/537.36 MMWEBID/4162 MicroMessenger/8.0.28.2240(0x28001C35) WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64 miniProgram/wxce6d08f781975d91'}

    run_log = "测试签到\n---------------------------------\n"

    def custom_infolog(message):
        infolog(message)
        nonlocal run_log
        run_log += message + "\n"

    custom_infolog(f"开始为学号 {username} 签到")

    jws = login(headers_login, username, password, custom_infolog)
    if not jws:
        custom_infolog("---------------------------------")
        update_status("测试签到失败")
        return

    headers = {
        'sec-ch-ua-platform': '"Android"',
        'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Android WebView";v="134"',
        'sec-ch-ua-mobile': '?1',
        'Host': 'wzxy.chaoxing.com',
        'Connection': 'keep-alive',
        'Accept': 'application/json, text/plain, */*',
        'jwsession': jws,
        "cookie": f'JWSESSION={jws}; WZXYSESSION={jws}',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 12; RTE-AL00 Build/HUAWEIRNA-AL00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/134.0.6998.136 Mobile Safari/537.36 XWEB/1340095 MMWEBSDK/20250201 MMWEBID/7220 MicroMessenger/8.0.58.2841(0x28003A3C) WeChat/arm64 Weixin NetType/4G Language/zh_CN ABI/arm64 miniProgram/wx252bd59b6381cfc1',
        'Content-Type': 'application/json;charset=UTF-8',
        'X-Requested-With': 'com.tencent.mm',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
        'Referer': 'https://wzxy.chaoxing.com/h5/mobile/dormSign/index/message ',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9,en-CN;q=0.8,en-US;q=0.7,en;q=0.6'
    }

    headers_sign = {
        'Host': 'wzxy.chaoxing.com',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'JWSESSION': f"{jws}",
        'Accept-Encoding': 'gzip,compress,br,deflate',
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.59(0x18003b2a) NetType/WIFI Language/zh_CN',
        'Referer': 'https://servicewechat.com/wx252bd59b6381cfc1/1/page-frame.html '
    }

    result = do_blue_punch(headers, headers_sign, custom_infolog)
    custom_infolog("---------------------------------")

    if result == 0:
        update_status("测试签到成功")
    else:
        update_status("测试签到失败")

    custom_infolog("正在发送日志邮件...")
    mail_result = mail_log(run_log)
    custom_infolog(mail_result)

# 加载用户数据
def load_users(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# 保存用户数据
def save_users(users, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

# 格式化序号为3位数
def format_index(index):
    return f"{index:03d}"

# Kivy应用界面
class MainScreen(Screen):
    pass

class MonthlyScreen(Screen):
    pass

class SingleScreen(Screen):
    pass

class TestScreen(Screen):
    pass

class MonthlySignScreen(Screen):
    log_text = StringProperty("")
    status_text = StringProperty("就绪")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.monthly_users = load_users(MONTHLY_USER_DATA_FILE)

    def start_sign_in(self):
        self.status_text = "正在执行..."
        self.log_text = "月卡玩家批量签到开始\n---------------------------------\n"
        
        # 在新线程中执行签到，避免界面卡顿
        thread = Thread(target=self.execute_in_thread)
        thread.daemon = True
        thread.start()

    def execute_in_thread(self):
        try:
            execute_monthly_sign_in(self.monthly_users, self.log_message,
                                    self.update_status_with_expiry)
        except Exception as e:
            self.log_message(f"执行过程中发生错误: {str(e)}")
            self.update_status("执行出错")

    def log_message(self, message):
        def update_log():
            self.log_text += message + "\n"
        
        Clock.schedule_once(lambda dt: update_log())

    def update_status(self, status):
        def update():
            self.status_text = status
        
        Clock.schedule_once(lambda dt: update())

    def update_status_with_expiry(self, status, expiring_users=None):
        def update():
            self.status_text = status
            
            # 显示即将过期的用户
            if expiring_users:
                self.show_expiry_warning(expiring_users)
        
        Clock.schedule_once(lambda dt: update())

    def show_expiry_warning(self, expiring_users):
        content = BoxLayout(orientation='vertical')
        content.add_widget(Label(text='以下月卡用户的订阅即将到期：', size_hint_y=None, height=40))
        
        scroll = ScrollView()
        grid = GridLayout(cols=4, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        
        # 添加表头
        grid.add_widget(Label(text='序号', size_hint_y=None, height=40))
        grid.add_widget(Label(text='用户名', size_hint_y=None, height=40))
        grid.add_widget(Label(text='到期时间', size_hint_y=None, height=40))
        grid.add_widget(Label(text='剩余天数', size_hint_y=None, height=40))
        
        # 添加数据
        for user in expiring_users:
            for item in user:
                grid.add_widget(Label(text=str(item), size_hint_y=None, height=30))
        
        scroll.add_widget(grid)
        content.add_widget(scroll)
        
        btn = Button(text='确定', size_hint_y=None, height=40)
        popup = Popup(title='月卡用户订阅即将到期提醒', content=content, size_hint=(0.8, 0.8))
        btn.bind(on_release=popup.dismiss)
        content.add_widget(btn)
        
        popup.open()

class MonthlyManageScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.monthly_users = load_users(MONTHLY_USER_DATA_FILE)
        self.refresh_user_list()

    def refresh_user_list(self):
        # 清空现有用户列表
        user_list = self.ids.user_list
        user_list.clear_widgets()
        
        # 添加用户数据
        for i, user in enumerate(self.monthly_users):
            formatted_index = format_index(i)
            item = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
            item.add_widget(Label(text=formatted_index, size_hint_x=0.2))
            item.add_widget(Label(text=user["username"], size_hint_x=0.3))
            item.add_widget(Label(text=user["user"], size_hint_x=0.3))
            item.add_widget(Label(text=user["stoptime"], size_hint_x=0.2))
            user_list.add_widget(item)

    def add_user(self):
        popup = AddMonthlyUserPopup(self)
        popup.open()

    def edit_user(self):
        # 这里需要实现选择用户的逻辑
        pass

    def delete_user(self):
        # 这里需要实现选择用户的逻辑
        pass

    def save_users(self):
        save_users(self.monthly_users, MONTHLY_USER_DATA_FILE)
        self.refresh_user_list()

class AddMonthlyUserPopup(Popup):
    def __init__(self, manage_screen, **kwargs):
        super().__init__(**kwargs)
        self.manage_screen = manage_screen
        self.title = "添加月卡用户"
        self.size_hint = (0.8, 0.8)

    def add_user(self):
        username = self.ids.username_input.text
        user_id = self.ids.user_id_input.text
        password = self.ids.password_input.text
        stoptime = self.ids.stoptime_input.text

        if not all([username, user_id, password, stoptime]):
            return

        user_data = {
            "username": username,
            "user": user_id,
            "password": password,
            "stoptime": stoptime
        }

        self.manage_screen.monthly_users.append(user_data)
        self.manage_screen.save_users()
        self.dismiss()

class SingleSignScreen(Screen):
    log_text = StringProperty("")
    status_text = StringProperty("就绪")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.single_users = load_users(SINGLE_USER_DATA_FILE)

    def start_sign_in(self):
        selected_text = self.ids.selected_indices_input.text.strip()
        if not selected_text:
            self.status_text = "请输入需要签到的用户序号"
            return

        try:
            # 解析输入的序号
            selected_indices = []
            for line in selected_text.split('\n'):
                if line.strip():
                    selected_indices.append(int(line.strip()))
        except ValueError:
            self.status_text = "请输入有效的数字序号"
            return

        self.status_text = "正在执行..."
        self.log_text = "单次玩家批量签到开始\n---------------------------------\n"
        
        # 在新线程中执行签到，避免界面卡顿
        thread = Thread(target=self.execute_in_thread, args=(selected_indices,))
        thread.daemon = True
        thread.start()

    def execute_in_thread(self, selected_indices):
        try:
            execute_single_sign_in(self.single_users, selected_indices, self.log_message,
                                   self.update_status)
        except Exception as e:
            self.log_message(f"执行过程中发生错误: {str(e)}")
            self.update_status("执行出错")

    def log_message(self, message):
        def update_log():
            self.log_text += message + "\n"
        
        Clock.schedule_once(lambda dt: update_log())

    def update_status(self, status):
        def update():
            self.status_text = status
        
        Clock.schedule_once(lambda dt: update())

class SingleManageScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.single_users = load_users(SINGLE_USER_DATA_FILE)
        self.refresh_user_list()

    def refresh_user_list(self):
        # 清空现有用户列表
        user_list = self.ids.user_list
        user_list.clear_widgets()
        
        # 添加用户数据
        for i, user in enumerate(self.single_users):
            formatted_index = format_index(i)
            item = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
            item.add_widget(Label(text=formatted_index, size_hint_x=0.25))
            item.add_widget(Label(text=user["username"], size_hint_x=0.35))
            item.add_widget(Label(text=user["user"], size_hint_x=0.4))
            user_list.add_widget(item)

    def add_user(self):
        popup = AddSingleUserPopup(self)
        popup.open()

    def edit_user(self):
        # 这里需要实现选择用户的逻辑
        pass

    def delete_user(self):
        # 这里需要实现选择用户的逻辑
        pass

    def save_users(self):
        save_users(self.single_users, SINGLE_USER_DATA_FILE)
        self.refresh_user_list()

class AddSingleUserPopup(Popup):
    def __init__(self, manage_screen, **kwargs):
        super().__init__(**kwargs)
        self.manage_screen = manage_screen
        self.title = "添加单次用户"
        self.size_hint = (0.8, 0.6)

    def add_user(self):
        username = self.ids.username_input.text
        user_id = self.ids.user_id_input.text
        password = self.ids.password_input.text

        if not all([username, user_id, password]):
            return

        user_data = {
            "username": username,
            "user": user_id,
            "password": password
        }

        self.manage_screen.single_users.append(user_data)
        self.manage_screen.save_users()
        self.dismiss()

class TestSignScreen(Screen):
    log_text = StringProperty("")
    status_text = StringProperty("就绪")

    def start_sign_in(self):
        username = self.ids.username_input.text.strip()
        password = self.ids.password_input.text.strip()

        if not username or not password:
            self.status_text = "请输入学号和密码"
            return

        self.status_text = "正在执行..."
        self.log_text = "测试签到开始\n---------------------------------\n"
        
        # 在新线程中执行签到，避免界面卡顿
        thread = Thread(target=self.execute_in_thread, args=(username, password))
        thread.daemon = True
        thread.start()

    def execute_in_thread(self, username, password):
        try:
            test_sign_in(username, password, self.log_message, self.update_status)
        except Exception as e:
            self.log_message(f"执行过程中发生错误: {str(e)}")
            self.update_status("执行出错")

    def log_message(self, message):
        def update_log():
            self.log_text += message + "\n"
        
        Clock.schedule_once(lambda dt: update_log())

    def update_status(self, status):
        def update():
            self.status_text = status
        
        Clock.schedule_once(lambda dt: update())

class SignInApp(App):
    def build(self):
        # 创建屏幕管理器
        sm = ScreenManager()
        
        # 添加主屏幕
        main_screen = MainScreen(name='main')
        sm.add_widget(main_screen)
        
        # 添加月卡屏幕
        monthly_screen = MonthlyScreen(name='monthly')
        sm.add_widget(monthly_screen)
        
        # 添加单次屏幕
        single_screen = SingleScreen(name='single')
        sm.add_widget(single_screen)
        
        # 添加测试屏幕
        test_screen = TestScreen(name='test')
        sm.add_widget(test_screen)
        
        # 添加月卡签到屏幕
        monthly_sign_screen = MonthlySignScreen(name='monthly_sign')
        sm.add_widget(monthly_sign_screen)
        
        # 添加月卡管理屏幕
        monthly_manage_screen = MonthlyManageScreen(name='monthly_manage')
        sm.add_widget(monthly_manage_screen)
        
        # 添加单次签到屏幕
        single_sign_screen = SingleSignScreen(name='single_sign')
        sm.add_widget(single_sign_screen)
        
        # 添加单次管理屏幕
        single_manage_screen = SingleManageScreen(name='single_manage')
        sm.add_widget(single_manage_screen)
        
        # 添加测试签到屏幕
        test_sign_screen = TestSignScreen(name='test_sign')
        sm.add_widget(test_sign_screen)
        
        return sm

if __name__ == "__main__":
    SignInApp().run()
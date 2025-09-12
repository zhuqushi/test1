import time
import requests
import json
import re
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from base64 import b64encode
import yagmail
from datetime import datetime, timedelta
import asyncio
import os

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


# 检查是否在签到时间区间内
def is_in_sign_time_range(start_time, end_time):
    if not start_time or not end_time:
        return False

    try:
        current_time = datetime.now().time()
        start = datetime.strptime(start_time, "%H:%M").time()
        end = datetime.strptime(end_time, "%H:%M").time()

        # 处理跨天的情况（如23:00到01:00）
        if start <= end:
            return start <= current_time <= end
        else:
            return current_time >= start or current_time <= end
    except Exception as e:
        return False


# 邮件日志函数
def mail_log(log):
    # 在移动端，邮件功能可能需要调整或移除
    # 这里保留但可能需要根据实际情况修改
    return "邮件功能在移动端暂不可用"


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
async def execute_monthly_sign_in(users, infolog, update_status):
    headers_login = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; WLZ-AN00 Build/HUAWEIWLZ-AN00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.99 XWEB/4343 MMWEBSDK/20220903 Mobile Safari/537.36 MMWEBID/4162 MicroMessenger/8.0.28.2240(0x28001C35) WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64 miniProgram/wxce6d08f781975d91'}

    run_log = "月卡玩家批量签到\n---------------------------------\n"
    valid_users_count = 0  # 记录有效用户数量
    success_count = 0  # 记录成功打卡数量

    def custom_infolog(message):
        infolog(message)
        nonlocal run_log
        run_log += message + "\n"

    for item in users:
        # 检查是否在有效期内
        if not time_judge(item["stoptime"], lambda x: None):  # 不显示时间判断的日志
            continue

        # 检查是否在签到时间区间内
        if not is_in_sign_time_range(item.get("start_time"), item.get("end_time")):
            continue

        valid_users_count += 1

        jws = login(headers_login, item["user"], item["password"], custom_infolog)
        if not jws:
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

        result = do_blue_punch(headers, headers_sign, lambda x: None)  # 不显示打卡过程的日志
        if result == 0:  # 只有打卡成功才记录
            custom_infolog(f"用户 {item['username']} 打卡成功")
            success_count += 1
        elif result == 1:  # 打卡失败或已结束，不记录
            pass

    if valid_users_count == 0:
        custom_infolog("没有符合条件的月卡用户需要签到")
    elif success_count == 0:
        custom_infolog("有符合条件的用户，但没有用户打卡成功")
    else:
        custom_infolog(f"月卡玩家批量签到结束，成功打卡用户数: {success_count}")
        custom_infolog("正在发送日志邮件...")
        mail_result = mail_log(run_log)
        custom_infolog(mail_result)

    # 检查即将过期的用户
    expiring_users = check_expiring_users(users)
    update_status("月卡玩家批量签到完成", expiring_users)


# 单次玩家批量签到函数
async def execute_single_sign_in(users, selected_indices, infolog, update_status):
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
            'User-Acept-Encoding': 'gzip,compress,br,deflate',
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
async def test_sign_in(username, password, infolog, update_status):
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
def load_users(app, file_name):
    try:
        data_path = app.paths.data / file_name
        if data_path.exists():
            with open(data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"加载用户数据失败: {e}")
    return []


# 保存用户数据
def save_users(app, users, file_name):
    try:
        data_path = app.paths.data / file_name
        # 确保数据目录存在
        app.paths.data.mkdir(parents=True, exist_ok=True)
        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存用户数据失败: {e}")


# 格式化序号为3位数
def format_index(index):
    return f"{index:03d}"


# 主应用程序类
class SignInApp(toga.App):
    def __init__(self):
        super().__init__('校园签到系统', 'com.example.signinapp')
        self.monthly_users = []
        self.single_users = []
        self.current_screen = None

    def startup(self):
        # 创建主窗口
        self.main_window = toga.MainWindow(title=self.formal_name, size=(400, 700))

        # 确保数据目录存在
        self.paths.data.mkdir(parents=True, exist_ok=True)

        # 加载用户数据
        self.monthly_users = load_users(self, MONTHLY_USER_DATA_FILE)
        self.single_users = load_users(self, SINGLE_USER_DATA_FILE)

        # 显示主菜单
        self.show_main_menu()

        # 显示主窗口
        self.main_window.show()

    def show_main_menu(self):
        """显示主菜单"""
        self.current_screen = "main_menu"

        box = toga.Box(style=Pack(direction=COLUMN, padding=20, flex=1))

        # 标题
        title = toga.Label('校园签到系统',
                           style=Pack(font_size=20, font_weight='bold', padding_bottom=30, text_align='center'))
        box.add(title)

        # 月卡玩家按钮
        monthly_button = toga.Button('月卡玩家', on_press=self.show_monthly_menu,
                                     style=Pack(padding=15, font_size=16))
        box.add(monthly_button)

        # 单次玩家按钮
        single_button = toga.Button('单次玩家', on_press=self.show_single_menu,
                                    style=Pack(padding=15, font_size=16))
        box.add(single_button)

        # 测试签到按钮
        test_button = toga.Button('测试签到', on_press=self.show_test_screen,
                                  style=Pack(padding=15, font_size=16))
        box.add(test_button)

        self.main_window.content = box

    def show_monthly_menu(self, widget=None):
        """显示月卡玩家菜单"""
        self.current_screen = "monthly_menu"

        box = toga.Box(style=Pack(direction=COLUMN, padding=20, flex=1))

        # 返回按钮
        back_button = toga.Button('返回', on_press=lambda w: self.show_main_menu(),
                                  style=Pack(padding=5, font_size=14))
        box.add(back_button)

        # 标题
        title = toga.Label('月卡玩家',
                           style=Pack(font_size=18, font_weight='bold', padding_bottom=30, text_align='center'))
        box.add(title)

        # 批量签到按钮
        batch_button = toga.Button('批量签到', on_press=self.show_monthly_batch,
                                   style=Pack(padding=15, font_size=16))
        box.add(batch_button)

        # 用户管理按钮
        manage_button = toga.Button('用户管理', on_press=self.show_monthly_management,
                                    style=Pack(padding=15, font_size=16))
        box.add(manage_button)

        self.main_window.content = box

    def show_monthly_batch(self, widget=None):
        """显示月卡玩家批量签到界面"""
        self.current_screen = "monthly_batch"

        box = toga.Box(style=Pack(direction=COLUMN, padding=20, flex=1))

        # 返回按钮
        back_button = toga.Button('返回', on_press=lambda w: self.show_monthly_menu(),
                                  style=Pack(padding=5, font_size=14))
        box.add(back_button)

        # 标题
        title = toga.Label('月卡玩家批量签到',
                           style=Pack(font_size=18, font_weight='bold', padding_bottom=20, text_align='center'))
        box.add(title)

        # 日志显示区域
        log_box = toga.ScrollContainer(style=Pack(flex=1, padding_bottom=10))
        self.log_text = toga.MultilineTextInput(readonly=True, style=Pack(flex=1))
        log_box.content = self.log_text
        box.add(log_box)

        # 状态显示
        self.status_label = toga.Label('', style=Pack(padding=10, color='blue'))
        box.add(self.status_label)

        # 开始签到按钮
        start_button = toga.Button('开始签到', on_press=self.start_monthly_execution,
                                   style=Pack(padding=10, font_size=16))
        box.add(start_button)

        self.main_window.content = box

    def start_monthly_execution(self, widget):
        """开始月卡玩家批量签到"""

        def infolog(message):
            """显示日志信息"""
            self.log_text.value += f"{datetime.now().strftime('%H:%M:%S')} - {message}\n"
            # 滚动到底部
            self.log_text.scroll_to_bottom()

        def update_status(message, expiring_users=None):
            """更新状态信息"""
            self.status_label.text = message
            if expiring_users and len(expiring_users) > 0:
                expiring_text = "\n即将过期的用户:\n"
                for idx, user, date, days in expiring_users:
                    expiring_text += f"用户 {user} 将在 {days} 天后过期 ({date})\n"
                self.log_text.value += expiring_text

        # 修复：使用create_task代替run，避免事件循环冲突
        asyncio.create_task(execute_monthly_sign_in(self.monthly_users, infolog, update_status))

    def show_monthly_management(self, widget=None):
        """显示月卡玩家管理界面"""
        self.current_screen = "monthly_management"

        box = toga.Box(style=Pack(direction=COLUMN, padding=20, flex=1))

        # 返回按钮
        back_button = toga.Button('返回', on_press=lambda w: self.show_monthly_menu(),
                                  style=Pack(padding=5, font_size=14))
        box.add(back_button)

        # 标题
        title = toga.Label('月卡玩家管理',
                           style=Pack(font_size=18, font_weight='bold', padding_bottom=20, text_align='center'))
        box.add(title)

        # 用户列表
        list_box = toga.ScrollContainer(style=Pack(flex=1, padding_bottom=10))
        self.monthly_list = toga.MultilineTextInput(readonly=True, style=Pack(flex=1))
        list_box.content = self.monthly_list
        box.add(list_box)

        # 选择用户输入框
        select_box = toga.Box(style=Pack(direction=ROW, padding=10))
        select_label = toga.Label('选择用户序号:', style=Pack(width=120))
        self.monthly_selected_index = toga.TextInput(placeholder="输入序号", style=Pack(flex=1))
        select_box.add(select_label)
        select_box.add(self.monthly_selected_index)
        box.add(select_box)

        # 按钮行
        buttons_box = toga.Box(style=Pack(direction=ROW, padding=10))

        add_button = toga.Button('添加用户', on_press=self.add_monthly_user,
                                 style=Pack(padding=5, flex=1))
        edit_button = toga.Button('编辑用户', on_press=self.edit_monthly_user,
                                  style=Pack(padding=5, flex=1))
        delete_button = toga.Button('删除用户', on_press=self.delete_monthly_user,
                                    style=Pack(padding=5, flex=1))

        buttons_box.add(add_button)
        buttons_box.add(edit_button)
        buttons_box.add(delete_button)
        box.add(buttons_box)

        # 刷新用户列表
        self.refresh_monthly_list()

        self.main_window.content = box

    def refresh_monthly_list(self):
        """刷新月卡用户列表"""
        self.monthly_list.value = "序号 | 用户名 | 学号 | 到期时间 | 签到时段\n"
        self.monthly_list.value += "-----------------------------------------\n"
        for i, user in enumerate(self.monthly_users):
            self.monthly_list.value += f"{format_index(i)} | {user['username']} | {user['user']} | {user['stoptime'] or '永久'} | {user.get('start_time', '')}-{user.get('end_time', '')}\n"

    async def add_monthly_user(self, widget):
        """添加月卡用户"""
        await self.show_monthly_user_form(None)

    async def edit_monthly_user(self, widget):
        """编辑月卡用户"""
        if not self.monthly_users:
            await self.main_window.dialog(toga.dialogs.InfoDialog('警告', '没有用户可编辑'))
            return

        # 获取用户输入的序号
        try:
            selected_index = int(self.monthly_selected_index.value)
        except ValueError:
            await self.main_window.dialog(toga.dialogs.InfoDialog('错误', '请输入有效的序号'))
            return

        if selected_index < 0 or selected_index >= len(self.monthly_users):
            await self.main_window.dialog(toga.dialogs.InfoDialog('错误', '序号超出范围'))
            return

        await self.show_monthly_user_form(selected_index)

    async def delete_monthly_user(self, widget):
        """删除月卡用户"""
        if not self.monthly_users:
            await self.main_window.dialog(toga.dialogs.InfoDialog('警告', '没有用户可删除'))
            return

        # 获取用户输入的序号
        try:
            selected_index = int(self.monthly_selected_index.value)
        except ValueError:
            await self.main_window.dialog(toga.dialogs.InfoDialog('错误', '请输入有效的序号'))
            return

        if selected_index < 0 or selected_index >= len(self.monthly_users):
            await self.main_window.dialog(toga.dialogs.InfoDialog('错误', '序号超出范围'))
            return

        user = self.monthly_users[selected_index]

        result = await self.main_window.dialog(
            toga.dialogs.QuestionDialog('确认删除', f'确定要删除用户 {user["username"]} 吗？')
        )

        if result:
            del self.monthly_users[selected_index]
            save_users(self, self.monthly_users, MONTHLY_USER_DATA_FILE)
            self.refresh_monthly_list()
            await self.main_window.dialog(toga.dialogs.InfoDialog('提示', '用户已删除'))

    async def show_monthly_user_form(self, index):
        """显示添加/编辑月卡用户表单"""
        is_new = index is None
        user = {"username": "", "user": "", "password": "", "stoptime": "", "start_time": "", "end_time": ""}

        if not is_new:
            user = self.monthly_users[index].copy()

        # 创建一个新窗口用于表单
        form_window = toga.Window(title='添加月卡用户' if is_new else '编辑月卡用户', size=(400, 500))
        form_box = toga.Box(style=Pack(direction=COLUMN, padding=20))

        # 用户名输入
        username_label = toga.Label('用户名:', style=Pack(padding_bottom=5))
        username_input = toga.TextInput(value=user["username"], placeholder="用户名", style=Pack(padding_bottom=10))
        form_box.add(username_label)
        form_box.add(username_input)

        # 学号输入
        user_label = toga.Label('学号:', style=Pack(padding_bottom=5))
        user_input = toga.TextInput(value=user["user"], placeholder="学号", style=Pack(padding_bottom=10))
        form_box.add(user_label)
        form_box.add(user_input)

        # 密码输入
        password_label = toga.Label('密码:', style=Pack(padding_bottom=5))
        password_input = toga.PasswordInput(value=user["password"], placeholder="密码", style=Pack(padding_bottom=10))
        form_box.add(password_label)
        form_box.add(password_input)

        # 到期时间输入
        stoptime_label = toga.Label('到期时间:', style=Pack(padding_bottom=5))
        stoptime_input = toga.TextInput(value=user["stoptime"], placeholder="YYYY-MM-DD，留空表示永久", style=Pack(padding_bottom=10))
        form_box.add(stoptime_label)
        form_box.add(stoptime_input)

        # 签到开始时间
        start_time_label = toga.Label('开始时间:', style=Pack(padding_bottom=5))
        start_time_input = toga.TextInput(value=user["start_time"], placeholder="HH:MM", style=Pack(padding_bottom=10))
        form_box.add(start_time_label)
        form_box.add(start_time_input)

        # 签到结束时间
        end_time_label = toga.Label('结束时间:', style=Pack(padding_bottom=5))
        end_time_input = toga.TextInput(value=user["end_time"], placeholder="HH:MM", style=Pack(padding_bottom=20))
        form_box.add(end_time_label)
        form_box.add(end_time_input)

        # 按钮
        buttons_box = toga.Box(style=Pack(direction=ROW, padding=10))
        save_button = toga.Button('保存', on_press=lambda w: self.save_monthly_user(
            is_new, index, username_input.value, user_input.value, password_input.value,
            stoptime_input.value, start_time_input.value, end_time_input.value, form_window
        ), style=Pack(flex=1, padding_right=5))
        cancel_button = toga.Button('取消', on_press=lambda w: form_window.close(), style=Pack(flex=1, padding_left=5))
        buttons_box.add(save_button)
        buttons_box.add(cancel_button)
        form_box.add(buttons_box)

        form_window.content = form_box
        form_window.show()

    def save_monthly_user(self, is_new, index, username, user_id, password, stoptime, start_time, end_time, window):
        """保存月卡用户"""
        # 验证输入
        if not username or not user_id or not password:
            asyncio.create_task(self.show_dialog('错误', '请填写用户名、学号和密码'))
            return

        new_user = {
            "username": username,
            "user": user_id,
            "password": password,
            "stoptime": stoptime,
            "start_time": start_time,
            "end_time": end_time
        }

        if is_new:
            self.monthly_users.append(new_user)
        else:
            self.monthly_users[index] = new_user

        # 保存用户数据
        save_users(self, self.monthly_users, MONTHLY_USER_DATA_FILE)
        self.refresh_monthly_list()
        window.close()
        asyncio.create_task(self.show_dialog('提示', '用户已保存'))

    def show_single_menu(self, widget=None):
        """显示单次玩家菜单"""
        self.current_screen = "single_menu"

        box = toga.Box(style=Pack(direction=COLUMN, padding=20, flex=1))

        # 返回按钮
        back_button = toga.Button('返回', on_press=lambda w: self.show_main_menu(),
                                  style=Pack(padding=5, font_size=14))
        box.add(back_button)

        # 标题
        title = toga.Label('单次玩家',
                           style=Pack(font_size=18, font_weight='bold', padding_bottom=30, text_align='center'))
        box.add(title)

        # 批量签到按钮
        batch_button = toga.Button('批量签到', on_press=self.show_single_batch,
                                   style=Pack(padding=15, font_size=16))
        box.add(batch_button)

        # 用户管理按钮
        manage_button = toga.Button('用户管理', on_press=self.show_single_management,
                                    style=Pack(padding=15, font_size=16))
        box.add(manage_button)

        self.main_window.content = box

    def show_single_batch(self, widget=None):
        """显示单次玩家批量签到界面"""
        self.current_screen = "single_batch"

        box = toga.Box(style=Pack(direction=COLUMN, padding=20, flex=1))

        # 返回按钮
        back_button = toga.Button('返回', on_press=lambda w: self.show_single_menu(),
                                  style=Pack(padding=5, font_size=14))
        box.add(back_button)

        # 标题
        title = toga.Label('单次玩家批量签到',
                           style=Pack(font_size=18, font_weight='bold', padding_bottom=20, text_align='center'))
        box.add(title)

        # 用户列表
        list_box = toga.ScrollContainer(style=Pack(height=200, padding_bottom=10))
        self.single_batch_list = toga.MultilineTextInput(readonly=True, style=Pack(flex=1))
        list_box.content = self.single_batch_list
        box.add(list_box)

        # 选择用户输入
        select_box = toga.Box(style=Pack(direction=ROW, padding=10))
        select_label = toga.Label('选择用户序号 (用逗号分隔):', style=Pack(width=200))
        self.select_input = toga.TextInput(placeholder="例如: 001,002")
        select_box.add(select_label)
        select_box.add(self.select_input)
        box.add(select_box)

        # 日志显示区域
        log_box = toga.ScrollContainer(style=Pack(flex=1, padding_bottom=10))
        self.single_log_text = toga.MultilineTextInput(readonly=True, style=Pack(flex=1))
        log_box.content = self.single_log_text
        box.add(log_box)

        # 状态显示
        self.single_status_label = toga.Label('', style=Pack(padding=10, color='blue'))
        box.add(self.single_status_label)

        # 开始签到按钮
        start_button = toga.Button('开始签到', on_press=self.start_single_execution,
                                   style=Pack(padding=10, font_size=16))
        box.add(start_button)

        # 刷新用户列表
        self.refresh_single_batch_list()

        self.main_window.content = box

    def refresh_single_batch_list(self):
        """刷新单次用户列表"""
        self.single_batch_list.value = "序号 | 用户名 | 学号\n"
        self.single_batch_list.value += "------------------------\n"
        for i, user in enumerate(self.single_users):
            self.single_batch_list.value += f"{format_index(i)} | {user['username']} | {user['user']}\n"

    def start_single_execution(self, widget):
        """开始单次玩家批量签到"""
        # 获取选择的用户序号
        selected_text = self.select_input.value
        if not selected_text:
            asyncio.create_task(self.show_dialog('警告', '请输入要签到的用户序号'))
            return

        try:
            selected_indices = [int(idx.strip()) for idx in selected_text.split(',')]
        except ValueError:
            asyncio.create_task(self.show_dialog('错误', '请输入有效的序号'))
            return

        def infolog(message):
            """显示日志信息"""
            self.single_log_text.value += f"{datetime.now().strftime('%H:%M:%S')} - {message}\n"
            # 滚动到底部
            self.single_log_text.scroll_to_bottom()

        def update_status(message):
            """更新状态信息"""
            self.single_status_label.text = message

        # 修复：使用create_task代替run，避免事件循环冲突
        asyncio.create_task(execute_single_sign_in(self.single_users, selected_indices, infolog, update_status))

    def show_single_management(self, widget=None):
        """显示单次玩家管理界面"""
        self.current_screen = "single_management"

        box = toga.Box(style=Pack(direction=COLUMN, padding=20, flex=1))

        # 返回按钮
        back_button = toga.Button('返回', on_press=lambda w: self.show_single_menu(),
                                  style=Pack(padding=5, font_size=14))
        box.add(back_button)

        # 标题
        title = toga.Label('单次玩家管理',
                           style=Pack(font_size=18, font_weight='bold', padding_bottom=20, text_align='center'))
        box.add(title)

        # 用户列表
        list_box = toga.ScrollContainer(style=Pack(flex=1, padding_bottom=10))
        self.single_list = toga.MultilineTextInput(readonly=True, style=Pack(flex=1))
        list_box.content = self.single_list
        box.add(list_box)

        # 选择用户输入框
        select_box = toga.Box(style=Pack(direction=ROW, padding=10))
        select_label = toga.Label('选择用户序号:', style=Pack(width=120))
        self.single_selected_index = toga.TextInput(placeholder="输入序号", style=Pack(flex=1))
        select_box.add(select_label)
        select_box.add(self.single_selected_index)
        box.add(select_box)

        # 按钮行
        buttons_box = toga.Box(style=Pack(direction=ROW, padding=10))

        add_button = toga.Button('添加用户', on_press=self.add_single_user,
                                 style=Pack(padding=5, flex=1))
        edit_button = toga.Button('编辑用户', on_press=self.edit_single_user,
                                  style=Pack(padding=5, flex=1))
        delete_button = toga.Button('删除用户', on_press=self.delete_single_user,
                                    style=Pack(padding=5, flex=1))

        buttons_box.add(add_button)
        buttons_box.add(edit_button)
        buttons_box.add(delete_button)
        box.add(buttons_box)

        # 刷新用户列表
        self.refresh_single_list()

        self.main_window.content = box

    def refresh_single_list(self):
        """刷新单次用户列表"""
        self.single_list.value = "序号 | 用户名 | 学号\n"
        self.single_list.value += "------------------------\n"
        for i, user in enumerate(self.single_users):
            self.single_list.value += f"{format_index(i)} | {user['username']} | {user['user']}\n"

    async def add_single_user(self, widget):
        """添加单次用户"""
        await self.show_single_user_form(None)

    async def edit_single_user(self, widget):
        """编辑单次用户"""
        if not self.single_users:
            await self.main_window.dialog(toga.dialogs.InfoDialog('警告', '没有用户可编辑'))
            return

        # 获取用户输入的序号
        try:
            selected_index = int(self.single_selected_index.value)
        except ValueError:
            await self.main_window.dialog(toga.dialogs.InfoDialog('错误', '请输入有效的序号'))
            return

        if selected_index < 0 or selected_index >= len(self.single_users):
            await self.main_window.dialog(toga.dialogs.InfoDialog('错误', '序号超出范围'))
            return

        await self.show_single_user_form(selected_index)

    async def delete_single_user(self, widget):
        """删除单次用户"""
        if not self.single_users:
            await self.main_window.dialog(toga.dialogs.InfoDialog('警告', '没有用户可删除'))
            return

        # 获取用户输入的序号
        try:
            selected_index = int(self.single_selected_index.value)
        except ValueError:
            await self.main_window.dialog(toga.dialogs.InfoDialog('错误', '请输入有效的序号'))
            return

        if selected_index < 0 or selected_index >= len(self.single_users):
            await self.main_window.dialog(toga.dialogs.InfoDialog('错误', '序号超出范围'))
            return

        user = self.single_users[selected_index]

        result = await self.main_window.dialog(
            toga.dialogs.QuestionDialog('确认删除', f'确定要删除用户 {user["username"]} 吗？')
        )

        if result:
            del self.single_users[selected_index]
            save_users(self, self.single_users, SINGLE_USER_DATA_FILE)
            self.refresh_single_list()
            await self.main_window.dialog(toga.dialogs.InfoDialog('提示', '用户已删除'))

    async def show_single_user_form(self, index):
        """显示添加/编辑单次用户表单"""
        is_new = index is None
        user = {"username": "", "user": "", "password": ""}

        if not is_new:
            user = self.single_users[index].copy()

        # 创建一个新窗口用于表单
        form_window = toga.Window(title='添加单次用户' if is_new else '编辑单次用户', size=(400, 400))
        form_box = toga.Box(style=Pack(direction=COLUMN, padding=20))

        # 用户名输入
        username_label = toga.Label('用户名:', style=Pack(padding_bottom=5))
        username_input = toga.TextInput(value=user["username"], placeholder="用户名", style=Pack(padding_bottom=10))
        form_box.add(username_label)
        form_box.add(username_input)

        # 学号输入
        user_label = toga.Label('学号:', style=Pack(padding_bottom=5))
        user_input = toga.TextInput(value=user["user"], placeholder="学号", style=Pack(padding_bottom=10))
        form_box.add(user_label)
        form_box.add(user_input)

        # 密码输入
        password_label = toga.Label('密码:', style=Pack(padding_bottom=5))
        password_input = toga.PasswordInput(value=user["password"], placeholder="密码", style=Pack(padding_bottom=20))
        form_box.add(password_label)
        form_box.add(password_input)

        # 按钮
        buttons_box = toga.Box(style=Pack(direction=ROW, padding=10))
        save_button = toga.Button('保存', on_press=lambda w: self.save_single_user(
            is_new, index, username_input.value, user_input.value, password_input.value, form_window
        ), style=Pack(flex=1, padding_right=5))
        cancel_button = toga.Button('取消', on_press=lambda w: form_window.close(), style=Pack(flex=1, padding_left=5))
        buttons_box.add(save_button)
        buttons_box.add(cancel_button)
        form_box.add(buttons_box)

        form_window.content = form_box
        form_window.show()

    def save_single_user(self, is_new, index, username, user_id, password, window):
        """保存单次用户"""
        # 验证输入
        if not username or not user_id or not password:
            asyncio.create_task(self.show_dialog('错误', '请填写用户名、学号和密码'))
            return

        new_user = {
            "username": username,
            "user": user_id,
            "password": password
        }

        if is_new:
            self.single_users.append(new_user)
        else:
            self.single_users[index] = new_user

        # 保存用户数据
        save_users(self, self.single_users, SINGLE_USER_DATA_FILE)
        self.refresh_single_list()
        window.close()
        asyncio.create_task(self.show_dialog('提示', '用户已保存'))

    def show_test_screen(self, widget=None):
        """显示测试签到界面"""
        self.current_screen = "test_screen"

        box = toga.Box(style=Pack(direction=COLUMN, padding=20, flex=1))

        # 返回按钮
        back_button = toga.Button('返回', on_press=lambda w: self.show_main_menu(),
                                  style=Pack(padding=5, font_size=14))
        box.add(back_button)

        # 标题
        title = toga.Label('测试签到',
                           style=Pack(font_size=18, font_weight='bold', padding_bottom=20, text_align='center'))
        box.add(title)

        # 学号输入
        user_box = toga.Box(style=Pack(direction=ROW, padding=10))
        user_label = toga.Label('学号:', style=Pack(width=100))
        self.test_user_input = toga.TextInput(placeholder="请输入学号")
        user_box.add(user_label)
        user_box.add(self.test_user_input)
        box.add(user_box)

        # 密码输入
        password_box = toga.Box(style=Pack(direction=ROW, padding=10))
        password_label = toga.Label('密码:', style=Pack(width=100))
        self.test_password_input = toga.PasswordInput(placeholder="请输入密码")
        password_box.add(password_label)
        password_box.add(self.test_password_input)
        box.add(password_box)

        # 日志显示区域
        log_box = toga.ScrollContainer(style=Pack(flex=1, padding_bottom=10))
        self.test_log_text = toga.MultilineTextInput(readonly=True, style=Pack(flex=1))
        log_box.content = self.test_log_text
        box.add(log_box)

        # 状态显示
        self.test_status_label = toga.Label('', style=Pack(padding=10, color='blue'))
        box.add(self.test_status_label)

        # 开始测试按钮
        start_button = toga.Button('开始测试', on_press=self.start_test,
                                   style=Pack(padding=10, font_size=16))
        box.add(start_button)

        self.main_window.content = box

    def start_test(self, widget):
        """开始测试签到"""
        username = self.test_user_input.value
        password = self.test_password_input.value

        if not username or not password:
            asyncio.create_task(self.show_dialog("错误", "请输入学号和密码"))
            return

        def infolog(message):
            """显示日志信息"""
            self.test_log_text.value += f"{datetime.now().strftime('%H:%M:%S')} - {message}\n"
            # 滚动到底部
            self.test_log_text.scroll_to_bottom()

        def update_status(message):
            """更新状态信息"""
            self.test_status_label.text = message

        # 修复：使用create_task代替run，避免事件循环冲突
        asyncio.create_task(test_sign_in(username, password, infolog, update_status))

    async def show_dialog(self, title, message):
        """显示对话框的辅助方法"""
        await self.main_window.dialog(toga.dialogs.InfoDialog(title, message))


def main():
    return SignInApp()



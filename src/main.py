import flet as ft
from bilibili_api import Picture, login_v2, sync, Credential, user, live
from typing import Any, Optional
import asyncio
import base64
import logging
import tempfile
import os
import json
from datetime import datetime, timedelta

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# MIME 类型映射
MIME_TYPES = {
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'gif': 'image/gif',
    'webp': 'image/webp',
    'bmp': 'image/bmp',
    'ico': 'image/x-icon',
}


def picture_to_base64_data_uri(picture: Picture) -> str:
    """
    将 Picture 对象转换为 data URI 格式
    
    Args:
        picture: Picture 对象，content 是完整的图片文件二进制内容
        
    Returns:
        data URI 字符串，例如: "data:image/png;base64,xxxxx"
    """
    img_bytes = picture.content
    base64_str = base64.b64encode(img_bytes).decode()
    
    # 获取 MIME 类型，默认使用 image/png
    mime_type = MIME_TYPES.get(picture.imageType.lower(), 'image/png')
    
    return base64_str


def picture_to_temp_file(picture: Picture) -> str:
    """
    将 Picture 对象保存为临时文件并返回文件路径
    
    Args:
        picture: Picture 对象
        
    Returns:
        临时文件路径
    """
    tmp_dir = tempfile.gettempdir()
    ext = picture.imageType.lower() if picture.imageType else 'png'
    # 使用时间戳生成唯一文件名
    file_path = os.path.join(tmp_dir, f"qr_{asyncio.get_event_loop().time()}.{ext}")
    
    with open(file_path, 'wb') as f:
        f.write(picture.content)
    
    logger.info(f"临时文件已保存: {file_path}")
    return file_path


# 全局凭证变量
credential = None

# 凭证文件路径
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "../storage/credentials.json")
MONITOR_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "../storage/monitor_history.json")
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "../storage/settings.json")
CACHE_DURATION_HOURS = 6  # 缓存时长（小时）

qr = login_v2.QrCodeLogin(platform=login_v2.QrCodeLoginChannel.WEB) # 生成二维码登录实例，平台选择网页端


def load_credential() -> Credential | None:
    """
    从本地加载凭证
    
    Returns:
        Credential: 如果凭证有效，返回Credential对象；否则返回None
    """
    global credential
    
    try:
        if not os.path.exists(CREDENTIALS_FILE):
            logger.info("凭证文件不存在")
            return None
        
        with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 检查是否过期
        expires_at = data.get('expires_at')
        if expires_at:
            if datetime.now().timestamp() > expires_at:
                logger.info("凭证已过期，需要重新登录")
                clear_credential()
                return None
        
        # 创建Credential对象
        credential = Credential(
            sessdata=data.get('sessdata'),
            bili_jct=data.get('bili_jct'),
            dedeuserid=data.get('dedeuserid'),
            ac_time_value=data.get('ac_time_value')
        )
        
        logger.info("凭证加载成功")
        return credential
    
    except Exception as e:
        logger.error(f"加载凭证失败: {e}")
        clear_credential()
        return None


def save_credential(cred: Credential) -> bool:
    """
    保存凭证到本地
    
    Args:
        cred: Credential对象
        
    Returns:
        bool: 保存是否成功
    """
    global credential
    
    try:
        # 确保storage目录存在
        storage_dir = os.path.dirname(CREDENTIALS_FILE)
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)
        
        # 计算过期时间
        expires_at = (datetime.now() + timedelta(hours=CACHE_DURATION_HOURS)).timestamp()
        
        data = {
            'sessdata': cred.sessdata,
            'bili_jct': cred.bili_jct,
            'dedeuserid': cred.dedeuserid,
            'ac_time_value': cred.ac_time_value,
            'expires_at': expires_at
        }
        
        with open(CREDENTIALS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # 设置文件权限（仅所有者可读写）
        os.chmod(CREDENTIALS_FILE, 0o600)
        
        credential = cred
        logger.info(f"凭证已保存，将在 {CACHE_DURATION_HOURS} 小时后过期")
        return True
    
    except Exception as e:
        logger.error(f"保存凭证失败: {e}")
        return False


def clear_credential() -> bool:
    """
    清除本地凭证
    
    Returns:
        bool: 清除是否成功
    """
    global credential
    
    try:
        if os.path.exists(CREDENTIALS_FILE):
            os.remove(CREDENTIALS_FILE)
            logger.info("凭证文件已删除")
        
        credential = None
        return True
    
    except Exception as e:
        logger.error(f"清除凭证失败: {e}")
        return False


def is_credential_valid() -> bool:
    """
    检查当前凭证是否有效
    
    Returns:
        bool: 凭证是否有效
    """
    if credential is None:
        return False
    
    try:
        # 检查文件是否存在
        if not os.path.exists(CREDENTIALS_FILE):
            return False
        
        # 检查是否过期
        with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        expires_at = data.get('expires_at')
        if expires_at:
            if datetime.now().timestamp() > expires_at:
                return False
        
        return True
    
    except Exception as e:
        logger.error(f"检查凭证有效性失败: {e}")
        return False


async def get_my_uid(credential: Credential) -> int | None:
    """获取当前登录用户的 uid"""
    try:
        # 获取当前用户信息
        my_info = await user.get_self_info(credential)
        uid = my_info['mid']
        logger.info(f"获取到当前用户 uid: {uid}")
        return uid
    except Exception as e:
        logger.error(f"获取用户 uid 失败: {e}")
        return None


async def check_login_status(page: ft.Page, login_container: ft.Column):
    """后台检查登录状态"""
    logger.info("开始检查登录状态...")
    while not qr.has_done():
        result = await qr.check_state()
        logger.info(f"登录状态检查: {result}")
        await asyncio.sleep(1)
    
    # 登录成功，保存凭证
    cred = qr.get_credential()
    if save_credential(cred):
        logger.info("凭证已缓存到本地")
    
    # 获取当前用户 uid
    uid = await get_my_uid(cred)
    if uid:
        logger.info(f"当前登录用户 uid: {uid}")
        # 可以将 uid 保存到全局变量或传递给其他函数
        # 现在你可以用这个 uid 初始化 User 对象
        # current_user = user.User(uid=uid, credential=cred)
    
    # 切换到主界面
    logger.info("登录成功！切换到主界面")
    page.remove(login_container)
    show_main_ui(page)


def show_login_ui(page: ft.Page):
    """显示登录界面"""
    # 生成二维码
    async def generate_qr():
        logger.info("开始生成二维码...")
        qr_img = await qr.generate_qrcode()
        picture = qr.get_qrcode_picture()
        
        logger.info(f"二维码信息 - 类型: {picture.imageType}, 尺寸: {picture.width}x{picture.height}")
        
        # 使用封装的函数转换为 data URI
        data_uri = picture_to_base64_data_uri(picture)
        
        logger.info(f"二维码 base64（前100字符）: {data_uri}")
        
        qr_image.src_base64 = data_uri
        qr_image.update()
        logger.info("二维码生成完成并显示")
        
        # 启动后台检查登录状态
        asyncio.create_task(check_login_status(page, login_container))
    
    qr_image = ft.Image(
        width=200,
        height=200,
        fit=ft.ImageFit.CONTAIN,
        src="https://picsum.photos/seed/placeholder/200/200.jpg",  # 添加占位图片
    )
    
    login_container = ft.Column(
        [
            ft.Container(
                content=qr_image,
                padding=20,
                bgcolor=ft.Colors.WHITE,
                border_radius=10,
                shadow=ft.BoxShadow(
                    blur_radius=10,
                    spread_radius=2,
                    color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
                ),
            ),
            ft.Text("请使用B站APP扫描二维码登录", size=16, color=ft.Colors.GREY_700),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
        expand=True,
    )
    
    page.add(login_container)
    
    # 使用 page.run_task 来安全地创建异步任务
    page.run_task(generate_qr)


async def get_current_user_info():
    """获取当前登录用户信息"""
    global credential
    if not credential:
        return None, None, None
    
    try:
        my_info = await user.get_self_info(credential)
        uid = my_info['mid']
        username = my_info['name']
        avatar_url = my_info['face']
        logger.info(f"用户信息 - UID: {uid}, 用户名: {username}, 头像: {avatar_url}")
        return uid, username, avatar_url
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        return None, None, None


def handle_popup_menu_selected(e):
    """处理弹出菜单选择"""
    # 获取当前页面引用
    current_page = e.control.page
    if e.control.text == "注销":
        handle_logout(current_page)  # 直接调用注销函数


def handle_logout(page: ft.Page):
    """处理用户注销"""
    global credential
    
    logger.info("用户请求注销...")
    
    # 清除本地凭证
    if clear_credential():
        logger.info("凭证已清除")
    
    # 重置全局凭证变量
    credential = None
    
    # 重新生成新的二维码登录实例
    global qr
    qr = login_v2.QrCodeLogin(platform=login_v2.QrCodeLoginChannel.WEB)
    
    # 重新加载页面并生成二维码
    page.clean()
    show_login_ui(page)


def load_monitor_history() -> list[str]:
    """加载历史监控房间号"""
    try:
        if os.path.exists(MONITOR_HISTORY_FILE):
            with open(MONITOR_HISTORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('room_ids', [])
        return []
    except Exception as e:
        logger.error(f"加载监控历史失败: {e}")
        return []


def save_monitor_history(room_ids: list[str]) -> bool:
    """保存历史监控房间号"""
    try:
        # 确保storage目录存在
        storage_dir = os.path.dirname(MONITOR_HISTORY_FILE)
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)
        
        # 只保留最近20个记录
        room_ids = room_ids[-20:] if len(room_ids) > 20 else room_ids
        
        data = {'room_ids': room_ids}
        with open(MONITOR_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"保存了 {len(room_ids)} 条监控历史记录")
        return True
    except Exception as e:
        logger.error(f"保存监控历史失败: {e}")
        return False


def add_room_to_history(room_id: str) -> bool:
    """添加房间号到历史记录"""
    try:
        # 获取当前历史记录
        history = load_monitor_history()
        
        # 如果房间号已存在，先删除
        if room_id in history:
            history.remove(room_id)
        
        # 添加到开头
        history.insert(0, room_id)
        
        # 保存
        return save_monitor_history(history)
    except Exception as e:
        logger.error(f"添加房间号到历史记录失败: {e}")
        return False


def load_settings() -> dict:
    """加载设置配置"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"加载设置失败: {e}")
        return {}


def save_settings(settings: dict) -> bool:
    """保存设置配置"""
    try:
        # 确保storage目录存在
        storage_dir = os.path.dirname(SETTINGS_FILE)
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)
        
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        
        # 设置文件权限（仅所有者可读写）
        os.chmod(SETTINGS_FILE, 0o600)
        
        logger.info("设置已保存")
        return True
    except Exception as e:
        logger.error(f"保存设置失败: {e}")
        return False


# 全局设置变量
app_settings = load_settings()

# 全局广告状态回调函数（用于设置页面的广告开关变化时通知监控页面）
ad_control_callback = None


def register_ad_control_callback(callback):
    """注册广告控制回调函数"""
    global ad_control_callback
    ad_control_callback = callback


def execute_ad_control_callback(enable: bool):
    """执行广告控制回调"""
    global ad_control_callback
    if ad_control_callback:
        ad_control_callback(enable)


async def get_room_details(room_id: str) -> dict[str, object]:
    """获取直播间详情"""
    try:
        global credential
        room_id_int = int(room_id)
        live_room = live.LiveRoom(room_display_id=room_id_int, credential=credential)
        
        # 获取房间基本信息
        room_info = await live_room.get_room_info()
        room_play_info = await live_room.get_room_play_info()
        
        return {
            "success": True,
            "room_info": room_info,
            "play_info": room_play_info
        }
    except Exception as e:
        logger.error(f"获取直播间详情失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def create_monitor_page(page: ft.Page):
    """创建监控页面"""
    # 加载历史记录
    history_room_ids = load_monitor_history()
    
    # 房间号输入框
    room_input = ft.TextField(
        label="输入监控直播房间号",
        hint_text="请输入直播间ID",
        width=300,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    
    # 历史记录下拉框选择事件
    def on_history_change(e):
        if e.data:
            room_input.value = e.data
            room_input.update()
            # 自动触发开始监控
            async def auto_start_monitor():
                await on_monitor_click(None)
            page.run_task(auto_start_monitor)
    
    # 历史记录下拉框
    history_dropdown = ft.Dropdown(
        label="历史监控房间号",
        width=300,
        options=[ft.dropdown.Option(room_id) for room_id in history_room_ids],
        on_change=on_history_change,
    )
    
    # 状态文本
    status_text = ft.Text(
        "",
        size=14,
        color=ft.Colors.GREY_600,
    )
    
    # 房间信息展示区域
    room_info_container = ft.Container(
        content=ft.Column([]),
        visible=False,
        padding=20,
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.BLUE_GREY_50),
        border_radius=10,
    )
    
    # 弹幕列表容器
    danmaku_list = ft.ListView(
        expand=True,
        spacing=5,
        auto_scroll=True,
    )
    
    # 弹幕监控状态文本
    danmaku_status_text = ft.Text("未开始监控", size=14, color=ft.Colors.GREY_500)
    
    # 当前监控的房间号
    current_room_id = {'value': None}
    
    # 发送弹幕输入框
    danmaku_input = ft.TextField(
        label="发送弹幕",
        hint_text="输入弹幕内容...",
        expand=True,
        on_submit=lambda e: page.run_task(send_danmaku),
    )
    
    # 发送弹幕函数
    async def send_danmaku(e=None):
        """  发送弹幕"""
        if not current_room_id['value']:
            logger.warning("未设置房间号，无法发送弹幕")
            return
        
        danmaku_text = danmaku_input.value.strip() if danmaku_input.value else ""
        if not danmaku_text:
            return
        
        try:
            room_id_int = int(current_room_id['value'])
            # 使用 LiveRoom 发送弹幕
            live_room = live.LiveRoom(room_display_id=room_id_int, credential=credential)
            await live_room.send_danmaku(live.Danmaku(danmaku_text))
            
            logger.info(f"发送弹幕成功: {danmaku_text}")
            
            # 清空输入框
            danmaku_input.value = ""
            danmaku_input.update()
            
        except Exception as ex:
            logger.error(f"发送弹幕失败: {ex}")
    
    # 发送按钮
    send_button = ft.IconButton(
        icon=ft.Icons.SEND,
        icon_color=ft.Colors.BLUE_500,
        tooltip="发送弹幕",
        on_click=lambda e: page.run_task(send_danmaku),
    )
    
    # 发送弹幕区域
    send_danmaku_row = ft.Row(
        [danmaku_input, send_button],
        spacing=5,
    )
    
    # 弹幕监控区域 - 初始时就显示，确保 ListView 被添加到页面
    danmaku_container = ft.Container(
        content=ft.Column([
            ft.Text("弹幕监控", size=18, weight=ft.FontWeight.BOLD),
            ft.Container(height=5),
            danmaku_status_text,
            ft.Container(height=5),
            ft.Container(
                content=danmaku_list,
                expand=True,  # 自适应高度
                border=ft.border.all(1, ft.Colors.GREY_300),
                border_radius=5,
                padding=10,
            ),
            ft.Container(height=10),
            send_danmaku_row,  # 添加发送弹幕区域
        ], expand=True),
        visible=True,  # 始终显示，确保 ListView 被添加到页面
        padding=20,
        bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.BLUE_GREY_50),
        border_radius=10,
        width=400,
        expand=True,  # 自适应高度
    )
    
    # 更新弹幕容器状态（启动监控时调用）
    def update_danmaku_container():
        danmaku_status_text.value = "正在监控中..."
        danmaku_status_text.color = ft.Colors.GREEN_500
        danmaku_status_text.update()
        # ListView 已经在页面上，直接设置就绪状态
        danmaku_state['listview_ready'] = True
    
    # 使用字典来存储弹幕监控状态
    danmaku_state = {
        'live_danmaku': None,
        'is_monitoring': False,
        'listview_ready': False,  # 添加标志来跟踪ListView是否已准备好
        'page_visible': True,  # 追踪页面是否可见
        'danmaku_queue': [],  # 弹幕缓存队列
        'ad_tasks': [],  # 定时广告任务列表
    }
    
    # 弹幕事件处理函数
    def on_danmaku_msg(event: dict) -> None:
        """处理弹幕消息"""
        try: 
            logger.info(f"弹幕消息: {event}")
            # 检查ListView是否已准备好
            if not danmaku_state['listview_ready']:
                logger.warning("ListView尚未准备好，跳过弹幕处理")
                return
                
            # 解析弹幕数据
            info = event.get('data', {}).get('info', [])
            if len(info) >= 2:
                user_info = info[2]
                danmaku_text = info[1]
                username = user_info[1] if len(user_info) > 1 else "未知用户"
                user_uid = str(user_info[0]) if len(user_info) > 0 else ""
                
                # 检查是否是当前登录用户的弹幕
                current_uid = credential.dedeuserid if credential else ""
                is_self = user_uid == current_uid
                
                # 使用 page.run_task 安全更新 UI
                async def update_ui():
                    try:
                        # 根据是否是当前用户设置颜色
                        if is_self:
                            # 当前用户的弹幕用浅绿色
                            name_color = ft.Colors.LIGHT_GREEN_700
                            text_color = ft.Colors.LIGHT_GREEN_600
                        else:
                            # 其他用户的弹幕
                            name_color = ft.Colors.BLUE_600
                            text_color = ft.Colors.GREY_800
                        
                        # 创建弹幕显示项
                        danmaku_item = ft.Row([
                            ft.Text(f"{username}:", size=12, weight=ft.FontWeight.BOLD, color=name_color),
                            ft.Text(danmaku_text, size=12, color=text_color),
                        ], spacing=5)
                        
                        # 添加到弹幕列表
                        danmaku_list.controls.append(danmaku_item)
                        
                        # 限制弹幕数量，最多保留100条
                        if len(danmaku_list.controls) > 100:
                            danmaku_list.controls.pop(0)
                        
                        danmaku_list.update()
                        logger.info(f"弹幕: {username} - {danmaku_text}{' [我]' if is_self else ''}")
                    except Exception as e:
                        logger.error(f"更新弹幕UI失败: {e}")
                
                # 如果页面可见，直接更新UI；否则缓存弹幕
                if danmaku_state['page_visible']:
                    page.run_task(update_ui)
                else:
                    # 缓存弹幕数据
                    danmaku_state['danmaku_queue'].append({
                        'type': 'danmaku',
                        'username': username,
                        'text': danmaku_text,
                        'is_self': is_self
                    })
                    # 限制队列长度
                    if len(danmaku_state['danmaku_queue']) > 50:
                        danmaku_state['danmaku_queue'].pop(0)
                
        except Exception as e:
            logger.error(f"处理弹幕消息失败: {e}")
    
    # 礼物事件处理函数
    def on_gift(event: dict) -> None:
        """处理礼物消息"""
        try:
            # 打印完整的礼物消息数据
            logger.info(f"收到礼物消息: {json.dumps(event, ensure_ascii=False, indent=2)}")
            
            # 检查ListView是否已准备好
            if not danmaku_state['listview_ready']:
                logger.warning("ListView尚未准备好，跳过礼物处理")
                return
                
            # 解析礼物数据
            data = event.get('data', {})
            data_detail: Any = data.get('data', {})
            logger.info(msg=f"data_detail: {data_detail}")
            gift_name = data_detail.get('giftName', '未知礼物')
            username = data_detail.get('uname', '未知用户')
            num = data_detail.get('num', 1)
            
            # 检查是否启用自动答谢
            thank_enabled = app_settings.get('thank_enabled', False)
            
            # 使用 page.run_task 安全更新 UI
            async def update_ui():
                try:
                    # 创建礼物显示项
                    gift_item = ft.Row([
                        ft.Icon(ft.Icons.CARD_GIFTCARD, size=16, color=ft.Colors.ORANGE_500),
                        ft.Text(f"{username} 赠送了 {gift_name} ×{num}", size=12, color=ft.Colors.ORANGE_600),
                    ], spacing=5)
                    
                    # 添加到弹幕列表
                    danmaku_list.controls.append(gift_item)
                    
                    # 限制弹幕数量，最多保留100条
                    if len(danmaku_list.controls) > 100:
                        danmaku_list.controls.pop(0)
                    
                    danmaku_list.update()
                    logger.info(f"礼物: {username} - {gift_name} ×{num}")
                    
                    # 自动答谢功能
                    if thank_enabled and current_room_id['value']:
                        await send_thank_message(username, gift_name, num)
                        
                except Exception as e:
                    logger.error(f"更新礼物UI失败: {e}")
            
            # 如果页面可见，直接更新UI；否则缓存礼物信息
            if danmaku_state['page_visible']:
                page.run_task(update_ui)
            else:
                # 缓存礼物数据
                cache_data = {
                    'type': 'gift',
                    'username': username,
                    'gift_name': gift_name,
                    'num': num
                }
                # 如果启用答谢，添加答谢标记
                if thank_enabled:
                    cache_data['thank_enabled'] = True
                    cache_data['thank_data'] = {
                        'username': username,
                        'gift_name': gift_name,
                        'num': num
                    }
                
                danmaku_state['danmaku_queue'].append(cache_data)
                # 限制队列长度
                if len(danmaku_state['danmaku_queue']) > 50:
                    danmaku_state['danmaku_queue'].pop(0)
            
        except Exception as e:
            logger.error(f"处理礼物消息失败: {e}")
    
    # 发送答谢消息
    async def send_thank_message(username: str, gift_name: str, num: int):
        """发送答谢弹幕"""
        try:
            if not current_room_id['value'] or not credential:
                return
            
            # 获取答谢模板
            template = app_settings.get('thank_template', '感谢【用户名】赠送的【礼物】×【数量】！')
            
            # 替换占位符
            message = template.replace('【用户名】', username)
            message = message.replace('【礼物】', gift_name)
            message = message.replace('【数量】', str(num))
            
            # 发送答谢弹幕
            room_id_int = int(current_room_id['value'])
            live_room = live.LiveRoom(room_display_id=room_id_int, credential=credential)
            await live_room.send_danmaku(live.Danmaku(message))
            
            logger.info(f"发送答谢弹幕: {message}")
            
            # 添加到弹幕列表（标记为答谢消息）
            thank_item = ft.Row([
                ft.Icon(ft.Icons.FAVORITE, size=16, color=ft.Colors.PINK_500),
                ft.Text(f"[答谢] {message}", size=12, color=ft.Colors.PINK_600),
            ], spacing=5)
            
            danmaku_list.controls.append(thank_item)
            if len(danmaku_list.controls) > 100:
                danmaku_list.controls.pop(0)
            
            danmaku_list.update()
            
        except Exception as e:
            logger.error(f"发送答谢消息失败: {e}")
    
    # 刷新缓存的弹幕到UI
    def flush_danmaku_queue():
        """将缓存队列中的弹幕刷新到UI"""
        if not danmaku_state['danmaku_queue']:
            return
        
        async def update_queued():
            try:
                for item in danmaku_state['danmaku_queue']:
                    if item['type'] == 'danmaku':
                        # 弹幕消息
                        if item['is_self']:
                            name_color = ft.Colors.LIGHT_GREEN_700
                            text_color = ft.Colors.LIGHT_GREEN_600
                        else:
                            name_color = ft.Colors.BLUE_600
                            text_color = ft.Colors.GREY_800
                        
                        danmaku_item = ft.Row([
                            ft.Text(f"{item['username']}:", size=12, weight=ft.FontWeight.BOLD, color=name_color),
                            ft.Text(item['text'], size=12, color=text_color),
                        ], spacing=5)
                    elif item['type'] == 'gift':
                        # 礼物消息
                        danmaku_item = ft.Row([
                            ft.Icon(ft.Icons.CARD_GIFTCARD, size=16, color=ft.Colors.ORANGE_500),
                            ft.Text(f"{item['username']} 赠送了 {item['gift_name']} ×{item['num']}", size=12, color=ft.Colors.ORANGE_600),
                        ], spacing=5)
                        
                        # 处理答谢（如果有）
                        if item.get('thank_enabled') and item.get('thank_data'):
                            thank_data = item['thank_data']
                            await send_thank_message(
                                thank_data['username'],
                                thank_data['gift_name'],
                                thank_data['num']
                            )
                    elif item['type'] == 'ad':
                        # 广告消息
                        danmaku_item = ft.Row([
                            ft.Icon(ft.Icons.CAMPAIGN, size=16, color=ft.Colors.PURPLE_500),
                            ft.Text(f"[广告] {item['text']}", size=12, color=ft.Colors.PURPLE_600),
                        ], spacing=5)
                    else:
                        continue

                    danmaku_list.controls.append(danmaku_item)

                # 限制弹幕数量
                while len(danmaku_list.controls) > 100:
                    danmaku_list.controls.pop(0)

                danmaku_list.update()
                logger.info(f"已刷新 {len(danmaku_state['danmaku_queue'])} 条缓存弹幕")
            except Exception as e:
                logger.error(f"刷新缓存弹幕失败: {e}")
            finally:
                danmaku_state['danmaku_queue'].clear()

        page.run_task(update_queued)
    
    # 设置页面可见性的方法（供外部调用）
    def set_page_visible(visible: bool):
        """设置页面可见性"""
        danmaku_state['page_visible'] = visible
        if visible:
            # 页面变为可见时，刷新缓存的弹幕
            flush_danmaku_queue()
    
    # 发送定时广告
    async def send_advertisement(ad_text: str):
        """发送广告弹幕"""
        try:
            logger.info(f"尝试发送广告弹幕: {ad_text}")
            
            if not current_room_id['value']:
                logger.warning("当前房间号未设置，无法发送广告")
                return
            
            if not credential:
                logger.warning("凭证未设置，无法发送广告")
                return
            
            if not ad_text.strip():
                logger.warning("广告文案为空，跳过发送")
                return
            
            room_id_int = int(current_room_id['value'])
            logger.info(f"创建直播房间对象，房间号: {room_id_int}")
            
            live_room = live.LiveRoom(room_display_id=room_id_int, credential=credential)
            
            logger.info("准备发送广告弹幕...")
            await live_room.send_danmaku(live.Danmaku(ad_text.strip()))
            
            logger.info(f"广告弹幕发送成功: {ad_text}")
            
            # 如果页面可见，直接添加到弹幕列表；否则缓存
            if danmaku_state['page_visible']:
                async def update_ui():
                    try:
                        ad_item = ft.Row([
                            ft.Icon(ft.Icons.CAMPAIGN, size=16, color=ft.Colors.PURPLE_500),
                            ft.Text(f"[广告] {ad_text}", size=12, color=ft.Colors.PURPLE_600),
                        ], spacing=5)
                        
                        danmaku_list.controls.append(ad_item)
                        if len(danmaku_list.controls) > 100:
                            danmaku_list.controls.pop(0)
                        
                        danmaku_list.update()
                        logger.info("广告消息已添加到弹幕列表")
                    except Exception as e:
                        logger.error(f"更新广告UI失败: {e}")
                
                page.run_task(update_ui)
            else:
                # 缓存广告消息
                danmaku_state['danmaku_queue'].append({
                    'type': 'ad',
                    'text': ad_text
                })
                # 限制队列长度
                if len(danmaku_state['danmaku_queue']) > 50:
                    danmaku_state['danmaku_queue'].pop(0)
                logger.info("广告消息已缓存到队列")
            
        except Exception as e:
            logger.error(f"发送广告失败: {e}")
            logger.error(f"详细错误信息: {type(e).__name__}: {str(e)}")
    
    # 启动定时广告
    async def start_advertisements():
        """启动所有定时广告任务"""
        # 清理现有任务
        await stop_advertisements()
        
        ad_enabled = app_settings.get('ad_enabled', False)
        if not ad_enabled:
            logger.info("定时广告功能未启用")
            return
        
        ad_list = app_settings.get('ad_list', [])
        if not ad_list:
            logger.info("广告列表为空")
            return
        
        current_time = asyncio.get_event_loop().time()
        
        for i, ad in enumerate(ad_list):
            if not ad.get('text', '').strip():
                logger.info(f"跳过空广告文案的条目 {i}")
                continue
            
            interval = ad.get('interval', 5)
            unit = ad.get('unit', '分钟')
            ad_text = ad.get('text', '')
            
            # 转换为秒
            if unit == '小时':
                interval_seconds = interval * 3600
            else:  # 分钟
                interval_seconds = interval * 60
            
            # 创建定时任务 - 使用闭包正确捕获变量
            async def ad_task(ad_content, interval_sec):
                logger.info(f"广告任务启动: {ad_content} (间隔: {interval_sec}秒)")
                
                while danmaku_state['is_monitoring']:
                    try:
                        # 每次循环前都检查最新的设置状态
                        current_settings = load_settings()
                        ad_enabled = current_settings.get('ad_enabled', False)
                        
                        if not ad_enabled:
                            logger.info("定时广告已关闭，停止广告任务")
                            break
                        
                        logger.info(f"准备发送广告: {ad_content}")
                        await send_advertisement(ad_content)
                        logger.info(f"广告发送完成，等待 {interval_sec} 秒后再次发送")
                        await asyncio.sleep(interval_sec)
                    except Exception as e:
                        logger.error(f"定时广告任务执行失败: {e}")
                        await asyncio.sleep(60)  # 出错后等待1分钟再重试
            
            # 创建任务时传入当前状态
            task = asyncio.create_task(ad_task(ad_text, interval_seconds))
            danmaku_state['ad_tasks'].append(task)
            logger.info(f"已启动定时广告任务: {ad_text} ({interval} {unit})")
    
    # 停止定时广告
    async def stop_advertisements():
        """停止所有定时广告任务"""
        for task in danmaku_state['ad_tasks']:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        danmaku_state['ad_tasks'].clear()
        logger.info("已停止所有定时广告任务")
    
    # 开始监控函数
    async def start_danmaku_monitoring(room_id: str):
        """开始弹幕监控"""
        
        try:
            # 停止之前的监控
            await stop_danmaku_monitoring()
            
            # 清空弹幕列表
            danmaku_list.controls.clear()

            # 先更新界面，确保ListView已添加到页面
            update_danmaku_container()

            # 创建新的弹幕监控实例
            danmaku_state['live_danmaku'] = live.LiveDanmaku(int(room_id), credential=credential)
            
            # 保存当前房间号，用于发送弹幕
            current_room_id['value'] = room_id
            
            # 注册事件监听器
            danmaku_state['live_danmaku'].add_event_listener('DANMU_MSG', on_danmaku_msg)
            danmaku_state['live_danmaku'].add_event_listener('SEND_GIFT', on_gift)
            
            # 启动监控
            danmaku_state['is_monitoring'] = True
            
            # 启动定时广告
            await start_advertisements()
            
            # 在后台运行连接
            async def connect_danmaku():
                try:
                    # ListView 已经在页面上，可以直接连接
                    logger.info("ListView已就绪，开始连接弹幕服务器")
                    await danmaku_state['live_danmaku'].connect()
                except Exception as e:
                    logger.error(f"弹幕监控连接失败: {e}")
                    danmaku_state['is_monitoring'] = False
                    danmaku_state['listview_ready'] = False
                    status_text.value = f"弹幕监控连接失败: {e}"
                    status_text.color = ft.Colors.RED_500
                    status_text.update()
            
            asyncio.create_task(connect_danmaku())
            
            # 检查定时广告状态
            ad_enabled = app_settings.get('ad_enabled', False)
            ad_status = "（定时广告已启用）" if ad_enabled else ""
            status_text.value = f"弹幕监控已启动{ad_status}"
            status_text.color = ft.Colors.GREEN_500
            status_text.update()
            
        except Exception as e:
            logger.error(f"启动弹幕监控失败: {e}")
            danmaku_state['listview_ready'] = False
            status_text.value = f"启动弹幕监控失败: {e}"
            status_text.color = ft.Colors.RED_500
            status_text.update()
    
    # 停止监控函数
    async def stop_danmaku_monitoring():
        """停止弹幕监控"""
        
        # 停止定时广告
        await stop_advertisements()
        
        if danmaku_state['live_danmaku'] and danmaku_state['is_monitoring']:
            try:
                await danmaku_state['live_danmaku'].disconnect()
                danmaku_state['is_monitoring'] = False
                logger.info("弹幕监控已停止")
            except Exception as e:
                logger.error(f"停止弹幕监控失败: {e}")
            finally:
                danmaku_state['live_danmaku'] = None
                danmaku_state['listview_ready'] = False
    
    # 监控按钮点击事件
    async def on_monitor_click(e):
        room_id = room_input.value.strip() if room_input.value else ""
        if not room_id:
            status_text.value = "请输入房间号"
            status_text.color = ft.Colors.RED_500
            status_text.update()
            return
        
        try:
            int(room_id)  # 验证是否为数字
        except ValueError:
            status_text.value = "房间号必须是数字"
            status_text.color = ft.Colors.RED_500
            status_text.update()
            return
        
        status_text.value = "正在获取直播间信息..."
        status_text.color = ft.Colors.BLUE_500
        status_text.update()
        
        # 获取直播间详情
        result = await get_room_details(room_id)
        
        if result["success"]:
            # 成功获取房间信息
            room_info: object = result["room_info"]
            play_info = result["play_info"]
            
            # 添加到历史记录
            add_room_to_history(room_id)
            
            # 更新下拉框选项
            new_history = load_monitor_history()
            history_dropdown.options = [ft.dropdown.Option(rid) for rid in new_history]
            history_dropdown.update()
            
            # logging.info(f"room_info: {json.dumps(room_info)}")
            # logging.info(f"play_info: {json.dumps(play_info)}")
            # 显示房间信息
            # 根据API文档，数据结构需要访问room_info下的数据
            room_data = room_info.get("room_info", {}) if isinstance(room_info, dict) else {}
            title = room_data.get("title", "未知标题") if isinstance(room_data, dict) else "未知标题"
            anchor_info = room_info.get("anchor_info", {}) if isinstance(room_info, dict) else {}
            base_info = anchor_info.get("base_info", {}) if isinstance(anchor_info, dict) else {}

            uname = base_info.get("uname", "未知主播") if isinstance(base_info, dict) else "未知主播"
            isLive = room_data.get("live_status", 0)
            isLiveText = "开播中" if isLive == 1 else "未开播"
            # 状态指示灯颜色：开播绿色，未开播红色
            live_status_color = ft.Colors.GREEN_500 if isLive == 1 else ft.Colors.RED_500
            # 从room_play_info获取在线人数和关键帧
            online = play_info.get("online", 0) if isinstance(play_info, dict) else 0
            keyframe = room_data.get("cover", "") if isinstance(room_data, dict) else ""
            
            room_info_content: list[ft.Control] = [
                ft.Text("直播间信息", size=18, weight=ft.FontWeight.BOLD),
                ft.Container(height=10),
                ft.Text(f"房间号: {room_id}"),
                ft.Text(f"标题: {title}"),
                ft.Text(f"主播: {uname}"),
                ft.Row([
                    ft.Text("状态: "),
                    ft.Icon(ft.Icons.CIRCLE, size=12, color=live_status_color),
                    ft.Text(isLiveText, color=live_status_color, weight=ft.FontWeight.BOLD),
                ], spacing=5)
            ]
            
            # 如果有关键帧图片，添加图片
            if keyframe:
                room_info_content.append(ft.Container(height=10))
                room_info_content.append(
                    ft.Image(
                        src=keyframe,
                        width=200,
                        height=150,
                        fit=ft.ImageFit.CONTAIN,
                    )
                )
            
            room_info_container.content = ft.Column(room_info_content)
            room_info_container.visible = True
            room_info_container.update()
            
            status_text.value = "获取直播间信息成功！"
            status_text.color = ft.Colors.GREEN_500
            status_text.update()
            
            # 启动弹幕监控
            await start_danmaku_monitoring(room_id)
            
        else:
            # 获取失败
            error_msg = result.get("error", "未知错误")
            status_text.value = f"获取直播间信息失败: {error_msg}"
            status_text.color = ft.Colors.RED_500
            status_text.update()
            
            room_info_container.visible = False
            room_info_container.update()
    
    # 停止监控按钮点击事件
    async def on_stop_monitor_click(e):
        await stop_danmaku_monitoring()
        
        # 重置状态文本
        danmaku_status_text.value = "未开始监控"
        danmaku_status_text.color = ft.Colors.GREY_500
        danmaku_status_text.update()
        
        status_text.value = "弹幕监控已停止"
        status_text.color = ft.Colors.GREY_500
        status_text.update()
    
    # 监控按钮
    monitor_button = ft.ElevatedButton(
        text="开始监控",
        icon=ft.Icons.PLAY_ARROW,
        on_click=on_monitor_click,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.GREEN,
            color=ft.Colors.WHITE,
        ),
    )
    
    # 停止监控按钮
    stop_button = ft.ElevatedButton(
        text="停止监控",
        icon=ft.Icons.STOP,
        on_click=on_stop_monitor_click,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.RED,
            color=ft.Colors.WHITE,
        ),
    )
    
    # 创建容器 - 使用Row布局将监控区域和弹幕区域并排显示
    monitor_row = ft.Row(
        [
            # 左侧：监控控制区域
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("直播监控", size=24, weight=ft.FontWeight.BOLD),
                        ft.Container(height=20),
                        room_input,
                        ft.Container(height=10),
                        history_dropdown,
                        ft.Container(height=20),
                        ft.Row(
                            [monitor_button, stop_button],
                            spacing=10,
                            alignment=ft.MainAxisAlignment.START,
                        ),
                        ft.Container(height=10),
                        status_text,
                        ft.Container(height=20),
                        room_info_container,
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    horizontal_alignment=ft.CrossAxisAlignment.START,
                    scroll=ft.ScrollMode.AUTO,
                ),
                padding=30,
                expand=1,
            ),
            # 右侧：弹幕监控区域
            danmaku_container,
        ],
        expand=True,
        spacing=20,
    )
    
    # 将 set_page_visible 方法附加到返回的组件上，供外部调用
    setattr(monitor_row, 'set_page_visible', set_page_visible)
    
    # 将广告控制方法附加到返回的组件上，供设置页面调用
    def ad_control_callback_wrapper(enable: bool):
        """广告控制回调包装函数"""
        if danmaku_state['is_monitoring']:
            if enable:
                logger.info("广告开关打开，启动广告任务")
                page.run_task(start_advertisements)
            else:
                logger.info("广告开关关闭，停止广告任务")
                page.run_task(stop_advertisements)
    
    setattr(monitor_row, 'ad_control_callback', ad_control_callback_wrapper)
    
    return monitor_row


def create_settings_page(page: ft.Page):
    """创建设置页面"""
    global app_settings
    
    # 答谢开关
    thank_switch = ft.Switch(
        label="自动答谢礼物",
        value=app_settings.get('thank_enabled', False),
        on_change=lambda e: update_setting('thank_enabled', e.control.value)
    )
    
    # 答谢模板
    thank_template = ft.TextField(
        label="答谢模板",
        value=app_settings.get('thank_template', '感谢【用户名】赠送的【礼物】×【数量】！'),
        helper_text="可使用占位符：【用户名】【礼物】【数量】",
        multiline=True,
        min_lines=2,
        max_lines=3,
        width=400,
        on_blur=lambda e: update_setting('thank_template', e.control.value)
    )
    
    # 定时广告开关
    def on_ad_switch_change(e):
        """广告开关变化处理"""
        update_setting('ad_enabled', e.control.value)
        # 通知监控页面广告开关状态变化
        execute_ad_control_callback(e.control.value)
    
    ad_switch = ft.Switch(
        label="定时广告广播",
        value=app_settings.get('ad_enabled', False),
        on_change=on_ad_switch_change
    )
    
    # 广告列表容器
    ad_list_container = ft.Container(
        content=ft.Column([]),
        padding=10,
        border=ft.border.all(1, ft.Colors.GREY_300),
        border_radius=5,
        width=500,
    )
    
    # 添加广告条目
    def add_ad_item():
        def remove_ad_item(index):
            ad_list = app_settings.get('ad_list', [])
            if 0 <= index < len(ad_list):
                ad_list.pop(index)
                update_setting('ad_list', ad_list)
                refresh_ad_list()
        
        def save_ad_item(index, interval, unit, text):
            ad_list = app_settings.get('ad_list', [])
            # 扩展列表到足够长度
            while len(ad_list) <= index:
                ad_list.append({'interval': 5, 'unit': '分钟', 'text': ''})
            
            ad_list[index] = {
                'interval': int(interval) if interval else 5,
                'unit': unit,
                'text': text
            }
            update_setting('ad_list', ad_list)
        
        ad_list = app_settings.get('ad_list', [])
        if not ad_list:
            # 如果列表为空，添加一个默认条目
            ad_list = [{'interval': 5, 'unit': '分钟', 'text': ''}]
            update_setting('ad_list', ad_list)
        
        refresh_ad_list()
    
    # 刷新广告列表
    def refresh_ad_list():
        ad_list = app_settings.get('ad_list', [])
        items = []
        
        for i, ad in enumerate(ad_list):
            interval_input = ft.TextField(
                label="间隔",
                value=str(ad.get('interval', 5)),
                width=80,
                keyboard_type=ft.KeyboardType.NUMBER,
            )
            
            unit_dropdown = ft.Dropdown(
                label="单位",
                value=ad.get('unit', '分钟'),
                width=100,
                options=[
                    ft.dropdown.Option("分钟"),
                    ft.dropdown.Option("小时"),
                ]
            )
            
            text_input = ft.TextField(
                label="广告文案",
                value=ad.get('text', ''),
                expand=True,
            )
            
            remove_button = ft.IconButton(
                icon=ft.Icons.DELETE,
                icon_color=ft.Colors.RED_500,
                tooltip="删除",
                on_click=lambda e, idx=i: (
                    current_list := app_settings.get('ad_list', []),
                    current_list.pop(idx),
                    update_setting('ad_list', current_list),
                    refresh_ad_list()
                )
            )
            
            # 保存按钮
            save_button = ft.IconButton(
                icon=ft.Icons.SAVE,
                icon_color=ft.Colors.GREEN_500,
                tooltip="保存",
                on_click=lambda e, idx=i, inter=interval_input, unit=unit_dropdown, txt=text_input: (
                    update_setting('ad_list', update_ad_item(idx, inter.value, unit.value, txt.value))
                )
            )
            
            ad_row = ft.Row([
                interval_input,
                unit_dropdown,
                text_input,
                save_button,
                remove_button
            ], spacing=10)
            
            items.append(ad_row)
        
        ad_list_container.content = ft.Column(items, spacing=10)
        # 只有当容器已经在页面中时才更新
        try:
            ad_list_container.update()
        except AssertionError:
            # 容器还未添加到页面，跳过更新
            pass
    
    def update_ad_item(index, interval, unit, text):
        ad_list = app_settings.get('ad_list', [])
        while len(ad_list) <= index:
            ad_list.append({'interval': 5, 'unit': '分钟', 'text': ''})
        
        ad_list[index] = {
            'interval': int(interval) if interval else 5,
            'unit': unit,
            'text': text
        }
        return ad_list
    
    # 更新设置
    def update_setting(key: str, value):
        global app_settings
        app_settings[key] = value
        save_settings(app_settings)
    
    # 初始化广告列表内容
    def init_ad_list():
        ad_list = app_settings.get('ad_list', [])
        if not ad_list:
            ad_list = [{'interval': 5, 'unit': '分钟', 'text': ''}]
            app_settings['ad_list'] = ad_list
            save_settings(app_settings)
        
        items = []
        for i, ad in enumerate(ad_list):
            interval_input = ft.TextField(
                label="间隔",
                value=str(ad.get('interval', 5)),
                width=80,
                keyboard_type=ft.KeyboardType.NUMBER,
            )
            
            unit_dropdown = ft.Dropdown(
                label="单位",
                value=ad.get('unit', '分钟'),
                width=100,
                options=[
                    ft.dropdown.Option("分钟"),
                    ft.dropdown.Option("小时"),
                ]
            )
            
            text_input = ft.TextField(
                label="广告文案",
                value=ad.get('text', ''),
                expand=True,
            )
            
            def make_delete_handler(idx):
                def delete_clicked(e):
                    current_list = app_settings.get('ad_list', [])
                    current_list.pop(idx)
                    update_setting('ad_list', current_list)
                    init_ad_list()
                return delete_clicked
            
            def make_save_handler(idx, inter, unit, txt):
                def save_clicked(e):
                    updated_list = update_ad_item(idx, inter.value, unit.value, txt.value)
                    update_setting('ad_list', updated_list)
                    init_ad_list()
                return save_clicked
            
            remove_button = ft.IconButton(
                icon=ft.Icons.DELETE,
                icon_color=ft.Colors.RED_500,
                tooltip="删除",
                on_click=make_delete_handler(i)
            )
            
            save_button = ft.IconButton(
                icon=ft.Icons.SAVE,
                icon_color=ft.Colors.GREEN_500,
                tooltip="保存",
                on_click=make_save_handler(i, interval_input, unit_dropdown, text_input)
            )
            
            ad_row = ft.Row([
                interval_input,
                unit_dropdown,
                text_input,
                save_button,
                remove_button
            ], spacing=10)
            
            items.append(ad_row)
        
        ad_list_container.content = ft.Column(items, spacing=10)
        try:
            ad_list_container.update()
        except AssertionError:
            pass
    
    def add_ad_clicked(e):
        current_ad_list = app_settings.get('ad_list', [])
        current_ad_list.append({'interval': 5, 'unit': '分钟', 'text': ''})
        update_setting('ad_list', current_ad_list)
        init_ad_list()
    
    # 添加广告按钮
    add_ad_button = ft.ElevatedButton(
        text="添加广告",
        icon=ft.Icons.ADD,
        on_click=add_ad_clicked
    )
    
    # 手动初始化广告列表内容
    items = []
    ad_list = app_settings.get('ad_list', [])
    for i, ad in enumerate(ad_list):
        interval_input = ft.TextField(
            label="间隔",
            value=str(ad.get('interval', 5)),
            width=80,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        unit_dropdown = ft.Dropdown(
            label="单位",
            value=ad.get('unit', '分钟'),
            width=100,
            options=[
                ft.dropdown.Option("分钟"),
                ft.dropdown.Option("小时"),
            ]
        )
        
        text_input = ft.TextField(
            label="广告文案",
            value=ad.get('text', ''),
            expand=True,
        )
        
        def delete_clicked(e, idx):
            current_list = app_settings.get('ad_list', [])
            current_list.pop(idx)
            update_setting('ad_list', current_list)
            refresh_ad_list()
        
        remove_button = ft.IconButton(
            icon=ft.Icons.DELETE,
            icon_color=ft.Colors.RED_500,
            tooltip="删除",
            on_click=lambda e, idx=i: delete_clicked(e, idx)
        )
        
        # 保存按钮
        def save_clicked(e, idx, inter, unit, txt):
            updated_list = update_ad_item(idx, inter.value, unit.value, txt.value)
            update_setting('ad_list', updated_list)
            refresh_ad_list()
        
        save_button = ft.IconButton(
            icon=ft.Icons.SAVE,
            icon_color=ft.Colors.GREEN_500,
            tooltip="保存",
            on_click=lambda e, idx=i, inter=interval_input, unit=unit_dropdown, txt=text_input: save_clicked(e, idx, inter, unit, txt)
        )
        
        ad_row = ft.Row([
            interval_input,
            unit_dropdown,
            text_input,
            save_button,
            remove_button
        ], spacing=10)
        
        items.append(ad_row)
    
    ad_list_container.content = ft.Column(items, spacing=10)
    
    settings_container = ft.Container(
        content=ft.Column(
            [
                ft.Text("设置", size=24, weight=ft.FontWeight.BOLD),
                ft.Container(height=20),
                
                # 答谢设置区域
                ft.Container(
                    content=ft.Column([
                        ft.Text("答谢设置", size=18, weight=ft.FontWeight.BOLD),
                        ft.Container(height=10),
                        thank_switch,
                        ft.Container(height=10),
                        thank_template,
                        ft.Container(
                            content=ft.Text("模板示例：感谢【用户名】赠送的【礼物】×【数量】！", 
                                          size=12, color=ft.Colors.GREY_600),
                            padding=10,
                            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.BLUE_GREY_50),
                            border_radius=5
                        ),
                    ]),
                    padding=15,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    border_radius=10,
                ),
                
                ft.Container(height=20),
                
                # 定时广告设置区域
                ft.Container(
                    content=ft.Column([
                        ft.Text("定时广告设置", size=18, weight=ft.FontWeight.BOLD),
                        ft.Container(height=10),
                        ad_switch,
                        ft.Container(height=10),
                        ft.Text("广告列表", size=14, weight=ft.FontWeight.BOLD),
                        ft.Container(height=5),
                        ad_list_container,
                        ft.Container(height=10),
                        add_ad_button,
                    ]),
                    padding=15,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    border_radius=10,
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.START,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=30,
        expand=True,
    )
    
    return settings_container


def show_main_ui(page: ft.Page):
    """显示主界面"""

    # 获取用户信息
    async def load_user_info():
        uid, username, avatar_url = await get_current_user_info()
        if username:
            user_name.value = username
            user_name.update()
        if avatar_url:
            user_avatar.foreground_image_src = avatar_url
            user_avatar.update()
        if uid:
            # 现在你可以用这个 uid 创建 User 对象
            logger.info(f"可以使用 uid {uid} 来初始化 user.User 对象")

    # 用户头像区域
    user_avatar = ft.CircleAvatar(
        foreground_image_src="https://picsum.photos/seed/bilibili/200/200.jpg",
        radius=30,
    )
    
    user_name = ft.Text(
        "B站用户",
        size=14,
        weight=ft.FontWeight.BOLD,
    )
    
    # 创建用户信息内容
    user_info_content = ft.Column(
        [
            user_avatar,
            ft.Container(height=10),
            user_name,
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )
    
    # 创建弹出菜单按钮，将整个用户信息区域作为内容
    popup_menu_button = ft.PopupMenuButton(
        content=user_info_content,
        tooltip="",  # 移除悬浮提示
        items=[
            ft.PopupMenuItem(
                text="注销",
                on_click=lambda e: handle_popup_menu_selected(e),
            ),
        ],
    )
    
    # 预先创建所有页面，保持状态
    monitor_page = create_monitor_page(page)
    settings_page = create_settings_page(page)
    
    # 注册监控页面的广告控制回调
    if hasattr(monitor_page, 'ad_control_callback'):
        register_ad_control_callback(getattr(monitor_page, 'ad_control_callback'))
    
    # 页面列表，索引对应导航栏选项
    pages = [monitor_page, settings_page]
    
    # 内容区域容器 - 用于切换页面
    content_container = ft.Column(
        [monitor_page],  # 默认显示监控页面
        alignment=ft.MainAxisAlignment.START,
        expand=True,
    )
    
    # 页面切换处理函数
    def on_nav_change(e):
        selected_index = e.control.selected_index
        # 更新内容区域显示的页面
        content_container.controls.clear()
        content_container.controls.append(pages[selected_index])
        content_container.update()
        
        # 通知监控页面可见性变化
        if hasattr(monitor_page, 'set_page_visible'):
            getattr(monitor_page, 'set_page_visible')(selected_index == 0)
        
        logger.info(f"切换到页面: {['监控', '设置'][selected_index]}")
    
    # 左侧导航栏内容
    navigation_content = ft.Column(
        [
            # 用户信息区
            ft.Container(
                content=popup_menu_button,
                padding=20,
                bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.BLUE_GREY_50),
                border_radius=10,
                animate=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
                on_hover=lambda e: (
                    setattr(e.control, 'bgcolor', ft.Colors.with_opacity(0.12, ft.Colors.BLUE_GREY_200)),
                    e.control.update()
                ) if e.data == "true" else (
                    setattr(e.control, 'bgcolor', ft.Colors.with_opacity(0.05, ft.Colors.BLUE_GREY_50)),
                    e.control.update()
                ),
            ),
            ft.Divider(),
            # 导航菜单
            ft.NavigationRail(
                selected_index=0,
                label_type=ft.NavigationRailLabelType.ALL,
                min_width=80,
                min_extended_width=200,
                expand=True,
                destinations=[
                    ft.NavigationRailDestination(
                        icon=ft.Icons.MONITOR,
                        selected_icon=ft.Icons.MONITOR,
                        label="监控",
                    ),
                    ft.NavigationRailDestination(
                        icon=ft.Icons.SETTINGS_OUTLINED,
                        selected_icon=ft.Icons.SETTINGS,
                        label="设置",
                    ),
                ],
                on_change=on_nav_change,
            ),
        ],
        expand=True,
    )
    
    page.add(
        ft.Row(
            [
                # 左侧导航栏，固定宽度为 1/5
                ft.Container(
                    content=navigation_content,
                    width=240,  # 设置固定宽度（1200 * 1/5 = 240）
                ),
                ft.VerticalDivider(width=1),
                # 右侧内容区域，占据剩余空间
                content_container,
            ],
            expand=True,
        )
    )
    
    # 启动用户信息加载
    asyncio.create_task(load_user_info())


async def main(page: ft.Page):
    page.title = "Bilibili Agent"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window.width = 1200
    page.window.height = 800
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    
    logger.info("应用启动，检查登录状态...")
    
    # 尝试从本地加载凭证
    loaded_cred = load_credential()
    
    # 检查是否有有效凭证
    if is_credential_valid():
        logger.info("检测到有效凭证，显示主界面")
        show_main_ui(page)
    else:
        logger.info("未登录或凭证已过期，显示登录二维码界面")
        show_login_ui(page)


ft.app(main)
"""
监控页面模块
"""
import logging

import flet as ft

from src.services.danmaku import DanmakuService
from src.config.settings import MonitorHistoryManager, app_settings
from src.core.auth import auth_manager
from src.constants import (
    DANMAKU_MAX_COUNT, DANMAKU_QUEUE_MAX_SIZE, COLOR_LIGHT_GREEN_700,
    COLOR_LIGHT_GREEN_600, COLOR_BLUE_600, COLOR_GREY_800,
    COLOR_ORANGE_500, COLOR_ORANGE_600, COLOR_PINK_500, COLOR_PINK_600,
    COLOR_PURPLE_500, COLOR_PURPLE_600, COLOR_GREEN_500, COLOR_RED_500,
    COLOR_GREY_500, COLOR_BLUE_GREY_50
)

logger = logging.getLogger(__name__)


def create_monitor_page(page: ft.Page):
    """创建监控页面"""
    danmaku_service = DanmakuService(page)
    
    # 加载历史记录
    history_room_ids = MonitorHistoryManager.load()
    
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
            page.run_task(on_monitor_click)
    
    # 历史记录下拉框
    history_dropdown = ft.Dropdown(
        label="历史监控房间号",
        width=300,
        options=[ft.dropdown.Option(room_id) for room_id in history_room_ids],
        on_change=on_history_change,
    )
    
    # 状态文本
    status_text = ft.Text("", size=14, color=ft.Colors.GREY_600)
    
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
    
    # 发送弹幕输入框
    danmaku_input = ft.TextField(
        label="发送弹幕",
        hint_text="输入弹幕内容...",
        expand=True,
        on_submit=lambda e: page.run_task(send_danmaku),
    )
    
    # 发送弹幕函数
    async def send_danmaku(e=None):
        """发送弹幕"""
        danmaku_text = danmaku_input.value.strip() if danmaku_input.value else ""
        if not danmaku_text:
            return
        
        await danmaku_service.send_danmaku(danmaku_text)
        
        danmaku_input.value = ""
        danmaku_input.update()
    
    # 发送按钮
    send_button = ft.IconButton(
        icon=ft.Icons.SEND,
        icon_color=ft.Colors.BLUE_500,
        tooltip="发送弹幕",
        on_click=lambda e: page.run_task(send_danmaku),
    )
    
    # 发送弹幕区域
    send_danmaku_row = ft.Row([danmaku_input, send_button], spacing=5)
    
    # 弹幕监控区域
    danmaku_container = ft.Container(
        content=ft.Column([
            ft.Text("弹幕监控", size=18, weight=ft.FontWeight.BOLD),
            ft.Container(height=5),
            danmaku_status_text,
            ft.Container(height=5),
            ft.Container(
                content=danmaku_list,
                expand=True,
                border=ft.border.all(1, ft.Colors.GREY_300),
                border_radius=5,
                padding=10,
            ),
            ft.Container(height=10),
            send_danmaku_row,
        ], expand=True),
        visible=True,
        padding=20,
        bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.BLUE_GREY_50),
        border_radius=10,
        width=400,
        expand=True,
    )
    
    # 弹幕事件处理函数
    def on_danmaku_msg(event: dict) -> None:
        """处理弹幕消息"""
        try:
            if not danmaku_service.state.listview_ready:
                return
            
            info = event.get('data', {}).get('info', [])
            if len(info) >= 2:
                user_info = info[2]
                danmaku_text = info[1]
                username = user_info[1] if len(user_info) > 1 else "未知用户"
                user_uid = str(user_info[0]) if len(user_info) > 0 else ""
                
                is_self = user_uid == (auth_manager.credential.dedeuserid if auth_manager.credential else "")
                
                async def update_ui():
                    try:
                        if is_self:
                            name_color = COLOR_LIGHT_GREEN_700
                            text_color = COLOR_LIGHT_GREEN_600
                        else:
                            name_color = COLOR_BLUE_600
                            text_color = COLOR_GREY_800
                        
                        danmaku_item = ft.Row([
                            ft.Text(f"{username}:", size=12, weight=ft.FontWeight.BOLD, color=name_color),
                            ft.Text(danmaku_text, size=12, color=text_color),
                        ], spacing=5)
                        
                        danmaku_list.controls.append(danmaku_item)
                        
                        if len(danmaku_list.controls) > DANMAKU_MAX_COUNT:
                            danmaku_list.controls.pop(0)
                        
                        danmaku_list.update()
                        logger.info(f"弹幕: {username} - {danmaku_text}{' [我]' if is_self else ''}")
                    except Exception as e:
                        logger.error(f"更新弹幕UI失败: {e}")
                
                if danmaku_service.state.page_visible:
                    page.run_task(update_ui)
                else:
                    danmaku_service.state.danmaku_queue.append({
                        'type': 'danmaku',
                        'username': username,
                        'text': danmaku_text,
                        'is_self': is_self
                    })
                    if len(danmaku_service.state.danmaku_queue) > DANMAKU_QUEUE_MAX_SIZE:
                        danmaku_service.state.danmaku_queue.pop(0)
        except Exception as e:
            logger.error(f"处理弹幕消息失败: {e}")
    
    # 礼物事件处理函数
    def on_gift(event: dict) -> None:
        """处理礼物消息"""
        try:
            if not danmaku_service.state.listview_ready:
                return
            
            data = event.get('data', {})
            data_detail: Any = data.get('data', {})
            gift_name = data_detail.get('giftName', '未知礼物')
            username = data_detail.get('uname', '未知用户')
            num = data_detail.get('num', 1)
            
            thank_enabled = app_settings.get('thank_enabled', False)
            
            async def update_ui():
                try:
                    gift_item = ft.Row([
                        ft.Icon(ft.Icons.CARD_GIFTCARD, size=16, color=COLOR_ORANGE_500),
                        ft.Text(f"{username} 赠送了 {gift_name} ×{num}", size=12, color=COLOR_ORANGE_600),
                    ], spacing=5)
                    
                    danmaku_list.controls.append(gift_item)
                    
                    if len(danmaku_list.controls) > DANMAKU_MAX_COUNT:
                        danmaku_list.controls.pop(0)
                    
                    danmaku_list.update()
                    logger.info(f"礼物: {username} - {gift_name} ×{num}")
                    
                    if thank_enabled:
                        await danmaku_service.send_thank_message(username, gift_name, num)
                except Exception as e:
                    logger.error(f"更新礼物UI失败: {e}")
            
            if danmaku_service.state.page_visible:
                page.run_task(update_ui)
            else:
                cache_data = {
                    'type': 'gift',
                    'username': username,
                    'gift_name': gift_name,
                    'num': num
                }
                if thank_enabled:
                    cache_data['thank_enabled'] = True
                    cache_data['thank_data'] = {
                        'username': username,
                        'gift_name': gift_name,
                        'num': num
                    }
                
                danmaku_service.state.danmaku_queue.append(cache_data)
                if len(danmaku_service.state.danmaku_queue) > DANMAKU_QUEUE_MAX_SIZE:
                    danmaku_service.state.danmaku_queue.pop(0)
        except Exception as e:
            logger.error(f"处理礼物消息失败: {e}")
    
    # 开始监控函数
    async def on_monitor_click(e=None):
        """开始监控"""
        room_id = room_input.value.strip() if room_input.value else ""
        if not room_id:
            status_text.value = "请输入房间号"
            status_text.color = ft.Colors.RED_500
            status_text.update()
            return
        
        try:
            int(room_id)
        except ValueError:
            status_text.value = "房间号必须是数字"
            status_text.color = ft.Colors.RED_500
            status_text.update()
            return
        
        status_text.value = "正在获取直播间信息..."
        status_text.color = ft.Colors.BLUE_500
        status_text.update()
        
        # 获取直播间详情
        result = await danmaku_service.get_room_details(room_id)
        
        if result["success"]:
            # 成功获取房间信息
            room_info = result["room_info"]
            play_info = result["play_info"]
            
            # 添加到历史记录
            MonitorHistoryManager.add(room_id)
            
            # 更新下拉框选项
            new_history = MonitorHistoryManager.load()
            history_dropdown.options = [ft.dropdown.Option(rid) for rid in new_history]
            history_dropdown.update()
            
            # 显示房间信息
            room_data = room_info.get("room_info", {}) if isinstance(room_info, dict) else {}
            title = room_data.get("title", "未知标题") if isinstance(room_data, dict) else "未知标题"
            anchor_info = room_info.get("anchor_info", {}) if isinstance(room_info, dict) else {}
            base_info = anchor_info.get("base_info", {}) if isinstance(anchor_info, dict) else {}
            uname = base_info.get("uname", "未知主播") if isinstance(base_info, dict) else "未知主播"
            isLive = room_data.get("live_status", 0)
            isLiveText = "开播中" if isLive == 1 else "未开播"
            live_status_color = COLOR_GREEN_500 if isLive == 1 else COLOR_RED_500
            online = play_info.get("online", 0) if isinstance(play_info, dict) else 0
            keyframe = room_data.get("cover", "") if isinstance(room_data, dict) else ""
            
            room_info_content = [
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
            await danmaku_service.start_monitoring(room_id, on_danmaku_msg, on_gift)

            # 更新弹幕监控状态文本
            ad_enabled = app_settings.get('ad_enabled', False)
            ad_status = "（定时广告已启用）" if ad_enabled else ""
            danmaku_status_text.value = f"弹幕监控已启动{ad_status}"
            danmaku_status_text.color = ft.Colors.GREEN_500
            danmaku_status_text.update()
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
        await danmaku_service.stop_monitoring()
        
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
    
    # 创建容器
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
    
    # 附加方法供外部调用
    setattr(monitor_row, 'set_page_visible', danmaku_service.set_page_visible)
    setattr(monitor_row, 'ad_control_callback', danmaku_service.start_advertisements)
    
    return monitor_row

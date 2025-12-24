"""
主界面模块
"""
import asyncio
import logging

import flet as ft

from src.core.auth import auth_manager
from src.ui.pages.monitor import create_monitor_page
from src.ui.pages.settings import create_settings_page
from src.constants import NAVIGATION_WIDTH

logger = logging.getLogger(__name__)


def handle_popup_menu_selected(e):
    """处理弹出菜单选择"""
    current_page = e.control.page
    if e.control.text == "注销":
        handle_logout(current_page)


def handle_logout(page: ft.Page):
    """处理用户注销"""
    logger.info("用户请求注销...")
    
    # 清除本地凭证
    auth_manager.clear_credential()
    
    # 重新生成新的二维码登录实例
    auth_manager.create_qr_login()
    
    # 重新加载页面并生成二维码
    page.clean()
    from src.ui.pages.login import show_login_ui
    show_login_ui(page)


def show_main_ui(page: ft.Page):
    """显示主界面"""

    # 获取用户信息
    async def load_user_info():
        uid, username, avatar_url = await auth_manager.get_current_user_info()
        if username:
            user_name.value = username
            user_name.update()
        if avatar_url:
            user_avatar.foreground_image_src = avatar_url
            user_avatar.update()
        if uid:
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
    
    # 创建弹出菜单按钮
    popup_menu_button = ft.PopupMenuButton(
        content=user_info_content,
        tooltip="",
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
    
    # 页面列表
    pages = [monitor_page, settings_page]
    
    # 内容区域容器
    content_container = ft.Column(
        [monitor_page],
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
                # 左侧导航栏，固定宽度
                ft.Container(
                    content=navigation_content,
                    width=NAVIGATION_WIDTH,
                ),
                ft.VerticalDivider(width=1),
                # 右侧内容区域
                content_container,
            ],
            expand=True,
        )
    )
    
    # 启动用户信息加载
    asyncio.create_task(load_user_info())

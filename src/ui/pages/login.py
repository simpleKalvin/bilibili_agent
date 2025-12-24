"""
登录页面模块
"""
import asyncio
import logging

import flet as ft

from src.core.auth import auth_manager
from src.utils.image import picture_to_base64_data_uri
from src.config.settings import ConfigManager, CACHE_DURATION_HOURS

logger = logging.getLogger(__name__)


async def check_login_status(page: ft.Page, login_container: ft.Column):
    """后台检查登录状态"""
    logger.info("开始检查登录状态...")
    qr = auth_manager.qr
    
    while not qr.has_done():
        result = await qr.check_state()
        logger.info(f"登录状态检查: {result}")
        await asyncio.sleep(1)
    
    # 登录成功，保存凭证
    cred = qr.get_credential()
    if auth_manager.save_credential(cred):
        logger.info("凭证已缓存到本地")
    
    # 切换到主界面
    logger.info("登录成功！切换到主界面")
    page.remove(login_container)
    
    # 导入主界面（避免循环导入）
    from src.ui.pages.main import show_main_ui
    show_main_ui(page)


def show_login_ui(page: ft.Page):
    """显示登录界面"""
    # 生成二维码
    async def generate_qr():
        logger.info("开始生成二维码...")
        qr = auth_manager.create_qr_login()
        await qr.generate_qrcode()
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
        src="https://picsum.photos/seed/placeholder/200/200.jpg",
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

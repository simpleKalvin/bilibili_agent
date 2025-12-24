"""
Bilibili Agent 应用入口
"""
import logging
import flet as ft

from src.core.auth import auth_manager
from src.ui.pages.login import show_login_ui
from src.ui.pages.main import show_main_ui
from src.constants import WINDOW_WIDTH, WINDOW_HEIGHT

logger = logging.getLogger(__name__)


async def main(page: ft.Page):
    """应用主函数"""
    page.title = "Bilibili Agent"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window.width = WINDOW_WIDTH
    page.window.height = WINDOW_HEIGHT
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    
    logger.info("应用启动，检查登录状态...")
    
    # 尝试从本地加载凭证
    auth_manager.load_credential()
    
    # 检查是否有有效凭证
    if auth_manager.is_credential_valid():
        logger.info("检测到有效凭证，显示主界面")
        show_main_ui(page)
    else:
        logger.info("未登录或凭证已过期，显示登录二维码界面")
        show_login_ui(page)


if __name__ == '__main__':
    ft.app(main)

"""
日志配置模块
"""
import logging
from src.constants import WINDOW_WIDTH, WINDOW_HEIGHT

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

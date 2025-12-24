"""
图片处理工具模块
"""
import base64
import tempfile
import os
import asyncio
import logging
from bilibili_api import Picture

logger = logging.getLogger(__name__)


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

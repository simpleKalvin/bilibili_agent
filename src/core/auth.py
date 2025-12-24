"""
认证管理模块
处理 Bilibili 登录认证相关逻辑
"""
import os
import json
import logging
from datetime import datetime
from bilibili_api import login_v2, Credential, user

from src.config.settings import CREDENTIALS_FILE, ConfigManager, CACHE_DURATION_HOURS

logger = logging.getLogger(__name__)


class AuthManager:
    """认证管理器"""

    def __init__(self):
        self.credential: Credential | None = None
        self.qr = None

    def create_qr_login(self) -> login_v2.QrCodeLogin:
        """创建二维码登录实例"""
        self.qr = login_v2.QrCodeLogin(platform=login_v2.QrCodeLoginChannel.WEB)
        return self.qr

    def load_credential(self) -> Credential | None:
        """从本地加载凭证"""
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
                    self.clear_credential()
                    return None
            
            # 创建Credential对象
            self.credential = Credential(
                sessdata=data.get('sessdata'),
                bili_jct=data.get('bili_jct'),
                dedeuserid=data.get('dedeuserid'),
                ac_time_value=data.get('ac_time_value')
            )
            
            logger.info("凭证加载成功")
            return self.credential
        
        except Exception as e:
            logger.error(f"加载凭证失败: {e}")
            self.clear_credential()
            return None

    def save_credential(self, cred: Credential) -> bool:
        """保存凭证到本地"""
        try:
            # 计算过期时间
            from datetime import timedelta
            expires_at = (datetime.now() + timedelta(hours=CACHE_DURATION_HOURS)).timestamp()
            
            data = {
                'sessdata': cred.sessdata,
                'bili_jct': cred.bili_jct,
                'dedeuserid': cred.dedeuserid,
                'ac_time_value': cred.ac_time_value,
                'expires_at': expires_at
            }
            
            result = ConfigManager.save_json_file(CREDENTIALS_FILE, data, secure=True)
            
            if result:
                self.credential = cred
                logger.info(f"凭证已保存，将在 {CACHE_DURATION_HOURS} 小时后过期")
            
            return result
        
        except Exception as e:
            logger.error(f"保存凭证失败: {e}")
            return False

    def clear_credential(self) -> bool:
        """清除本地凭证"""
        try:
            if os.path.exists(CREDENTIALS_FILE):
                os.remove(CREDENTIALS_FILE)
                logger.info("凭证文件已删除")
            
            self.credential = None
            return True
        
        except Exception as e:
            logger.error(f"清除凭证失败: {e}")
            return False

    def is_credential_valid(self) -> bool:
        """检查当前凭证是否有效"""
        if self.credential is None:
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

    async def get_current_user_info(self) -> tuple[int | None, str | None, str | None]:
        """
        获取当前登录用户信息
        
        Returns:
            (uid, username, avatar_url)
        """
        if not self.credential:
            return None, None, None
        
        try:
            my_info = await user.get_self_info(self.credential)
            uid = my_info['mid']
            username = my_info['name']
            avatar_url = my_info['face']
            logger.info(f"用户信息 - UID: {uid}, 用户名: {username}, 头像: {avatar_url}")
            return uid, username, avatar_url
        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            return None, None, None


# 全局认证管理器实例
auth_manager = AuthManager()

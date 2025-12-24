"""
弹幕服务模块
处理弹幕监控、礼物处理、广告发送等业务逻辑
"""
import asyncio
import logging
import json
from typing import Any, Callable

import flet as ft
from bilibili_api import live, Credential

from src.config.settings import app_settings
from src.core.auth import auth_manager
from src.constants import (
    DANMAKU_MAX_COUNT, DANMAKU_QUEUE_MAX_SIZE,
    COLOR_LIGHT_GREEN_700, COLOR_LIGHT_GREEN_600, COLOR_BLUE_600,
    COLOR_GREY_800, COLOR_ORANGE_500, COLOR_ORANGE_600,
    COLOR_PURPLE_500, COLOR_PURPLE_600, COLOR_PINK_500, COLOR_PINK_600
)

logger = logging.getLogger(__name__)


class DanmakuState:
    """弹幕监控状态管理"""

    def __init__(self):
        self.live_danmaku = None
        self.is_monitoring = False
        self.listview_ready = False
        self.page_visible = True
        self.danmaku_queue: list[dict] = []
        self.ad_tasks: list[asyncio.Task] = []


class DanmakuService:
    """弹幕服务"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.state = DanmakuState()
        self.current_room_id = None
        self.ad_control_callback: Callable[[bool], None] | None = None

    async def get_room_details(self, room_id: str) -> dict[str, object]:
        """获取直播间详情"""
        try:
            room_id_int = int(room_id)
            live_room = live.LiveRoom(room_display_id=room_id_int, credential=auth_manager.credential)
            
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

    async def send_danmaku(self, text: str) -> bool:
        """发送弹幕"""
        try:
            if not self.current_room_id or not auth_manager.credential:
                logger.warning("未设置房间号或凭证，无法发送弹幕")
                return False
            
            room_id_int = int(self.current_room_id)
            live_room = live.LiveRoom(room_display_id=room_id_int, credential=auth_manager.credential)
            await live_room.send_danmaku(live.Danmaku(text))
            
            logger.info(f"发送弹幕成功: {text}")
            return True
        
        except Exception as e:
            logger.error(f"发送弹幕失败: {e}")
            return False

    async def send_thank_message(self, username: str, gift_name: str, num: int) -> bool:
        """发送答谢弹幕"""
        try:
            template = app_settings.get('thank_template', '感谢【用户名】赠送的【礼物】×【数量】！')
            
            message = template.replace('【用户名】', username)
            message = message.replace('【礼物】', gift_name)
            message = message.replace('【数量】', str(num))
            
            room_id_int = int(self.current_room_id)
            live_room = live.LiveRoom(room_display_id=room_id_int, credential=auth_manager.credential)
            await live_room.send_danmaku(live.Danmaku(message))
            
            logger.info(f"发送答谢弹幕: {message}")
            return True
        
        except Exception as e:
            logger.error(f"发送答谢消息失败: {e}")
            return False

    async def send_advertisement(self, ad_text: str) -> bool:
        """发送广告弹幕"""
        try:
            if not self.current_room_id or not auth_manager.credential:
                logger.warning("当前房间号未设置或凭证未设置，无法发送广告")
                return False
            
            if not ad_text.strip():
                logger.warning("广告文案为空，跳过发送")
                return False
            
            room_id_int = int(self.current_room_id)
            live_room = live.LiveRoom(room_display_id=room_id_int, credential=auth_manager.credential)
            await live_room.send_danmaku(live.Danmaku(ad_text.strip()))
            
            logger.info(f"广告弹幕发送成功: {ad_text}")
            return True
        
        except Exception as e:
            logger.error(f"发送广告失败: {e}")
            return False

    def register_ad_control_callback(self, callback: Callable[[bool], None]):
        """注册广告控制回调"""
        self.ad_control_callback = callback

    async def start_advertisements(self):
        """启动所有定时广告任务"""
        # 清理现有任务
        await self.stop_advertisements()
        
        ad_enabled = app_settings.get('ad_enabled', False)
        if not ad_enabled:
            logger.info("定时广告功能未启用")
            return
        
        ad_list = app_settings.get('ad_list', [])
        if not ad_list:
            logger.info("广告列表为空")
            return
        
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
            
            # 创建定时任务
            async def ad_task(ad_content: str, interval_sec: int):
                logger.info(f"广告任务启动: {ad_content} (间隔: {interval_sec}秒)")
                
                while self.state.is_monitoring:
                    try:
                        current_settings = app_settings.get_all()
                        ad_enabled = current_settings.get('ad_enabled', False)
                        
                        if not ad_enabled:
                            logger.info("定时广告已关闭，停止广告任务")
                            break
                        
                        logger.info(f"准备发送广告: {ad_content}")
                        await self.send_advertisement(ad_content)
                        logger.info(f"广告发送完成，等待 {interval_sec} 秒后再次发送")
                        await asyncio.sleep(interval_sec)
                    except Exception as e:
                        logger.error(f"定时广告任务执行失败: {e}")
                        await asyncio.sleep(60)
            
            task = asyncio.create_task(ad_task(ad_text, interval_seconds))
            self.state.ad_tasks.append(task)
            logger.info(f"已启动定时广告任务: {ad_text} ({interval} {unit})")

    async def stop_advertisements(self):
        """停止所有定时广告任务"""
        for task in self.state.ad_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self.state.ad_tasks.clear()
        logger.info("已停止所有定时广告任务")

    async def start_monitoring(self, room_id: str, on_danmaku_msg, on_gift):
        """开始弹幕监控"""
        try:
            await self.stop_monitoring()
            
            # 创建新的弹幕监控实例
            self.state.live_danmaku = live.LiveDanmaku(int(room_id), credential=auth_manager.credential)
            self.current_room_id = room_id
            self.state.is_monitoring = True
            self.state.listview_ready = True
            
            # 注册事件监听器
            self.state.live_danmaku.add_event_listener('DANMU_MSG', on_danmaku_msg)
            self.state.live_danmaku.add_event_listener('SEND_GIFT', on_gift)
            
            # 启动定时广告
            await self.start_advertisements()
            
            # 在后台运行连接
            async def connect_danmaku():
                try:
                    logger.info("开始连接弹幕服务器")
                    await self.state.live_danmaku.connect()
                except Exception as e:
                    logger.error(f"弹幕监控连接失败: {e}")
                    self.state.is_monitoring = False
                    self.state.listview_ready = False
            
            asyncio.create_task(connect_danmaku())
            logger.info("弹幕监控已启动")
        
        except Exception as e:
            logger.error(f"启动弹幕监控失败: {e}")
            self.state.listview_ready = False

    async def stop_monitoring(self):
        """停止弹幕监控"""
        await self.stop_advertisements()
        
        if self.state.live_danmaku and self.state.is_monitoring:
            try:
                await self.state.live_danmaku.disconnect()
                self.state.is_monitoring = False
                logger.info("弹幕监控已停止")
            except Exception as e:
                logger.error(f"停止弹幕监控失败: {e}")
            finally:
                self.state.live_danmaku = None
                self.state.listview_ready = False

    def set_page_visible(self, visible: bool):
        """设置页面可见性"""
        self.state.page_visible = visible

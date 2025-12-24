"""
设置页面模块
"""
import logging

import flet as ft

from src.config.settings import app_settings
from src.constants import (
    DEFAULT_THANK_TEMPLATE, DEFAULT_AD_INTERVAL, DEFAULT_AD_UNIT, DEFAULT_AD_TEXT
)

logger = logging.getLogger(__name__)


def create_settings_page(page: ft.Page):
    """创建设置页面"""
    
    # 答谢开关
    thank_switch = ft.Switch(
        label="自动答谢礼物",
        value=app_settings.get('thank_enabled', False),
        on_change=lambda e: app_settings.set('thank_enabled', e.control.value)
    )
    
    # 答谢模板
    thank_template = ft.TextField(
        label="答谢模板",
        value=app_settings.get('thank_template', DEFAULT_THANK_TEMPLATE),
        helper_text="可使用占位符：【用户名】【礼物】【数量】",
        multiline=True,
        min_lines=2,
        max_lines=3,
        width=400,
        on_blur=lambda e: app_settings.set('thank_template', e.control.value)
    )
    
    # 定时广告开关
    ad_switch = ft.Switch(
        label="定时广告广播",
        value=app_settings.get('ad_enabled', False),
        on_change=lambda e: app_settings.set('ad_enabled', e.control.value)
    )
    
    # 广告列表容器
    ad_list_container = ft.Container(
        content=ft.Column([]),
        padding=10,
        border=ft.border.all(1, ft.Colors.GREY_300),
        border_radius=5,
        width=500,
    )
    
    # 更新广告列表
    def refresh_ad_list():
        ad_list = app_settings.get('ad_list', [])
        items = []
        
        for i, ad in enumerate(ad_list):
            interval_input = ft.TextField(
                label="间隔",
                value=str(ad.get('interval', DEFAULT_AD_INTERVAL)),
                width=80,
                keyboard_type=ft.KeyboardType.NUMBER,
            )
            
            unit_dropdown = ft.Dropdown(
                label="单位",
                value=ad.get('unit', DEFAULT_AD_UNIT),
                width=100,
                options=[
                    ft.dropdown.Option("分钟"),
                    ft.dropdown.Option("小时"),
                ]
            )
            
            text_input = ft.TextField(
                label="广告文案",
                value=ad.get('text', DEFAULT_AD_TEXT),
                expand=True,
            )
            
            def delete_clicked(e, idx):
                current_list = app_settings.get('ad_list', [])
                current_list.pop(idx)
                app_settings.set('ad_list', current_list)
                refresh_ad_list()
            
            remove_button = ft.IconButton(
                icon=ft.Icons.DELETE,
                icon_color=ft.Colors.RED_500,
                tooltip="删除",
                on_click=lambda e, idx=i: delete_clicked(e, idx)
            )
            
            def save_clicked(e, idx, inter, unit, txt):
                current_list = app_settings.get('ad_list', [])
                while len(current_list) <= idx:
                    current_list.append({
                        'interval': DEFAULT_AD_INTERVAL,
                        'unit': DEFAULT_AD_UNIT,
                        'text': DEFAULT_AD_TEXT
                    })
                
                current_list[idx] = {
                    'interval': int(inter.value) if inter.value else DEFAULT_AD_INTERVAL,
                    'unit': unit.value,
                    'text': txt.value
                }
                app_settings.set('ad_list', current_list)
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
        try:
            ad_list_container.update()
        except AssertionError:
            pass
    
    # 添加广告
    def add_ad_clicked(e):
        current_ad_list = app_settings.get('ad_list', [])
        current_ad_list.append({
            'interval': DEFAULT_AD_INTERVAL,
            'unit': DEFAULT_AD_UNIT,
            'text': DEFAULT_AD_TEXT
        })
        app_settings.set('ad_list', current_ad_list)
        refresh_ad_list()
    
    # 添加广告按钮
    add_ad_button = ft.ElevatedButton(
        text="添加广告",
        icon=ft.Icons.ADD,
        on_click=add_ad_clicked
    )
    
    # 初始化广告列表内容
    ad_list = app_settings.get('ad_list', [])
    if not ad_list:
        ad_list = [{
            'interval': DEFAULT_AD_INTERVAL,
            'unit': DEFAULT_AD_UNIT,
            'text': DEFAULT_AD_TEXT
        }]
        app_settings.set('ad_list', ad_list)
    
    for i, ad in enumerate(ad_list):
        interval_input = ft.TextField(
            label="间隔",
            value=str(ad.get('interval', DEFAULT_AD_INTERVAL)),
            width=80,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        unit_dropdown = ft.Dropdown(
            label="单位",
            value=ad.get('unit', DEFAULT_AD_UNIT),
            width=100,
            options=[
                ft.dropdown.Option("分钟"),
                ft.dropdown.Option("小时"),
            ]
        )
        
        text_input = ft.TextField(
            label="广告文案",
            value=ad.get('text', DEFAULT_AD_TEXT),
            expand=True,
        )
        
        def delete_clicked(e, idx):
            current_list = app_settings.get('ad_list', [])
            current_list.pop(idx)
            app_settings.set('ad_list', current_list)
            refresh_ad_list()
        
        remove_button = ft.IconButton(
            icon=ft.Icons.DELETE,
            icon_color=ft.Colors.RED_500,
            tooltip="删除",
            on_click=lambda e, idx=i: delete_clicked(e, idx)
        )
        
        def save_clicked(e, idx, inter, unit, txt):
            current_list = app_settings.get('ad_list', [])
            while len(current_list) <= idx:
                current_list.append({
                    'interval': DEFAULT_AD_INTERVAL,
                    'unit': DEFAULT_AD_UNIT,
                    'text': DEFAULT_AD_TEXT
                })
            
            current_list[idx] = {
                'interval': int(inter.value) if inter.value else DEFAULT_AD_INTERVAL,
                'unit': unit.value,
                'text': txt.value
            }
            app_settings.set('ad_list', current_list)
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
        
        ad_list_container.content.controls.append(ad_row)
    
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

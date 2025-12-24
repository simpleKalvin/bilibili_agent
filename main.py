"""
Bilibili Agent - 项目根目录入口

此文件用于 Flet 构建工具识别应用入口。
实际应用逻辑位于 src/app.py
"""
from src.app import main

if __name__ == '__main__':
    import flet as ft
    _ = ft.app(main)
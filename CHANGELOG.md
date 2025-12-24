# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- 初始版本发布
- B站二维码登录功能
- 直播间弹幕监控
- 礼物接收与自动答谢
- 定时广告广播功能
- 监控历史记录
- 用户信息显示与注销功能

### Changed
- 重构项目结构，按职责分模块拆分代码
  - `src/config/`: 配置管理模块
  - `src/constants.py`: 常量定义
  - `src/core/auth.py`: 认证管理
  - `src/services/danmaku.py`: 弹幕服务
  - `src/ui/pages/`: UI 页面组件
  - `src/utils/`: 工具函数

### Removed
- 删除旧的 `src/main.py` 单文件实现

---

## [0.1.0] - 2025-12-24

### Added
- B站二维码登录
- 直播间信息获取
- 弹幕监控与显示
- 弹幕发送功能
- 礼物接收提示
- 自动答谢礼物
- 定时广告发送
- 监控历史记录
- 用户头像与信息显示
- 注销功能
- 设置页面（答谢模板、广告配置）

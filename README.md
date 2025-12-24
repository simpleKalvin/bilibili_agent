# BilibiliAgent app

## Run the app

### uv

Run as a desktop app:

```
uv run flet run
```

Run as a web app:

```
uv run flet run --web
```

### Poetry

Install dependencies from `pyproject.toml`:

```
poetry install
```

Run as a desktop app:

```
poetry run flet run
```

Run as a web app:

```
poetry run flet run --web
```

For more details on running the app, refer to the [Getting Started Guide](https://flet.dev/docs/getting-started/).

## Build the app

### Android

```
flet build apk -v
```

For more details on building and signing `.apk` or `.aab`, refer to the [Android Packaging Guide](https://flet.dev/docs/publish/android/).

### iOS

```
flet build ipa -v
```

For more details on building and signing `.ipa`, refer to the [iOS Packaging Guide](https://flet.dev/docs/publish/ios/).

### macOS

```
flet build macos -v
```

For more details on building macOS package, refer to the [macOS Packaging Guide](https://flet.dev/docs/publish/macos/).

### Linux

```
flet build linux -v
```

For more details on building Linux package, refer to the [Linux Packaging Guide](https://flet.dev/docs/publish/linux/).

### Windows

```
flet build windows -v
```

For more details on building Windows package, refer to the [Windows Packaging Guide](https://flet.dev/docs/publish/windows/).

## 自动构建和发版

项目使用 GitHub Actions 实现自动构建，发版时会自动生成 macOS、Windows、Linux 三平台安装包。

### 发版流程

1. **使用版本管理脚本发版**

```bash
python scripts/release.py 1.0.0
```

该脚本会：
- 更新 `pyproject.toml` 中的版本号
- 显示最近的变更记录
- 提交版本变更并推送到远程仓库
- 创建并推送 git tag（如 `v1.0.0`）
- 触发 GitHub Actions 自动构建

2. **GitHub Actions 自动构建**

推送 tag 后，GitHub Actions 会自动：
- 同时构建 macOS、Windows、Linux 三平台安装包
- 将构建产物上传到 GitHub Releases
- 生成 Release Notes（包含最近的提交记录）

3. **下载安装包**

在 GitHub Releases 页面下载对应平台的安装包：
- https://github.com/你的用户名/bilibili_agent/releases

### 本地手动构建

如果需要在本地手动构建，使用构建脚本：

```bash
# 构建 macOS
./scripts/build.sh -p macos

# 构建 Windows
./scripts/build.sh -p windows

# 构建 Linux
./scripts/build.sh -p linux

# 查看详细输出
./scripts/build.sh -p macos -v
```

**注意**：
- macOS 构建需要安装 Xcode 和 CocoaPods
- Windows 构建需要安装 Visual Studio
- Linux 构建需要安装开发工具（如 `build-essential`）

### 构建产物

构建完成后，安装包位于 `build/` 目录：

| 平台 | 产物 |
|------|------|
| macOS | `.dmg` 文件 |
| Windows | `.exe` 文件 |
| Linux | `.AppImage` / `.deb` / `.rpm` 文件 |
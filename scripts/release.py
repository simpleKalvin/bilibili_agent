#!/usr/bin/env python3
"""
版本管理脚本

用于发版本，包括：
1. 更新 pyproject.toml 中的版本号
2. 生成 CHANGELOG 摘要
3. 创建并推送 git tag
"""

import argparse
import re
import subprocess
from pathlib import Path


def get_current_version():
    """获取当前版本号"""
    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    content = pyproject.read_text()
    match = re.search(r'version = "(\d+\.\d+\.\d+)"', content)
    if match:
        return match.group(1)
    raise ValueError("未找到版本号")


def update_version(new_version):
    """更新 pyproject.toml 中的版本号"""
    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    content = pyproject.read_text()
    content = re.sub(
        r'version = "\d+\.\d+\.\d+"',
        f'version = "{new_version}"',
        content
    )
    pyproject.write_text(content)
    print(f"✓ 版本号已更新为 {new_version}")


def get_latest_changes():
    """获取最新的变更内容"""
    try:
        result = subprocess.run(
            ["git", "log", "--pretty=format:%s", "--no-merges", "-10"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return ""


def create_and_push_tag(version):
    """创建并推送 git tag"""
    tag_name = f"v{version}"
    
    # 检查 tag 是否已存在
    result = subprocess.run(
        ["git", "tag", "-l", tag_name],
        capture_output=True,
        text=True
    )
    if tag_name in result.stdout:
        print(f"⚠ Tag {tag_name} 已存在，请先删除或使用其他版本号")
        return False
    
    # 创建 tag
    subprocess.run(["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}"], check=True)
    print(f"✓ 已创建 tag {tag_name}")
    
    # 推送 tag
    subprocess.run(["git", "push", "origin", tag_name], check=True)
    print(f"✓ 已推送 tag {tag_name}")
    print(f"\n🚀 GitHub Actions 将自动构建多平台安装包，请查看:")
    print(f"   https://github.com/你的用户名/bilibili_agent/actions")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="版本管理脚本")
    parser.add_argument("version", help="新版本号，例如: 1.0.0")
    parser.add_argument("--skip-update", action="store_true", help="跳过版本号更新")
    args = parser.parse_args()
    
    # 验证版本号格式
    if not re.match(r'^\d+\.\d+\.\d+$', args.version):
        print("❌ 版本号格式错误，应为: x.y.z (例如: 1.0.0)")
        return
    
    current_version = get_current_version()
    print(f"当前版本: {current_version}")
    print(f"新版本: {args.version}")
    
    # 更新版本号
    if not args.skip_update:
        update_version(args.version)
    
    # 显示最新变更
    changes = get_latest_changes()
    if changes:
        print("\n📝 最新变更:")
        print("-" * 60)
        for i, line in enumerate(changes.split('\n')[:10], 1):
            print(f"{i}. {line}")
        print("-" * 60)
    
    # 确认
    confirm = input("\n确认创建并推送 tag? (y/N): ")
    if confirm.lower() != 'y':
        print("已取消")
        return
    
    # 提交版本变更
    if not args.skip_update:
        subprocess.run(["git", "add", "pyproject.toml"], check=True)
        subprocess.run(["git", "commit", "-m", f"chore: bump version to {args.version}"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("✓ 已推送版本变更")
    
    # 创建并推送 tag
    create_and_push_tag(args.version)


if __name__ == "__main__":
    main()

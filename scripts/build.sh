#!/bin/bash
# 本地构建脚本
# 用于手动构建指定平台的安装包

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 获取脚本所在目录的父目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# 显示帮助信息
show_help() {
    cat << EOF
本地构建脚本 - 用于手动构建指定平台的安装包

用法: ./scripts/build.sh [选项]

选项:
    -p, --platform PLATFORM   指定构建平台 (macos|windows|linux)
    -v, --verbose             启用详细输出
    -h, --help                显示此帮助信息

示例:
    ./scripts/build.sh -p macos          # 构建 macOS 安装包
    ./scripts/build.sh -p windows -v     # 构建 Windows 安装包（详细模式）
    ./scripts/build.sh -p linux          # 构建 Linux 安装包

注意:
    - macOS 构建需要安装 Xcode 和 CocoaPods
    - Windows 构建需要安装 Visual Studio
    - Linux 构建需要安装必要的开发工具
EOF
}

# 解析参数
PLATFORM=""
VERBOSE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--platform)
            PLATFORM="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE="-v"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

# 验证平台参数
if [[ -z "$PLATFORM" ]]; then
    print_error "请指定构建平台 (-p/--platform)"
    show_help
    exit 1
fi

PLATFORM=$(echo "$PLATFORM" | tr '[:upper:]' '[:lower:]')
if [[ ! "$PLATFORM" =~ ^(macos|windows|linux)$ ]]; then
    print_error "无效的平台: $PLATFORM (支持: macos, windows, linux)"
    exit 1
fi

# 检查是否在虚拟环境中
if [[ -z "$VIRTUAL_ENV" && -z "$CONDA_PREFIX" ]]; then
    print_warn "未检测到虚拟环境，建议先激活虚拟环境"
fi

# 检查必要的工具
check_dependencies() {
    print_info "检查依赖..."

    # 检查 uv
    if ! command -v uv &> /dev/null; then
        print_warn "未安装 uv，尝试使用 pip..."
        if ! command -v pip &> /dev/null; then
            print_error "请先安装 uv 或 pip"
            exit 1
        fi
        PIP_CMD="pip"
    else
        PIP_CMD="uv pip"
    fi

    # 检查 flet
    if ! uv run flet --version &> /dev/null; then
        print_error "未安装 flet，请先运行: uv sync --all-extras"
        exit 1
    fi

    # 平台特定检查
    case $PLATFORM in
        macos)
            if ! command -v xcodebuild &> /dev/null; then
                print_error "未找到 Xcode，请先安装: xcode-select --install"
                exit 1
            fi
            ;;
        windows)
            if [[ ! -d "C:/Program Files/Microsoft Visual Studio" ]]; then
                print_warn "未检测到 Visual Studio，Windows 构建可能失败"
            fi
            ;;
        linux)
            if ! command -v gcc &> /dev/null; then
                print_warn "未检测到 gcc，请安装开发工具: sudo apt install build-essential"
            fi
            ;;
    esac
}

# 执行构建
build() {
    print_info "开始构建 $PLATFORM 平台..."
    print_info "项目根目录: $PROJECT_ROOT"

    # 安装依赖
    print_info "安装依赖..."
    uv sync --all-extras

    # 初始化 Flet 构建
    print_info "初始化 Flet 构建..."
    uv run flet build setup

    # 执行构建
    print_info "构建 $PLATFORM 安装包..."
    case $PLATFORM in
        macos)
            uv run flet build macos $VERBOSE
            ;;
        windows)
            uv run flet build windows $VERBOSE
            ;;
        linux)
            uv run flet build linux $VERBOSE
            ;;
    esac

    # 查找构建产物
    BUILD_DIR="$PROJECT_ROOT/build"
    if [[ -d "$BUILD_DIR" ]]; then
        print_info "构建产物:"
        case $PLATFORM in
            macos)
                find "$BUILD_DIR" -name "*.dmg" -o -name "*.app" | head -5
                ;;
            windows)
                find "$BUILD_DIR" -name "*.exe" | head -5
                ;;
            linux)
                find "$BUILD_DIR" -name "*.AppImage" -o -name "*.deb" -o -name "*.rpm" | head -5
                ;;
        esac
    fi
}

# 主流程
check_dependencies
build

print_info "✓ 构建完成！"

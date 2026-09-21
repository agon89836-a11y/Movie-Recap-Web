#!/bin/bash
set -e

# 函数：打印日志
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# 函数：检查必要的文件和目录
check_requirements() {
    log "检查应用环境..."

    # 检查配置文件
    if [ ! -f "config.toml" ]; then
        if [ -f "config.example.toml" ]; then
            log "复制示例配置文件..."
            cp config.example.toml config.toml
        else
            log "警告: 未找到配置文件"
        fi
    fi

    # 检查必要的目录
    for dir in "storage/temp" "storage/tasks" "storage/json" "storage/narration_scripts" "storage/drama_analysis"; do
        if [ ! -d "$dir" ]; then
            log "创建目录: $dir"
            mkdir -p "$dir"
        fi
    done

    log "环境检查完成"
}

# 函数：启动 WebUI
start_webui() {
    PORT="${PORT:-8501}"
    log "启动 NarratoAI WebUI (User) — Port: $PORT ..."

    exec streamlit run webui.py \
        --server.address=0.0.0.0 \
        --server.port="$PORT" \
        --server.enableCORS=true \
        --server.maxUploadSize=2048 \
        --server.enableXsrfProtection=false \
        --server.headless=true \
        --browser.gatherUsageStats=false \
        --browser.serverAddress=0.0.0.0 \
        --logger.level=info
}

# 函数：启动 Admin WebUI
start_admin() {
    PORT="${PORT:-8502}"
    log "启动 NarratoAI Admin WebUI — Port: $PORT ..."

    exec streamlit run admin_web.py \
        --server.address=0.0.0.0 \
        --server.port="$PORT" \
        --server.enableCORS=true \
        --server.maxUploadSize=2048 \
        --server.enableXsrfProtection=false \
        --server.headless=true \
        --browser.gatherUsageStats=false \
        --browser.serverAddress=0.0.0.0 \
        --logger.level=info
}

# 函数：启动 Telegram Bot
start_bot() {
    log "启动 Telegram Bot..."
    exec python telegram_bot.py
}

# 主逻辑
log "NarratoAI Docker 容器启动中..."

# 检查环境
check_requirements

# 根据参数执行不同的命令
case "$1" in
    "webui"|"")
        start_webui
        ;;
    "admin")
        start_admin
        ;;
    "bot"|"telegram")
        start_bot
        ;;
    "bash"|"sh")
        log "启动交互式 shell..."
        exec /bin/bash
        ;;
    "health")
        PORT="${PORT:-8501}"
        log "执行健康检查 — Port: $PORT ..."
        if curl -f "http://localhost:$PORT/_stcore/health" >/dev/null 2>&1; then
            log "健康检查通过"
            exit 0
        else
            log "健康检查失败"
            exit 1
        fi
        ;;
    *)
        log "执行自定义命令: $*"
        exec "$@"
        ;;
esac

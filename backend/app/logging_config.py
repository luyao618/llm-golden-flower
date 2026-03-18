"""集中式日志配置

提供统一的日志格式、控制台输出和文件输出（自动轮转）。
在 create_app() 中调用 setup_logging() 即可激活。

日志文件存放在 backend/logs/ 目录下：
- app.log        : 所有 INFO 及以上级别的日志（主日志文件）
- app_debug.log  : 所有 DEBUG 及以上级别的日志（仅 debug=True 时启用）
- error.log      : 仅 WARNING 及以上级别的日志（便于快速排查问题）

环境变量:
- LOG_LEVEL: 日志级别 (DEBUG/INFO/WARNING/ERROR)，默认 INFO
- DEBUG: 设置为 true 时自动使用 DEBUG 级别
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(
    log_level: str = "INFO",
    debug: bool = False,
    log_dir: str | None = None,
) -> None:
    """配置全局日志系统

    Args:
        log_level: 日志级别 (DEBUG/INFO/WARNING/ERROR)
        debug: 是否为调试模式（覆盖 log_level 为 DEBUG）
        log_dir: 日志文件目录，默认为 backend/logs/
    """
    # 确定日志级别
    if debug:
        level = logging.DEBUG
    else:
        level = getattr(logging, log_level.upper(), logging.INFO)

    # 确定日志目录
    if log_dir is None:
        # 默认: backend/logs/
        backend_dir = Path(__file__).resolve().parent.parent
        log_dir_path = backend_dir / "logs"
    else:
        log_dir_path = Path(log_dir)

    log_dir_path.mkdir(parents=True, exist_ok=True)

    # ---- 日志格式 ----
    # 控制台：紧凑格式
    console_fmt = logging.Formatter(
        fmt="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    # 文件：完整格式（含日期、进程/线程信息）
    file_fmt = logging.Formatter(
        fmt="%(asctime)s %(levelname)-8s [%(name)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ---- 根日志器 ----
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 清除已有 handler（避免重复添加）
    root_logger.handlers.clear()

    # ---- 控制台 Handler ----
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(console_fmt)
    root_logger.addHandler(console_handler)

    # ---- 主日志文件 Handler (app.log) ----
    # 10 MB 轮转，保留 5 个备份
    app_log_handler = RotatingFileHandler(
        filename=str(log_dir_path / "app.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    app_log_handler.setLevel(logging.INFO)
    app_log_handler.setFormatter(file_fmt)
    root_logger.addHandler(app_log_handler)

    # ---- 错误日志文件 Handler (error.log) ----
    # 仅记录 WARNING 及以上，5 MB 轮转，保留 3 个备份
    error_log_handler = RotatingFileHandler(
        filename=str(log_dir_path / "error.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    error_log_handler.setLevel(logging.WARNING)
    error_log_handler.setFormatter(file_fmt)
    root_logger.addHandler(error_log_handler)

    # ---- 调试日志文件 (debug=True 时启用) ----
    if debug:
        debug_log_handler = RotatingFileHandler(
            filename=str(log_dir_path / "app_debug.log"),
            maxBytes=20 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        debug_log_handler.setLevel(logging.DEBUG)
        debug_log_handler.setFormatter(file_fmt)
        root_logger.addHandler(debug_log_handler)

    # ---- 抑制第三方库的噪音日志 ----
    noisy_loggers = [
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "httpx",
        "httpcore",
        "litellm",
        "openai",
        "sqlalchemy.engine",
        "sqlalchemy.pool",
        "websockets",
        "watchfiles",
        "hpack",
    ]
    for name in noisy_loggers:
        logging.getLogger(name).setLevel(logging.WARNING)

    # uvicorn.error 需要保留 INFO（否则启动信息不可见）
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)

    # ---- 启动确认 ----
    logger = logging.getLogger(__name__)
    logger.info(
        "日志系统已初始化 — 级别: %s, 目录: %s",
        logging.getLevelName(level),
        log_dir_path,
    )

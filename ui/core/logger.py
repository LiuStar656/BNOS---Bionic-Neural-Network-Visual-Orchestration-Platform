"""
BNOS 全局日志配置模块

用法:
    from ui.core.logger import logger
    logger.info("节点 '%s' 已添加到画布", node_name)
    logger.debug("路径检查: %s", path)
    logger.warning("配置未找到: %s", key)
    logger.error("加载失败: %s", e)
"""
import logging
import sys
from pathlib import Path


def setup_logger(name: str = "BNOS") -> logging.Logger:
    """配置并返回全局 logger"""
    logger = logging.getLogger(name)

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # 控制台输出（INFO 级别）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_fmt = logging.Formatter(
        '[%(asctime)s] %(levelname)-5s %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)

    # 文件输出（DEBUG 级别，保留完整日志）
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(
        log_dir / "bnos_console.log", encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        '[%(asctime)s] %(levelname)-5s %(name)s (%(filename)s:%(lineno)d): %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)

    return logger


# 全局 logger 实例
logger = setup_logger()

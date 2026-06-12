"""
BNOS 全局日志配置模块

日志文件架构:
    logs/
    ├── bnos.log              ← 日常日志 (INFO+, 按天轮转, 保留7天)
    ├── bnos.log.YYYY-MM-DD   ← 历史日常日志 (自动归档)
    └── bnos_error.log        ← 错误日志 (ERROR+, 按大小轮转, 独立保留)

用法:
    from ui.core.logger import logger
    logger.info("节点 '%s' 已添加到画布", node_name)
    logger.error("加载失败: %s", e)

运行时控制:
    from ui.core.logger import set_debug_mode
    set_debug_mode(True)   # 开启全模块 DEBUG 输出
    set_debug_mode(False)  # 回到生产模式
"""
import logging
import logging.handlers
import sys
import time
from pathlib import Path


class SafeStreamHandler(logging.StreamHandler):
    """安全控制台处理器，自动处理 Windows GBK 编码下的特殊字符"""

    def emit(self, record):
        try:
            super().emit(record)
        except UnicodeEncodeError:
            msg = record.getMessage().encode(
                sys.stdout.encoding or 'gbk', errors='replace'
            ).decode(sys.stdout.encoding or 'gbk', errors='replace')
            record = logging.makeLogRecord(record.__dict__)
            record.msg = msg
            try:
                super().emit(record)
            except Exception:
                pass


class FrequencyFilter(logging.Filter):
    """频率过滤器：相同日志在时间窗口内超过阈值后抑制

    规则：同一(级别, 消息, 文件)在 time_window 秒内 > max_count 次时，
         输出一条汇总 WARNING，后续相同日志被丢弃。
    """

    def __init__(self, max_count: int = 5, time_window: int = 30):
        super().__init__()
        self.max_count = max_count
        self.time_window = time_window
        self._counters: dict = {}

    def filter(self, record):
        # ERROR/CRITICAL 永远不过滤
        if record.levelno >= logging.ERROR:
            return True

        key = (record.levelno, record.getMessage(), getattr(record, 'filename', ''))
        now = time.time()

        # 清理过期记录
        self._counters = {
            k: v for k, v in self._counters.items()
            if now - v['first'] < self.time_window
        }

        if key not in self._counters:
            self._counters[key] = {'count': 1, 'first': now}
            return True

        counter = self._counters[key]
        counter['count'] += 1

        if counter['count'] <= self.max_count:
            return True

        # 首次超频：输出汇总
        if counter['count'] == self.max_count + 1:
            suppressed = key[1][:80]
            record.msg = (
                f"[FREQ] 日志过于频繁(>={self.max_count}次/{self.time_window}s)"
                f"，后续抑制: {suppressed}"
            )
            record.levelno = logging.WARNING
            return True

        return False


class DebugLevelManager(logging.Filter):
    """模块级 DEBUG 控制器

    高频模块默认不输出 DEBUG，避免日志洪水。
    """

    DEFAULT_QUIET_MODULES = {
        'canvas_view', 'canvas_layout', 'edge_item', 'node_item',
        'anchor_item', 'polling_manager',
    }

    def __init__(self):
        super().__init__()
        self._debug_mode = False
        self._quiet_modules = set(self.DEFAULT_QUIET_MODULES)

    def filter(self, record):
        if self._debug_mode:
            return True
        if record.levelno <= logging.DEBUG:
            filename = getattr(record, 'filename', '')
            if filename.replace('.py', '') in self._quiet_modules:
                return False
        return True

    def set_debug_mode(self, enabled: bool):
        self._debug_mode = enabled


# ──── 日志文件清理 ────

def _cleanup_old_logs(log_dir: Path, keep_days: int = 7):
    """启动时清理超过 keep_days 天的旧日志"""
    try:
        now = time.time()
        cutoff = now - keep_days * 86400
        for f in log_dir.glob("bnos.log.*"):
            if f.stat().st_mtime < cutoff:
                f.unlink()
    except Exception:
        pass


# ──── 日志配置 ────

_LOG_FMT_DETAIL = logging.Formatter(
    '[%(asctime)s] %(levelname)-5s (%(filename)s:%(lineno)d): %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
_LOG_FMT_CONSOLE = logging.Formatter(
    '[%(asctime)s] %(levelname)-5s (%(filename)s): %(message)s',
    datefmt='%H:%M:%S',
)


def setup_logger(name: str = "BNOS") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    # 启动时清理旧日志
    _cleanup_old_logs(log_dir, keep_days=7)

    # ── 过滤器 ──
    logger.addFilter(FrequencyFilter(max_count=5, time_window=30))
    debug_mgr = DebugLevelManager()
    logger.addFilter(debug_mgr)

    # ── 控制台：INFO+ ──
    console = SafeStreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(_LOG_FMT_CONSOLE)
    logger.addHandler(console)

    # ── 日常日志：INFO+，按天轮转，保留 7 天 ──
    daily = logging.handlers.TimedRotatingFileHandler(
        log_dir / "bnos.log",
        when='midnight',
        interval=1,
        backupCount=7,
        encoding='utf-8',
    )
    daily.suffix = "%Y-%m-%d"
    daily.setLevel(logging.INFO)
    daily.setFormatter(_LOG_FMT_DETAIL)
    logger.addHandler(daily)

    # ── 错误日志：ERROR+，按大小轮转，独立保留 ──
    error = logging.handlers.RotatingFileHandler(
        log_dir / "bnos_error.log",
        maxBytes=1 * 1024 * 1024,  # 1MB
        backupCount=5,             # 最多保留 5 个备份 = 6MB
        encoding='utf-8',
    )
    error.setLevel(logging.ERROR)
    error.setFormatter(_LOG_FMT_DETAIL)
    logger.addHandler(error)

    return logger


# 全局 logger 实例
logger = setup_logger()


# ──── 运行时 API ────

def set_debug_mode(enabled: bool = True):
    """切换调试模式"""
    for f in logger.filters:
        if isinstance(f, DebugLevelManager):
            f.set_debug_mode(enabled)
            status = "开启" if enabled else "关闭"
            logger.info("[LOG] 调试模式 %s", status)
            return


def add_quiet_module(module_name: str):
    """将模块加入 DEBUG 静默列表"""
    for f in logger.filters:
        if isinstance(f, DebugLevelManager):
            f._quiet_modules.add(module_name)
            return


def remove_quiet_module(module_name: str):
    """将模块移出 DEBUG 静默列表"""
    for f in logger.filters:
        if isinstance(f, DebugLevelManager):
            f._quiet_modules.discard(module_name)
            return

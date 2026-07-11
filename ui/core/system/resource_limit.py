"""全平台节点资源限制组件。

跨平台统一接口，根据操作系统自动选择底层实现：
- Linux: cgroups v2（CPU 硬限制 + 内存硬限制）
- Windows: Job Objects（CPU 硬限制 + 内存硬限制）
- macOS: 仅 nice 优先级（系统 API 不支持硬限制）

用法:
    limit = create_resource_limit(pid, {"memory_mb": 512, "cpu_percent": 50})
    limit.apply()

    # 或作为上下文管理器
    with create_resource_limit(pid, config) as limit:
        limit.apply()
"""

from __future__ import annotations

import logging
import platform
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import psutil

logger = logging.getLogger(__name__)

_SYSTEM = platform.system()

# ── 优先级映射表 ──────────────────────────────────────────────
_PRIORITY_WINDOWS: dict[str, int] = {
    "low": psutil.IDLE_PRIORITY_CLASS,
    "below_normal": psutil.BELOW_NORMAL_PRIORITY_CLASS,
    "normal": psutil.NORMAL_PRIORITY_CLASS,
    "above_normal": psutil.ABOVE_NORMAL_PRIORITY_CLASS,
    "high": psutil.HIGH_PRIORITY_CLASS,
}
_PRIORITY_UNIX: dict[str, int] = {
    "low": 19,
    "below_normal": 10,
    "normal": 0,
    "above_normal": -5,
    "high": -10,
}


# ── 抽象基类 ─────────────────────────────────────────────────


class ResourceLimit(ABC):
    """全平台资源限制器基类。"""

    def __init__(self, pid: int, config: dict[str, Any]) -> None:
        self._pid = pid
        self._config = config
        self._proc: psutil.Process | None = None

    def _get_proc(self) -> psutil.Process | None:
        """延迟获取 psutil.Process 对象，PID 不存在时返回 None。"""
        if self._proc is None:
            try:
                self._proc = psutil.Process(self._pid)
            except psutil.NoSuchProcess:
                logger.warning("Process not found: pid=%d", self._pid)
                return None
        return self._proc

    def apply(self) -> list[str]:
        """应用所有配置的资源限制。

        Returns:
            实际生效的限制列表（用于日志 / UI 反馈）。未配置的项不会出现在列表中。
        """
        applied: list[str] = []
        applied += self._apply_priority()
        applied += self._apply_affinity()
        applied += self._apply_hard_limits()
        return applied

    def _apply_priority(self) -> list[str]:
        """设置进程优先级。全平台通用。"""
        level: str | None = self._config.get("priority")
        if level is None:
            return []

        proc = self._get_proc()
        if proc is None:
            return []

        if _SYSTEM == "Windows":
            mapping = _PRIORITY_WINDOWS
        else:
            mapping = _PRIORITY_UNIX

        value = mapping.get(level)
        if value is None:
            logger.warning("Unknown priority level: %s", level)
            return []

        try:
            proc.nice(value)
            logger.info("Priority set: %s (pid=%d)", level, self._pid)
            return [f"priority={level}"]
        except psutil.AccessDenied:
            logger.warning("Access denied setting priority for pid=%d", self._pid)
            return []

    def _apply_affinity(self) -> list[str]:
        """设置 CPU 亲和性。"""
        cores: list[int] | None = self._config.get("cpu_affinity")
        if cores is None:
            return []

        if _SYSTEM == "Darwin":
            logger.info("CPU affinity not supported on macOS")
            return []

        proc = self._get_proc()
        if proc is None:
            return []

        try:
            proc.cpu_affinity(cores)
            logger.info("CPU affinity set: %s (pid=%d)", cores, self._pid)
            return [f"cpu_affinity={cores}"]
        except psutil.AccessDenied:
            logger.warning("Access denied setting CPU affinity for pid=%d", self._pid)
            return []

    @abstractmethod
    def _apply_hard_limits(self) -> list[str]:
        """应用硬资源限制（平台特定实现）。"""
        ...

    def __enter__(self) -> ResourceLimit:
        return self


# ── Linux: cgroups v2 ─────────────────────────────────────────


class _LinuxResourceLimit(ResourceLimit):
    """Linux cgroups v2 实现。"""

    _CGROUP_BASE = Path("/sys/fs/cgroup")

    def _apply_hard_limits(self) -> list[str]:
        applied: list[str] = []
        cpu_percent: int | None = self._config.get("cpu_percent")
        mem_mb: int | None = self._config.get("memory_mb")

        if cpu_percent is None and mem_mb is None:
            return []

        cgroup_path = self._create_cgroup()
        if cgroup_path is None:
            return []

        # 将进程移入 cgroup
        try:
            (cgroup_path / "cgroup.procs").write_text(str(self._pid))
        except OSError as e:
            logger.warning("Failed to assign pid %d to cgroup: %s", self._pid, e)
            return []

        if cpu_percent is not None:
            applied += self._set_cpu_limit(cgroup_path, cpu_percent)

        if mem_mb is not None:
            applied += self._set_memory_limit(cgroup_path, mem_mb)

        return applied

    def _create_cgroup(self) -> Path | None:
        """创建专用 cgroup 目录。"""
        cgroup_path = self._CGROUP_BASE / f"bnos_node_{self._pid}"
        try:
            cgroup_path.mkdir(parents=True, exist_ok=True)
            return cgroup_path
        except PermissionError:
            logger.warning("Permission denied creating cgroup. Run with sudo or configure user cgroup delegation.")
            return None

    def _set_cpu_limit(self, cgroup_path: Path, cpu_percent: int) -> list[str]:
        """设置 CPU 配额。cpu_percent = 100 表示 1 核。"""
        cpu_max_file = cgroup_path / "cpu.max"
        if not cpu_max_file.exists():
            logger.warning("cpu.max not found (cgroups v1?), skipping CPU limit")
            return []

        quota_us = int(cpu_percent * 1000)  # 100% = 100000us per 100ms
        period_us = 100_000
        try:
            cpu_max_file.write_text(f"{quota_us} {period_us}")
            logger.info("CPU limit: %d%% (pid=%d)", cpu_percent, self._pid)
            return [f"cpu_percent={cpu_percent}"]
        except OSError as e:
            logger.warning("Failed to set CPU limit: %s", e)
            return []

    def _set_memory_limit(self, cgroup_path: Path, mem_mb: int) -> list[str]:
        """设置内存硬上限。"""
        mem_max_file = cgroup_path / "memory.max"
        if not mem_max_file.exists():
            logger.warning("memory.max not found, skipping memory limit")
            return []

        try:
            mem_max_file.write_text(str(mem_mb * 1024 * 1024))
            logger.info("Memory limit: %d MB (pid=%d)", mem_mb, self._pid)
            return [f"memory_mb={mem_mb}"]
        except OSError as e:
            logger.warning("Failed to set memory limit: %s", e)
            return []


# ── Windows: Job Objects ──────────────────────────────────────


class _WindowsResourceLimit(ResourceLimit):
    """Windows Job Objects 实现。"""

    def _apply_hard_limits(self) -> list[str]:
        applied: list[str] = []
        cpu_percent: int | None = self._config.get("cpu_percent")
        mem_mb: int | None = self._config.get("memory_mb")

        if cpu_percent is None and mem_mb is None:
            return []

        try:
            import ctypes
        except ImportError:
            logger.warning("ctypes not available, skipping hard limits")
            return []

        kernel32 = ctypes.windll.kernel32
        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            logger.warning("CreateJobObjectW failed")
            return []

        # ── 内存限制 ──
        if mem_mb is not None:
            applied += self._set_memory_limit(kernel32, job, mem_mb)

        # ── CPU 限制 ──
        if cpu_percent is not None:
            applied += self._set_cpu_limit(kernel32, job, cpu_percent)

        # ── 将进程加入 Job Object ──
        handle = kernel32.OpenProcess(0x1F0FFF, False, self._pid)
        if not handle:
            logger.warning("OpenProcess failed for pid=%d", self._pid)
            kernel32.CloseHandle(job)
            return applied

        if not kernel32.AssignProcessToJobObject(job, handle):
            logger.warning("AssignProcessToJobObject failed for pid=%d", self._pid)

        kernel32.CloseHandle(handle)
        kernel32.CloseHandle(job)
        return applied

    def _set_memory_limit(self, kernel32: Any, job: int, mem_mb: int) -> list[str]:
        """设置进程内存硬上限。"""
        import ctypes

        class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", ctypes.c_ubyte * 48),
                ("IoInfo", ctypes.c_ubyte * 48),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
            ]

        info = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        # 解析 BasicLimitInformation 中的 LimitFlags (DWORD at offset 0)
        # JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x100
        # Set limit flags via pointer into the first 4 bytes
        limit_flags = ctypes.c_uint32.from_buffer(info.BasicLimitInformation)
        limit_flags.value |= 0x100  # JOB_OBJECT_LIMIT_PROCESS_MEMORY
        info.ProcessMemoryLimit = mem_mb * 1024 * 1024

        # JobObjectExtendedLimitInformation = 9
        if kernel32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
            logger.info("Memory limit: %d MB (pid=%d)", mem_mb, self._pid)
            return [f"memory_mb={mem_mb}"]
        logger.warning("SetInformationJobObject (memory) failed")
        return []

    def _set_cpu_limit(self, kernel32: Any, job: int, cpu_percent: int) -> list[str]:
        """设置 CPU 使用率上限。"""
        import ctypes

        class _JOBOBJECT_CPU_RATE_CONTROL_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("ControlFlags", ctypes.c_uint32),
                ("CpuRate", ctypes.c_uint32),
            ]

        cpu_info = _JOBOBJECT_CPU_RATE_CONTROL_INFORMATION()
        cpu_info.ControlFlags = 0x1  # JOB_OBJECT_CPU_RATE_CONTROL_ENABLE
        # CpuRate: 10000 = 100%, so multiply by 100
        cpu_info.CpuRate = min(cpu_percent * 100, 10000)

        # JobObjectCpuRateControlInformation = 15
        if kernel32.SetInformationJobObject(job, 15, ctypes.byref(cpu_info), ctypes.sizeof(cpu_info)):
            logger.info("CPU limit: %d%% (pid=%d)", cpu_percent, self._pid)
            return [f"cpu_percent={cpu_percent}"]
        logger.warning("SetInformationJobObject (CPU) failed")
        return []


# ── macOS: 软限制 ─────────────────────────────────────────────


class _DarwinResourceLimit(ResourceLimit):
    """macOS 实现 —— 系统不支持硬 CPU/内存限制。"""

    def _apply_hard_limits(self) -> list[str]:
        applied: list[str] = []
        if "memory_mb" in self._config:
            logger.info("Memory limit not supported on macOS (config ignored)")
        if "cpu_percent" in self._config:
            logger.info("CPU limit not supported on macOS (config ignored)")
        if "cpu_affinity" in self._config:
            logger.info("CPU affinity not supported on macOS (config ignored)")
        return applied


# ── 工厂函数 ──────────────────────────────────────────────────


def create_resource_limit(pid: int, config: dict[str, Any]) -> ResourceLimit:
    """根据当前操作系统创建对应的资源限制器。

    Args:
        pid: 目标进程 ID。
        config: 资源配置字典，支持以下键：
            - memory_mb: int, 内存硬上限（MB），macOS 不支持
            - cpu_percent: int, CPU 使用率百分比（100 = 1 核），macOS 不支持
            - cpu_affinity: list[int], 绑定的 CPU 核心编号，macOS 不支持
            - priority: str, 进程优先级（low / below_normal / normal / above_normal / high）

    Returns:
        平台对应的 ResourceLimit 实例。
    """
    if _SYSTEM == "Linux":
        return _LinuxResourceLimit(pid, config)
    if _SYSTEM == "Windows":
        return _WindowsResourceLimit(pid, config)
    return _DarwinResourceLimit(pid, config)

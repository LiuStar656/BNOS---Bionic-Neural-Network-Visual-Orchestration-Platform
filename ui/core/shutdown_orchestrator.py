"""
关闭序列编排器 — 声明式定义关闭步骤及其依赖顺序
"""
from typing import List, Callable
from ui.core.logger import logger


class ShutdownStep:
    """单个关闭步骤"""
    def __init__(self, name: str, action: Callable, depends_on: List[str] = None):
        self.name = name
        self.action = action
        self.depends_on = depends_on or []


class ShutdownOrchestrator:
    """关闭编排器 — 按依赖顺序执行关闭步骤"""

    def __init__(self):
        self._steps: List[ShutdownStep] = []

    def add_step(self, name: str, action: Callable, depends_on: List[str] = None):
        self._steps.append(ShutdownStep(name, action, depends_on))

    def execute(self):
        """按拓扑顺序执行所有关闭步骤"""
        executed = set()

        def run_step(step: ShutdownStep):
            if step.name in executed:
                return
            for dep in step.depends_on:
                dep_step = next((s for s in self._steps if s.name == dep), None)
                if dep_step:
                    run_step(dep_step)
            logger.info("[Shutdown] %s...", step.name)
            try:
                step.action()
                executed.add(step.name)
                logger.info("[Shutdown] %s OK", step.name)
            except Exception as e:
                logger.error("[Shutdown] %s FAIL: %s", step.name, e)

        for step in self._steps:
            run_step(step)

        logger.info("[Shutdown] Done, %d/%d steps", len(executed), len(self._steps))

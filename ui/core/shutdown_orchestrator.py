"""
关闭序列编排器 — 声明式定义关闭步骤及其依赖顺序
"""
from typing import List, Callable


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
            print(f"  [Shutdown] {step.name}...")
            try:
                step.action()
                executed.add(step.name)
                print(f"  [Shutdown] {step.name} OK")
            except Exception as e:
                print(f"  [Shutdown] {step.name} FAIL: {e}")

        for step in self._steps:
            run_step(step)

        print(f"[Shutdown] Done, {len(executed)}/{len(self._steps)} steps")

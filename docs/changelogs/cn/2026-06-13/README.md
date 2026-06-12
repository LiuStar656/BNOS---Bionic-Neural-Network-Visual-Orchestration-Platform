# 【2026-06-13】V2.0.13 - 日志系统架构重设计

---

## 更新列表

### 1. 日志系统架构重设计

[详细内容](./01_日志系统架构重设计.md)

- 双文件分离：`bnos.log`（按天轮转）+ `bnos_error.log`（按大小轮转，独立存储错误）
- 三层防臃肿：FrequencyFilter → DebugLevelManager → 轮转清理
- ERROR/CRITICAL 永不过滤，错误日志独立可查
- SafeStreamHandler 处理 Windows GBK 编码兼容
- 启动自动清理 7 天前旧日志

### 2. PollingManager super().__init__() 修复

- 修复单例模式下 QObject C++ 层未初始化的崩溃
- `super().__init__(parent)` 移到单例检查之前

### 3. CanvasHost 面板加载顺序调整

- 终端 Dock 延迟到第一个画布创建后初始化
- 先画布面板后终端面板，减少启动闪烁

### 4. Emoji 清理

- 所有日志调用中 emoji 替换为 `[TAG]` 标签前缀
- 彻底解决 Windows GBK 编码下的 UnicodeEncodeError

---

## 主要更新

| 类别 | 更新内容 |
|------|----------|
| **日志架构** | 双文件分离，三层防臃肿，错误独立存储 |
| **Bug 修复** | PollingManager QObject 初始化顺序修复 |
| **面板优化** | CanvasHost 加载顺序调整 |
| **编码兼容** | Emoji 清理 + SafeStreamHandler 双重保障 |

---

## 验证结果

- ✅ 新日志文件 `bnos.log` / `bnos_error.log` 正常生成
- ✅ 控制台输出无 UnicodeEncodeError
- ✅ polling_manager 全局文件监控引用已同步更新
- ✅ 旧日志文件引用全部清理完毕

---

[← 返回总索引](../README.md)

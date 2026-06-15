# 【2026-06-15】V2.0.15 - 节点样式统一化与锚点坐标修复

---

## 更新列表

### 1. 节点样式统一化与锚点坐标修复

[详细内容](./01_节点样式统一化_锚点坐标修复与生命周期保护.md)

- **节点样式精简**：删除矩形/圆点样式文件（rect.py、dot.py），全系统统一为面板模式 DetailedNodeStyle
- **锚点位置统一**：输入/输出锚点回落位置改为节点两侧边线中点（x=0/nw, y=h/2）
- **坐标系统修复**：修正 `setPos` 多减 `size/2` 的偏移 bug 和 `_find_nearest` 补偿 bug，消除 8px 视觉偏移
- **继承链修正**：DetailedNodeStyle 直接继承 NodeStyle 基类，不再依赖已删除的 RectNodeStyle
- **进程生命周期保护**：TerminalProcess 析构时对已销毁的 QProcess 对象加 RuntimeError 保护

---

## 主要更新

| 类别 | 更新内容 |
|------|----------|
| **样式系统** | 删除 rect.py / dot.py，统一为面板模式 DetailedNodeStyle |
| **锚点坐标** | 回退位置统一为左右边线中点；修正 setPos 偏移 bug |
| **Bug 修复** | DetailedNodeStyle 继承链断裂；锚点 8px 视觉偏移；QProcess 析构 RuntimeError |
| **代码质量** | node_item.py 移除 is_dot 判断分支；StyleRegistry 精简为单一样式 |

---

## 验证结果

- ✅ 11/11 修改文件 Python 编译通过
- ✅ 无 `ModuleNotFoundError: No module named 'ui.canvas.items.styles.rect'`
- ✅ 无 `RectNodeStyle` / `DotNodeStyle` 代码引用残留

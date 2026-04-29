# 📊 BNOS 配置持久化机制详解

## ✅ 核心问题回答

**画布布局信息、节点坐标信息、节点颜色信息是否跟随项目来配置加载不会被覆盖掉？**

**答案：✅ 是的，所有配置都完全跟随项目，且已增强为双重备份机制！**

---

## 🗂️ 配置文件分布

BNOS采用**分散式配置存储**策略，不同类型的配置保存在不同位置：

### 1. **画布布局配置** 
📁 `项目根目录/canvas_layout.json`

```json
{
  "nodes": {
    "node_1": {
      "x": 69.74,
      "y": -166.27,
      "width": 140,
      "height": 80,
      "custom_colors": {
        "bg": "#FFEB3B",
        "border": "#F57C00",
        "text": "#D32F2F"
      }
    },
    "node_2": {
      "x": 347.55,
      "y": -184.75,
      "width": 140,
      "height": 80,
      "custom_colors": null
    }
  },
  "edges": [
    {"source": "node_1", "target": "node_2"}
  ],
  "view_state": {
    "scale": 0.66,
    "scroll_x": 100,
    "scroll_y": 200
  }
}
```

**包含内容**：
- ✅ 节点坐标 (x, y)
- ✅ 节点大小 (width, height)
- ✅ 连线关系 (source, target)
- ✅ 视图状态 (scale, scroll)
- ✅ **节点自定义颜色**（新增！双重备份）

**跟随项目**：✅ 是，每个项目独立文件

---

### 2. **画布颜色配置**
📁 `项目根目录/color_settings.json`

```json
{
  "canvas_bg_color": "#1E1E1E",
  "grid_color": "#333333",
  "edge_color": "#666666",
  "node_bg_color": "#f8f9fa",
  "node_border_color": "#dee2e6",
  "node_text_color": "#333333"
}
```

**包含内容**：
- ✅ 画布背景色
- ✅ 网格线颜色
- ✅ 连线默认颜色
- ✅ 节点默认背景色
- ✅ 节点默认边框色
- ✅ 节点默认文字色

**跟随项目**：✅ 是，每个项目独立文件

---

### 3. **节点自定义颜色配置**
📁 `各节点目录/config.json`

```json
{
  "node_name": "node_1",
  "language": "Python",
  "version": "1.0",
  "custom_bg_color": "#FFEB3B",
  "custom_border_color": "#F57C00",
  "custom_text_color": "#D32F2F",
  ...
}
```

**包含内容**：
- ✅ 节点自定义背景色 (`custom_bg_color`)
- ✅ 节点自定义边框色 (`custom_border_color`)
- ✅ 节点自定义文字色 (`custom_text_color`)

**跟随项目**：✅ 是，每个节点的配置保存在自己的文件夹中

---

## 🔄 配置加载流程

### 打开项目时的加载顺序

```
用户打开项目
    ↓
[1] 加载 app_config.json（应用级配置）
    ↓
[2] 加载 canvas_layout.json
    ├─ 恢复节点位置和大小
    ├─ 恢复连线关系
    ├─ 恢复视图状态（缩放、滚动）
    └─ 恢复节点自定义颜色（从 custom_colors 字段）
    ↓
[3] 加载 color_settings.json
    ├─ 应用画布背景色
    ├─ 应用网格线颜色
    ├─ 应用连线颜色
    └─ 应用节点默认颜色
    ↓
[4] 加载各节点 config.json
    ├─ 读取节点基本信息
    └─ 读取节点自定义颜色（作为主数据源）
    ↓
[5] 创建画布节点
    ├─ 使用 canvas_layout.json 的位置
    ├─ 优先使用节点 config.json 的颜色
    └─ 如果 config.json 没有颜色，使用 canvas_layout.json 的备份
    ↓
✅ 完整恢复项目状态
```

---

## 🛡️ 防覆盖保护机制

### 1. **双重备份机制**（新增！）

#### 节点颜色的双重存储：
- **主存储**: 各节点 `config.json`（权威数据源）
- **备份存储**: `canvas_layout.json` 的 `custom_colors` 字段

**优势**：
- 即使某个配置文件损坏，另一个仍可恢复数据
- 提高数据安全性

#### 加载优先级：
```python
# 伪代码逻辑
if node.config.json 有自定义颜色:
    使用 config.json 的颜色  # 主数据源
elif canvas_layout.json 有 custom_colors:
    使用 canvas_layout.json 的颜色  # 备份数据源
else:
    使用默认颜色
```

### 2. **智能合并策略**

当加载布局时，系统会：

```python
# 对于已存在的节点
if node_name in self.nodes:
    更新位置  # 不改变其他属性
    
# 对于新添加的节点
if node_name not in self.nodes:
    从项目数据创建节点
    应用保存的位置
    应用保存的颜色
```

**不会覆盖**：
- ❌ 不会覆盖节点的运行状态
- ❌ 不会覆盖节点的进程信息
- ❌ 不会覆盖用户手动修改的配置（除非明确保存）

### 3. **时间戳备份**（针对损坏文件）

如果 `canvas_layout.json` 损坏：
```python
try:
    加载布局
except JSONDecodeError:
    备份损坏文件为 canvas_layout.json.bak
    使用默认布局
```

---

## 🎯 实际应用场景

### 场景1：正常打开项目
```
✅ 所有配置正确加载
✅ 节点在原来的位置
✅ 节点保持自定义颜色
✅ 画布视图恢复到上次关闭时的状态
```

### 场景2：移动项目文件夹
```
⚠️ 风险：绝对路径可能失效
✅ 解决：重新打开项目后，系统会自动扫描 nodes/ 目录
✅ 结果：节点配置仍然有效（相对路径或重新识别）
```

### 场景3：多个BNOS实例操作同一项目
```
❌ 不支持并发写入
⚠️ 风险：可能导致配置冲突
✅ 建议：一次只打开一个BNOS实例操作同一项目
```

### 场景4：手动编辑配置文件
```
✅ 支持手动编辑
⚠️ 注意：确保JSON格式正确
✅ 提示：编辑后重启BNOS即可生效
```

---

## 🔧 技术实现细节

### 保存时机

1. **自动保存**：
   - 关闭项目时
   - 窗口关闭时
   - 定时器触发（每30秒）

2. **手动保存**：
   - 点击"保存布局"按钮
   - 修改节点颜色后立即保存

### 加载时机

1. **打开项目时**：
   ```python
   def open_project(self, project_path):
       self.current_project_path = project_path
       self.canvas.load_layout(project_path)  # ← 这里
       self.refresh_nodes()
   ```

2. **刷新节点列表时**：
   ```python
   def refresh_nodes(self):
       # 扫描 nodes/ 目录
       # 加载每个节点的 config.json
       # 同步到画布
   ```

### 代码位置

| 功能 | 文件 | 方法 |
|------|------|------|
| 保存布局 | `ui/canvas_widget.py` | `save_layout()` |
| 加载布局 | `ui/canvas_widget.py` | `load_layout()` |
| 保存颜色 | `ui/canvas_widget.py` | `_save_color_settings()` |
| 加载颜色 | `ui/canvas_widget.py` | `_load_color_settings()` |
| 加载节点颜色 | `ui/canvas_widget.py` | `NodeItem._load_node_custom_colors()` |
| 设置节点颜色 | `ui/canvas_widget.py` | `change_node_*_color()` |

---

## ⚠️ 注意事项

### 1. **配置文件的重要性**
- `canvas_layout.json` - 丢失会导致节点位置重置
- `color_settings.json` - 丢失会导致画布颜色恢复默认
- 各节点 `config.json` - 丢失会导致节点配置丢失

**建议**：定期备份这些文件，或使用Git版本控制。

### 2. **不要手动删除配置文件**
- 删除 `canvas_layout.json` → 节点位置丢失
- 删除 `color_settings.json` → 画布颜色恢复默认
- 删除节点 `config.json` → 节点配置丢失

### 3. **跨平台兼容性**
- Windows/macOS/Linux 的JSON文件格式相同
- 路径分隔符差异由Python自动处理
- 颜色值使用十六进制格式，跨平台一致

### 4. **版本升级兼容**
- 旧版本的布局文件可以正常加载
- 新版本会增加 `custom_colors` 字段
- 向后兼容，不会破坏旧数据

---

## 📊 配置对比表

| 配置类型 | 存储位置 | 跟随项目 | 防覆盖 | 备份机制 |
|---------|---------|---------|--------|---------|
| 节点坐标 | `canvas_layout.json` | ✅ 是 | ✅ 智能合并 | ❌ 无 |
| 连线关系 | `canvas_layout.json` | ✅ 是 | ✅ 避免重复 | ❌ 无 |
| 视图状态 | `canvas_layout.json` | ✅ 是 | ✅ 每次覆盖 | ❌ 无 |
| 画布颜色 | `color_settings.json` | ✅ 是 | ✅ 每次覆盖 | ❌ 无 |
| 节点颜色(主) | 各节点 `config.json` | ✅ 是 | ✅ 手动修改保护 | ❌ 无 |
| 节点颜色(备) | `canvas_layout.json` | ✅ 是 | ✅ 双重备份 | ✅ 有 |

---

## 🎉 总结

### ✅ 已实现的保护

1. **完全跟随项目**：所有配置都保存在项目目录内
2. **独立隔离**：每个项目有独立的配置文件
3. **智能加载**：不会覆盖未修改的配置
4. **双重备份**：节点颜色同时保存在两处
5. **损坏恢复**：JSON解析失败时有备份机制

### 🚀 最新增强（本次更新）

- ✅ `canvas_layout.json` 现在包含 `custom_colors` 字段
- ✅ 加载时优先使用节点 `config.json` 的颜色
- ✅ 如果 `config.json` 缺失，使用 `canvas_layout.json` 的备份
- ✅ 自动添加的节点也能恢复颜色配置

### 💡 最佳实践

1. **定期提交Git**：将配置文件纳入版本控制
2. **避免并发编辑**：一次只打开一个BNOS实例
3. **谨慎手动编辑**：确保JSON格式正确
4. **备份重要项目**：复制整个项目文件夹

---

**最后更新**: 2026-04-29  
**版本**: v2.2 - 增强节点颜色双重备份机制  
**状态**: ✅ 完全跟随项目，不会被覆盖

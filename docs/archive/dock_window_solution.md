# Dock窗口尺寸持久化和智能化布局方案

## 一、问题概述

当前应用程序的dock窗口存在以下问题：
1. 窗口尺寸调整后重启无法保持
2. 缺少窗口吸附功能
3. 多个dock组合时没有智能尺寸分配
4. 用户交互体验有待提升
5. 在不同屏幕尺寸下布局适配性不足

## 二、目标

参考Adobe Photoshop的dock窗口特性，实现以下功能：

### 2.1 核心功能
1. **Dock窗口吸附功能** - 窗口靠近边缘或其他窗口时自动吸附并形成组合布局
2. **智能尺寸分配机制** - 多个dock窗口组合时，实现类似Photoshop的智能尺寸分配
3. **尺寸持久化系统** - 用户调整后的dock窗口尺寸在应用重启后保持
4. **用户交互控制** - 提供分隔线拖拽、双击重置等功能
5. **响应式布局规则** - 在不同屏幕分辨率和窗口大小变化时保持布局合理

### 2.2 技术目标
- 代码架构清晰，易于维护和扩展
- 性能影响最小化
- 与现有系统良好兼容
- 渐进式开发，不破坏现有功能

---

## 三、系统架构设计

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        用户交互层                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  拖拽控制器  │  │ 双击重置器   │  │ 快捷操作器   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                        业务逻辑层                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  吸附管理器   │  │ 尺寸分配器   │  │ 布局协调器   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                        数据持久层                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ 状态序列化   │  │ 配置读写器   │  │ 版本管理器   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                        基础组件层                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  增强型Dock  │  │ 分割线控件   │  │ 布局容器     │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 核心模块设计

#### 3.2.1 增强型Dock基类（SmartDock）
- 继承自 `BnosDock`
- 新增：吸附区域检测
- 新增：尺寸调整事件监听
- 新增：布局信息暴露接口

#### 3.2.2 吸附管理器（SnapManager）
- 检测窗口边缘和其他dock的接近
- 计算吸附位置
- 执行吸附动画
- 管理吸附区域（5-10像素可配置）

#### 3.2.3 尺寸分配器（SizeAllocator）
- 等比例分配算法
- 智能比例分配（根据历史使用习惯）
- 最小尺寸保护
- 冲突检测和解决

#### 3.2.4 布局持久化管理器（LayoutPersistenceManager）
- 序列化布局配置
- 版本兼容处理
- 自动保存（间隔/事件触发）
- 配置恢复

---

## 四、详细实现方案

### 4.1 数据模型设计

#### 4.1.1 Dock布局配置结构
```python
# app_config.json 新增配置项
{
  "dock_layouts": {
    "version": "1.0",
    "main_window": {
      "left_docks": [
        {
          "id": "node_list",
          "width": 280,
          "height": 600,
          "is_visible": true,
          "is_collapsed": false,
          "snap_position": "left_edge",
          "relative_to": null
        }
      ],
      "right_docks": [
        {
          "id": "resource_monitor",
          "width": 300,
          "height": 500,
          "is_visible": true,
          "is_collapsed": false,
          "snap_position": "right_edge",
          "relative_to": null
        },
        {
          "id": "node_monitor",
          "width": 300,
          "height": 400,
          "is_visible": true,
          "is_collapsed": false,
          "snap_position": "below",
          "relative_to": "resource_monitor"
        }
      ],
      "bottom_docks": [
        {
          "id": "terminal",
          "width": 800,
          "height": 250,
          "is_visible": true,
          "is_collapsed": false,
          "snap_position": "bottom_edge",
          "relative_to": null
        }
      ],
      "floating_docks": []
    },
    "canvas_host": {
      "terminal_dock": {
        "width": 600,
        "height": 300,
        "is_visible": true,
        "snap_position": "bottom"
      }
    },
    "global_settings": {
      "snap_distance": 8,
      "animation_duration": 200,
      "auto_save_interval": 30000,
      "minimum_dock_width": 150,
      "minimum_dock_height": 100,
      "double_click_reset_enabled": true
    }
  }
}
```

### 4.2 核心算法设计

#### 4.2.1 吸附检测算法
```python
class SnapManager:
    SNAP_DISTANCE = 8  # 像素
    
    def check_snap(self, dock, all_docks, parent_geometry):
        """
        检测dock是否应该吸附到某个位置
        
        Returns:
            dict: 吸附信息 {snap_type, target, position}
        """
        # 1. 检测边缘吸附
        edge_snap = self._check_edge_snap(dock, parent_geometry)
        if edge_snap:
            return edge_snap
        
        # 2. 检测与其他dock的吸附
        for other_dock in all_docks:
            if other_dock == dock:
                continue
            dock_snap = self._check_dock_snap(dock, other_dock)
            if dock_snap:
                return dock_snap
        
        return None
    
    def _check_edge_snap(self, dock, parent_geometry):
        """检测是否吸附到边缘"""
        dock_geo = dock.geometry()
        
        # 检测左边缘
        if abs(dock_geo.left() - parent_geometry.left()) < self.SNAP_DISTANCE:
            return {
                'snap_type': 'left_edge',
                'target': None,
                'position': (parent_geometry.left(), dock_geo.top())
            }
        
        # 检测右边缘
        if abs(dock_geo.right() - parent_geometry.right()) < self.SNAP_DISTANCE:
            return {
                'snap_type': 'right_edge',
                'target': None,
                'position': (parent_geometry.right() - dock_geo.width(), dock_geo.top())
            }
        
        # 检测底部边缘
        if abs(dock_geo.bottom() - parent_geometry.bottom()) < self.SNAP_DISTANCE:
            return {
                'snap_type': 'bottom_edge',
                'target': None,
                'position': (dock_geo.left(), parent_geometry.bottom() - dock_geo.height())
            }
        
        return None
    
    def _check_dock_snap(self, dock, other_dock):
        """检测是否吸附到另一个dock"""
        dock_geo = dock.geometry()
        other_geo = other_dock.geometry()
        
        # 检测吸附到下方
        if (abs(dock_geo.top() - other_geo.bottom()) < self.SNAP_DISTANCE and
            self._is_horizontally_aligned(dock_geo, other_geo)):
            return {
                'snap_type': 'below',
                'target': other_dock,
                'position': (other_geo.left(), other_geo.bottom())
            }
        
        # 检测吸附到上方
        if (abs(dock_geo.bottom() - other_geo.top()) < self.SNAP_DISTANCE and
            self._is_horizontally_aligned(dock_geo, other_geo)):
            return {
                'snap_type': 'above',
                'target': other_dock,
                'position': (other_geo.left(), other_geo.top() - dock_geo.height())
            }
        
        # 检测吸附到右侧
        if (abs(dock_geo.left() - other_geo.right()) < self.SNAP_DISTANCE and
            self._is_vertically_aligned(dock_geo, other_geo)):
            return {
                'snap_type': 'right_of',
                'target': other_dock,
                'position': (other_geo.right(), other_geo.top())
            }
        
        # 检测吸附到左侧
        if (abs(dock_geo.right() - other_geo.left()) < self.SNAP_DISTANCE and
            self._is_vertically_aligned(dock_geo, other_geo)):
            return {
                'snap_type': 'left_of',
                'target': other_dock,
                'position': (other_geo.left() - dock_geo.width(), other_geo.top())
            }
        
        return None
```

#### 4.2.2 智能尺寸分配算法
```python
class SizeAllocator:
    def allocate_sizes(self, dock_group, available_space, allocation_type='equal'):
        """
        在一组dock中智能分配尺寸
        
        Args:
            dock_group: dock列表
            available_space: 可用空间（宽度或高度）
            allocation_type: 分配类型 ('equal', 'weighted', 'history_based')
        """
        if allocation_type == 'equal':
            return self._equal_allocation(dock_group, available_space)
        elif allocation_type == 'weighted':
            return self._weighted_allocation(dock_group, available_space)
        elif allocation_type == 'history_based':
            return self._history_based_allocation(dock_group, available_space)
        else:
            return self._equal_allocation(dock_group, available_space)
    
    def _equal_allocation(self, dock_group, available_space):
        """等比例分配"""
        if not dock_group:
            return {}
        
        # 减去最小尺寸总和
        min_total = sum(dock.min_size for dock in dock_group)
        remaining = available_space - min_total
        
        if remaining <= 0:
            # 空间不足，按最小尺寸分配
            return {dock: dock.min_size for dock in dock_group}
        
        # 平均分配剩余空间
        each_extra = remaining / len(dock_group)
        sizes = {}
        for dock in dock_group:
            sizes[dock] = dock.min_size + each_extra
        
        return sizes
    
    def _weighted_allocation(self, dock_group, available_space):
        """按权重分配（根据dock的重要性）"""
        # 实现权重分配逻辑
        pass
    
    def _history_based_allocation(self, dock_group, available_space):
        """基于历史使用习惯分配"""
        # 实现基于历史的分配逻辑
        pass
```

### 4.3 实现步骤

#### 阶段1：增强型Dock基类和基础持久化
1. 创建 `SmartDock` 类继承自 `BnosDock`
2. 新增尺寸调整事件监听
3. 扩展 `app_config.json` 结构
4. 实现基础的尺寸保存和恢复

#### 阶段2：吸附功能实现
1. 创建 `SnapManager` 类
2. 实现吸附检测算法
3. 实现吸附动画效果
4. 测试吸附功能

#### 阶段3：尺寸分配和用户交互
1. 创建 `SizeAllocator` 类
2. 实现分割线拖拽功能
3. 实现双击重置功能
4. 测试用户交互

#### 阶段4：响应式布局
1. 实现屏幕尺寸监听
2. 实现布局自适应算法
3. 实现最小尺寸保护
4. 测试响应式布局

#### 阶段5：集成和优化
1. 集成所有模块
2. 性能优化
3. 全面测试
4. 文档完善

---

## 五、文件结构变更

```
ui/
├── core/
│   ├── smart_dock.py          # 新增：增强型Dock基类
│   ├── snap_manager.py         # 新增：吸附管理器
│   ├── size_allocator.py       # 新增：尺寸分配器
│   ├── layout_persistence.py   # 新增：布局持久化管理器
│   ├── splitter_handle.py      # 新增：分割线控件
│   ├── bnos_dock.py            # 修改：增强现有功能
│   ├── window_state_manager.py # 修改：整合新功能
│   ├── dock_manager.py         # 修改：使用新模块
│   └── app_config.py           # 修改：扩展配置结构
└── main_window.py              # 修改：集成新功能
```

---

## 六、可行性分析

### 6.1 技术实现难度

| 功能模块 | 难度 | 说明 |
|---------|------|------|
| 增强型Dock基类 | ⭐⭐ | 基于现有BnosDock扩展，难度适中 |
| 吸附功能 | ⭐⭐⭐ | 算法逻辑相对复杂，但技术可行 |
| 尺寸分配 | ⭐⭐ | 算法设计是关键，实现难度适中 |
| 持久化系统 | ⭐⭐ | 已有基础框架，扩展相对容易 |
| 用户交互 | ⭐⭐⭐ | 需要处理多种手势，细节较多 |
| 响应式布局 | ⭐⭐ | 边界情况较多，但技术可行 |

**总体评估**：技术实现完全可行，预估难度中等。

### 6.2 性能影响评估

1. **吸附检测**：每30ms检测一次，每次检测O(n)复杂度，n为dock数量，性能影响极小
2. **自动保存**：间隔30秒保存一次，增量保存，性能影响可忽略
3. **布局计算**：仅在布局变化时计算，性能影响极小
4. **内存占用**：新增模块约增加500KB内存占用，影响可忽略

**总体评估**：性能影响极小，用户感知不到。

### 6.3 与现有系统兼容性

1. **向后兼容**：新增功能为可选，现有功能完全保留
2. **配置兼容**：新旧配置格式兼容，支持平滑升级
3. **API兼容**：现有接口保持不变，新增接口独立
4. **UI兼容**：新功能UI与现有风格统一

**总体评估**：兼容性良好，无破坏性变更。

### 6.4 开发周期预估

| 阶段 | 功能模块 | 预估时间 |
|------|---------|---------|
| 1 | 增强型Dock基类和基础持久化 | 2-3天 |
| 2 | 吸附功能实现 | 3-4天 |
| 3 | 尺寸分配和用户交互 | 3-4天 |
| 4 | 响应式布局 | 2-3天 |
| 5 | 集成和优化 | 2-3天 |
| **总计** | | **12-17天** |

### 6.5 用户体验改进效果

1. **直观性**：吸附功能让布局更直观，类似Photoshop体验
2. **效率**：持久化避免重复调整，提升工作效率
3. **灵活性**：丰富的交互方式满足不同用户习惯
4. **稳定性**：窗口位置和尺寸不再随机变化
5. **专业感**：整体UI专业度提升

**总体评估**：用户体验将有显著提升。

---

## 七、测试方案

### 7.1 单元测试
- 吸附检测算法测试
- 尺寸分配算法测试
- 配置读写测试
- 边界条件测试

### 7.2 集成测试
- 完整流程测试
- 多dock交互测试
- 重启恢复测试
- 配置兼容性测试

### 7.3 用户体验测试
- 真实场景测试
- 性能感知测试
- 易用性评估

### 7.4 兼容性测试
- 不同屏幕尺寸测试
- 不同分辨率测试
- 新旧配置版本测试

---

## 八、风险评估和应对

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|---------|
| 吸附判断误触发 | 中 | 中 | 增加灵敏度调节，记录用户操作习惯优化算法 |
| 配置损坏丢失 | 低 | 高 | 配置文件自动备份，支持恢复默认 |
| 性能问题 | 低 | 低 | 优化算法，增加性能监控 |
| 用户不适应新功能 | 中 | 中 | 提供开关选项，保持原有功能可选 |
| 与现有功能冲突 | 低 | 高 | 充分测试，保持API向后兼容 |

---

## 九、后续扩展方向

1. **布局预设**：支持保存和快速切换多种布局方案
2. **拖拽排序**：支持dock之间的拖拽排序
3. **多显示器支持**：优化多显示器环境下的布局体验
4. **AI布局建议**：基于用户习惯推荐最佳布局
5. **主题定制**：支持dock视觉风格的自定义

---

## 十、总结

本方案设计了一套完整的dock窗口智能化布局系统，参考了Adobe Photoshop的成功经验，同时结合了项目实际情况。方案具有以下特点：

1. **功能完整**：覆盖了吸附、尺寸分配、持久化、交互、响应式等核心需求
2. **架构清晰**：分层设计，模块职责明确，易于维护和扩展
3. **可行性高**：技术风险可控，与现有系统兼容性好
4. **用户导向**：以提升用户体验为核心目标
5. **渐进实施**：可以分阶段实施，降低风险

建议按照本方案的5个阶段逐步实施，每个阶段完成后进行充分测试，确保质量和稳定性。

# BNOS Toast通知 - 快速参考

## 🚀 一行代码使用

```python
self.show_toast("消息内容", "类型", 时长)
```

## 📝 参数速查

| 参数 | 可选值 | 默认值 | 说明 |
|------|--------|--------|------|
| message | 任意字符串 | - | 通知文本 |
| toast_type | info / success / warning / error | info | 通知类型 |
| duration | 整数（毫秒） | 3000 | 显示时长 |

## 🎨 类型与颜色

- **info** → 灰色 `rgba(50, 50, 50, 230)`
- **success** → 绿色 `rgba(76, 175, 80, 230)`
- **warning** → 橙色 `rgba(255, 152, 0, 230)`
- **error** → 红色 `rgba(244, 67, 54, 230)`

## ⏱️ 时长建议

- **2000ms** - 简短反馈
- **3000ms** - 一般通知（默认）
- **4000ms** - 重要信息
- **5000ms** - 错误详情

## 💡 常用示例

```python
# 成功提示
self.show_toast("保存成功", "success")

# 错误提示
self.show_toast("操作失败", "error", 5000)

# 警告提示
self.show_toast("注意：数据未保存", "warning")

# 信息提示
self.show_toast("节点已加载", "info", 2000)
```

## 📍 位置

固定在窗口**右下角**，距离边缘**20px**

## ✨ 动画效果

- **淡入**：300ms
- **停留**：自定义时长
- **淡出**：300ms
- **帧率**：60fps流畅动画

## 🔍 测试

运行测试脚本查看效果：
```bash
python test_toast.py
```

---

**更多文档**：
- [TOAST_USAGE.md](./TOAST_USAGE.md) - 完整使用指南
- [TOAST_EXAMPLES.md](./TOAST_EXAMPLES.md) - 实际代码示例
- [TOAST_IMPLEMENTATION_SUMMARY.md](./TOAST_IMPLEMENTATION_SUMMARY.md) - 实现总结

# 🚀 BNOS 项目 GitHub 自动更新工具

## 📦 包含的脚本

### 1. **update_github.bat** - Windows批处理版本（推荐）
- ✅ 双击即可运行，最简单
- ✅ 自动生成带时间戳的提交信息
- ✅ 完整的错误处理
- 📝 语言：英文（避免编码问题）

**使用方法**：
```
双击 update_github.bat 文件
```

### 2. **update_github.ps1** - PowerShell增强版
- ✅ 支持自定义提交信息
- ✅ 彩色输出和修改预览
- ✅ 更友好的交互体验
- 📝 语言：英文

**使用方法**：
```powershell
# 首次使用需要设置执行策略
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 运行脚本
.\update_github.ps1
```

## 🎯 快速开始

### 方式一：最简单（推荐新手）
1. 在文件资源管理器中找到 `update_github.bat`
2. 双击运行
3. 等待完成，看到 "SUCCESS" 提示

### 方式二：自定义提交信息（推荐开发者）
1. 右键点击 `update_github.ps1`
2. 选择"使用PowerShell运行"
3. 输入您的提交信息（或直接回车使用默认）
4. 等待完成

## 📋 自动化流程

```
启动脚本
    ↓
✅ 配置Git用户 (LiuStar / 1240543656@qq.com)
    ↓
✅ 检查Git状态和修改
    ↓
✅ 添加所有文件 (git add .)
    ↓
✅ 提交更改 (git commit -m "BNOS auto update - 时间戳")
    ↓
✅ 拉取远程代码 (git pull origin main)
    ↓
✅ 推送到GitHub (git push origin main)
    ↓
🎉 完成！
```

## ⚙️ 自定义配置

### 修改Git用户信息

编辑脚本中的以下行：

**update_github.bat** (第7-8行):
```batch
git config --global user.name "Your Name"
git config --global user.email "your@email.com"
```

**update_github.ps1** (第9-10行):
```powershell
git config --global user.name "Your Name"
git config --global user.email "your@email.com"
```

### 修改分支名称

如果您的主分支不是 `main`，修改：

**update_github.bat** (第52、59行):
```batch
git pull origin main
git push origin main
```

**update_github.ps1** (第71、81行):
```powershell
git pull origin main
git push origin main
```

改为您的分支名，如 `master` 或 `develop`。

## ❗ 注意事项

1. **确保已安装Git**：运行 `git --version` 检查
2. **确保是Git仓库**：项目根目录应有 `.git` 文件夹
3. **确保有推送权限**：配置SSH密钥或HTTPS凭据
4. **网络连接**：确保可以访问GitHub
5. **冲突处理**：如遇合并冲突，需手动解决后重新运行

## 🔧 故障排除

### 问题1：提示"Not a Git repository"
**解决**：确保在项目根目录运行脚本

### 问题2：PowerShell脚本无法运行
**解决**：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 问题3：推送失败，认证错误
**解决**：
- HTTPS: 运行 `git credential-manager configure`
- SSH: 检查SSH密钥配置

### 问题4：中文显示乱码
**解决**：脚本已使用英文避免此问题

## 📊 脚本对比

| 特性 | update_github.bat | update_github.ps1 |
|------|-------------------|-------------------|
| 易用性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 自定义提交信息 | ❌ 自动 | ✅ 可输入 |
| 彩色输出 | ❌ | ✅ |
| 修改预览 | ❌ | ✅ |
| 编码兼容性 | ✅ 英文 | ✅ 英文 |
| 推荐用户 | 所有人 | 开发者 |

## 💡 最佳实践

1. **频繁提交**：每完成小功能就提交一次
2. **清晰说明**：使用ps1版本编写有意义的提交信息
3. **提交前检查**：运行 `git status` 确认修改
4. **定期推送**：避免本地积累过多未推送提交
5. **备份重要更改**：重大修改前先创建分支

## 📞 更多信息

详细使用指南请查看：[UPDATE_GITHUB_GUIDE.md](UPDATE_GITHUB_GUIDE.md)

---

**维护者**: LiuStar  
**邮箱**: 1240543656@qq.com  
**最后更新**: 2026-04-29

# BNOS 项目 GitHub 自动更新脚本使用指南

## 📋 概述

BNOS项目提供了两个自动化脚本，帮助您快速将代码更新上传到GitHub仓库。

## 🚀 可用脚本

### 1. **update_github.bat** (Windows批处理版本)
- ✅ 简单直接，双击即可运行
- ✅ 自动生成带时间戳的提交信息
- ✅ 适合快速提交场景

### 2. **update_github.ps1** (PowerShell增强版)
- ✅ 支持自定义提交信息
- ✅ 彩色输出，更友好的用户体验
- ✅ 详细的修改文件列表预览
- ✅ 适合需要编写提交说明的场景

## 📖 使用方法

### 方法一：双击运行（推荐）

1. 在文件资源管理器中找到 `update_github.bat` 或 `update_github.ps1`
2. 双击运行
3. 等待脚本自动完成所有步骤
4. 看到"🎉 代码更新上传完成！"提示即成功

### 方法二：命令行运行

#### 使用批处理脚本：
```bash
cd d:\bnos_new\BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform
update_github.bat
```

#### 使用PowerShell脚本：
```powershell
cd d:\bnos_new\BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform
.\update_github.ps1
```

> ⚠️ **注意**：首次运行PowerShell脚本可能需要设置执行策略：
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

## 🔧 脚本功能详解

### 完整工作流程

```
启动脚本
    ↓
[1] 配置Git用户信息 (LiuStar / 1240543656@qq.com)
    ↓
[2] 检查Git状态和修改文件
    ↓
[3] 添加所有修改文件 (git add .)
    ↓
[4] 提交更改 (git commit)
    ├─ bat版本: 自动生成带时间戳的提交信息
    └─ ps1版本: 可自定义提交信息
    ↓
[5] 拉取远程最新代码 (git pull origin main)
    ↓
[6] 推送到GitHub (git push origin main)
    ↓
完成！✅
```

### 错误处理

脚本包含完善的错误检测：

| 错误类型 | 处理方式 |
|---------|---------|
| 非Git仓库 | 提示并退出 |
| 无修改文件 | 提示无需提交 |
| 添加失败 | 显示错误并退出 |
| 提交失败 | 显示错误并退出 |
| 拉取冲突 | 提示手动解决 |
| 推送失败 | 检查网络/权限 |

## 💡 使用场景

### ✅ 适合使用自动脚本的场景
- **日常开发**：频繁的代码保存和提交
- **功能完成**：完成一个小功能后快速提交
- **备份代码**：定期将本地代码同步到GitHub
- **团队协作**：确保代码及时推送到远程仓库

### ❌ 不适合的场景
- **重要提交**：需要详细编写提交说明时
- **复杂变更**：涉及多个模块的大规模重构
- **敏感信息**：需要仔细审查修改内容时
- **分支管理**：需要在不同分支间切换时

## 📝 自定义配置

### 修改Git用户信息

编辑脚本中的以下行：

**bat版本** (第7-8行):
```batch
git config --global user.name "您的用户名"
git config --global user.email "您的邮箱"
```

**ps1版本** (第9-10行):
```powershell
git config --global user.name "您的用户名"
git config --global user.email "您的邮箱"
```

### 修改提交分支

如果主分支不是 `main`，修改以下行：

**bat版本** (第33、40行):
```batch
git pull origin main
git push origin main
```

**ps1版本** (第71、81行):
```powershell
git pull origin main
git push origin main
```

将 `main` 改为您的分支名（如 `master`、`develop` 等）。

### 修改默认提交信息格式

**bat版本** (第29行):
```batch
set commit_msg=您的前缀 - %datetime:~0,4%-%datetime:~4,2%-%datetime:~6,2% %datetime:~8,2%:%datetime:~10,2%
```

**ps1版本** (第43行):
```powershell
$default_msg = "您的前缀 - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
```

## ⚠️ 注意事项

1. **首次使用前**：
   - 确保已安装Git
   - 确保当前目录是Git仓库
   - 确保已配置远程仓库地址

2. **网络连接**：
   - 确保可以访问GitHub
   - 如有代理，请提前配置Git代理

3. **权限问题**：
   - 确保有推送权限
   - 如使用SSH，确保密钥已配置
   - 如使用HTTPS，确保凭据已缓存

4. **冲突处理**：
   - 如遇到合并冲突，脚本会提示
   - 需手动解决冲突后重新运行

5. **大文件警告**：
   - Git不建议提交超过100MB的文件
   - 大文件请使用Git LFS

## 🔍 常见问题

### Q1: 提示"不是Git仓库"？
**A**: 确保在项目根目录运行脚本，该目录应包含 `.git` 文件夹。

### Q2: PowerShell脚本无法运行？
**A**: 以管理员身份运行PowerShell，执行：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Q3: 推送失败，提示认证错误？
**A**: 
- HTTPS方式：运行 `git credential-manager configure` 重新配置凭据
- SSH方式：检查SSH密钥是否正确配置

### Q4: 如何查看提交历史？
**A**: 运行 `git log --oneline` 查看简洁的提交历史。

### Q5: 能否撤销最后一次提交？
**A**: 运行 `git reset --soft HEAD~1` 撤销提交但保留更改。

## 📊 脚本对比

| 特性 | update_github.bat | update_github.ps1 |
|------|-------------------|-------------------|
| 易用性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 自定义提交信息 | ❌ | ✅ |
| 彩色输出 | ❌ | ✅ |
| 修改预览 | ❌ | ✅ |
| 兼容性 | Windows所有版本 | Windows 7+ |
| 推荐场景 | 快速提交 | 常规开发 |

## 🎯 最佳实践

1. **频繁小提交**：每完成一个小功能就提交一次
2. **清晰的提交信息**：使用ps1版本编写有意义的提交说明
3. **提交前检查**：运行 `git status` 确认修改内容
4. **定期推送**：避免本地积累过多未推送的提交
5. **备份重要更改**：重大修改前先创建分支

## 📞 技术支持

如遇到问题，请检查：
1. Git是否正确安装：`git --version`
2. 远程仓库配置：`git remote -v`
3. 当前分支状态：`git branch`
4. 网络连接：`ping github.com`

---

**最后更新**: 2026-04-29  
**维护者**: LiuStar  
**联系方式**: 1240543656@qq.com

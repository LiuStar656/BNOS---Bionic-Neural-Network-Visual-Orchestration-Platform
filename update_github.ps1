# BNOS 项目一键自动更新上传脚本 (PowerShell版本)
# 功能更强大，支持交互式提交信息输入

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "     BNOS 项目 一键自动更新上传 (PowerShell)" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# ===================== 配置Git用户信息 =====================
git config --global user.name "LiuStar"
git config --global user.email "1240543656@qq.com"
Write-Host "✅ 已配置：用户名 LiuStar，邮箱 1240543656@qq.com" -ForegroundColor Green
Write-Host ""

# ===================== 1. 检查Git状态 =====================
Write-Host "[1/6] 正在检查Git状态..." -ForegroundColor Yellow
$status = git status --short
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Git仓库检测失败！请确认当前目录是Git仓库" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

if ([string]::IsNullOrWhiteSpace($status)) {
    Write-Host "⚠️  没有需要提交的更改" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "==============================================" -ForegroundColor Cyan
    Write-Host "     所有文件已是最新状态" -ForegroundColor Green
    Write-Host "==============================================" -ForegroundColor Cyan
    Read-Host "按回车键退出"
    exit 0
}

Write-Host "📝 检测到以下修改：" -ForegroundColor Cyan
Write-Host $status -ForegroundColor White
Write-Host ""

# ===================== 2. 添加所有修改 =====================
Write-Host "[2/6] 正在添加所有修改文件..." -ForegroundColor Yellow
git add .
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 添加文件失败！" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}
Write-Host "✅ 文件添加完成" -ForegroundColor Green
Write-Host ""

# ===================== 3. 输入提交信息 =====================
Write-Host "[3/6] 请输入提交信息（直接回车使用默认信息）:" -ForegroundColor Yellow
$default_msg = "BNOS项目自动更新 - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
$user_msg = Read-Host "提交信息"

if ([string]::IsNullOrWhiteSpace($user_msg)) {
    $commit_msg = $default_msg
} else {
    $commit_msg = $user_msg
}

Write-Host "📝 提交信息: $commit_msg" -ForegroundColor Cyan
Write-Host ""

# ===================== 4. 提交更改 =====================
Write-Host "[4/6] 正在提交更新..." -ForegroundColor Yellow
git commit -m $commit_msg
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 提交失败！" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}
Write-Host "✅ 提交成功" -ForegroundColor Green
Write-Host ""

# ===================== 5. 拉取最新代码 =====================
Write-Host "[5/6] 正在拉取远程最新代码..." -ForegroundColor Yellow
git pull origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  拉取代码时出现冲突或错误" -ForegroundColor Yellow
    Write-Host "请手动解决冲突后再次运行此脚本" -ForegroundColor Yellow
    Read-Host "按回车键退出"
    exit 1
}
Write-Host "✅ 拉取完成" -ForegroundColor Green
Write-Host ""

# ===================== 6. 推送到GitHub =====================
Write-Host "[6/6] 正在推送到 GitHub 仓库..." -ForegroundColor Yellow
git push origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 推送失败！请检查网络连接或权限" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}
Write-Host "✅ 推送成功" -ForegroundColor Green
Write-Host ""

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "     🎉 代码更新上传完成！" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""
Read-Host "按回车键退出"

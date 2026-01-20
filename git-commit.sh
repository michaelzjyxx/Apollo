#!/bin/bash
# Git 快速提交脚本

# 检查是否提供了提交信息
if [ -z "$1" ]; then
    echo "❌ 请提供提交信息"
    echo "用法: ./git-commit.sh \"你的提交信息\""
    exit 1
fi

# 显示当前状态
echo "📋 当前修改的文件："
git status --short

echo ""
echo "📦 添加所有修改..."
git add .

echo ""
echo "💾 提交更改..."
git commit -m "$1

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

echo ""
echo "🚀 推送到 GitHub..."
git push

echo ""
echo "✅ 完成！查看仓库: https://github.com/michaelzjyxx/Apollo"

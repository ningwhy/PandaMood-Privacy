#!/bin/sh
# 生成静态站输出目录 dist/。
#
# 为什么要单独一个 dist/：
# 站点根目录里混着 tool/（ASC 元数据脚本与备份），那不是网页内容，
# 绝不能作为静态资源上传——否则 .py 源码和备份 JSON 会被公网直接下载。
# Cloudflare Pages / Workers 的 assets.directory 会把目录下所有文件
# 原样发布，所以这里显式挑白名单，而不是「排除黑名单」。
set -e

ROOT=$(cd "$(dirname "$0")/.." && pwd)
DIST="$ROOT/dist"

rm -rf "$DIST"
mkdir -p "$DIST"

# 站点根级文件
for f in index.html style.css 404.html _headers; do
  cp "$ROOT/$f" "$DIST/$f"
done

# 站点目录
for d in assets privacy support; do
  cp -R "$ROOT/$d" "$DIST/$d"
done

# 清掉 macOS 垃圾与 VCS 残留
find "$DIST" -name '.DS_Store' -delete
find "$DIST" -name '.git' -type d -exec rm -rf {} + 2>/dev/null || true

echo "dist/ 已生成："
echo "  文件数: $(find "$DIST" -type f | wc -l | tr -d ' ')"
echo "  体积:   $(du -sh "$DIST" | cut -f1)"
echo "  tool/ 未包含: $([ -d "$DIST/tool" ] && echo '❌ 已混入!' || echo '✅')"

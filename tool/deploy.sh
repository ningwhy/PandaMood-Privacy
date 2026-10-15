#!/bin/sh
# 部署到 Cloudflare。
#
# 用法：
#   sh tool/deploy.sh login     # 首次：浏览器 OAuth 授权
#   sh tool/deploy.sh pages     # 部署到 Cloudflare Pages（默认，域名 *.pages.dev）
#   sh tool/deploy.sh workers   # 部署到 Workers + static assets（域名 *.workers.dev）
#
# 为什么命令写得这么绕：wrangler 装在本机隔离的 node workspace 里，
# 没有全局安装（不污染系统环境），直接敲 `wrangler` 会 command not found。
# 这里优先用系统里的 wrangler，没有就回落到隔离路径。
#
# 为什么两条路线都要留：2026-10 起 Cloudflare 把 Pages 的 Dashboard 创建入口
# 藏进了 Workers 流程，但 pages 的 CLI 与 API 完全没被砍。命令行建项目、
# 传产物都不经过 Dashboard，入口找不到也照样能部署。
set -e

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

PROJECT=panda-mood-diary-privacy

if command -v wrangler >/dev/null 2>&1; then
  WRANGLER=wrangler
else
  WRANGLER_BIN=/Users/bot/.workbuddy/binaries/node/workspace/node_modules/wrangler/bin/wrangler.js
  NODE_BIN=/Users/bot/.workbuddy/binaries/node/versions/22.22.2-6/bin/node
  if [ ! -f "$WRANGLER_BIN" ]; then
    echo "wrangler 未安装。先装："
    echo "  cd /Users/bot/.workbuddy/binaries/node/workspace && npm install wrangler"
    exit 1
  fi
  WRANGLER="$NODE_BIN $WRANGLER_BIN"
fi

CMD=${1:-pages}

case "$CMD" in
  login)
    $WRANGLER login
    ;;
  pages)
    sh tool/build_dist.sh
    # 项目已存在时 create 会报错，属预期，吞掉即可
    $WRANGLER pages project create "$PROJECT" --production-branch=main 2>/dev/null || true
    $WRANGLER pages deploy dist --project-name="$PROJECT" --branch=main
    echo ""
    echo "部署完成。上线后记得回刷 ASC 三 URL："
    echo "  python3 tool/asc_metadata.py --urls-only"
    ;;
  workers)
    sh tool/build_dist.sh
    $WRANGLER deploy
    echo ""
    echo "部署完成。注意 Workers 域名是 *.workers.dev，与 ASC 里已填的 *.pages.dev 不同，"
    echo "必须回刷 ASC 三 URL："
    echo "  python3 tool/asc_metadata.py --urls-only"
    ;;
  *)
    echo "用法: sh tool/deploy.sh [login|pages|workers]"
    exit 1
    ;;
esac

# panda-privacy

「熊猫心情日记」（App Store ID `1506120121`）的**官网 + 法务与支持静态站**，整站部署到 Cloudflare Pages。

| 路径 | 内容 | ASC 对应字段 |
|---|---|---|
| `/` | 产品介绍官网 | `marketingUrl` |
| `/support/` | 支持与常见问题（中英双语，单页） | `supportUrl` |
| `/privacy/zh-Hans.html` | 隐私政策（中文） | `privacyPolicyUrl`（zh-Hans） |
| `/privacy/en.html` | 隐私政策（英文） | `privacyPolicyUrl`（en-AU / en-GB） |

## 文件结构

```
index.html              产品官网（手写，根路径）      ← marketingUrl
style.css               站点样式（手写，含暗色模式）
privacy/zh-Hans.html    隐私政策中文（手写）
privacy/en.html         隐私政策英文（手写）
support/index.html      支持与 FAQ（手写，中英双语）  ← supportUrl
404.html                未找到页
_headers                Cloudflare Pages 安全响应头（含 CSP：script-src 'none'）
README.md               本文件
```

本项目**没有生成器**：文案量可控（4 个页面），手写更直白，也避免「改生成物不改源」的漂移。
若日后扩到 5+ 语种，再引入 `build_legal_site.py` 范式（见 `~/Documents/App/drawing-privacy`）。

## 正式域名（已上线）

`https://pandamood.pages.dev`

| URL | 指向 |
|---|---|
| `https://pandamood.pages.dev/` | 产品官网 ← `marketingUrl` |
| `https://pandamood.pages.dev/support/index.html` | 支持页 ← `supportUrl` |
| `https://pandamood.pages.dev/privacy/zh-Hans.html` | 隐私政策（zh-Hans）← `privacyPolicyUrl` |
| `https://pandamood.pages.dev/privacy/en.html` | 隐私政策（en-AU / en-GB）← `privacyPolicyUrl` |

4 个 URL 已全部 HTTP 200 实测，并已回刷进 ASC 共 9 处
（App 级 privacyPolicyUrl x 3 locale + 版本级 support/marketing x 3 locale），
旧域名零残留。

🔴 **以后换域名必须重跑两步**，只跑一步会漏：
1. `python3 tool/asc_metadata.py --urls-only` —— 只覆盖 App 级隐私 URL
2. 版本级 `supportUrl` / `marketingUrl` 要单独 PATCH，`--urls-only` **不覆盖**这两层

## 部署

```bash
sh tool/deploy.sh login     # 首次：浏览器 OAuth 授权
sh tool/deploy.sh pages     # 部署到 Cloudflare Pages，域名 *.pages.dev
```

脚本封装了 wrangler 的真实路径 —— 它装在本机隔离的 node workspace 里，
没有全局安装，直接敲 `wrangler` 会 command not found。

### Dashboard 里找不到 Pages 创建入口

2026-10 起 Cloudflare 把 Pages 的 Dashboard 入口藏进了 Workers 流程，
官方文档也挂上了 "Are You Sure You Want to Use Pages?" 劝退横幅。
但 **Pages 本身没有被砍**：`wrangler pages project create` /
`wrangler pages deploy` 全部照常工作，压根不经过 Dashboard。

三条路任选：

| 路线 | 做法 | 域名 |
|---|---|---|
| CLI 建 Pages（推荐） | `sh tool/deploy.sh pages` | `*.pages.dev` |
| Workers static assets | `sh tool/deploy.sh workers` | `*.workers.dev` |
| Dashboard 直达链接 | 见下方 | `*.pages.dev` |

Dashboard 直达链接（按钮被藏了，但路由还在）：

```text
https://dash.cloudflare.com/?to=/:account/workers-and-pages/create/pages
```

### 产物与安全

🔴 **必须走 `tool/build_dist.sh`，不要把仓库根当输出目录**：
根目录里有 `tool/`（ASC 脚本 + 备份 JSON），而 assets 目录会被**原样发布**，
那等于把脚本源码挂到公网。脚本用的是白名单复制，不是黑名单排除，
漏文件会直接体现在文件数上（29），比排除法好验证。

`dist/`：29 个文件 / 2.9 MB。已加入 `.gitignore`。

### Pages 与 Workers 的行为差异

| 项 | Pages | Workers |
|---|---|---|
| 输出目录 | 自动识别 | 必须显式 `assets.directory` |
| 404 行为 | 自动猜（看有无 404.html） | 必须显式 `not_found_handling: "404-page"` |
| `_headers` | 生效 | **同样生效**，CSP 无需改动 |
| 域名 | `*.pages.dev` | `*.workers.dev` |

两者静态资源请求都免费；Workers 路线是 asset-only（无 `main`），
不产生 invocation 计费。

⚠️ 拿到真实域名后，**必须回填 ASC 的三个 URL**（隐私 / 支持 / 营销）：
`python3 tool/asc_metadata.py --urls-only`。
填成未部署的域名是死链，审核必挂。

## ASC 现状与回填（2026-10-15 实测，非推测）

### App 基本面

| 项 | 值 |
|---|---|
| App ID | `1506120121` |
| Bundle ID | `com.assistant.mood.diary`（**不可改**，保 listing/评分/搜索权重） |
| Seller | 宏岩 王（Team `FMWDL3P9Z4`，Apple ID `yanoutech@163.com`） |
| 现有版本 | 1.0（build 2，2020-04-24 上传）`READY_FOR_SALE` |
| 本地化 | 仅 3 个：`zh-Hans` / `en-AU` / `en-GB` |

### 🔴 字段层级：与直觉不同（实测确认）

| 字段 | 归属资源 |
|---|---|
| `name` / `subtitle` | **App 级** `appInfoLocalizations` |
| `privacyPolicyUrl` | **两级都有**（App 级可写，版本级也可写） |
| `description` / `keywords` / `promotionalText` / `whatsNew` | **版本级** `appStoreVersionLocalizations` |
| `supportUrl` / `marketingUrl` | **仅版本级** |

⚠️ 把 `keywords` 塞进 App 级会 409；把 `description` 塞进 App 级也 409。

### 🔴 PATCH 是原子的

一个非法字段会让**整批**字段全部不生效，只报一个
`409 ENTITY_ERROR.ATTRIBUTE.UNKNOWN`。所以 `tool/asc_metadata.py`
**逐字段** PATCH —— 一次运行就能既写入可用字段、又打印出「哪些字段属于哪一层」。

### 🔴 已发布版本（READY_FOR_SALE）大部分字段被 Apple 锁定

| 结果 | 字段 | 错误原文 |
|---|---|---|
| ✅ **可改** | `promotionalText`（3 locale 已写入） | — |
| 🔒 锁定 | App 级 `name` / `subtitle` / `privacyPolicyUrl` | `The field 'x' can not be modified in the current state.` |
| 🔒 锁定 | 版本级 `description` / `keywords` | `Attribute 'x' cannot be edited at this time` |

**结论：1.0 的文案与 URL 改不动，全部新元数据必须等 v2.0 版本创建后写入。**
本轮已完成的写入只有 promotionalText ×3。

### 老版遗留问题（v2.0 版本创建后必须修）

| 项 | 老值 | 问题 |
|---|---|---|
| App 级 `privacyPolicyUrl` ×3 | `https://s.orzjun.com/web_html/panda_mood_diary_glass_new_privacy.html` | 老 App 遗留（Word 导出页，域名 `o` 为大写 O），内容不是本 App |
| 版本级 `supportUrl` ×3 | `https://www.facebook.com/Jingqi-103004027902475` | 遗留 Facebook 主页，非支持页 |
| 版本级 `keywords` ×3 | 堆砌 100 字符 | 含「倒数日/大姨妈/记账/宝宝相册/情侣空间」等**完全无关词**（ASO 自我竞争） |
| App 级 `name`/`subtitle` en-AU/en-GB | 中文 | 英文区显示中文 |
| 版本级 `description` | 261/267 字符 | 老版文案，未提任何现有功能 |

### 工具用法

```bash
export ASC_KEY_ID=<你的 Key ID>
export ASC_ISSUER_ID=<你的 Issuer ID>
export ASC_KEY_PATH=~/.appstoreconnect/private_keys/AuthKey_<KEY_ID>.p8

python3 tool/asc_metadata.py --check          # 只校验文案字符数，不连 API
python3 tool/asc_metadata.py --audit          # 只读巡检 ASC 现状
python3 tool/asc_metadata.py                   # 写 App 级文案（逐字段）
python3 tool/asc_metadata.py --version-locals # 写版本级文案
python3 tool/asc_metadata.py --urls-only       # 只写 URL（**站点部署后才可用**）
```

写入前快照存 `tool/backup/appInfoLocalizations_before.json`，可回滚。

⚠️ `--urls-only` 在站点部署前不要跑 —— privacy URL 指向
`pandamood.pages.dev`，未部署就是死链，审核必挂。
（2026-10-15 站点已上线并回刷完成，此条已解除。）

## 内容合规约束（修改前必读）

隐私政策与官网文案必须与**代码事实**一致，改文案前先核对实现：

- **无账号、无服务器、无内购、无广告、无追踪 SDK** —— v2.0 范围冻结的硬约束，
  政策里不得出现任何暗示存在这些的表述；
- **权限只有三项**：照片图库（读用户选中的图，不扫描相册、不写回）、相机（拍照不写入系统相册）、
  通知（每日提醒，内容为中性提示不含日记正文）；不得声称申请了位置/通讯录等；
- **隐私锁没有找回入口** —— 官网与政策都必须如实说明「忘记 PIN 只能卸载重装、数据随之删除」，
  这是隐私锁设计的核心承诺（见 `panda_mood_diary/lib/features/lock/pin_lock.dart` 头注释）；
- **「你的规律」不是医学结论** —— 措辞必须停在「你自己记录里的规律」，
  样本 <3 天或差异 <0.15 时不展示（见 `factor_insight.dart`）；
- **引导复盘不是医疗建议** —— 页面与政策都需带免责句。

## 验收

```bash
# 爬链 + 自检（无死链 / 无 U+FFFD / 无残留占位符）
python3 tool_check_links.py   # 或直接复用 README 记录的自检脚本
```

当前基线：**4 个页面 / 20 条站内链接全部有效**，外部链接 4 个
（App Store、Apple 隐私政策、mailto、canonical）。

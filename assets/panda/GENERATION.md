# 熊猫形象生成记录

> 生成工具：`~/.workbuddy/skills/local-image-studio/scripts/image_studio.py`
> 服务器：ComfyUI @ `192.168.4.66:8188`（RTX 5070 Ti 16G）
> 生成日期：2026-10-15
> 模型：Qwen Image 2.1（cfg=1.0，steps=30）+ MiniMax H3（图生视频）+ rembg（抠图）

## 调性来源（**先读这一节**）

品牌主色 `#FE6655` 取自 **2020 年老版 App Store 图标**（App ID 1506120121）。
老版已有 4.611 分 / 18 条评价，是已经在用户心里建立的视觉印象。

配套两个固定色：

| 用途 | 色值 | 出处 |
|---|---|---|
| 主背景 / 品牌主色 | `#FE6655` | 老版图标底色 |
| 熊猫黑眼圈 | `#3E3E3E` | 老版图标 |
| 书签奶油黄 | `#FFDEB2` | 老版图标 |

**下面第六节记录的第一版（米白 `#FDFBF7`）已被 V3 全部替换。**
保留它是为了说明「为什么 V3 要重做」：米白 + 深灰的插画调性与珊瑚红高对比 logo
完全不搭，是「设计没有符合 logo 调性」的根因。

## 边界：什么能生图，什么不能

- ✅ **插画位**（Hero、表情展示、App 图标）→ AI 生图
- ❌ **心情图标**（首页 7 个小方块）→ 保持 MaterialIcons 提取的 SVG
  （`assets/icons/mood-*.svg`），因为 App 内真实渲染的就是那些字形，
  换成生图就是虚假宣传

## 一、找到老版图标的路径

App Store Connect API **没有**暴露商店图标：
`appInfoLocalizations` / `appStoreVersionLocalizations` 都没有 `appIconAsset` 字段，
`/apps/{id}/appScreenshotSets` 路径 404。

最终走 iTunes Lookup API（按 App ID 拿线上架页面的 artwork）：

```bash
curl "https://itunes.apple.com/lookup?id=1506120121&country=cn"
# -> results[0].artworkUrl512
```

顺带确认了线上架状态：`version 1.0` / `releaseDate 2020-04-25` /
`averageUserRating 4.61111` / `userRatingCount 18` / `sellerName 宏岩 王`。

## 二、V3 基准图（panda_hero_v3）

```bash
$SCRIPT qwen21 --variant t2i \
  --prompt "Cute chibi cartoon baby panda, chubby round head, large black eye patches with big glossy eyes and white highlight dots, small round black ears, holding a tiny open diary notebook with both front paws, sitting facing viewer, sticking out tongue playfully, soft blush on cheeks, flat vector illustration style, clean sharp black outlines, simple cel shading, thin white outline around the entire silhouette, SOLID warm coral red #FE6655 flat background, no text, no watermark, centered, full body visible occupying 70% of frame" \
  --width 1024 --height 1024 --steps 30 --name panda_hero_v3
```

**7 个表情全部以这张为 `image_1` 做 edit**，身份一致性由此保证。
换基准图就要把 7 个表情全部重跑。

## 三、7 个表情（edit）

统一 prompt 骨架：

```
Make the panda in <image1> show a [表情描述] facial expression.
Keep the same panda identity:
- identical black-and-white fur pattern
- same round black ears
- same chubby round head shape
- same large round black eye patches with big glossy eyes and white highlight dots
- same pink blush on both cheeks
- same body pose sitting and holding the open diary notebook with both front paws
- same flat vector cel-shaded style with sharp black outlines
- keep the thin white outline around the entire silhouette
Keep the exact same solid warm coral red background color #FE6655, flat, no gradient, no shadow.
Only the facial expression changes. Do not add any extra objects, symbols, icons, sparkles or text.
```

最后那句「不要加额外符号」是 V3 的关键修正——第一版给 `lonely` 加了云、
给 `irritated` 加了闪电，导致这两张的 bbox 被撑大，标尺很难统一，
而且和 `Icons.cloud_outlined` 的对齐反而成了负担。V3 全部只用表情本身。

| 文件 | 表情描述 | seed | 对应 App 心情 |
|---|---|---|---|
| panda-happy | joyful, wide open smile showing tongue, eyes curved happily | — | 开心 |
| panda-calm | gentle serene smile, soft relaxed eyes | — | 平静 |
| panda-fulfilled | warm content and satisfied: eyes gently closed into soft upward curves, small sweet smile | 8101 | 充实 |
| panda-surprised | surprised and amazed: eyes wide open and rounder with enlarged highlights, eyebrows raised, small round open mouth | 8102 | 惊喜 |
| panda-low | low and sad: droopy half-closed eyes looking downward, eyebrows tilted upward in the middle, small flat downturned mouth | 8103 | 低落 |
| panda-lonely | lonely and wistful: eyes looking slightly to the side, one eyebrow slightly raised, small quiet mouth, a single small teardrop at the corner of one eye | 8104 | 孤独 |
| panda-irritated | irritated and annoyed: sharply furrowed angled eyebrows, narrowed eyes, small tense straight-line mouth | 8105 | 烦躁 |

## 四、动态 idle 循环

```bash
$SCRIPT video --input v3_happy-01.png --mode i2v \
  --prompt "A cute flat-vector cartoon panda sits holding an open diary notebook, on a flat solid warm coral red background #FE6655. The panda blinks its eyes once slowly, then its chest rises and falls gently like calm breathing, then it smiles softly and returns exactly to its starting pose. The camera holds perfectly steady with no movement, no zoom, no pan. ... Audio: N/A, no music, no sound." \
  --aspect 1:1 --name panda_idle_v3
```

短边 480 是 H3 的显存红线，不要为了清晰度调到 720 以上。

⚠️ **当前 App 里并没有播放这个视频**，理由见
`panda_mood_diary/assets/brand/README.md`「idle 视频路线」：
播 mp4 需要 `video_player` 原生插件，且一个 5 秒循环动画对这个
「一屏点一下就记完」的产品是负资产。

## 五、抠图与统一标尺

```bash
$VENV $SCRIPT cutout v3_$mood-01.png --output alpha/raw-$mood.png
```

做法（与第一版同一套，但 V3 全是纯表情，标尺更简单）：

1. 按 alpha bbox 裁掉透明边
2. 所有图按**主体高度** `ref_h = 688` 等比缩放
3. 画布取缩放后的最大宽高（本次 510×688）
4. 入库时再按高度缩到 512 → **380×512**（比例 0.742）
5. 验收：四边 `alpha > 16` 的像素数必须全为 0

⚠️ 第 3/5 步是实测踩出来的：**固定 512 画布会把主体切掉几百像素**
（第一版实测 `happy`/`surprised` 上下各被切 500/426 像素）。
而「文件存在、体积正常、curl 200、浏览器能加载」**全通过**，
只有逐边量 alpha 才能发现。Flutter 侧已把这个检查固化进
`test/brand_assets_test.dart`，并做过投毒证伪。

## 六、第一版（米白调性，已废弃）

基准图 prompt 用的是 `warm cream background #FDFBF7`，
`lonely` 加了头顶云、`irritated` 加了闪电，材质偏米白/深灰柔和插画。

**废弃原因**：与老版 logo 的珊瑚红高对比完全不搭，
「设计没有符合 logo 的调性」就是这个问题的表现。

## 七、文件去向

| 位置 | 内容 |
|---|---|
| `panda-privacy/assets/panda/panda-hero*.png` | Hero（1000 + 512） |
| `panda-privacy/assets/panda/panda-{mood}-512.png` | 7 张表情，官网 `#expressions` 用 |
| `panda-privacy/assets/panda/logo-512.png` / `favicon-*.png` | 导航品牌标记 + favicon |
| `panda_mood_diary/assets/brand/panda-{mood}-512.png` | 同一批 7 张，App 首页用 |
| `panda_mood_diary/assets/brand/panda-expressions-sheet.png` | 棋盘底接触表（人工走查） |

**原始带底色大图不进仓库**：页面一张都没引用，要复现按本文 prompt + seed 重跑。

## 八、复现注意

- 脚本打印的 `(0 MB)` **不代表文件损坏**：289 KB 会显示成 0 MB。用 `ls -la` 核对。
- 本机 LM Studio 未启动，`pe --expand-prompt` 走不通；prompt 手写即可达标。
- 生图耗时：单张 t2i/edit ≈ 40–60 s；5 s 视频 ≈ 3.5 分钟。
- 抠图用 `cutout`（rembg）就够，边缘实测零白边；不必上 `matte`（SAM + SDMatte），
  那是给发丝级主体用的，熊猫是硬边卡通。
- 表情画布是**竖版 0.742**，网页和 Flutter 里都不能给正方形 size，
  给了会把熊猫压扁且不报错。

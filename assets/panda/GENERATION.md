# 熊猫形象生成记录

> 生成工具：`~/.workbuddy/skills/local-image-studio/scripts/image_studio.py`
> 服务器：ComfyUI @ `192.168.4.66:8188`（RTX 5070 Ti 16G）
> 生成日期：2026-10-15
> 全部产物：Qwen Image 2.1，cfg=1.0，steps=30，seed=100（表情）/ 42（基准）

## 为什么用 AI 生图而不是继续画 SVG

官网原本用的是自绘 SVG 熊猫。它的优势是**与 App 内 MaterialIcons 心情图标严格对齐**，
但它没有表情、只有一种姿态 conveying 一种情绪。生图能给出 7 个可辨识的表情，
这是「日记 App 的情绪载体」真正需要的。

**注意边界**：心情**图标**（首页 7 个小方块）仍然是 SVG 提取物，**不要换成生图**——
那些是 App 内真实渲染的 MaterialIcons 字形，换掉就是虚假宣传。
生图熊猫只用于**插画位**（Hero、表情展示、App 内的插画场景）。

## 一、基准图（panda_base）

```bash
$SCRIPT qwen21 --variant t2i \
  --prompt "Cute chibi cartoon baby panda, chubby round head, large black eye patches, small round black ears, holding a tiny open diary notebook with both front paws, sitting facing viewer, soft blush on cheeks, flat vector illustration style, clean sharp black outlines, simple cel shading, warm cream background #FDFBF7, no text, no watermark, centered, full body visible occupying 70% of frame" \
  --width 1024 --height 1024 --steps 30 --seed 42 --name panda_base
```

7 个表情全部以这张为 `image_1` 做 edit，保证身份一致。
**不要重新生成基准图**——换一张就要把 7 个表情全部重跑，否则身份漂移。

## 二、7 个表情（edit，全部 seed=100）

统一 prompt 骨架：

```
Make the panda in <image1> show a [表情描述] expression on its face.
Keep the same panda identity: identical black-and-white fur pattern,
same round black ears, same chubby head shape, same eye patch positions,
same body pose holding the open diary notebook, same flat vector
cel-shaded style with sharp black outlines.
Keep the exact same solid cream #FDFBF7 background.
Only the facial expression changes.
```

| 文件 | 表情描述 | 对应 App 心情 |
|---|---|---|
| panda-happy | joyful, wide open smile showing mouth, eyes curved happily upward | 开心 |
| panda-calm | gentle serene smile, soft relaxed eyes, peaceful expression | 平静 |
| panda-fulfilled | content relaxed smile with gentle sparkle, peaceful and satisfied | 充实 |
| panda-surprised | surprised expression, round wide-open eyes, small open oval mouth, eyebrows raised | 惊喜 |
| panda-low | downcast sad expression, drooping mouth, eyes looking downward, slightly lowered head | 低落 |
| panda-lonely | quiet lonely expression, looking slightly to the side, small closed mouth, a single small rain cloud floating above the head | 孤独 |
| panda-irritated | annoyed irritated expression, furrowed brow, flat straight mouth, small lightning bolts around the head | 烦躁 |

`lonely` 的云、`irritated` 的闪电**不是装饰**，是刻意对齐 App 内
`Icons.cloud_outlined` / `Icons.thunderstorm_rounded` 的语义符号。

## 三、动态 idle 循环

```bash
$SCRIPT video --input panda_calm-01.png --mode i2v \
  --prompt "A cute cartoon baby panda sits holding an open diary notebook, facing the viewer. Over 5 seconds the panda performs one smooth looping idle animation: it blinks slowly once, its chest rises and falls gently with breathing, and the corners of its mouth lift slightly into a calm smile, then everything returns smoothly to the starting pose by the end of the 5 seconds. The panda keeps the same black-and-white fur pattern, same round black ears, same eye patch positions, and the same flat vector cel-shaded cartoon style with sharp black outlines throughout. The camera holds perfectly steady with no movement, no zoom, no pan. The background stays a single solid flat cream color, no shadow, no gradient. Non-diegetic music: N/A." \
  --aspect 1:1 --name panda_idle
```

产物 `panda_idle-01.mp4`：5.17s / 480×480 / 24fps / 124 帧。
第 11-12 帧回到接近起始姿态，可作无缝循环。
短边 480 是 H3 的显存红线，不要为了清晰度调到 720 以上。

## 四、文件去向

| 位置 | 内容 | 理由 |
|---|---|---|
| `panda-privacy/assets/panda/*-512.png` | 8 张透明 PNG（Hero + 7 表情） | 官网实际引用的就是这 8 张，1.9 MB |
| `panda_mood_diary/assets/brand/*-512.png` | 7 张表情 512 | App 内用 |
| `panda_mood_diary/assets/brand/panda-idle-loop.mp4` | 动态循环 | App 内插画动画 |

**原始带底色大图（`*-1024.png`）不进仓库**：5.6 MB，页面一张都没引用，
要复现按本文的 prompt + seed 重跑即可（单张约 60s）。

## 五、统一标尺（重要，别踩）

7 个表情的主体尺寸**天然不一致**：`lonely` 头顶有云、`irritated` 两侧有闪电，
rembg 抠出的 bbox 会被符号撑大（实测 489×775 / 687×748 vs 其余 523×689）。
不统一缩放的话，这两只熊猫在网页卡片里会明显偏大。

做法：
1. 取 5 个「纯表情」主体高度的中位数作标尺（本次 `ref_h = 688`）
2. 所有图按 `ref_h` 等比缩放
3. 画布取**缩放后最大宽高**（本次 636×688 → 688），不能想当然用 512
4. 验收：四边不透明像素数必须全为 0 —— 固定 512 画布会把熊猫上下切掉几百像素

⚠️ 第 3 步是实测踩出来的：第一版直接用固定 512 画布，
`happy`/`surprised` 上下各被切 500/426 像素，`irritated` 左右各切 17/21 像素（闪电直接没了）。
**指标（文件存在、体积正常）全通过，只有逐边量 alpha 才能发现。**

## 六、复现注意
- 脚本打印的 `(0 MB)` **不代表文件损坏**：289 KB 会显示成 0 MB。用 `ls -la` 核对真实字节数。
- 本机 LM Studio 未启动，`pe --expand-prompt` 走不通；本次 prompt 是手写的，效果已达标，
  不必强依赖 VL。
- 生图耗时：单张 t2i/edit ≈ 40–60 s；5 s 视频 ≈ 3.5 分钟。
- 抠图用 `cutout`（rembg）就够，边缘实测零白边；不必上 `matte`（SAM + SDMatte），
  那是给发丝级主体用的，熊猫是硬边卡通。

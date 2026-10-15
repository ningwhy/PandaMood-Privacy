#!/usr/bin/env python3
"""ASC 元数据回填：熊猫心情日记（App ID 1506120121）。

用法
----
    export ASC_KEY_ID=<你的 Key ID>
    export ASC_ISSUER_ID=<你的 Issuer ID>
    export ASC_KEY_PATH=~/.appstoreconnect/private_keys/AuthKey_<KEY_ID>.p8
    /opt/homebrew/bin/python3 asc_metadata.py --check     # 只校验，不写
    /opt/homebrew/bin/python3 asc_metadata.py --urls-only # 只写 URL（部署后用）
    /opt/homebrew/bin/python3 asc_metadata.py             # 全量写入

⚠️ ASC 路径坑（已实测）：
- /apps/{id}/appInfoLocalizations → 404 PATH_ERROR（关系不存在），必须两跳：
  /apps/{id}/appInfos → /appInfos/{id}/appInfoLocalizations
- PATCH 必须 JSON:API 包装 {"data":{"type":..,"id":..,"attributes":{..}}}
- /apps/{id}/builds 不接受 include 参数

⚠️ ASC 有两套 URL 字段（appInfoLocalizations / appStoreVersionLocalizations），
本脚本只管 App 级；创建 v2.0 版本时必须同步填版本级，否则审核仍看到旧值。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".workbuddy/skills/ios-app-store-pipeline/scripts"))
from asc_client import AscClient, AscError  # noqa: E402

APP_ID = "1506120121"
SITE = "https://panda-mood-diary-privacy.pages.dev"

# ====================================================================
# 🔴 本账号 ASC 元数据可写性实测结论（2026-10-15，写脚本前先用 API 验证过）
#
# 1) 字段层级（Apple 的实际划分，与直觉不同）：
#    - appInfoLocalizations（App 级）只有：name / subtitle / privacyPolicyUrl
#    - appStoreVersionLocalizations（版本级）才有：description / keywords /
#      promotionalText / whatsNew / privacyPolicyUrl / supportUrl / marketingUrl
#    ⚠️ 实测（2026-10-15 v2.0 创建后复核）：版本级 privacyPolicyUrl 写入 409，
#    **隐私 URL 只能 App 级填**（memory 铁律成立）。
#    之前「版本级也能填」是误读——字段存在不代表可写。
#
# 2) PATCH 是**原子**的：一个非法字段（如把 keywords 塞进 appInfoLocalizations）
#    会让**整批**字段全部不生效，只报 409 ENTITY_ERROR.ATTRIBUTE.UNKNOWN。
#    → 必须**逐字段** PATCH（见 write()）。
#
# 3) 已发布版本（appStoreState=READY_FOR_SALE）的锁定规则：
#    - 可改：promotionalText ✅（实测写入成功）
#    - 锁定：「The field 'x' can not be modified in the current state.」
#      → App 级 name / subtitle / privacyPolicyUrl
#    - 锁定：「Attribute 'x' cannot be edited at this time」
#      → 版本级 description / keywords
#    结论：**1.0 的文案基本改不动**，新文案必须等 v2.0 版本创建后写入。
#
# 4) 路径坑：
#    - /apps/{id}/appInfoLocalizations → 404 PATH_ERROR，必须两跳
#      /apps/{id}/appInfos → /appInfos/{id}/appInfoLocalizations
#    - /apps/{id}/builds 不接受 include 参数；查版本要 /builds/{buildId}?include=appStoreVersion
# ====================================================================

LIMITS = {"name": 30, "subtitle": 30, "keywords": 100, "promotionalText": 170}

# ---------------------------------------------------------------- 文案

ZH = {
    # name 不改：老版 name 已含长尾词「记录生活点滴的笔记本」，
    # 改名会损失 ASO 搜索权重（保 listing 是复刻的硬约束）。
    "name": "熊猫心情日记-记录生活点滴的笔记本",
    "subtitle": "点一下记心情，月末看见自己",
    # keywords / promotionalText 见下方 VERSION_COPY（版本级字段）
    # 🔴 keywords 与 promotionalText **不属于 appInfoLocalizations**（实测 409
    # ENTITY_ERROR.ATTRIBUTE.UNKNOWN），它们是**版本级**字段，挂在
    # appStoreVersionLocalizations 下 —— 见 VERSION_COPY。
    # 关键教训：PATCH 是原子的，一个非法字段会让**整批**字段全部不生效。
    "description": """一个安静的私人日记：点一下，今天就记完了。

想写的时候，再打开碎碎念。

■ 心情记录，点一下就够
七个心情选一个，今天就算记完。也可以加一句话、勾几个影响因素（睡得好、运动了、见了朋友……），一分钟内完成。

■ 时间线，想写再写
不想写也没关系。写日记时支持配图、草稿自动保存，写到一半退出不会丢。全部日记按时间排列，支持关键词搜索。

■ 月末回顾，看见自己的节奏
每月回顾告诉你：哪些天心情更好、连续记录了多少天、你常见的心情是什么，以及你自己的规律。

■ 你的规律，只看数据不下诊断
你勾选的影响因素会和当天的心情一起被记住。回顾页会在你的手机本机做一个简单对比：勾了「运动了」的那些天，平均心情是不是更高？
· 全部计算在本地完成，不上传任何数据
· 某因素记录不足 3 天、或差异过小时不给结论，避免误导
· 这是你自己记录里的规律，不是医学结论

■ 引导复盘，不想面对空白页时
提供两套小模板：今日三问（今天发生了什么、此刻的感受、明天想为自己做的一件小事），以及想法记录（把一件烦心事拆成：发生了什么、我当时怎么想、换个角度怎么看、接下来怎么做）。
照着问题写，不用自己想标题。这是一个自我反思小工具，不构成医疗建议。

■ 每日提醒
需要提醒就开启：到设定时间提醒你来记一笔。通知里只有一句中性提示，不包含你的任何日记内容。

■ 隐私锁
在意被人随手翻看？设置 4–6 位 PIN，之后每次打开 App 都需要输入。PIN 以加盐迭代哈希的形式存放，不存明文。
隐私锁没有找回密码的入口——因为本地没有服务器，也就没有任何后门。忘记 PIN 只能卸载重装，数据会随之删除。

■ 你的记录，只属于你的设备
· 没有账号，不需要注册，打开即用
· 所有数据存在本机，不上传、不同步
· 没有广告，没有行为分析，没有追踪
· 全部功能免费，无内购、无订阅

■ 卸载前请注意
你的记录只存在本机，服务器上没有任何副本。换手机或卸载 App 前，请先导出备份。

隐私政策：""" + SITE + "/privacy/zh-Hans.html""",
}

EN = {
    "name": "Panda Mood Diary: Mood Journal",
    "subtitle": "Log your mood in one tap",
    # keywords / promotionalText 见下方 VERSION_COPY（版本级字段）
    "description": """A quiet private diary: one tap and today is logged.

When you want to write more, open the journal.

■ Logging a mood takes one tap
Pick one of the seven moods and the day is done. You can add a sentence and tick a few factors (slept well, exercised, saw friends…) — under a minute.

■ A timeline for the days you want to write
No pressure to write. Entries can include photos, and drafts save automatically, so leaving halfway never loses your words. Everything is in one timeline, with keyword search.

■ A monthly look back at your own rhythm
Each month, see which days felt better, how long your streak was, which moods show up most — and your own patterns.

■ Your patterns: patterns only, never a diagnosis
The factors you tick are remembered alongside that day's mood. On the review page the app makes one simple comparison — on days you ticked "exercised", was your average mood higher?
· All of it is computed on your device. Nothing is uploaded.
· No conclusion is shown when a factor appears on fewer than 3 days, or when the difference is too small to be meaningful.
· This is a pattern in your own records, not a medical conclusion.

■ Guided reflection, for days when a blank page feels hard
Two short templates: Three Questions Today (what happened, how you feel now, one small thing you'll do for yourself tomorrow) and Thought Record (a nagging situation split into: what happened, what I thought, another way to look at it, what I'd like to do next).
Answer the prompts instead of inventing titles. This is a self-reflection tool, not medical advice.

■ Daily reminder
Turn it on if it helps: a nudge at your chosen time. The notification is a neutral prompt and never includes any diary content.

■ Privacy lock
Worried about someone glancing at your phone? Set a 4–6 digit PIN and the app asks for it every time it opens. Your PIN is stored as a salted, repeatedly iterated hash — never in plain text.
There is no password recovery, because with no server there is no back door. If you forget it, reinstalling is the only option, and your data goes with it.

■ Your entries belong to your device
· No account, no sign-up — open and start
· Everything stays on your device, never uploaded or synced
· No ads, no analytics, no tracking
· Completely free: no in-app purchases, no subscriptions

■ Before you uninstall
Your entries live only on this device; no copy exists anywhere else. Export a backup before switching phones or uninstalling.

Privacy Policy: """ + SITE + "/privacy/en.html""",
}

VERSION_COPY = {
    "zh-Hans": {
        "description": ZH["description"],
        "promotionalText": "全部功能免费：无广告、无内购、无账号。你的心情和日记只存在自己的手机里，不上传任何服务器。",
        "keywords": "心情日记,情绪记录,日记本,树洞,心情,情绪,记录,私密,隐私锁,本机存储,情绪管理,月历",
    },
    "en-AU": {
        "description": EN["description"],
        "promotionalText": "Free, with no ads, no subscriptions, and no accounts. Your moods and journal entries stay on your device — nothing is ever uploaded.",
        "keywords": "mood diary,journal,feelings,mood tracker,private diary,offline,no ads,daily journal,reflection",
    },
}
VERSION_COPY["en-GB"] = VERSION_COPY["en-AU"]

LOCALE_URL = {
    "zh-Hans": SITE + "/privacy/zh-Hans.html",
    "en-AU": SITE + "/privacy/en.html",
    "en-GB": SITE + "/privacy/en.html",
}
SUPPORT_URL = SITE + "/support/index.html"
MARKETING_URL = SITE + "/"

COPY = {"zh-Hans": ZH, "en-AU": EN, "en-GB": EN}


# ---------------------------------------------------------------- 工具

def app_info_id(c: AscClient, editable: bool = False) -> str:
    """🔴 关键：App 有两个 appInfo——
    1. 绑定已发布 1.0 的（data[0]）→ 全字段锁定
    2. 随待提交版本创建的可编辑副本（data[1]）→ 才是能 PATCH 的那个
    取 data[0] 会永远撞 "can not be modified in the current state"。
    """
    r = c.get(f"/apps/{APP_ID}/appInfos", params={"limit": 10})
    data = r.get("data", [])
    if not data:
        raise SystemExit("查不到 appInfos")
    if editable:
        if len(data) < 2:
            raise SystemExit("只有 1 个 appInfo（无待提交版本），无可编辑副本")
        return data[1]["id"]
    return data[0]["id"]


def loc_ids(c: AscClient, info_id: str) -> dict[str, str]:
    r = c.get(f"/appInfos/{info_id}/appInfoLocalizations", params={"limit": 50})
    return {d["attributes"]["locale"]: d["id"] for d in r.get("data", [])}


def validate(verbose: bool = True) -> bool:
    ok = True
    for loc, fields in COPY.items():
        for key in ("name", "subtitle"):
            v = fields[key]
            n = len(v)
            lim = LIMITS[key]
            if n > lim:
                ok = False
                print(f"❌ [{loc}] {key} = {n} 字符，超出 ASC 上限 {lim}")
            elif verbose:
                print(f"  [{loc}] {key} = {n}/{lim}")
        vf = VERSION_COPY.get(loc, {})
        for key in ("promotionalText", "keywords"):
            v = vf.get(key)
            if v is None:
                continue
            n, lim = len(v), LIMITS[key]
            if n > lim:
                ok = False
                print(f"❌ [{loc}] {key} = {n} 字符，超出 ASC 上限 {lim}")
            elif verbose:
                print(f"  [{loc}] {key} = {n}/{lim} (版本级)")
        d = fields["description"]
        if len(d) > 4000:
            ok = False
            print(f"❌ [{loc}] description = {len(d)} 字符，超出 4000")
        elif verbose:
            print(f"  [{loc}] description = {len(d)}/4000")
    # 关键词卫生：英文短语**必须允许空格**（"mood diary" 是完整短语，
    # 拆成 "mood,diary" 反而两个词都失去竞争力）。
    # 真正要禁的是：逗号旁空格、首尾空格、连续逗号（ASC 会把空项算进字符数）。
    for loc, fields in VERSION_COPY.items():
        kw = fields["keywords"]
        if kw != kw.strip():
            ok = False
            print(f"❌ [{loc}] keywords 有首尾空格")
        for bad in (", ", " ,", ",,"):
            if bad in kw:
                ok = False
                print(f"❌ [{loc}] keywords 含 {bad!r} —— ASC 按逗号精确分隔，空项白占字符")
        for part in kw.split(","):
            if part != part.strip():
                ok = False
                print(f"❌ [{loc}] 关键词 {part!r} 有多余空格")
    return ok


def write(c: AscClient, info_id: str, locs: dict[str, str],
          fields: dict[str, dict], urls: bool) -> int:
    """逐字段 PATCH（**不是**整批提交）。

    🔴 为什么逐字段：ASC 的 PATCH 是**原子**的 —— 一个非法字段会让
    **整批**字段全部不生效（实测：带 keywords 的批次元数据一个都没写进去，
    且报的是 409 ENTITY_ERROR.ATTRIBUTE.UNKNOWN）。
    字段归属只能靠 API 实证（description/keywords/promotionalText 全在
    版本级，不在 appInfoLocalizations），所以这里逐个试、失败的记下来跳过，
    成功的照样落库 —— 一次运行就能拿到「哪些字段属于哪一层」的完整结论。
    """
    written = 0
    rejected: list[tuple[str, str, str]] = []
    for loc, attrs in fields.items():
        lid = locs.get(loc)
        if lid is None:
            print(f"⚠️  ASC 上没有 {loc} 的本地化，跳过（需先在网页端添加语言）")
            continue
        ok_here = []
        for key, value in attrs.items():
            try:
                c.patch(f"/appInfoLocalizations/{lid}", attributes={key: value})
                ok_here.append(key)
                written += 1
            except AscError as e:
                detail = ""
                try:
                    import json as _json
                    errs = _json.loads(e.body).get("errors", [])
                    detail = errs[0].get("detail", "") if errs else ""
                except Exception:
                    detail = e.body[:120]
                rejected.append((loc, key, detail))
        if ok_here:
            print(f"✅ [{loc}] 已写入 {ok_here}")
    if rejected:
        print("\n⚠️  以下字段不属于 appInfoLocalizations（需在版本级写入）：")
        for loc, key, detail in rejected:
            print(f"   [{loc}] {key}: {detail}")
    return written


def version_ids(c: AscClient) -> dict[str, str]:
    """版本 id → versionString。

    ⚠️ ASC 的 `/apps/{id}/appStoreVersions` 在本账号 403（memory 铁律），
    `/apps/{id}/builds` 又不接受 include。
    实测可用路径：`/builds/{buildId}?include=appStoreVersion`
    从 included[] 里取 —— 这里对每个 build 逐个查（当前只有 1 个 build）。
    """
    out: dict[str, str] = {}
    builds = c.get(f"/apps/{APP_ID}/builds", params={"limit": 20}).get("data", [])
    for b in builds:
        d = c.get(f"/builds/{b['id']}", params={"include": "appStoreVersion"})
        for inc in d.get("included", []):
            if inc.get("type") == "appStoreVersions":
                out[inc["id"]] = inc["attributes"].get("versionString", "?")
    return out


def write_version_locals(c: AscClient) -> int:
    """写版本级字段（keywords / promotionalText / whatsNew）。"""
    versions = version_ids(c)
    if not versions:
        print("⚠️  查不到任何 appStoreVersion —— 可能该 App 还没有创建版本")
        return 0
    total = 0
    for vid, vstr in versions.items():
        locs = c.get(
            f"/appStoreVersions/{vid}/appStoreVersionLocalizations",
            params={"limit": 50},
        ).get("data", [])
        print(f"== 版本 {vstr} ({vid})：{len(locs)} 个 locale ==")
        for d in locs:
            loc = d["attributes"].get("locale")
            attrs = dict(VERSION_COPY.get(loc, {}))
            if urls_only_global(loc):
                attrs["privacyPolicyUrl"] = LOCALE_URL[loc]
                attrs["supportUrl"] = SUPPORT_URL
                attrs["marketingUrl"] = MARKETING_URL
            if not attrs:
                print(f"⚠️  [{loc}] 无版本级文案，跳过")
                continue
            ok_here = []
            for key, value in attrs.items():
                try:
                    c.patch(f"/appStoreVersionLocalizations/{d['id']}",
                            attributes={key: value})
                    ok_here.append(key)
                    total += 1
                except AscError as e:
                    print(f"⚠️  [{loc}] {key} 被拒：{e.body[:160]}")
            if ok_here:
                print(f"✅ [{loc}] 已写入 {ok_here}")
    return total


def urls_only_global(loc: str) -> bool:
    return "--urls-only" in sys.argv and loc in LOCALE_URL


def audit(c: AscClient) -> None:
    """只读巡检：打印 ASC 现状 + 每个字段的可写性结论。"""
    info_id = app_info_id(c)
    locs = loc_ids(c, info_id)
    print(f"appInfo={info_id}\n=== App 级 appInfoLocalizations ===")
    for loc, lid in sorted(locs.items()):
        at = c.get(f"/appInfoLocalizations/{lid}").get("data", {}).get("attributes", {})
        print(f"[{loc}]")
        print(f"   name={at.get('name')!r}")
        print(f"   subtitle={at.get('subtitle')!r}")
        print(f"   privacyPolicyUrl={at.get('privacyPolicyUrl')}")

    print("\n=== 版本级 appStoreVersionLocalizations ===")
    for vid, vstr in version_ids(c).items():
        st = c.get(f"/appStoreVersions/{vid}").get("data", {}).get("attributes", {})
        print(f"-- {vstr} ({vid}) state={st.get('appStoreState')}")
        for d in c.get(f"/appStoreVersions/{vid}/appStoreVersionLocalizations",
                       params={"limit": 50}).get("data", []):
            at = d["attributes"]
            print(f"   [{at['locale']}] desc={len(at.get('description') or '')} "
                  f"kw_len={len(at.get('keywords') or '')} "
                  f"promo_len={len(at.get('promotionalText') or '')}")
            print(f"        privacyUrl={at.get('privacyPolicyUrl')} "
                  f"supportUrl={at.get('supportUrl')} marketingUrl={at.get('marketingUrl')}")


def main() -> None:
    argv = sys.argv[1:]
    mode = " ".join(argv)
    urls_only = "--urls-only" in argv
    check_only = "--check" in argv
    # --copy-only：只写文案不写 URL。站点未部署时 URL 是死链，
    # 审核必挂 —— 这就是默认模式；部署后显式加 --urls-only 才写 URL。
    copy_only = "--copy-only" in argv or (not urls_only and not check_only)
    version_locals = "--version-locals" in argv

    print("== 字符数校验 ==")
    if not validate():
        raise SystemExit("文案不合规，已中止（未写入任何内容）")
    print("✅ 全部字段在 ASC 限制内\n")

    if check_only:
        return
    if "--audit" in argv:
        return audit(AscClient())
    if copy_only:
        print("⚠️  模式：只写文案，不写 URL（站点未部署，privacy URL 会是死链）\n")

    c = AscClient()
    info_id = app_info_id(c)
    locs = loc_ids(c, info_id)
    print(f"appInfo={info_id}  locales={sorted(locs.keys())}\n")

    if version_locals:
        return write_version_locals(c)

    for loc, lid in sorted(locs.items()):
        fields: dict[str, object] = {}
        if not urls_only:
            fields.update(COPY.get(loc, {}))
        if urls_only and loc in LOCALE_URL:
            # 🔴 App 级只有 privacyPolicyUrl 可写（实测 supportUrl /
            # marketingUrl 不属该资源）；support/marketing 属版本级。
            fields["privacyPolicyUrl"] = LOCALE_URL[loc]
        if fields:
            write(c, info_id, locs, {loc: fields}, urls_only)
        else:
            print(f"⚠️  [{loc}] 无可写字段")


if __name__ == "__main__":
    main()

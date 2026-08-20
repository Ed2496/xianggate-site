# -*- coding: utf-8 -*-
r"""
相閘 XiangGate · 每週五素材彙整週報產生器
================================================================
定位：相閘五層管線的 ①提取層(掃描/正規化) + ⑤趨勢層(彙整/環次命中) 的離線落地。
      掃描兩個 Downloads 資料夾內的文字檔 → 環次命中(六環/五環) → 彙整 →
      產出淺綠單頁 HTML 週報 → 追加歷史快照(不遺忘) → 供 git push 上 GitHub Pages。

紀律：
  * 不替 Edward 坍縮、不下結論，只給方位/計數/命中(規格 §10)。
  * 環次命中為「關鍵詞啟發式·示範層」(規格 §9)。關鍵詞放檔頭 RING_KEYWORDS 可編，
    坍縮權/命名權屬 Edward。正式版由對撞引擎逐命題判定。
  * 歷史 append-only：history.json 每週一筆(以 ISO 週為 key，重跑覆寫同週)。
  * 日期鐵律：以「執行當下 datetime.now()」為錨(Task Scheduler 週五跑=該週五)，
    不繼承任何寫死日期。可用 --asof 覆寫僅供測試。
  * OpenClaw 已廢：定期由 Windows Task Scheduler 觸發本 script，不假設任何常駐服務。

用法：
  python xianggate_weekly.py                 # 正式：掃描 SCAN_DIRS，輸出到 OUTPUT_DIR
  python xianggate_weekly.py --asof 2026-08-21   # 測試：固定 as-of 日期(週五)
  python xianggate_weekly.py --dirs D:\a D:\b --out D:\site   # 覆寫掃描/輸出路徑
"""

import os
import re
import sys
import json
import html
import argparse
import hashlib
from datetime import datetime, timedelta, date

# ============================================================
# 可編設定區（坍縮權：Edward）
# ============================================================

# 掃描資料夾（預設 Edward 的兩個 Downloads 目錄；--dirs 可覆寫）
SCAN_DIRS = [
    r"C:\Users\ed249\Downloads\TXT2026",
    r"C:\Users\ed249\Downloads\Transcripts-20260120",
]

# 掃描副檔名（小寫，含點）
EXTENSIONS = [".txt", ".md"]

# 輸出目錄（GitHub Pages repo 的網站根；--out 可覆寫）
# index.html 覆寫成最新一週；reports/YYYY-Www.html 存每週封存；history.json 存趨勢
OUTPUT_DIR = r"C:\Users\ed249\Downloads\xianggate-site"

# ── 匯入日期基準（坍縮權：Edward）──────────────────────────
# 'created'  ＝ 檔案建立日期（原地生成的檔用這個才對）
# 'modified' ＝ 檔案修改日期（批次複製/移動進來的檔用這個才對）
# ⚠ Windows 陷阱：複製/移動檔案會把「建立日期」重設成複製當下(可能全變今天)，
#   而「修改日期」常保留原始內容變更時間。若建立日期全擠成今天 → 改用 'modified'。
# 用 `python xianggate_weekly.py --diag` 看兩個日期實際差多少再決定。
DATE_BASIS = "modified"

# 讀檔嘗試編碼順序（台灣 Windows：utf-8 / cp950(Big5) 混用是常態）
ENCODINGS = ["utf-8-sig", "utf-8", "cp950", "big5", "gb18030", "latin-1"]

# 環次命中關鍵詞（示範層啟發式；來源＝相閘正典 canon_proposition is_active=1）
# 命中計分：某環任一關鍵詞出現即算命中該環，強度 = min(1.0, 命中次數/飽和值)
RING_SATURATION = 5  # 一檔內某環累計命中達此值即視為強度 1.0

RING_KEYWORDS = {
    # ── 總綱 · 六環自噬迴圈（社會截面）──
    "總綱環①": ["金融資本化", "實體經濟", "回報壓縮", "資本化", "脫實向虛", "產業空心", "空心化"],
    "總綱環②": ["演算法", "注意力", "流量", "變現", "碎片化", "眼球", "平台經濟", "帶貨"],
    "總綱環③": ["焦慮", "努力無用", "內捲", "躺平", "無力感", "相對剝奪", "階級固化"],
    "總綱環④": ["獵巫", "出征", "網暴", "帶風向", "炎上", "公審", "鍵盤", "肉搜", "取消文化"],
    "總綱環⑤": ["傳統文化", "集體價值", "上一代", "世代對立", "文化戰", "解構", "去中心價值"],
    "總綱環⑥": ["原子化", "個體化", "集體瓦解", "一盤散沙", "無組織", "抵抗歸零", "去團結"],
    # ── 總經 · 食利瀑布（五環 · 金融截面）──
    "總經環①": ["食利", "租金", "資產端", "被動收入", "收租", "rentier", "持有回報", "生產端撤出"],
    "總經環②": ["估值", "敘事", "灌水", "造神", "本夢比", "畫餅", "願景", "想像空間", "hype", "炒作"],
    "總經環③": ["加密", "泡沫", "全民繳租", "割韭菜", "meme", "迷因幣", "代幣", "空氣幣"],
    "總經環④": ["做空", "抹黑", "下架", "清除", "死亡記錄", "狙擊", "汙名", "抹掉", "獵殺"],
    "總經環⑤": ["托底", "紓困", "印鈔", "通膨", "社會化", "兜底", "QE", "bailout", "風險轉嫁"],
}

# 六環/五環環序(供柱圖排序與計數鎖死顯示)
RING_ORDER_6 = ["總綱環①", "總綱環②", "總綱環③", "總綱環④", "總綱環⑤", "總綱環⑥"]
RING_ORDER_5 = ["總經環①", "總經環②", "總經環③", "總經環④", "總經環⑤"]

# 相閘淺綠戰略色調(取自現行展示站 index__3_.html)
PALETTE = {
    "void": "#EDF6F1", "ink": "#FFFFFF", "gold": "#0F766E", "gold_dim": "#99D5CC",
    "jade": "#0E8A6D", "jade_dim": "#A8DCC9", "red": "#C2393E", "blue": "#2563EB",
    "paper": "#17362E", "mute": "#5F7A70", "line": "#C9E0D7", "panel": "#F7FBF9",
}

# ============================================================
# 工具函式
# ============================================================

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", "replace")).hexdigest()

def read_text_robust(path: str):
    """以多編碼嘗試讀檔；回傳 (text, encoding_used)。latin-1 永不失敗兜底。"""
    with open(path, "rb") as f:
        raw = f.read()
    for enc in ENCODINGS:
        try:
            return raw.decode(enc), enc
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("latin-1", "replace"), "latin-1(fallback)"

def count_units(text: str):
    """回傳 (行數, 非空白字元數, 中文字數, 概略詞數)。"""
    lines = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    non_ws = len(re.sub(r"\s+", "", text))
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    words = len(re.findall(r"[A-Za-z0-9]+", text)) + cjk  # 中文以字計，英數以詞計
    return lines, non_ws, cjk, words

# 智慧取句(v1.3)：跳過導言/hashtag/標題重複行，取首個實質句
_SKIP_PREFIX = ("#", "＃", "http", "www.", "---", "===", "***", "```")
def extract_first_substantial(text: str, min_len: int = 12) -> str:
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        low = line.lower()
        if low.startswith(_SKIP_PREFIX):
            continue
        # 去掉行內 hashtag 與 URL 後判長度
        cleaned = re.sub(r"https?://\S+|#\S+|＃\S+", "", line).strip()
        if len(cleaned) >= min_len:
            return cleaned[:120]
    return ""

def scan_rings(text: str):
    """回傳 {ring: (hit_count, strength)}；未命中的環不列入。"""
    result = {}
    for ring, kws in RING_KEYWORDS.items():
        total = 0
        for kw in kws:
            total += text.count(kw)
        if total > 0:
            strength = min(1.0, total / RING_SATURATION)
            result[ring] = (total, round(strength, 3))
    return result

def iso_week_key(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"

def week_start_monday(d: date) -> date:
    return d - timedelta(days=d.isoweekday() - 1)  # 週一

# ============================================================
# 掃描 + 彙整
# ============================================================

def gather(scan_dirs, extensions, asof_dt):
    asof_date = asof_dt.date()
    wk_start = week_start_monday(asof_date)
    wk_start_ts = datetime.combine(wk_start, datetime.min.time()).timestamp()

    files = []
    missing_dirs = []
    exts = tuple(e.lower() for e in extensions)

    for d in scan_dirs:
        if not os.path.isdir(d):
            missing_dirs.append(d)
            continue
        for root, _dirs, fnames in os.walk(d):
            for fn in fnames:
                if not fn.lower().endswith(exts):
                    continue
                fpath = os.path.join(root, fn)
                try:
                    st = os.stat(fpath)
                except OSError:
                    continue
                text, enc = read_text_robust(fpath)
                lines, non_ws, cjk, words = count_units(text)
                # 同時記錄建立日期與修改日期，依 DATE_BASIS 決定週窗判準（坍縮權：Edward）
                # Windows: st_birthtime(3.12+) 優先，退回 st_ctime(Windows 上＝建立時間)
                created_ts = getattr(st, "st_birthtime", None)
                if created_ts is None:
                    created_ts = st.st_ctime
                mtime_ts = st.st_mtime
                basis_ts = created_ts if DATE_BASIS == "created" else mtime_ts
                created = datetime.fromtimestamp(created_ts)
                modified = datetime.fromtimestamp(mtime_ts)
                rings = scan_rings(text)
                files.append({
                    "path": fpath,
                    "name": fn,
                    "src_dir": d,
                    "size": st.st_size,
                    "created": created.isoformat(timespec="seconds"),
                    "created_ts": created_ts,
                    "modified": modified.isoformat(timespec="seconds"),
                    "modified_ts": mtime_ts,
                    "basis_ts": basis_ts,
                    "is_new": basis_ts >= wk_start_ts,
                    "encoding": enc,
                    "lines": lines,
                    "chars": non_ws,
                    "cjk": cjk,
                    "words": words,
                    "rings": rings,
                    "first_line": extract_first_substantial(text),
                    "sha256": sha256_text(text)[:16],
                })

    files.sort(key=lambda x: x["basis_ts"], reverse=True)

    # 環次命中彙總(全庫 + 本週)
    ring_total = {r: 0.0 for r in RING_ORDER_6 + RING_ORDER_5}
    ring_week = {r: 0.0 for r in RING_ORDER_6 + RING_ORDER_5}
    ring_files = {r: 0 for r in RING_ORDER_6 + RING_ORDER_5}
    for f in files:
        for r, (cnt, strength) in f["rings"].items():
            ring_total[r] += strength
            ring_files[r] += 1
            if f["is_new"]:
                ring_week[r] += strength

    week_files = [f for f in files if f["is_new"]]

    # 全庫回溯分佈：每檔依 basis 日期(修改/建立)歸入 ISO 週(規格 §5「本機即時計算」)
    # 同時累計每環強度 → 環次命中時間趨勢(規格 §5「環次每週11線趨勢」熱區版)
    all_rings = RING_ORDER_6 + RING_ORDER_5
    dist = {}
    for f in files:
        wk = iso_week_key(datetime.fromtimestamp(f["basis_ts"]).date())
        b = dist.setdefault(wk, {"week": wk, "files": 0, "chars": 0,
                                 "rings": {r: 0.0 for r in all_rings}})
        b["files"] += 1
        b["chars"] += f["chars"]
        for r, (_cnt, strength) in f["rings"].items():
            b["rings"][r] += strength
    for b in dist.values():
        b["rings"] = {r: round(v, 3) for r, v in b["rings"].items()}
    week_distribution = sorted(dist.values(), key=lambda d: d["week"])

    summary = {
        "asof": asof_dt.isoformat(timespec="seconds"),
        "week_key": iso_week_key(asof_date),
        "week_start": wk_start.isoformat(),
        "date_basis": DATE_BASIS,
        "scan_dirs": scan_dirs,
        "missing_dirs": missing_dirs,
        "total_files": len(files),
        "week_files": len(week_files),
        "total_chars": sum(f["chars"] for f in files),
        "week_chars": sum(f["chars"] for f in week_files),
        "total_words": sum(f["words"] for f in files),
        "week_distribution": week_distribution,
        "ring_total": {r: round(v, 3) for r, v in ring_total.items()},
        "ring_week": {r: round(v, 3) for r, v in ring_week.items()},
        "ring_files": ring_files,
    }
    return files, summary

# ============================================================
# 歷史(append-only，以 ISO 週為 key)
# ============================================================

def update_history(out_dir, summary):
    hpath = os.path.join(out_dir, "history.json")
    hist = []
    if os.path.isfile(hpath):
        try:
            with open(hpath, "r", encoding="utf-8") as f:
                hist = json.load(f)
        except (json.JSONDecodeError, OSError):
            hist = []
    snap = {
        "week_key": summary["week_key"],
        "asof": summary["asof"],
        "total_files": summary["total_files"],
        "week_files": summary["week_files"],
        "total_chars": summary["total_chars"],
        "week_chars": summary["week_chars"],
        "ring_week": summary["ring_week"],
        "ring_total": summary["ring_total"],
    }
    # 同週覆寫(重跑不增筆)，否則追加
    hist = [h for h in hist if h.get("week_key") != summary["week_key"]]
    hist.append(snap)
    hist.sort(key=lambda h: h["week_key"])
    with open(hpath, "w", encoding="utf-8") as f:
        json.dump(hist, f, ensure_ascii=False, indent=2)
    return hist

# ============================================================
# HTML 產生(自足單頁，內嵌 CSS + SVG，GitHub Pages 直接開)
# ============================================================

def _svg_bars(data_pairs, color, max_val=None, height=150, bar_w=34, gap=14):
    """data_pairs: [(label, value), ...] → 回傳內嵌 SVG 長條圖字串。"""
    if not data_pairs:
        return '<div class="empty">無命中</div>'
    max_val = max_val or max((v for _, v in data_pairs), default=1) or 1
    n = len(data_pairs)
    width = n * bar_w + (n + 1) * gap
    bars = []
    for i, (label, val) in enumerate(data_pairs):
        x = gap + i * (bar_w + gap)
        h = 0 if max_val == 0 else (val / max_val) * (height - 30)
        y = height - 22 - h
        bars.append(
            f'<rect x="{x}" y="{y:.1f}" width="{bar_w}" height="{h:.1f}" rx="3" fill="{color}"/>'
            f'<text x="{x + bar_w/2:.1f}" y="{y - 4:.1f}" text-anchor="middle" '
            f'font-size="11" fill="{PALETTE["paper"]}">{val:g}</text>'
            f'<text x="{x + bar_w/2:.1f}" y="{height - 6}" text-anchor="middle" '
            f'font-size="11" fill="{PALETTE["mute"]}">{html.escape(label)}</text>'
        )
    return (f'<svg viewBox="0 0 {width} {height}" width="100%" '
            f'preserveAspectRatio="xMidYMid meet" role="img">{"".join(bars)}</svg>')

def _trend_svg(history, key="week_chars", height=160, pad=34):
    """歷史多週折線圖。"""
    if len(history) < 1:
        return '<div class="empty">尚無歷史</div>'
    pts = [(h["week_key"], h.get(key, 0)) for h in history]
    n = len(pts)
    width = max(320, n * 70)
    max_v = max((v for _, v in pts), default=1) or 1
    inner_w = width - pad * 2
    inner_h = height - pad * 2
    coords = []
    for i, (_, v) in enumerate(pts):
        x = pad + (inner_w * (i / (n - 1)) if n > 1 else inner_w / 2)
        y = pad + inner_h - (v / max_v) * inner_h
        coords.append((x, y))
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{PALETTE["gold"]}"/>'
        f'<text x="{x:.1f}" y="{y - 8:.1f}" text-anchor="middle" font-size="10" '
        f'fill="{PALETTE["paper"]}">{pts[i][1]:,.0f}</text>'
        for i, (x, y) in enumerate(coords)
    )
    labels = "".join(
        f'<text x="{x:.1f}" y="{height - 8}" text-anchor="middle" font-size="10" '
        f'fill="{PALETTE["mute"]}">{html.escape(pts[i][0])}</text>'
        for i, (x, _y) in enumerate(coords)
    )
    line = (f'<polyline points="{poly}" fill="none" stroke="{PALETTE["jade"]}" '
            f'stroke-width="2"/>') if n > 1 else ""
    return (f'<svg viewBox="0 0 {width} {height}" width="100%" '
            f'preserveAspectRatio="xMidYMid meet" role="img">{line}{dots}{labels}</svg>')

def _histogram_svg(dist, key, color, height=200):
    """全庫回溯直方圖：dist=[{week,files,chars}...]，依週橫排，橫向可捲。"""
    if not dist:
        return '<div class="empty">無資料</div>'
    n = len(dist)
    bar_w = max(6, min(30, int(760 / n)))
    gap = max(2, bar_w // 3)
    width = n * (bar_w + gap) + gap
    max_val = max((d[key] for d in dist), default=1) or 1
    label_every = max(1, n // 14)  # 週數多時稀疏標籤，避免擠成一團
    parts = []
    for i, d in enumerate(dist):
        x = gap + i * (bar_w + gap)
        h = (d[key] / max_val) * (height - 44)
        y = height - 26 - h
        parts.append(
            f'<rect x="{x}" y="{y:.1f}" width="{bar_w}" height="{h:.1f}" rx="2" fill="{color}">'
            f'<title>{html.escape(d["week"])} ｜ {d["files"]:,} 檔 ｜ {d["chars"]:,} 字元</title></rect>'
        )
        if i % label_every == 0 or i == n - 1:
            wk_short = d["week"].split("-")[-1]  # e.g. W34
            parts.append(
                f'<text x="{x + bar_w/2:.1f}" y="{height - 8}" text-anchor="middle" '
                f'font-size="9" fill="{PALETTE["mute"]}">{html.escape(wk_short)}</text>'
            )
    peak = max(dist, key=lambda d: d[key])
    parts.append(
        f'<text x="{gap}" y="14" font-size="11" fill="{PALETTE["mute"]}">'
        f'峰值 {html.escape(peak["week"])}：{peak[key]:,}</text>'
    )
    svg = (f'<svg viewBox="0 0 {width} {height}" width="{max(width, 320)}" height="{height}" '
           f'role="img">{"".join(parts)}</svg>')
    return f'<div style="overflow-x:auto;padding-bottom:4px">{svg}</div>'

def _ring_heatmap_svg(dist, rings_6, rings_5):
    """環次命中時間熱區圖：環當列、週當欄、色深＝該週該環累計強度。
    六環用 teal(gold)、五環用 jade，以色相區分兩組截面。"""
    if not dist:
        return '<div class="empty">無資料</div>'
    rings = rings_6 + rings_5
    n = len(dist)
    cell_w = max(9, min(26, int(760 / n)))
    cell_h = 17
    left = 46            # 左側環標籤欄寬
    top = 6
    gap_group = 6        # 六環/五環之間留白
    rows = len(rings)
    height = top + rows * cell_h + gap_group + 22
    width = left + n * cell_w + 6
    # 全域最大強度(排除 0)供正規化
    gmax = max((b["rings"][r] for b in dist for r in rings), default=1) or 1
    label_every = max(1, n // 14)

    def short(r):
        return r.replace("總綱環", "綱").replace("總經環", "經")

    parts = []
    for ri, r in enumerate(rings):
        grp_color = PALETTE["gold"] if r in rings_6 else PALETTE["jade"]
        extra = gap_group if r in rings_5 else 0   # 五環起始下推留白
        ry = top + ri * cell_h + extra
        # 左側環標籤
        parts.append(
            f'<text x="{left - 6}" y="{ry + cell_h*0.7:.1f}" text-anchor="end" '
            f'font-size="10" fill="{PALETTE["paper"]}">{html.escape(short(r))}</text>'
        )
        for wi, b in enumerate(dist):
            v = b["rings"][r]
            x = left + wi * cell_w
            op = 0.0 if v == 0 else round(0.12 + 0.88 * (v / gmax), 3)
            fill = "#F2F7F5" if v == 0 else grp_color
            parts.append(
                f'<rect x="{x}" y="{ry:.1f}" width="{cell_w-1}" height="{cell_h-1}" '
                f'rx="1.5" fill="{fill}" fill-opacity="{op}">'
                f'<title>{html.escape(b["week"])} ｜ {html.escape(short(r))} ｜ 強度 {v:g}</title></rect>'
            )
    # 底部週標籤(稀疏)
    ybase = top + rows * cell_h + gap_group + 14
    for wi, b in enumerate(dist):
        if wi % label_every == 0 or wi == n - 1:
            x = left + wi * cell_w + cell_w / 2
            parts.append(
                f'<text x="{x:.1f}" y="{ybase}" text-anchor="middle" font-size="9" '
                f'fill="{PALETTE["mute"]}">{html.escape(b["week"].split("-")[-1])}</text>'
            )
    svg = (f'<svg viewBox="0 0 {width} {height}" width="{max(width, 320)}" height="{height}" '
           f'role="img">{"".join(parts)}</svg>')
    return f'<div style="overflow-x:auto;padding-bottom:4px">{svg}</div>'

def _stat_card(label, value, sub=""):
    sub_html = f'<div class="stat-sub">{html.escape(sub)}</div>' if sub else ""
    return (f'<div class="stat"><div class="stat-val">{html.escape(str(value))}</div>'
            f'<div class="stat-label">{html.escape(label)}</div>{sub_html}</div>')

def render_html(files, summary, history):
    P = PALETTE
    week_files = [f for f in files if f["is_new"]]

    # 統計卡
    cards = "".join([
        _stat_card("素材總數", summary["total_files"], f'本週新增 {summary["week_files"]}'),
        _stat_card("本週新增", summary["week_files"], summary["week_key"]),
        _stat_card("字元總量", f'{summary["total_chars"]:,}', f'本週 +{summary["week_chars"]:,}'),
        _stat_card("掃描目錄", len(summary["scan_dirs"]),
                   f'缺 {len(summary["missing_dirs"])}' if summary["missing_dirs"] else "全部就緒"),
    ])

    # 六環 / 五環 柱圖(本週強度)
    six_pairs = [(r.replace("總綱環", ""), summary["ring_week"][r]) for r in RING_ORDER_6]
    five_pairs = [(r.replace("總經環", ""), summary["ring_week"][r]) for r in RING_ORDER_5]
    six_total_pairs = [(r.replace("總綱環", ""), summary["ring_total"][r]) for r in RING_ORDER_6]
    five_total_pairs = [(r.replace("總經環", ""), summary["ring_total"][r]) for r in RING_ORDER_5]

    # 缺目錄警示
    missing_html = ""
    if summary["missing_dirs"]:
        items = "".join(f"<li>{html.escape(d)}</li>" for d in summary["missing_dirs"])
        missing_html = (f'<div class="warn"><b>掃描目錄缺失</b>（未計入）：<ul>{items}</ul></div>')

    # 本週新增檔清單
    basis = summary.get("date_basis", "modified")
    b_created = " (基準)" if basis == "created" else ""
    b_modified = " (基準)" if basis == "modified" else ""
    if week_files:
        rows = []
        for f in week_files[:200]:
            ring_tags = "".join(
                f'<span class="ring-tag">{html.escape(r.replace("總綱","綱").replace("總經","經"))}·{s:g}</span>'
                for r, (_c, s) in sorted(f["rings"].items(), key=lambda kv: -kv[1][1])
            ) or '<span class="ring-none">—</span>'
            # 建立==修改 標一致；不同則標出（複製污染的線索）
            same = f["created"][:16] == f["modified"][:16]
            cre_cls = "" if basis != "created" else ' style="font-weight:600"'
            mod_cls = "" if basis != "modified" else ' style="font-weight:600"'
            rows.append(
                f'<tr><td class="fn" title="{html.escape(f["path"])}">{html.escape(f["name"])}</td>'
                f'<td{cre_cls}>{f["created"][:16].replace("T"," ")}</td>'
                f'<td{mod_cls}>{f["modified"][:16].replace("T"," ")}</td>'
                f'<td class="num">{f["lines"]:,}</td>'
                f'<td class="num">{f["chars"]:,}</td>'
                f'<td class="enc">{html.escape(f["encoding"])}</td>'
                f'<td class="rings">{ring_tags}</td></tr>'
                f'<tr class="preview"><td colspan="7">{html.escape(f["first_line"])}</td></tr>'
            )
        week_table = (
            '<table class="ftable"><thead><tr><th>檔名</th>'
            f'<th>建立時間{b_created}</th><th>修改時間{b_modified}</th>'
            '<th class="num">行</th><th class="num">字元</th><th>編碼</th>'
            '<th>環次命中(強度)</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table>"
        )
        if len(week_files) > 200:
            week_table += f'<div class="mute">（僅列前 200 筆，本週共 {len(week_files)} 筆）</div>'
    else:
        week_table = f'<div class="empty">本週無新增素材（依檔案{"建立" if basis=="created" else "修改"}日期判定）</div>'

    generated = summary["asof"].replace("T", " ")

    css = f"""
    :root{{--void:{P['void']};--gold:{P['gold']};--gold-dim:{P['gold_dim']};
      --jade:{P['jade']};--red:{P['red']};--paper:{P['paper']};--mute:{P['mute']};
      --line:{P['line']};--panel:{P['panel']};}}
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:var(--void);color:var(--paper);
      font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",system-ui,sans-serif;
      line-height:1.6;padding:28px 18px}}
    .wrap{{max-width:1080px;margin:0 auto}}
    h1{{font-family:"Noto Serif TC","Songti TC",serif;font-size:26px;color:var(--gold);
      letter-spacing:2px}}
    .sub{{color:var(--mute);font-size:13px;margin:4px 0 2px}}
    .motto{{font-family:"Noto Serif TC",serif;color:var(--jade);font-size:14px;margin:6px 0 22px}}
    .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:24px}}
    .stat{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px 14px;text-align:center}}
    .stat-val{{font-family:"JetBrains Mono",Consolas,monospace;font-size:28px;color:var(--gold);font-weight:700}}
    .stat-label{{font-size:13px;color:var(--paper);margin-top:2px}}
    .stat-sub{{font-size:11px;color:var(--mute);margin-top:2px}}
    section{{background:#fff;border:1px solid var(--line);border-radius:14px;padding:20px;margin-bottom:20px}}
    section h2{{font-family:"Noto Serif TC",serif;font-size:18px;color:var(--gold);
      border-bottom:1px solid var(--line);padding-bottom:8px;margin-bottom:14px}}
    .two{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}
    @media(max-width:720px){{.two{{grid-template-columns:1fr}}}}
    .chart-title{{font-size:13px;color:var(--mute);margin-bottom:4px}}
    .ftable{{width:100%;border-collapse:collapse;font-size:13px}}
    .ftable th{{text-align:left;color:var(--mute);font-weight:600;border-bottom:1px solid var(--line);
      padding:6px 8px;font-size:12px}}
    .ftable td{{padding:6px 8px;border-bottom:1px solid #EDF3F0;vertical-align:top}}
    .ftable td.num{{text-align:right;font-family:"JetBrains Mono",monospace}}
    .ftable td.fn{{font-weight:600;max-width:230px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
    .ftable td.enc{{font-family:"JetBrains Mono",monospace;font-size:11px;color:var(--mute)}}
    tr.preview td{{color:var(--mute);font-size:12px;border-bottom:1px solid var(--line);padding-top:0}}
    .ring-tag{{display:inline-block;background:var(--void);border:1px solid var(--gold-dim);
      color:var(--gold);border-radius:6px;padding:1px 6px;margin:1px 2px;font-size:11px;
      font-family:"JetBrains Mono",monospace}}
    .ring-none,.mute{{color:var(--mute);font-size:12px}}
    .empty{{color:var(--mute);text-align:center;padding:20px;font-size:13px}}
    .warn{{background:#FBF1F1;border:1px solid var(--red);color:var(--red);border-radius:10px;
      padding:10px 14px;margin-bottom:18px;font-size:13px}}
    .warn ul{{margin:6px 0 0 18px}}
    .note{{color:var(--mute);font-size:12px;margin-top:8px}}
    footer{{color:var(--mute);font-size:12px;text-align:center;margin-top:26px;
      font-family:"Noto Serif TC",serif}}
    """

    body = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>相閘 XiangGate · 週報 {html.escape(summary['week_key'])}</title>
<style>{css}</style>
</head>
<body>
<div class="wrap">
  <h1>相閘 XiangGate · 素材週報</h1>
  <div class="sub">{html.escape(summary['week_key'])} ｜ 週起 {html.escape(summary['week_start'])} ｜ 產出 {html.escape(generated)} ｜ 匯入日期基準：<b>{'建立日期' if summary.get('date_basis')=='created' else '修改日期'}</b></div>
  <div class="motto">相入 · 閘決 · Edward 坍縮 · 軸不動，θ 趨近。</div>

  {missing_html}

  <div class="grid">{cards}</div>

  <section>
    <h2>環次命中 · 本週強度</h2>
    <div class="two">
      <div>
        <div class="chart-title">總綱 · 六環自噬迴圈（社會截面）</div>
        {_svg_bars(six_pairs, P['gold'])}
      </div>
      <div>
        <div class="chart-title">總經 · 食利瀑布（五環 · 金融截面）</div>
        {_svg_bars(five_pairs, P['jade'])}
      </div>
    </div>
    <div class="note">環次命中為關鍵詞啟發式（示範層，規格 §9）。強度＝Σ min(1, 命中次數/{RING_SATURATION})。
      關鍵詞源自相閘正典 is_active 命題；正式版由對撞引擎逐命題判定。命名/坍縮權屬 Edward。</div>
  </section>

  <section>
    <h2>環次命中 · 全庫累計</h2>
    <div class="two">
      <div>
        <div class="chart-title">總綱六環（累計強度）</div>
        {_svg_bars(six_total_pairs, P['gold_dim'])}
      </div>
      <div>
        <div class="chart-title">總經五環（累計強度）</div>
        {_svg_bars(five_total_pairs, P['jade_dim'])}
      </div>
    </div>
  </section>

  <section>
    <h2>環次命中 · 時間趨勢（依{'建立' if summary.get('date_basis')=='created' else '修改'}週 · 熱區圖）</h2>
    <div class="chart-title">11 環 × 週 ｜ 上 6 列＝總綱六環(teal)、下 5 列＝總經五環(jade) ｜ 色深＝該週該環累計強度</div>
    {_ring_heatmap_svg(summary['week_distribution'], RING_ORDER_6, RING_ORDER_5)}
    <div class="note">規格 §5「環次每週 11 線趨勢」的熱區版——哪一環在哪幾週發熱一眼看穿。
      滑鼠移到格看週／環／強度。強度為關鍵詞啟發式（示範層 §9），正式版由對撞引擎判定。</div>
  </section>

  <section>
    <h2>素材時間分佈 · 全庫（依{'建立' if summary.get('date_basis')=='created' else '修改'}週）</h2>
    <div class="chart-title">每週素材數（共 {len(summary['week_distribution'])} 週 · {summary['total_files']:,} 檔）</div>
    {_histogram_svg(summary['week_distribution'], 'files', P['gold'])}
    <div class="chart-title" style="margin-top:14px">每週字元量</div>
    {_histogram_svg(summary['week_distribution'], 'chars', P['jade'])}
    <div class="note">全庫回溯：每檔依其{'建立' if summary.get('date_basis')=='created' else '修改'}日期歸入 ISO 週，
      即時計算（規格 §5），非腳本執行紀錄。滑鼠移到長條看該週檔數／字元。
      history.json 仍每週追加做不遺忘稽核。</div>
  </section>

  <section>
    <h2>本週新增素材（{summary['week_files']} 筆）</h2>
    {week_table}
  </section>

  <footer>相閘 · 系統做 90-99%，Edward 做 100% · 本報告只給方位/計數/命中，不做結論、不替 Edward 坍縮。</footer>
</div>
</body>
</html>"""
    return body

# ============================================================
# 主流程
# ============================================================

def run_diag(scan_dirs, asof_dt, sample=30):
    """診斷：列出樣本檔的建立 vs 修改日期，看哪個被複製動作污染成今天。"""
    files, summary = gather(scan_dirs, EXTENSIONS, asof_dt)
    today = asof_dt.date().isoformat()
    cre_today = sum(1 for f in files if f["created"][:10] == today)
    mod_today = sum(1 for f in files if f["modified"][:10] == today)
    print(f"[診斷] 掃到 {len(files)} 檔  as-of {today}")
    print(f"  建立日期＝今天的檔數：{cre_today}  （{cre_today*100//max(1,len(files))}%）")
    print(f"  修改日期＝今天的檔數：{mod_today}  （{mod_today*100//max(1,len(files))}%）")
    print(f"  建立≠修改 的檔數    ：{sum(1 for f in files if f['created'][:16]!=f['modified'][:16])}")
    print(f"  → 若「建立日期＝今天」佔比異常高，代表檔案是被複製進來的，改用 DATE_BASIS='modified'\n")
    print(f"{'檔名':<40} {'建立':<17} {'修改':<17}")
    print("-" * 78)
    for f in files[:sample]:
        nm = (f["name"][:38] + "..") if len(f["name"]) > 40 else f["name"]
        print(f"{nm:<40} {f['created'][:16]:<17} {f['modified'][:16]:<17}")
    if len(files) > sample:
        print(f"...（僅列前 {sample} 筆，共 {len(files)} 筆）")

def main():
    ap = argparse.ArgumentParser(description="相閘週報產生器")
    ap.add_argument("--dirs", nargs="+", help="覆寫掃描目錄")
    ap.add_argument("--out", help="覆寫輸出目錄")
    ap.add_argument("--asof", help="固定 as-of 日期(YYYY-MM-DD，僅測試用)；預設 now()")
    ap.add_argument("--diag", action="store_true", help="診斷模式：對照建立vs修改日期，不產報告")
    args = ap.parse_args()

    scan_dirs = args.dirs if args.dirs else SCAN_DIRS
    out_dir = args.out if args.out else OUTPUT_DIR
    if args.asof:
        asof_dt = datetime.strptime(args.asof, "%Y-%m-%d")
    else:
        asof_dt = datetime.now()  # 日期鐵律：以執行當下為錨

    if args.diag:
        run_diag(scan_dirs, asof_dt)
        return 0

    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(os.path.join(out_dir, "reports"), exist_ok=True)

    files, summary = gather(scan_dirs, EXTENSIONS, asof_dt)
    history = update_history(out_dir, summary)
    page = render_html(files, summary, history)

    # 覆寫最新首頁
    index_path = os.path.join(out_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(page)
    # 封存本週
    archive_path = os.path.join(out_dir, "reports", f"{summary['week_key']}.html")
    with open(archive_path, "w", encoding="utf-8") as f:
        f.write(page)

    print(f"[相閘週報] {summary['week_key']}  as-of {summary['asof']}")
    print(f"  匯入日期基準: {summary['date_basis']}（{'建立日期' if summary['date_basis']=='created' else '修改日期'}）")
    print(f"  掃描目錄  : {scan_dirs}")
    if summary["missing_dirs"]:
        print(f"  ⚠ 缺目錄  : {summary['missing_dirs']}")
    print(f"  素材總數  : {summary['total_files']}（本週新增 {summary['week_files']}）")
    print(f"  字元總量  : {summary['total_chars']:,}（本週 +{summary['week_chars']:,}）")
    print(f"  歷史週數  : {len(history)}")
    print(f"  首頁      : {index_path}")
    print(f"  封存      : {archive_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())

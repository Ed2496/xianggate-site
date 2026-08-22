# -*- coding: utf-8 -*-
r"""
相閘 XiangGate · 標記模組 xianggate_mark.py  (v0.1)
================================================================
定位：第四境(鑑識)之下的共用標記資料層。
      相→行→體→用 為座標軸，五數學為軸上讀數。一篇文本 × 一環 = mark_chain 一筆。

欄位（對齊 2026-08-22 定義）：
  depth      標記鏈停在第幾層 0/1/2/3/4（0＝四層皆未標）
  layer_vec  傅立葉：[相,行,體,用] 命中句數比
  sigma      拉普拉斯：環級四週 depth 變化率（由 weekly 用 history 算，文本級寫 NULL）
  mobius     莫比烏斯：相層主語 == 用層主語 → 1；算不出 NULL
  mobius_pair莫比烏斯配對（PUBLIC_SAFE 只留機構類型，遮人名/專名）
  klein      克萊因瓶：內／外／無／NULL
  q_state    量子：疊加／坍縮／反觀測／無／NULL（糾纏、觀測者中毒 環級留空待定義）
  src        規則＝'rule'；lambda TXT 手改覆寫＝'hand'

紀律：
  * 算不出就 NULL，不填 0、不填預設。
  * 詞表可由 OUTPUT_DIR/terms/*.txt 覆寫（一行一詞，# 開頭為註解），改詞表不改碼。
  * 零第三方依賴：只用標準庫 re / json / sqlite3。
"""

import os
import re
import json
import sqlite3

# ============================================================
# 詞表（預設；可被 terms/*.txt 覆寫）
# ============================================================

DEFAULT_LAYER_TERMS = {
    "相": ["現象", "數據", "數字", "出現", "報導", "趨勢", "發現", "看到", "統計", "指標", "上漲", "下跌", "增加", "減少"],
    "行": ["SOP", "流程", "步驟", "作業", "程序", "標準", "規範", "執行", "操作", "機制", "做法", "手續", "制度設計"],
    "體": ["負責", "責任", "主管", "部門", "條款", "ISO", "稽核", "審查", "授權", "權責", "董事", "經理", "監管", "主管機關", "該由"],
    "用": ["獲利", "利潤", "營收", "受益", "成本", "損益", "股東", "分潤", "獲益", "利益", "金流", "賺", "收益", "套利", "誰拿"],
}

# 克萊因瓶：體層責任人在制度內(可指到崗位/條款)或制度外(無崗位主語)
DEFAULT_KLEIN_IN = ["主管", "部門", "經理", "課長", "董事會", "委員會", "條款", "稽核", "PM", "工程師", "處長", "總經理", "董事長", "主管機關", "監管機構", "央行", "金管會"]
DEFAULT_KLEIN_OUT = ["市場", "環境", "時代", "大家", "社會", "大環境", "體制", "趨勢使然", "結構性", "無可避免", "自然"]

# 量子態：用層主語判定
DEFAULT_Q_REFLEX = ["你應該", "我們都", "各位", "每個人都", "你我", "讀者", "你要", "大家要"]
DEFAULT_Q_VAGUE = ["有人", "部分人", "相關方", "某些", "一些人", "既得利益者", "有心人", "背後的人", "少數人"]
# 明確主語：以機構後綴抓
ORG_SUFFIX = ["公司", "集團", "銀行", "基金", "政府", "平台", "機構", "交易所", "財團", "券商", "保險", "企業", "黨", "局", "部", "署", "會"]

_SENT_SPLIT = re.compile(r"[。！？!?\n]+")
_ORG_RE = re.compile(r"([\u4e00-\u9fffA-Za-z0-9]{2,10}?)(" + "|".join(ORG_SUFFIX) + r")(?![\u4e00-\u9fff])")
_NAME_MASK = "○"

def _load_terms_file(path):
    if not os.path.isfile(path):
        return None
    out = []
    with open(path, "r", encoding="utf-8-sig") as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith("#"):
                out.append(s)
    return out or None

def load_terms(terms_dir):
    """從 terms_dir 讀詞表覆寫；缺檔用預設。回傳 dict。"""
    t = {
        "layer": {k: list(v) for k, v in DEFAULT_LAYER_TERMS.items()},
        "klein_in": list(DEFAULT_KLEIN_IN),
        "klein_out": list(DEFAULT_KLEIN_OUT),
        "q_reflex": list(DEFAULT_Q_REFLEX),
        "q_vague": list(DEFAULT_Q_VAGUE),
    }
    if not terms_dir:
        return t
    for k, fn in (("相", "layer_xiang.txt"), ("行", "layer_xing.txt"),
                  ("體", "layer_ti.txt"), ("用", "layer_yong.txt")):
        v = _load_terms_file(os.path.join(terms_dir, fn))
        if v:
            t["layer"][k] = v
    for k, fn in (("klein_in", "klein_in.txt"), ("klein_out", "klein_out.txt"),
                  ("q_reflex", "q_reflex.txt"), ("q_vague", "q_vague.txt")):
        v = _load_terms_file(os.path.join(terms_dir, fn))
        if v:
            t[k] = v
    return t

def write_default_terms(terms_dir):
    """第一次跑時把預設詞表吐成 TXT，讓 Edward 直接改。已存在不覆寫。"""
    os.makedirs(terms_dir, exist_ok=True)
    files = {
        "layer_xiang.txt": DEFAULT_LAYER_TERMS["相"],
        "layer_xing.txt": DEFAULT_LAYER_TERMS["行"],
        "layer_ti.txt": DEFAULT_LAYER_TERMS["體"],
        "layer_yong.txt": DEFAULT_LAYER_TERMS["用"],
        "klein_in.txt": DEFAULT_KLEIN_IN,
        "klein_out.txt": DEFAULT_KLEIN_OUT,
        "q_reflex.txt": DEFAULT_Q_REFLEX,
        "q_vague.txt": DEFAULT_Q_VAGUE,
    }
    for fn, words in files.items():
        p = os.path.join(terms_dir, fn)
        if os.path.isfile(p):
            continue
        with open(p, "w", encoding="utf-8") as f:
            f.write("# 一行一詞，# 開頭為註解。改詞表不改碼。坍縮權：Edward\n")
            f.write("\n".join(words) + "\n")

# ============================================================
# 標記核心
# ============================================================

LAYERS = ["相", "行", "體", "用"]

def _sentences(text):
    return [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]

def _mask_org(name, suffix, public_safe):
    """PUBLIC_SAFE：遮專名留機構類型（○○公司）。"""
    if not public_safe:
        return name + suffix
    return _NAME_MASK * min(len(name), 2) + suffix

def mark_text(text, terms, public_safe=True):
    """回傳單篇文本的標記 dict（不含環號；環號由呼叫端掛上）。"""
    sents = _sentences(text)
    hit = {k: 0 for k in LAYERS}
    layer_sents = {k: [] for k in LAYERS}
    for s in sents:
        for k in LAYERS:
            if any(w in s for w in terms["layer"][k]):
                hit[k] += 1
                layer_sents[k].append(s)
    total = sum(hit.values())
    if total == 0:
        layer_vec = [0.0, 0.0, 0.0, 0.0]
        depth = 0
    else:
        layer_vec = [round(hit[k] / total, 3) for k in LAYERS]
        depth = max(i + 1 for i, k in enumerate(LAYERS) if hit[k] > 0)

    # 克萊因瓶（需到體層）
    klein = None
    if depth >= 3:
        ti_text = "。".join(layer_sents["體"])
        if any(w in ti_text for w in terms["klein_in"]):
            klein = "內"
        elif any(w in ti_text for w in terms["klein_out"]):
            klein = "外"
        else:
            klein = None  # 到了體層但指不出內外 → 算不出
    else:
        klein = "無"

    # 量子態（需到用層）
    q_state = None
    yong_text = "。".join(layer_sents["用"])
    yong_orgs = _ORG_RE.findall(yong_text) if depth >= 4 else []
    if depth >= 4:
        if any(w in yong_text for w in terms["q_reflex"]):
            q_state = "反觀測"
        elif yong_orgs:
            q_state = "坍縮"
        elif any(w in yong_text for w in terms["q_vague"]):
            q_state = "疊加"
        else:
            q_state = None
    else:
        q_state = "無"

    # 莫比烏斯（需 q_state=坍縮 才可算）
    mobius = None
    mobius_pair = None
    if q_state == "坍縮":
        xiang_text = "。".join(layer_sents["相"])
        xiang_orgs = set(n + s for n, s in _ORG_RE.findall(xiang_text))
        yong_set = set(n + s for n, s in yong_orgs)
        same = xiang_orgs & yong_set
        mobius = 1 if same else 0
        narr = sorted(xiang_orgs)[:3]
        prof = sorted(yong_set)[:3]
        def _m(lst):
            out = []
            for full in lst:
                m = _ORG_RE.fullmatch(full)
                if m:
                    out.append(_mask_org(m.group(1), m.group(2), public_safe))
                else:
                    out.append(full if not public_safe else _NAME_MASK * 2)
            return out
        mobius_pair = json.dumps({"敘事方": _m(narr), "獲利方": _m(prof)}, ensure_ascii=False)

    return {
        "depth": depth,
        "layer_vec": layer_vec,
        "layer_hits": hit,
        "klein": klein,
        "q_state": q_state,
        "mobius": mobius,
        "mobius_pair": mobius_pair,
    }

def ring_sequence(text, ring_keywords):
    """各環在文本中首次出現的位置 → 依位置排序給 ring_seq（從 1 起）。未命中不列。"""
    firsts = []
    for ring, kws in ring_keywords.items():
        pos = None
        for kw in kws:
            i = text.find(kw)
            if i >= 0 and (pos is None or i < pos):
                pos = i
        if pos is not None:
            firsts.append((pos, ring))
    firsts.sort()
    return {ring: i + 1 for i, (_p, ring) in enumerate(firsts)}

# ============================================================
# sqlite
# ============================================================

SCHEMA = """
CREATE TABLE IF NOT EXISTS mark_chain (
  text_id      TEXT NOT NULL,          -- 檔案 sha256[:16]（weekly 既有）
  week_key     TEXT NOT NULL,          -- 依 basis 日期歸入的 ISO 週
  ring_id      TEXT NOT NULL,          -- 總綱環①…總經環⑤
  ring_seq     INTEGER,                -- 該環在此文本內的出現順序
  depth        INTEGER,
  layer_vec    TEXT,                   -- JSON [相,行,體,用]
  sigma        REAL,                   -- 文本級一律 NULL（環級見 ring_week_stats）
  mobius       INTEGER,
  mobius_pair  TEXT,
  klein        TEXT,
  q_state      TEXT,
  src          TEXT DEFAULT 'rule',
  asof         TEXT,
  PRIMARY KEY (text_id, ring_id)
);
CREATE TABLE IF NOT EXISTS ring_week_stats (
  week_key   TEXT NOT NULL,
  ring_id    TEXT NOT NULL,
  n_files    INTEGER,
  avg_depth  REAL,
  sigma      REAL,                     -- 四週 depth 變化率；無歷史 NULL
  layer_vec  TEXT,                     -- 該環該週平均 [相,行,體,用]
  klein_in   INTEGER, klein_out INTEGER,
  q_collapse INTEGER, q_super INTEGER, q_reflex INTEGER,
  mobius_cnt INTEGER,
  asof       TEXT,
  PRIMARY KEY (week_key, ring_id)
);
CREATE TABLE IF NOT EXISTS lambda_statement (
  week_key   TEXT NOT NULL,
  ring_id    TEXT NOT NULL,
  status     TEXT NOT NULL,            -- 候選 / 定稿 / 否決
  statement  TEXT,
  src        TEXT,                     -- rule / hand
  updated    TEXT,
  PRIMARY KEY (week_key, ring_id)
);
CREATE INDEX IF NOT EXISTS idx_mark_week ON mark_chain(week_key, ring_id);
"""

def open_db(db_path):
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)
    return con

def write_marks(con, rows):
    """rows: list of dict（與 mark_chain 欄位同名）。src='hand' 的既有列不被 rule 覆寫。"""
    cur = con.cursor()
    for r in rows:
        cur.execute("SELECT src FROM mark_chain WHERE text_id=? AND ring_id=?", (r["text_id"], r["ring_id"]))
        ex = cur.fetchone()
        if ex and ex[0] == "hand":
            continue
        cur.execute("""INSERT OR REPLACE INTO mark_chain
            (text_id,week_key,ring_id,ring_seq,depth,layer_vec,sigma,mobius,mobius_pair,klein,q_state,src,asof)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (r["text_id"], r["week_key"], r["ring_id"], r.get("ring_seq"), r["depth"],
             json.dumps(r["layer_vec"]), None, r.get("mobius"), r.get("mobius_pair"),
             r.get("klein"), r.get("q_state"), r.get("src", "rule"), r.get("asof")))
    con.commit()

def write_ring_week_stats(con, stats):
    cur = con.cursor()
    for s in stats:
        cur.execute("""INSERT OR REPLACE INTO ring_week_stats
            (week_key,ring_id,n_files,avg_depth,sigma,layer_vec,klein_in,klein_out,
             q_collapse,q_super,q_reflex,mobius_cnt,asof)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (s["week_key"], s["ring_id"], s["n_files"], s["avg_depth"], s.get("sigma"),
             json.dumps(s["layer_vec"]), s["klein_in"], s["klein_out"],
             s["q_collapse"], s["q_super"], s["q_reflex"], s["mobius_cnt"], s["asof"]))
    con.commit()

def read_lambda(con, week_key):
    cur = con.cursor()
    cur.execute("SELECT ring_id,status,statement,src,updated FROM lambda_statement WHERE week_key=?", (week_key,))
    return {r[0]: {"status": r[1], "statement": r[2], "src": r[3], "updated": r[4]} for r in cur.fetchall()}

# ============================================================
# 彙整（環級）
# ============================================================

def aggregate_ring_week(marks, ring_order, week_key, asof, history_depth=None):
    """marks: list of mark_chain rows(本週)。history_depth: {ring: [前幾週 avg_depth...]}（舊→新）供 sigma。"""
    out = []
    by_ring = {}
    for m in marks:
        by_ring.setdefault(m["ring_id"], []).append(m)
    for r in ring_order:
        ms = by_ring.get(r, [])
        n = len(ms)
        if n == 0:
            out.append({"week_key": week_key, "ring_id": r, "n_files": 0, "avg_depth": None,
                        "sigma": None, "layer_vec": [None] * 4, "klein_in": 0, "klein_out": 0,
                        "q_collapse": 0, "q_super": 0, "q_reflex": 0, "mobius_cnt": 0, "asof": asof})
            continue
        avg_depth = round(sum(m["depth"] for m in ms) / n, 3)
        lv = [round(sum(m["layer_vec"][i] for m in ms) / n, 3) for i in range(4)]
        sigma = None
        if history_depth and history_depth.get(r):
            prev = [d for d in history_depth[r] if d is not None][-4:]
            if len(prev) >= 1:
                sigma = round((avg_depth - sum(prev) / len(prev)) / 4, 4)
        out.append({
            "week_key": week_key, "ring_id": r, "n_files": n, "avg_depth": avg_depth,
            "sigma": sigma, "layer_vec": lv,
            "klein_in": sum(1 for m in ms if m["klein"] == "內"),
            "klein_out": sum(1 for m in ms if m["klein"] == "外"),
            "q_collapse": sum(1 for m in ms if m["q_state"] == "坍縮"),
            "q_super": sum(1 for m in ms if m["q_state"] == "疊加"),
            "q_reflex": sum(1 for m in ms if m["q_state"] == "反觀測"),
            "mobius_cnt": sum(1 for m in ms if m["mobius"] == 1),
            "asof": asof,
        })
    return out

# -*- coding: utf-8 -*-
r"""
相閘 XiangGate · 第五境 Λ 陳述引擎 xianggate_lambda.py  (v0.1)
================================================================
定位：第五境（刀收回，立命題）。讀第四境寫入的 mark_chain / ring_week_stats，
      依環號順序出 Λ 陳述「候選」，寫 lambda_statement 表 + 吐 lambda/lambda_<week>.txt。
      Edward 改 TXT 定稿，下次跑回讀覆寫 db。

定稿操作（三值，無第四種）：
  [總綱環②] status=候選   ← 改成 定稿 / 否決；Λ: 那行可改字
  status=定稿 的環：下次自動跑不再覆蓋。
  status=否決 的環：保留紀錄，報告標灰。
  status=候選 的環：每次重出候選（規則模板）。

紀律：
  * 候選是規則模板（零依賴），不是模型生成。候選只給方位/讀數，Λ 陳述的正面命題由 Edward 下筆。
  * 日期鐵律：week_key 預設由 datetime.now() 算，--week 可覆寫。
  * 不碰 weekly 的掃描/命中邏輯。需要重刷報告時呼叫 weekly.main()。

用法：
  python xianggate_lambda.py                  # 生成/回讀本週
  python xianggate_lambda.py --week 2026-W34  # 指定週
  python xianggate_lambda.py --rerender       # 回讀定稿後重跑 weekly 產報告
"""

import os
import re
import sys
import json
import argparse
from datetime import datetime

import xianggate_mark as XM

# 與 weekly 同一 OUTPUT_DIR；weekly 若有 --out 覆寫，這裡也用 --out
OUTPUT_DIR = r"C:\Users\ed249\Downloads\xianggate-site"
DB_NAME = "xianggate.db"
LAMBDA_SUBDIR = "lambda"

RING_ORDER = ["總綱環①", "總綱環②", "總綱環③", "總綱環④", "總綱環⑤", "總綱環⑥",
              "總經環①", "總經環②", "總經環③", "總經環④", "總經環⑤"]
LAYER_NAME = ["相", "行", "體", "用"]
STATUS_OK = ("候選", "定稿", "否決")

_HEAD_RE = re.compile(r"^\[(總綱環[①-⑥]|總經環[①-⑤])\]\s*status=(\S+)")

def iso_week_key(d):
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"

# ------------------------------------------------------------
# 候選模板（規則）
# ------------------------------------------------------------

def _fmt(v, nd=2):
    return "—" if v is None else f"{v:.{nd}f}"

def candidate_statement(stat):
    """由 ring_week_stats 一筆產出候選。只給讀數與方位，不下結論。"""
    if not stat or not stat["n_files"]:
        return "本週此環無命中。Λ：（待 Edward 下筆或留空）"
    lv = stat["layer_vec"]
    main_layer = LAYER_NAME[max(range(4), key=lambda i: (lv[i] or 0))] if all(v is not None for v in lv) else "—"
    parts = [
        f"命中 {stat['n_files']} 檔",
        f"depth 均值 {_fmt(stat['avg_depth'])}",
        f"主頻＝{main_layer}層",
        f"σ {_fmt(stat['sigma'], 4)}",
        f"klein 內/外 {stat['klein_in']}/{stat['klein_out']}",
        f"q 坍縮/疊加/反觀測 {stat['q_collapse']}/{stat['q_super']}/{stat['q_reflex']}",
        f"mobius 同面 {stat['mobius_cnt']}",
    ]
    hint = ""
    if (stat["avg_depth"] or 0) <= 1.5:
        hint = "截斷在相層，兩本帳密度高；"
    elif stat["klein_out"] > stat["klein_in"]:
        hint = "責任多指向制度外；"
    elif stat["q_super"] > stat["q_collapse"]:
        hint = "到用層但獲利方未坍縮；"
    return "讀數：" + "，".join(parts) + "。方位：" + hint + "Λ：（待 Edward 下筆）"

# ------------------------------------------------------------
# TXT 讀寫
# ------------------------------------------------------------

def lambda_txt_path(out_dir, week_key):
    d = os.path.join(out_dir, LAMBDA_SUBDIR)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"lambda_{week_key}.txt")

def parse_lambda_txt(path):
    """回傳 {ring: {"status":..., "statement":...}}；檔不存在回 {}。"""
    if not os.path.isfile(path):
        return {}
    out = {}
    cur = None
    with open(path, "r", encoding="utf-8-sig") as f:
        for raw in f:
            line = raw.rstrip("\n")
            m = _HEAD_RE.match(line.strip())
            if m:
                cur = m.group(1)
                st = m.group(2)
                if st not in STATUS_OK:
                    st = "候選"  # 非三值一律退回候選，不做第四種
                out[cur] = {"status": st, "statement": ""}
                continue
            if cur and line.strip().startswith("Λ:"):
                out[cur]["statement"] = line.strip()[2:].strip()
            elif cur and line.strip().startswith("Λ："):
                out[cur]["statement"] = line.strip()[2:].strip()
    return out

def write_lambda_txt(path, week_key, entries):
    """entries: {ring: {"status","statement"}} 依 RING_ORDER 輸出。"""
    lines = [
        f"# 相閘 第五境 Λ 陳述 ｜ {week_key} ｜ 產出 {datetime.now().isoformat(timespec='seconds')}",
        "# 操作：改 status=候選 → 定稿 / 否決；Λ: 那行可改字。定稿不會被自動跑覆蓋。",
        "# 三值以外一律視為候選。坍縮權：Edward",
        "",
    ]
    for r in RING_ORDER:
        e = entries.get(r, {"status": "候選", "statement": ""})
        lines.append(f"[{r}] status={e['status']}")
        lines.append(f"Λ: {e['statement']}")
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

# ------------------------------------------------------------
# 主流程
# ------------------------------------------------------------

def run(out_dir, week_key, asof):
    db_path = os.path.join(out_dir, DB_NAME)
    con = XM.open_db(db_path)
    cur = con.cursor()

    # 讀環級統計
    cur.execute("""SELECT ring_id,n_files,avg_depth,sigma,layer_vec,klein_in,klein_out,
                          q_collapse,q_super,q_reflex,mobius_cnt
                   FROM ring_week_stats WHERE week_key=?""", (week_key,))
    stats = {}
    for row in cur.fetchall():
        stats[row[0]] = {
            "n_files": row[1], "avg_depth": row[2], "sigma": row[3],
            "layer_vec": json.loads(row[4]) if row[4] else [None] * 4,
            "klein_in": row[5], "klein_out": row[6],
            "q_collapse": row[7], "q_super": row[8], "q_reflex": row[9], "mobius_cnt": row[10],
        }

    # 讀既有 db 與 TXT
    db_existing = XM.read_lambda(con, week_key)
    txt_path = lambda_txt_path(out_dir, week_key)
    txt = parse_lambda_txt(txt_path)

    entries = {}
    n_final = n_reject = n_cand = 0
    for r in RING_ORDER:
        t = txt.get(r)
        d = db_existing.get(r)
        if t and t["status"] in ("定稿", "否決"):
            entries[r] = {"status": t["status"], "statement": t["statement"], "src": "hand"}
        elif d and d["status"] in ("定稿", "否決"):
            entries[r] = {"status": d["status"], "statement": d["statement"], "src": d["src"] or "hand"}
        else:
            # 候選：若 TXT 有手改文字但未定稿，保留文字仍標候選
            hand_edited = bool(t and t["statement"] and "待 Edward 下筆" not in t["statement"])
            stmt = t["statement"] if hand_edited else candidate_statement(stats.get(r))
            entries[r] = {"status": "候選", "statement": stmt, "src": "hand" if hand_edited else "rule"}
        if entries[r]["status"] == "定稿":
            n_final += 1
        elif entries[r]["status"] == "否決":
            n_reject += 1
        else:
            n_cand += 1

    # 寫 db
    for r, e in entries.items():
        cur.execute("""INSERT OR REPLACE INTO lambda_statement
                       (week_key,ring_id,status,statement,src,updated) VALUES (?,?,?,?,?,?)""",
                    (week_key, r, e["status"], e["statement"], e["src"], asof))
    con.commit()
    con.close()

    # 回寫 TXT（定稿/否決原樣保留，候選刷新）
    write_lambda_txt(txt_path, week_key, entries)

    print(f"[第五境 Λ] {week_key}  定稿 {n_final} ｜ 否決 {n_reject} ｜ 候選 {n_cand}")
    print(f"  TXT: {txt_path}")
    print(f"  DB : {db_path}")
    return entries

def main():
    ap = argparse.ArgumentParser(description="相閘 第五境 Λ 陳述引擎")
    ap.add_argument("--out", help="覆寫輸出目錄（與 weekly 同）")
    ap.add_argument("--week", help="指定 ISO 週 YYYY-Www；預設 now()")
    ap.add_argument("--rerender", action="store_true", help="回讀後重跑 weekly 產報告")
    args = ap.parse_args()
    out_dir = args.out if args.out else OUTPUT_DIR
    now = datetime.now()  # 日期鐵律
    week_key = args.week if args.week else iso_week_key(now.date())
    run(out_dir, week_key, now.isoformat(timespec="seconds"))
    if args.rerender:
        import xianggate_weekly as XW
        sys.argv = [sys.argv[0]] + (["--out", out_dir] if args.out else [])
        return XW.main()
    return 0

if __name__ == "__main__":
    sys.exit(main())

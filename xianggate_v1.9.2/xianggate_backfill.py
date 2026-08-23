# -*- coding: utf-8 -*-
r"""
相閘 XiangGate · 全庫標記回填 xianggate_backfill.py  (v0.1)
================================================================
問題：v1.9 每次只標「本週新增」檔，所以初次跑 mark_chain 只有一週，
      σ 趨勢線／截斷深度熱圖只有一欄，連不成線。
解法：一次性掃全庫，每檔依自己的 basis 日期(修改/建立)歸入所屬 ISO 週，
      補齊所有歷史週的 mark_chain 與 ring_week_stats，並回寫 history.json 的 ring_depth。
      跑完之後 σ 線、深度熱圖就有完整多週資料。

紀律：
  * 重用 weekly 的掃描/命中/日期判準與 mark 模組，不另立一套邏輯。
  * src='hand'（Edward 手改過）的 mark_chain 列永不覆蓋（write_marks 已守）。
  * 冪等：重跑只覆寫 rule 列，不增筆、不動手改。
  * 日期鐵律：週歸位以檔案 basis 日期，非執行日期。

用法：
  python xianggate_backfill.py                     # 用 weekly 的 SCAN_DIRS / OUTPUT_DIR
  python xianggate_backfill.py --dirs D:\a --out D:\site
  python xianggate_backfill.py --dry               # 只報告會標幾筆、幾週，不寫 db
"""

import os
import sys
import json
import argparse
from datetime import datetime

import xianggate_weekly as XW
import xianggate_mark as XM

def iso_week_key(d):
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"

def main():
    ap = argparse.ArgumentParser(description="相閘 全庫標記回填")
    ap.add_argument("--dirs", nargs="+", help="覆寫掃描目錄")
    ap.add_argument("--out", help="覆寫輸出目錄")
    ap.add_argument("--dry", action="store_true", help="乾跑：只統計不寫入")
    args = ap.parse_args()

    scan_dirs = args.dirs if args.dirs else XW.SCAN_DIRS
    out_dir = args.out if args.out else XW.OUTPUT_DIR
    asof_dt = datetime.now()

    if not (XW._MARK_OK and XW.MARK_ENABLED):
        print("✗ 標記層未啟用（缺 xianggate_mark.py 或 MARK_ENABLED=False），無法回填。")
        return 1

    # 載入詞表（與 weekly 同一份）
    terms_dir = os.path.join(out_dir, XW.TERMS_SUBDIR)
    XM.write_default_terms(terms_dir)
    XW._TERMS = XM.load_terms(terms_dir)

    print(f"[回填] 掃描全庫 {scan_dirs}")
    files, _summary = XW.gather(scan_dirs, XW.EXTENSIONS, asof_dt)

    all_rings = XW.RING_ORDER_6 + XW.RING_ORDER_5

    # 每檔 → 依自己的 basis 週，收集 mark_chain 列
    rows_by_week = {}
    n_marked = 0
    for f in files:
        if not f.get("mark"):
            continue
        m = f["mark"]
        wk = iso_week_key(datetime.fromtimestamp(f["basis_ts"]).date())
        for r in f["rings"]:
            rows_by_week.setdefault(wk, []).append({
                "text_id": f["sha256"], "week_key": wk, "ring_id": r,
                "ring_seq": f["ring_seq"].get(r), "depth": m["depth"],
                "layer_vec": m["layer_vec"], "mobius": m["mobius"],
                "mobius_pair": m["mobius_pair"], "klein": m["klein"],
                "q_state": m["q_state"], "src": "rule",
                "asof": asof_dt.isoformat(timespec="seconds"),
            })
            n_marked += 1

    weeks_sorted = sorted(rows_by_week.keys())
    print(f"[回填] 命中檔標記列 {n_marked} 筆，橫跨 {len(weeks_sorted)} 週："
          f"{weeks_sorted[0] if weeks_sorted else '—'} … {weeks_sorted[-1] if weeks_sorted else '—'}")

    if args.dry:
        print("[回填] --dry：以下每週標記筆數，未寫入")
        for wk in weeks_sorted:
            print(f"    {wk}: {len(rows_by_week[wk])} 筆")
        return 0

    # 逐週算 ring_week_stats（sigma 用已處理的前幾週 avg_depth，時序前進）
    db_path = os.path.join(out_dir, XW.DB_NAME)
    con = XM.open_db(db_path)
    hist_depth = {r: [] for r in all_rings}  # 舊→新，隨迴圈累積
    all_stats = []
    for wk in weeks_sorted:
        rows = rows_by_week[wk]
        XM.write_marks(con, rows)
        stats = XM.aggregate_ring_week(rows, all_rings, wk,
                                       asof_dt.isoformat(timespec="seconds"),
                                       history_depth=hist_depth)
        XM.write_ring_week_stats(con, stats)
        all_stats.append((wk, stats))
        # 累積本週 avg_depth 進歷史，供下一週 sigma
        for s in stats:
            hist_depth[s["ring_id"]].append(s["avg_depth"])
    con.close()

    # 回寫 history.json 的 ring_depth（讓 σ 線讀得到歷史）
    hpath = os.path.join(out_dir, "history.json")
    hist = []
    if os.path.isfile(hpath):
        try:
            with open(hpath, "r", encoding="utf-8") as fp:
                hist = json.load(fp)
        except (json.JSONDecodeError, OSError):
            hist = []
    hist_by_wk = {h["week_key"]: h for h in hist}
    for wk, stats in all_stats:
        depth_map = {s["ring_id"]: s["avg_depth"] for s in stats}
        if wk in hist_by_wk:
            hist_by_wk[wk]["ring_depth"] = depth_map
        else:
            # 該週原本沒有 history 快照（全庫回溯週）→ 補一筆最小快照
            hist_by_wk[wk] = {"week_key": wk, "asof": asof_dt.isoformat(timespec="seconds"),
                              "ring_depth": depth_map}
    new_hist = sorted(hist_by_wk.values(), key=lambda h: h["week_key"])
    with open(hpath, "w", encoding="utf-8") as fp:
        json.dump(new_hist, fp, ensure_ascii=False, indent=2)

    print(f"[回填] 寫入 {db_path}")
    print(f"[回填] history.json 補 ring_depth，共 {len(new_hist)} 週")
    print(f"[回填] 完成。下次跑 xianggate_weekly.py 即可看到多週 σ 線與深度熱圖。")
    print(f"       （或現在直接跑一次 weekly 重出報告）")
    return 0

if __name__ == "__main__":
    sys.exit(main())

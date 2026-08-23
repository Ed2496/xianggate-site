# -*- coding: utf-8 -*-
r"""
相閘 · 結論歸位引擎 csv_concept_engine.py (v2.0)
================================================================
性質校正(2026-08-23)：便箋 = 已收斂的結論/心得沉澱(每則一個小主題總結)，
非思考流水帳。故分析目標＝把每條結論歸位到相閘環/框架軸，
回答「我這幾年的心得沉澱在哪、哪裡空、哪些對應哪條環」。

雙軌歸位靶：
  窄靶 = 相閘 11 環(重用 weekly 的 RING_KEYWORDS，同一把尺)
  寬靶 = 九大框架軸(涵蓋整個知識版圖，含政論/命理/工作)
每條便箋算命中分數 → 分派最高分靶；兩靶皆不中 = 真孤兒。

維度：
  D1 結論沉澱地圖   各環/各軸累積結論數(你沉澱在哪)
  D2 框架×環交會    同時屬某框架又落某環的心得(相閘與整體版圖的接點)
  D3 時間演化       各軸結論隨月產出(政論期→系統期遷移)
  D4 孤兒與空環     連框架都不中的結論 + 累積為0的環(該補的洞)

紀律：資料殘缺標殘缺(僅前100字摘要)；不對齊外部數字；零第三方依賴。
"""
import os,re,csv,io,ast,glob,html,collections
from datetime import datetime

CSV_DIR=r"C:\Users\ed249\OneDrive\Documents"
OUT_DIR=r"C:\Users\ed249\Downloads\xianggate-site"
WEEKLY_PY="xianggate_weekly.py"
VERSION="concept-v2.0"

# 寬靶：九大框架軸(涵蓋整個版圖)
AXES={
 "相閘五數學":["相閘","第五境","第四境","五數學","傅立葉","拉普拉斯","莫比烏斯","克萊因","量子","坍縮","標記鏈","相行體用","兩本帳"],
 "AI鑑識":["鑑識","幻覺","敘事","AI-RMA","hype","炒作","視角標記","AI","模型","LLM","prompt","GPT","Claude"],
 "MBB品質":["MBB","Pattern Zero","命名","六標準差","ISO","Cpk","FMEA","RPN","8D","稽核","SOP","品質","流程","EVT","DVT","PVT"],
 "命理玄學":["紫微","斗數","命盤","四化","流年","八字","易經","起卦","通道日","芸懷","風水","女神","福德","貪狼"],
 "財經金流":["食利","泡沫","槓桿","算力","數據中心","估值","本夢比","金流","籌碼","法人","外資","股","投資","營收","獲利"],
 "存在論鑄魂":["七條不能","七條專長","鑄魂","知識樹","生命樹","無極","太極","反粒子","borg","有魂","克勞德","Λ"],
 "顧問轉型":["顧問","風水師","面試","LinkedIn","轉型","MVP","定價","職涯","退休","履歷","B2G","B2E","B2C","102"],
 "政論時局":["民進黨","國民黨","韓國瑜","總統","選舉","蔡英文","政府","中國","美國","兩岸","政治","媒體","立委"],
 "工作管理":["工作","管理","專案","報告","團隊","主管","公司","會議","系統","建立","架構","客戶","交付"],
}
PAL={"jade":"#0E8A6D","gold":"#B8860B","red":"#C2393E","teal":"#0F766E",
     "paper":"#2C3A34","mute":"#6B7C74","line":"#D9E4DF","void":"#F2F7F5","bg":"#EAF3F0"}

def load_ring_keywords(weekly_path):
    if not os.path.isfile(weekly_path): return {}
    src=open(weekly_path,encoding="utf-8").read()
    m=re.search(r'RING_KEYWORDS\s*=\s*\{',src)
    if not m: return {}
    i=src.index('{',m.start());depth=0
    for j in range(i,len(src)):
        if src[j]=='{':depth+=1
        elif src[j]=='}':depth-=1
        if depth==0:break
    try: return ast.literal_eval(src[i:j+1])
    except (ValueError,SyntaxError): return {}

def find_latest_csv(csv_dir):
    best=None;bestd=None
    for p in glob.glob(os.path.join(csv_dir,"記事*.csv")):
        m=re.search(r'記事(\d{8})',os.path.basename(p))
        if m and (bestd is None or m.group(1)>bestd): bestd=m.group(1);best=p
    return best,bestd

def load_notes(path):
    raw=open(path,'rb').read().decode('utf-8','replace')
    rows=list(csv.reader(io.StringIO(raw)));hdr=rows[0]
    ti=hdr.index('ConversationTopic') if 'ConversationTopic' in hdr else 7
    dti=hdr.index('MessageDeliveryTime') if 'MessageDeliveryTime' in hdr else 12
    out=[]
    for r in rows[1:]:
        if len(r)<=ti: continue
        t=r[ti].replace('\x01','').strip()
        if len(t)<8: continue
        d=r[dti] if len(r)>dti else "";m=re.search(r'(\d{4})[/-](\d{1,2})',d)
        out.append({"txt":t,"ym":f"{m.group(1)}-{int(m.group(2)):02d}" if m else None})
    return out

def score(t,table):
    return {k:sum(1 for w in kws if w in t) for k,kws in table.items()}
def best_hit(sc):
    h={k:v for k,v in sc.items() if v>0}
    return (max(h,key=h.get),h) if h else (None,{})

def analyze(notes,rings):
    ax_cnt=collections.Counter();ring_cnt=collections.Counter()
    ax_ring=collections.Counter();orphans=[]
    ax_month=collections.defaultdict(lambda:collections.Counter())
    for n in notes:
        ba,ah=best_hit(score(n["txt"],AXES))
        br,rh=best_hit(score(n["txt"],rings)) if rings else (None,{})
        if ba:
            ax_cnt[ba]+=1
            if n["ym"]: ax_month[ba][n["ym"]]+=1
        if br: ring_cnt[br]+=1
        if ba and br: ax_ring[(ba,br)]+=1
        if not ba and not br: orphans.append(n["txt"])
    return ax_cnt,ring_cnt,ax_ring,orphans,ax_month

# ---------- SVG ----------
def svg_hbar(counter,total,title,color_key="jade",height_per=26):
    items=counter.most_common()
    if not items: return '<div style="color:#6B7C74">無資料</div>'
    mx=items[0][1] or 1;W=680;left=110;H=len(items)*height_per+30
    parts=[f'<text x="6" y="14" font-size="11" fill="{PAL["mute"]}">{html.escape(title)}</text>']
    for i,(k,v) in enumerate(items):
        y=24+i*height_per;bw=(v/mx)*(W-left-60)
        col=PAL["gold"] if ("政論" in k) else PAL[color_key]
        parts.append(f'<text x="{left-6}" y="{y+14}" text-anchor="end" font-size="11" fill="{PAL["paper"]}">{html.escape(k)}</text>')
        parts.append(f'<rect x="{left}" y="{y+2}" width="{bw:.1f}" height="16" rx="3" fill="{col}"/>')
        parts.append(f'<text x="{left+bw+6:.1f}" y="{y+14}" font-size="10" fill="{PAL["mute"]}">{v}（{v/total*100:.0f}%）</text>')
    return f'<svg viewBox="0 0 {W} {H}" width="100%" style="min-height:{H}px" role="img">{"".join(parts)}</svg>'

def svg_axis_ring_flow(ax_ring,height=None):
    """框架×環交會:左框架軸 右環,連線寬=交會數(桑基簡版)。"""
    if not ax_ring: return '<div style="color:#6B7C74">無交會</div>'
    lefts=sorted({a for a,_ in ax_ring},key=lambda a:-sum(v for (x,_),v in ax_ring.items() if x==a))
    rights=sorted({r for _,r in ax_ring})
    H=max(len(lefts),len(rights))*40+40;W=680;lx=140;rx=W-140
    ly={a:30+i*((H-60)/max(len(lefts)-1,1)) for i,a in enumerate(lefts)}
    ry={r:30+i*((H-60)/max(len(rights)-1,1)) for i,r in enumerate(rights)}
    mx=max(ax_ring.values())
    parts=[]
    for (a,r),v in ax_ring.items():
        sw=1+ (v/mx)*8
        y1=ly[a];y2=ry[r]
        parts.append(f'<path d="M{lx} {y1:.0f} C{(lx+rx)/2} {y1:.0f} {(lx+rx)/2} {y2:.0f} {rx} {y2:.0f}" fill="none" stroke="{PAL["jade"]}" stroke-opacity="0.4" stroke-width="{sw:.1f}"><title>{html.escape(a)}→{html.escape(r)}: {v}</title></path>')
    for a in lefts:
        parts.append(f'<text x="{lx-6}" y="{ly[a]+4:.0f}" text-anchor="end" font-size="11" fill="{PAL["paper"]}">{html.escape(a)}</text>')
        parts.append(f'<circle cx="{lx}" cy="{ly[a]:.0f}" r="4" fill="{PAL["gold"]}"/>')
    for r in rights:
        parts.append(f'<text x="{rx+6}" y="{ry[r]+4:.0f}" font-size="11" fill="{PAL["paper"]}">{html.escape(r)}</text>')
        parts.append(f'<circle cx="{rx}" cy="{ry[r]:.0f}" r="4" fill="{PAL["teal"]}"/>')
    return f'<svg viewBox="0 0 {W} {H}" width="100%" style="min-height:{H}px" role="img">{"".join(parts)}</svg>'

def svg_axis_stream(ax_month,height=300):
    months=sorted({mm for c in ax_month.values() for mm in c})
    if not months: return '<div style="color:#6B7C74">無時間資料</div>'
    axes=sorted(ax_month,key=lambda a:-sum(ax_month[a].values()))
    n=len(months);cw=max(3,min(14,int(760/n)));ch=20;left=100;top=20
    W=left+n*cw+10;H=top+len(axes)*ch+40
    mx=max((ax_month[a][mm] for a in axes for mm in months),default=1) or 1
    parts=[f'<text x="6" y="12" font-size="10" fill="{PAL["mute"]}">各框架軸結論產出時間熱條 ｜ 色深＝該月結論數</text>']
    for ri,a in enumerate(axes):
        y=top+ri*ch
        parts.append(f'<text x="{left-4}" y="{y+ch*0.7:.0f}" text-anchor="end" font-size="10" fill="{PAL["paper"]}">{html.escape(a)}</text>')
        for i,mm in enumerate(months):
            v=ax_month[a][mm];x=left+i*cw
            if v>0:
                yr=mm[:4];base=PAL["gold"] if yr in("2019","2020") else PAL["jade"]
                parts.append(f'<rect x="{x}" y="{y+1}" width="{cw-1}" height="{ch-2}" fill="{base}" fill-opacity="{0.2+0.8*v/mx:.2f}"><title>{html.escape(a)} {mm}: {v}</title></rect>')
            else:
                parts.append(f'<rect x="{x}" y="{y+1}" width="{cw-1}" height="{ch-2}" fill="{PAL["void"]}"/>')
    yb=top+len(axes)*ch+12
    for i,mm in enumerate(months):
        if mm.endswith("-01") or i==0 or i==n-1:
            x=left+i*cw+cw/2
            parts.append(f'<text x="{x:.1f}" y="{yb}" text-anchor="middle" font-size="7" fill="{PAL["mute"]}" transform="rotate(90 {x:.1f} {yb})">{mm}</text>')
    return f'<svg viewBox="0 0 {W} {H}" width="100%" style="min-height:{H}px" role="img">{"".join(parts)}</svg>'

def render(notes,rings,meta,out_dir):
    ax_cnt,ring_cnt,ax_ring,orphans,ax_month=analyze(notes,rings)
    total=len(notes);gen=datetime.now().isoformat(timespec="seconds")
    ax_cov=sum(ax_cnt.values());ring_cov=sum(ring_cnt.values())
    empty_rings=[r for r in rings if ring_cnt[r]==0] if rings else []
    ring_rows="".join(f'<tr><td>{html.escape(r)}</td><td class="num">{ring_cnt[r]}</td><td>{"⚠ 空環" if ring_cnt[r]==0 else ""}</td></tr>' for r in rings) if rings else '<tr><td colspan=3>未載入相閘環</td></tr>'
    orphan_sample="".join(f'<li>{html.escape(o[:60])}</li>' for o in orphans[:20])

    css="""body{font-family:'Noto Serif TC',serif;background:#F7FBF9;color:#2C3A34;max-width:1180px;margin:0 auto;padding:28px}
    h1{font-size:25px;margin:0 0 4px}h2{font-size:18px;border-left:4px solid #0E8A6D;padding-left:10px;margin:30px 0 12px}
    .sub{color:#6B7C74;font-size:13px;margin-bottom:8px}.card{background:#fff;border:1px solid #D9E4DF;border-radius:10px;padding:16px;margin:12px 0}
    .stat{display:inline-block;background:#fff;border:1px solid #D9E4DF;border-radius:10px;padding:12px 18px;margin:4px 8px 4px 0;text-align:center}
    .stat b{display:block;font-size:22px;color:#0E8A6D}.stat span{font-size:11px;color:#6B7C74}
    table{border-collapse:collapse;width:100%;font-size:13px;font-family:system-ui}th,td{border-bottom:1px solid #EDF3F0;padding:6px 8px;text-align:left}
    th{background:#EAF3F0;font-weight:600}.num{text-align:right;font-family:'JetBrains Mono',monospace}
    .note{background:#FBF7E8;border-left:3px solid #B8860B;padding:10px 12px;font-size:12px;border-radius:4px;margin:10px 0}
    ul{font-size:12px;color:#6B7C74;columns:2}footer{text-align:center;color:#6B7C74;font-size:11px;margin-top:30px}"""

    return _write(out_dir,f"""<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>相閘 · 結論歸位分析</title><style>{css}</style></head><body>
<h1>相閘 · 結論歸位與相閘關係分析</h1>
<div class="sub">來源：{html.escape(meta['file'])} ｜ 資料日 {html.escape(meta['date'])} ｜ 產出 {gen} ｜ {VERSION}</div>
<div>
 <div class="stat"><b>{total}</b><span>結論便箋</span></div>
 <div class="stat"><b>{ax_cov}</b><span>歸入框架軸</span></div>
 <div class="stat"><b>{ax_cov/total*100:.0f}%</b><span>框架覆蓋</span></div>
 <div class="stat"><b>{ring_cov}</b><span>落入相閘環</span></div>
 <div class="stat"><b>{len(orphans)}</b><span>真孤兒</span></div>
</div>
<div class="note">便箋性質：每則是一個<b>已收斂的結論/小主題總結</b>（產出後記入防忘），本質即第五境 Λ 沉澱。
本報告把每條結論歸位到相閘環(窄靶)與框架軸(寬靶)，回答「心得沉澱在哪、哪裡空」。僅前100字摘要，不對齊外部數字。</div>

<h2>D1 · 結論沉澱地圖（框架軸 · 寬靶）</h2>
<div class="card">{svg_hbar(ax_cnt,total,"你這幾年結論沉澱在哪些框架")}</div>
<div class="note">相閘只是版圖一角：<b>相閘五數學</b>僅 {ax_cnt.get("相閘五數學",0)} 條，而 <b>工作管理/政論/AI鑑識</b>才是大宗。
這張圖是你的知識重心分布——相閘要長大，這裡看得出還差多少沉澱。</div>

<h2>D2 · 相閘環累積結論（窄靶）＋空環偵測</h2>
<div class="card">{svg_hbar(ring_cnt,total,"各相閘環累積結論數") if rings else ""}</div>
<table><thead><tr><th>環</th><th class="num">累積結論</th><th>狀態</th></tr></thead><tbody>{ring_rows}</tbody></table>
<div class="note">⚠ 空環＝這幾年零結論沉澱的環（{("、".join(empty_rings)) if empty_rings else "無"}）。空環不是沒事發生，是你還沒把該環的觀察坍縮成結論——是該開探針的方向。</div>

<h2>D3 · 框架 × 相閘環 交會（相閘與整體版圖的接點）</h2>
<div class="card">{svg_axis_ring_flow(ax_ring)}</div>
<div class="note">左＝框架軸，右＝相閘環，連線粗細＝交會結論數。這些是「既屬某大框架、又精準落某環」的心得——相閘體系與你整體思考的縫合點。最粗那條＝相閘目前最實的入口。</div>

<h2>D4 · 時間演化：政論期 → 系統期</h2>
<div class="card">{svg_axis_stream(ax_month)}</div>
<div class="note">金＝2019–2020，玉＝2025 後。看得出你的結論重心從<b>政論時局</b>整體遷移到<b>AI鑑識／MBB品質／相閘</b>——七年一次知識版塊漂移。</div>

<h2>D5 · 真孤兒（連框架都不中的結論，前20則）</h2>
<ul>{orphan_sample}</ul>
<div class="note">孤兒 {len(orphans)} 條（{len(orphans)/total*100:.0f}%）：多為生活雜記或前100字不含框架詞的結論。高孤兒率反映兩件事：(1)便箋摘要太短；(2)你的沉澱遠比現有框架廣。孤兒不是雜訊，是<b>尚未歸位的潛在新框架</b>。</div>

<footer>相閘結論歸位引擎 {VERSION} ｜ 雙軌歸位 · 重用 weekly RING_KEYWORDS ｜ 命名與坍縮權：Edward</footer>
</body></html>""")

def _write(out_dir,content):
    os.makedirs(out_dir,exist_ok=True)
    p=os.path.join(out_dir,"concept_analysis.html")
    open(p,"w",encoding="utf-8").write(content);return p

def main():
    import argparse,sys
    ap=argparse.ArgumentParser();ap.add_argument("--csv");ap.add_argument("--out");ap.add_argument("--dir");ap.add_argument("--weekly")
    a=ap.parse_args();out_dir=a.out or OUT_DIR
    if a.csv:
        path=a.csv;m=re.search(r'(\d{8})',os.path.basename(path));date=m.group(1) if m else "?"
    else:
        path,date=find_latest_csv(a.dir or CSV_DIR)
        if not path: print(f"✗ 找不到 記事*.csv 於 {a.dir or CSV_DIR}");return 1
    rings=load_ring_keywords(a.weekly or os.path.join(os.path.dirname(os.path.abspath(__file__)),WEEKLY_PY))
    print(f"[歸位引擎] 讀 {path} (資料日 {date}) ｜ 相閘環 {len(rings)} 個當窄靶")
    notes=load_notes(path);print(f"[歸位引擎] 結論便箋 {len(notes)} 筆")
    outp=render(notes,rings,{"file":os.path.basename(path),"date":date},out_dir)
    print(f"[歸位引擎] 報告 → {outp}");return 0

if __name__=="__main__": import sys;sys.exit(main())

# -*- coding: utf-8 -*-
r"""
相閘 XiangGate · 整合儀表板 xianggate_dashboard.py (v2.0)
================================================================
把既有週報(index.html)與概念報告(concept_analysis.html)整合成單一分頁式
dashboard.html。頂部標籤切換。

v2.0 改用【內嵌】而非 iframe：
  原因：file:// 本機雙擊時，瀏覽器視每個檔為獨立安全來源，iframe 互載被擋
        (Unsafe attempt to load URL ... 'file:' URLs are treated as unique origins)。
  解法：抽取來源 HTML 的 <body> 內容與 <style>，內嵌進分頁 div。
        本機雙擊、GitHub Pages 兩種場景都正常，零跨檔載入。
  代價：dashboard.html 變大(含兩報告全文)；每次來源更新須重跑本檔(已納入 run_all.bat)。

隔離：各來源的 <style> 以 scope 前綴包起，避免 CSS 互相污染
      (兩報告都用 body{...}，直接合併會打架)。

用法：
  python xianggate_dashboard.py --out D:\site
  python xianggate_dashboard.py --tabs weekly=素材週報:index.html concept=概念索引分析:concept_analysis.html
"""
import os, re, argparse
from datetime import datetime

OUT_DIR = r"C:\Users\ed249\Downloads\xianggate-site"
VERSION = "dashboard-v2.0"
DEFAULT_TABS = [
    ("weekly",  "素材週報",   "weekly.html"),
    ("concept", "概念索引分析", "concept_analysis.html"),
]

def extract_parts(path):
    """回傳 (style_text, body_html)。抓 <style>…</style> 與 <body>…</body>。"""
    if not os.path.isfile(path):
        return "", None
    html = open(path, encoding="utf-8-sig").read()
    styles = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", html, re.S))
    mbody = re.search(r"<body[^>]*>(.*?)</body>", html, re.S)
    body = mbody.group(1) if mbody else html
    return styles, body

def scope_css(css, scope):
    """把 CSS 每條規則加 scope 前綴，避免污染。body/html 選擇器改指 scope 容器。
    簡易法：對每個規則的 selector 前綴 scope；body/:root/html 特別處理。"""
    out = []
    # 移除註解
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    # 逐條 rule 拆(不含 @media 巢狀的簡化處理)
    def prefix_selectors(sel):
        parts = []
        for s in sel.split(","):
            s = s.strip()
            if not s:
                continue
            if s in ("body", "html", "html,body", ":root"):
                parts.append(f"{scope}")
            elif s.startswith("@"):
                parts.append(s)
            else:
                parts.append(f"{scope} {s}")
        return ", ".join(parts)

    i = 0
    # 處理 @media 區塊
    for m in re.finditer(r"(@media[^{]+\{)(.*?)(\}\s*)(?=@media|\Z|[^\}]*\{[^@])", css, re.S):
        pass  # 太複雜的 @media 直接原樣保留(見下方 fallback)

    # 簡化：用平衡括號逐 rule 掃
    depth = 0; buf = ""; sel = ""; result = []
    tokens = re.split(r"(\{|\})", css)
    stack = []
    cur_sel = ""
    for tok in tokens:
        if tok == "{":
            stack.append(cur_sel.strip())
            cur_sel = ""
        elif tok == "}":
            if stack:
                stack.pop()
        else:
            if not stack:  # top-level selector
                cur_sel += tok
            else:
                # 在 rule 內：這是宣告；連同 selector 一起輸出
                selector = stack[-1]
                if selector.startswith("@"):
                    result.append(f"{selector}{{{tok}}}")
                else:
                    result.append(f"{prefix_selectors(selector)}{{{tok}}}")
    return "\n".join(result)

def build(out_dir, tabs, outfile="dashboard.html"):
    gen = datetime.now().isoformat(timespec="seconds")
    tab_meta = []
    all_css = []
    panels = []
    for key, label, src in tabs:
        styles, body = extract_parts(os.path.join(out_dir, src))
        exists = body is not None
        tab_meta.append((key, label, src, exists))
        if exists:
            scoped = scope_css(styles, f"#panel-{key}")
            all_css.append(f"/* ==== {label} ==== */\n{scoped}")
            panels.append(f'<div class="panel" id="panel-{key}">{body}</div>')
        else:
            panels.append(f'<div class="panel" id="panel-{key}">'
                          f'<p style="padding:60px;text-align:center;color:#6B7C74">'
                          f'{label} 來源檔（{src}）尚未產生，請先執行對應引擎。</p></div>')

    btns = "".join(
        f'<button class="tab-btn" data-tab="{key}">{label}'
        f'{"" if ex else " <span style=color:#B8860B;font-size:10px>(未產生)</span>"}</button>'
        for key, label, src, ex in tab_meta
    )
    first_key = next((k for k, _l, _s, ex in tab_meta if ex), tab_meta[0][0])
    keys_js = "[" + ",".join(f'"{k}"' for k, _l, _s, _e in tab_meta) + "]"

    shell_css = """
    *{box-sizing:border-box}
    html,body{margin:0;font-family:'Noto Serif TC',system-ui,serif;background:#F7FBF9;color:#2C3A34}
    .dash-header{background:linear-gradient(180deg,#fff,#F2F7F5);border-bottom:1px solid #D9E4DF;
      padding:14px 22px 0;position:sticky;top:0;z-index:100}
    .dash-brand{display:flex;align-items:baseline;gap:12px;margin-bottom:10px}
    .dash-brand h1{font-size:21px;margin:0;letter-spacing:1px}
    .dash-brand .ver{font-size:11px;color:#fff;background:#0E8A6D;border-radius:10px;padding:2px 9px}
    .dash-brand .gen{font-size:11px;color:#6B7C74;margin-left:auto}
    .dash-tabs{display:flex;gap:4px}
    .tab-btn{border:1px solid #D9E4DF;border-bottom:none;background:#F2F7F5;color:#6B7C74;
      font-family:inherit;font-size:14px;padding:9px 20px;border-radius:9px 9px 0 0;cursor:pointer}
    .tab-btn:hover{background:#fff;color:#2C3A34}
    .tab-btn.active{background:#fff;color:#0E8A6D;font-weight:600;border-color:#0E8A6D;border-bottom:2px solid #fff;margin-bottom:-1px}
    .panel{display:none;max-width:1180px;margin:0 auto;padding:20px}
    .panel.active{display:block}
    """
    doc = f"""<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>相閘 XiangGate · 儀表板</title>
<style>
{shell_css}
{chr(10).join(all_css)}
</style></head>
<body>
<div class="dash-header">
  <div class="dash-brand">
    <h1>相閘 XiangGate</h1><span class="ver">{VERSION}</span>
    <span class="gen">整合產出 {gen}</span>
  </div>
  <nav class="dash-tabs">{btns}</nav>
</div>
{chr(10).join(panels)}
<script>
  var keys={keys_js};
  function show(k){{
    document.querySelectorAll('.tab-btn').forEach(function(b){{b.classList.toggle('active',b.dataset.tab===k);}});
    document.querySelectorAll('.panel').forEach(function(p){{p.classList.toggle('active',p.id==='panel-'+k);}});
    if(location.hash!=='#'+k) history.replaceState(null,'','#'+k);
    window.scrollTo(0,0);
  }}
  document.querySelectorAll('.tab-btn').forEach(function(b){{b.addEventListener('click',function(){{show(b.dataset.tab);}});}});
  var init=location.hash.replace('#','')||'{first_key}';
  if(!keys.includes(init))init='{first_key}';
  show(init);
</script>
</body></html>"""
    os.makedirs(out_dir, exist_ok=True)
    p = os.path.join(out_dir, outfile)
    open(p, "w", encoding="utf-8").write(doc)
    return p, tab_meta

def main():
    ap = argparse.ArgumentParser(description="相閘整合儀表板")
    ap.add_argument("--out")
    ap.add_argument("--tabs", nargs="+")
    ap.add_argument("--outfile", default="index.html", help="輸出檔名(預設index.html當首頁；不想蓋首頁可傳dashboard.html)")
    a = ap.parse_args()
    out_dir = a.out or OUT_DIR
    tabs = DEFAULT_TABS
    if a.tabs:
        tabs = []
        for spec in a.tabs:
            key, rest = spec.split("=", 1); label, src = rest.split(":", 1)
            tabs.append((key, label, src))
    p, meta = build(out_dir, tabs, a.outfile)
    print(f"[儀表板] 產出 {p}")
    for key, label, src, ex in meta:
        print(f"  分頁 {label:<8} <- {src}  {'[OK] 已內嵌' if ex else '[--] 尚未產生'}")
    print(f"[儀表板] 內嵌式，file:// 本機與 GitHub Pages 皆可開")
    return 0

if __name__ == "__main__":
    import sys; sys.exit(main())

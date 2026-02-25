"""
IMANNOOR Canlı Ciro Dashboard
Selenium YOK — requests + BeautifulSoup kullanır
Railway.app ücretsiz planında çalışır
"""

import os
import time
import threading
import requests
from datetime import datetime
from flask import Flask, jsonify, render_template_string
from bs4 import BeautifulSoup

app = Flask(__name__)

# ══════════════════════════════════════════════════════
#  AYARLAR — Railway Variables'a gir
# ══════════════════════════════════════════════════════
KULLANICI_ADI  = os.environ.get("IMANNOOR_USER", "")
SIFRE          = os.environ.get("IMANNOOR_PASS", "")
HEDEF_ETICARET = int(os.environ.get("HEDEF_ETICARET", "3250000"))
HEDEF_MAGAZA   = int(os.environ.get("HEDEF_MAGAZA",   "750000"))
HEDEF_TOPTAN   = int(os.environ.get("HEDEF_TOPTAN",   "500000"))
HEDEF_TOPLAM   = HEDEF_ETICARET + HEDEF_MAGAZA + HEDEF_TOPTAN
# ══════════════════════════════════════════════════════

son_veri = {
    "bugun_ciro"    : 0,
    "dun_ciro"      : 0,
    "toplam_adet"   : 0,
    "eticaret_ciro" : 0,
    "magaza_ciro"   : 0,
    "toptan_ciro"   : 0,
    "guncelleme"    : "Henüz güncellenmedi",
    "hata"          : None,
}


def parse_sayi(metin):
    """'1.234,56' → 1234.56"""
    if not metin:
        return 0.0
    temiz = metin.strip().replace('\xa0', '').replace(' ', '')
    temiz = temiz.replace('.', '').replace(',', '.')
    try:
        return float(temiz)
    except:
        return 0.0


def veri_cek():
    """requests ile oturum aç, OrderReport sayfasından veri çek."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
    })

    # 1. Login sayfasını al (CSRF token için)
    login_url = "https://rapor.imannoor.com/Account/Login/"
    r = session.get(login_url, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")

    # CSRF token bul
    token_input = soup.find("input", {"name": "__RequestVerificationToken"})
    token = token_input["value"] if token_input else ""

    # 2. Giriş yap
    payload = {
        "UserName"                  : KULLANICI_ADI,
        "Password"                  : SIFRE,
        "__RequestVerificationToken": token,
    }
    r2 = session.post(login_url, data=payload, timeout=15, allow_redirects=True)

    if "Login" in r2.url or "login" in r2.url:
        raise Exception("Giriş başarısız — kullanıcı adı veya şifre hatalı")

    # 3. OrderReport sayfasını çek
    r3 = session.get("https://rapor.imannoor.com/Report/OrderReport", timeout=15)
    soup2 = BeautifulSoup(r3.text, "html.parser")

    # Sayfadaki tüm metni satır satır al
    page_text = soup2.get_text(separator="\n")

    def parse_satir(etiket):
        lines = page_text.split("\n")
        for i, line in enumerate(lines):
            if etiket.lower() in line.lower().strip():
                # Sonraki boş olmayan satırı al
                for j in range(i+1, min(i+4, len(lines))):
                    val = lines[j].strip()
                    if val:
                        return parse_sayi(val)
        return 0.0

    return {
        "bugun_ciro"    : parse_satir("Bugün Ciro"),
        "dun_ciro"      : parse_satir("Dün Ciro"),
        "toplam_adet"   : int(parse_satir("Adet")),
        "eticaret_ciro" : parse_satir("Eticaret Ciro"),
        "magaza_ciro"   : parse_satir("Mağaza Ciro"),
        "toptan_ciro"   : parse_satir("Toptan Ciro"),
    }


def guncelle_dongu():
    global son_veri
    while True:
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Veri çekiliyor...")
            veri = veri_cek()
            AYLAR = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
                     "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]
            d = datetime.now()
            son_veri = {
                **veri,
                "guncelleme": f"{d.day} {AYLAR[d.month-1]} {d.year}  {d.strftime('%H:%M')}",
                "hata": None,
            }
            print(f"  ✅ Bugün: {veri['bugun_ciro']:,.0f} TL | Adet: {veri['toplam_adet']}")
        except Exception as e:
            son_veri["hata"] = str(e)
            print(f"  ❌ Hata: {e}")

        time.sleep(300)  # 5 dakika


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Imannoor — Canlı Ciro Raporu</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Mono:wght@500;600&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'DM Sans',sans-serif;background:#0f0f17;color:#fff;min-height:100vh}
.container{max-width:860px;margin:0 auto;padding:32px 20px}
.header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:28px;flex-wrap:wrap;gap:12px}
.header h1{font-size:26px;font-weight:700;letter-spacing:-0.5px}
.header p{font-size:13px;color:#444466;margin-top:4px}
.live-badge{display:flex;align-items:center;gap:8px;background:#1a1a2e;border:1px solid #2a2a4a;border-radius:99px;padding:8px 16px;font-size:12px;color:#666}
.live-dot{width:8px;height:8px;background:#22c55e;border-radius:50%;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}
.kart{background:#1a1a2e;border:1px solid #2a2a4a;border-radius:18px;padding:22px}
.kart.altin{background:linear-gradient(135deg,#221800,#150f00);border-color:#c9a84c33}
.kart-label{font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#444466;margin-bottom:10px}
.kart-value{font-family:'DM Mono',monospace;font-size:28px;font-weight:600;letter-spacing:-0.5px;line-height:1}
.kart-value .unit{font-size:13px;color:#444466;margin-left:3px}
.kart.altin .kart-value{color:#c9a84c}
.kart-sub{font-size:12px;color:#333355;margin-top:8px;font-family:'DM Mono',monospace}
.oran-val{font-family:'DM Mono',monospace;font-size:40px;font-weight:700;letter-spacing:-1px}
.bar-track{width:100%;height:5px;background:#1f1f35;border-radius:99px;margin-top:12px;overflow:hidden}
.bar-fill{height:100%;border-radius:99px;transition:width 1s ease}
.dun-kart{background:#131320;border:1px solid #1f1f35;border-radius:18px;padding:18px 22px;display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:10px}
.dun-label{font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#333355;margin-bottom:5px}
.dun-value{font-family:'DM Mono',monospace;font-size:22px;font-weight:600;color:#555}
.fark{font-family:'DM Mono',monospace;font-size:14px;font-weight:700;padding:7px 14px;border-radius:99px}
.fark.pos{background:#0a1f12;color:#22c55e}
.fark.neg{background:#1f0a0a;color:#ef4444}
.bolum{font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#333355;margin-bottom:12px}
.kat-grid{display:grid;gap:12px;margin-bottom:24px}
.kat{background:#131320;border:1px solid #1f1f35;border-radius:14px;padding:18px 22px}
.kat-ust{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px}
.kat-isim{font-size:12px;font-weight:700;color:#555;letter-spacing:1px;text-transform:uppercase}
.kat-oran{font-family:'DM Mono',monospace;font-size:13px;font-weight:700}
.kat-ciro{font-family:'DM Mono',monospace;font-size:26px;font-weight:600;letter-spacing:-0.5px;margin-bottom:3px}
.kat-hedef{font-size:11px;color:#2a2a44;margin-bottom:10px;font-family:'DM Mono',monospace}
.footer{text-align:center;padding:20px 0 0;font-size:11px;color:#222233;border-top:1px solid #1a1a2e}
.footer span{color:#c9a84c;font-weight:700;letter-spacing:1px}
.hata-banner{background:#2a0a0a;border:1px solid #ef444433;border-radius:12px;padding:12px 18px;margin-bottom:16px;font-size:12px;color:#ef4444;display:none}
@media(max-width:580px){.grid2{grid-template-columns:1fr}.kart-value{font-size:22px}.oran-val{font-size:30px}}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <div>
      <h1>Canlı Ciro Raporu</h1>
      <p id="tarih"></p>
    </div>
    <div class="live-badge">
      <div class="live-dot"></div>
      <span id="guncelleme">Bağlanıyor...</span>
    </div>
  </div>

  <div id="hata-banner" class="hata-banner"></div>

  <div class="grid2">
    <div class="kart altin">
      <div class="kart-label">Bugün Ciro</div>
      <div class="kart-value" id="bugun-ciro">—<span class="unit">TL</span></div>
      <div class="kart-sub" id="adet">— adet</div>
    </div>
    <div class="kart">
      <div class="kart-label">Gerçekleştirme</div>
      <div class="oran-val" id="oran">—</div>
      <div class="kart-sub" id="hedef-label">Hedef: — TL</div>
      <div class="bar-track"><div class="bar-fill" id="oran-bar" style="width:0%"></div></div>
    </div>
  </div>

  <div class="dun-kart">
    <div>
      <div class="dun-label">Dün Ciro</div>
      <div class="dun-value" id="dun-ciro">—</div>
    </div>
    <div class="fark" id="fark">— TL</div>
  </div>

  <div class="bolum">Kategori Bazında</div>
  <div class="kat-grid" id="kategoriler"></div>

  <div class="footer"><span>IMANNOOR</span> &nbsp;·&nbsp; 5 dakikada bir güncellenir</div>
</div>

<script>
const H={et:{{ hedef_eticaret }},mg:{{ hedef_magaza }},tp:{{ hedef_toptan }},top:{{ hedef_toplam }}};
const AYLAR=['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'];
const GUNLER=['Pazar','Pazartesi','Salı','Çarşamba','Perşembe','Cuma','Cumartesi'];
function fmt(n){return Math.round(n).toLocaleString('tr-TR')}
function renk(o){return o>=100?'#22c55e':o>=75?'#facc15':'#ef4444'}

function guncelle(){
  fetch('/api/veri').then(r=>r.json()).then(d=>{
    const now=new Date();
    document.getElementById('tarih').textContent=
      GUNLER[now.getDay()]+' '+now.getDate()+' '+AYLAR[now.getMonth()]+' '+now.getFullYear();
    document.getElementById('guncelleme').textContent='Son: '+d.guncelleme;

    // Hata
    const hb=document.getElementById('hata-banner');
    if(d.hata){hb.style.display='block';hb.textContent='⚠️ '+d.hata;}
    else hb.style.display='none';

    // Bugün
    document.getElementById('bugun-ciro').innerHTML=fmt(d.bugun_ciro)+' <span class="unit">TL</span>';
    document.getElementById('adet').textContent=fmt(d.toplam_adet)+' adet sipariş';

    // Oran
    const o=H.top>0?Math.round(d.bugun_ciro/H.top*100):0;
    const r=renk(o);
    document.getElementById('oran').textContent='%'+o;
    document.getElementById('oran').style.color=r;
    document.getElementById('hedef-label').textContent='Hedef: '+fmt(H.top)+' TL';
    const bar=document.getElementById('oran-bar');
    bar.style.width=Math.min(o,100)+'%';bar.style.background=r;

    // Dün
    document.getElementById('dun-ciro').textContent=fmt(d.dun_ciro)+' TL';
    const fark=d.bugun_ciro-d.dun_ciro;
    const fel=document.getElementById('fark');
    fel.textContent=(fark>=0?'▲ ':'▼ ')+fmt(Math.abs(fark))+' TL';
    fel.className='fark '+(fark>=0?'pos':'neg');

    // Kategoriler
    const katlar=[
      {isim:'E-Ticaret',ciro:d.eticaret_ciro,hedef:H.et,renk:'#4f72f5'},
      {isim:'Mağaza',   ciro:d.magaza_ciro,  hedef:H.mg,renk:'#2ea84d'},
      {isim:'Toptan',   ciro:d.toptan_ciro,  hedef:H.tp,renk:'#e07c18'},
    ];
    document.getElementById('kategoriler').innerHTML=katlar.map(k=>{
      const o2=k.hedef>0?Math.round(k.ciro/k.hedef*100):0;
      const r2=renk(o2);
      return `<div class="kat">
        <div class="kat-ust"><span class="kat-isim">${k.isim}</span>
        <span class="kat-oran" style="color:${r2}">%${o2}</span></div>
        <div class="kat-ciro" style="color:${k.renk}">${fmt(k.ciro)} TL</div>
        <div class="kat-hedef">Hedef: ${fmt(k.hedef)} TL</div>
        <div class="bar-track"><div class="bar-fill" style="width:${Math.min(o2,100)}%;background:${k.renk}"></div></div>
      </div>`;
    }).join('');
  }).catch(()=>{
    document.getElementById('guncelleme').textContent='Bağlantı hatası';
  });
}

guncelle();
setInterval(guncelle,60000);
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(
        DASHBOARD_HTML,
        hedef_eticaret=HEDEF_ETICARET,
        hedef_magaza=HEDEF_MAGAZA,
        hedef_toptan=HEDEF_TOPTAN,
        hedef_toplam=HEDEF_TOPLAM,
    )

@app.route("/api/veri")
def api_veri():
    return jsonify(son_veri)

@app.route("/api/saglik")
def saglik():
    return jsonify({"durum": "ok", "guncelleme": son_veri["guncelleme"]})

if __name__ == "__main__":
    t = threading.Thread(target=guncelle_dongu, daemon=True)
    t.start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

"""
IMANNOOR Canlı Ciro Dashboard
- requests + BeautifulSoup (Selenium yok, hafif)
- Admin paneli ile günlük hedef değiştirme
- Railway.app ücretsiz planında çalışır
"""

import os
import time
import json
import threading
import requests
from datetime import datetime
from flask import Flask, jsonify, render_template_string, request
from bs4 import BeautifulSoup

app = Flask(__name__)

# ══════════════════════════════════════════════════════
KULLANICI_ADI  = os.environ.get("IMANNOOR_USER", "")
SIFRE          = os.environ.get("IMANNOOR_PASS", "")
ADMIN_SIFRE    = os.environ.get("ADMIN_SIFRE", "imn26*")
# ══════════════════════════════════════════════════════

# Hedefler — admin panelinden değiştirilebilir
hedefler = {
    "eticaret" : int(os.environ.get("HEDEF_ETICARET", "3250000")),
    "magaza"   : int(os.environ.get("HEDEF_MAGAZA",   "750000")),
    "toptan"   : int(os.environ.get("HEDEF_TOPTAN",   "500000")),
}

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
    if not metin:
        return 0.0
    temiz = str(metin).strip().replace('\xa0','').replace(' ','')
    temiz = temiz.replace('.','').replace(',','.')
    try:
        return float(temiz)
    except:
        return 0.0


def veri_cek():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
    })

    login_url = "https://rapor.imannoor.com/Account/Login/"
    r = session.get(login_url, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")

    token_input = soup.find("input", {"name": "__RequestVerificationToken"})
    token = token_input["value"] if token_input else ""

    payload = {
        "UserName"                  : KULLANICI_ADI,
        "Password"                  : SIFRE,
        "__RequestVerificationToken": token,
    }
    r2 = session.post(login_url, data=payload, timeout=15, allow_redirects=True)

    if "Login" in r2.url or "login" in r2.url:
        raise Exception("Giriş başarısız — kullanıcı adı veya şifre hatalı")

    r3 = session.get("https://rapor.imannoor.com/Report/OrderReport", timeout=15)
    soup2 = BeautifulSoup(r3.text, "html.parser")
    page_text = soup2.get_text(separator="\n")

    def parse_satir(etiket):
        lines = page_text.split("\n")
        for i, line in enumerate(lines):
            if etiket.lower() in line.lower().strip():
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
        time.sleep(300)


# ═══════════════════════════════════════════════════════════════
HTML = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Imannoor — Canlı Ciro</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Mono:wght@500;600&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'DM Sans',sans-serif;background:#0f0f17;color:#fff;min-height:100vh}
.wrap{max-width:860px;margin:0 auto;padding:28px 18px}

/* HEADER */
.hdr{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:24px;flex-wrap:wrap;gap:10px}
.hdr h1{font-size:24px;font-weight:700;letter-spacing:-0.5px}
.hdr p{font-size:12px;color:#333355;margin-top:3px}
.hdr-right{display:flex;align-items:center;gap:10px}
.live{display:flex;align-items:center;gap:7px;background:#1a1a2e;border:1px solid #2a2a4a;border-radius:99px;padding:7px 14px;font-size:12px;color:#555}
.dot{width:7px;height:7px;background:#22c55e;border-radius:50%;animation:p 2s infinite}
@keyframes p{0%,100%{opacity:1}50%{opacity:.3}}
.ayar-btn{background:#1a1a2e;border:1px solid #2a2a4a;border-radius:99px;padding:7px 14px;font-size:13px;color:#888;cursor:pointer;transition:.2s}
.ayar-btn:hover{border-color:#c9a84c;color:#c9a84c}

/* KARTLAR */
.g2{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px}
.k{background:#1a1a2e;border:1px solid #2a2a4a;border-radius:16px;padding:20px}
.k.gold{background:linear-gradient(135deg,#1e1500,#110d00);border-color:#c9a84c2a}
.klbl{font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#333355;margin-bottom:9px}
.kval{font-family:'DM Mono',monospace;font-size:26px;font-weight:600;letter-spacing:-.5px;line-height:1}
.kval .u{font-size:12px;color:#333355;margin-left:3px}
.k.gold .kval{color:#c9a84c}
.ksub{font-size:11px;color:#2a2a44;margin-top:7px;font-family:'DM Mono',monospace}
.oran{font-family:'DM Mono',monospace;font-size:38px;font-weight:700;letter-spacing:-1px}
.bar{width:100%;height:5px;background:#1a1a30;border-radius:99px;margin-top:10px;overflow:hidden}
.barf{height:100%;border-radius:99px;transition:width 1s ease}

/* DÜN */
.dun{background:#111120;border:1px solid #1a1a2e;border-radius:16px;padding:16px 20px;display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;flex-wrap:wrap;gap:8px}
.dlbl{font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#2a2a44;margin-bottom:4px}
.dval{font-family:'DM Mono',monospace;font-size:20px;font-weight:600;color:#444}
.fark{font-family:'DM Mono',monospace;font-size:13px;font-weight:700;padding:6px 12px;border-radius:99px}
.fp{background:#081410;color:#22c55e}
.fn{background:#140808;color:#ef4444}

/* KATEGORİ */
.sec{font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#2a2a3a;margin-bottom:10px}
.kg{display:grid;gap:10px;margin-bottom:22px}
.kk{background:#111120;border:1px solid #1a1a2e;border-radius:14px;padding:16px 20px}
.kku{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:3px}
.kkisim{font-size:11px;font-weight:700;color:#444;letter-spacing:1px;text-transform:uppercase}
.kkoran{font-family:'DM Mono',monospace;font-size:12px;font-weight:700}
.kkciro{font-family:'DM Mono',monospace;font-size:24px;font-weight:600;letter-spacing:-.5px;margin-bottom:2px}
.kkhedef{font-size:11px;color:#222233;margin-bottom:9px;font-family:'DM Mono',monospace}

/* FOOTER */
.foot{text-align:center;padding:18px 0 0;font-size:11px;color:#1e1e2e;border-top:1px solid #1a1a2e}
.foot span{color:#c9a84c;font-weight:700;letter-spacing:1px}

/* MODAL */
.overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:100;justify-content:center;align-items:center}
.overlay.open{display:flex}
.modal{background:#1a1a2e;border:1px solid #2a2a4a;border-radius:20px;padding:28px;width:340px;max-width:95vw}
.modal h2{font-size:18px;font-weight:700;margin-bottom:6px}
.modal p{font-size:12px;color:#444466;margin-bottom:20px}
.modal input{width:100%;background:#111120;border:1px solid #2a2a4a;border-radius:10px;padding:10px 14px;color:#fff;font-size:14px;font-family:'DM Mono',monospace;margin-bottom:10px;outline:none}
.modal input:focus{border-color:#c9a84c}
.modal label{font-size:11px;color:#444466;font-weight:700;letter-spacing:1px;text-transform:uppercase;display:block;margin-bottom:4px;margin-top:8px}
.btn-row{display:flex;gap:10px;margin-top:18px}
.btn{flex:1;padding:10px;border-radius:10px;font-size:14px;font-weight:700;cursor:pointer;border:none}
.btn-cancel{background:#111120;color:#555}
.btn-save{background:#c9a84c;color:#000}
.err{color:#ef4444;font-size:12px;margin-top:6px;display:none}

@media(max-width:560px){.g2{grid-template-columns:1fr}.kval{font-size:20px}.oran{font-size:28px}}
</style>
</head>
<body>
<div class="wrap">
  <div class="hdr">
    <div>
      <h1>Canlı Ciro Raporu</h1>
      <p id="tarih"></p>
    </div>
    <div class="hdr-right">
      <div class="live"><div class="dot"></div><span id="son-gun">Bağlanıyor...</span></div>
      <button class="ayar-btn" onclick="modalAc()">⚙️ Hedefler</button>
    </div>
  </div>

  <div class="g2">
    <div class="k gold">
      <div class="klbl">Bugün Ciro</div>
      <div class="kval" id="bugun">—<span class="u">TL</span></div>
      <div class="ksub" id="adet">—</div>
    </div>
    <div class="k">
      <div class="klbl">Gerçekleştirme</div>
      <div class="oran" id="oran">—</div>
      <div class="ksub" id="hlbl">Hedef: —</div>
      <div class="bar"><div class="barf" id="obar" style="width:0%"></div></div>
    </div>
  </div>

  <div class="dun">
    <div><div class="dlbl">Dün Ciro</div><div class="dval" id="dun">—</div></div>
    <div class="fark" id="fark">—</div>
  </div>

  <div class="sec">Kategori Bazında</div>
  <div class="kg" id="katlar"></div>

  <div class="foot"><span>IMANNOOR</span> &nbsp;·&nbsp; 5 dakikada bir güncellenir</div>
</div>

<!-- MODAL -->
<div class="overlay" id="overlay">
  <div class="modal">
    <h2>⚙️ Günlük Hedefler</h2>
    <p>Hedefleri güncellemek için admin şifresini gir.</p>
    <div id="sifre-alan">
      <label>Admin Şifresi</label>
      <input type="password" id="sifre-inp" placeholder="••••••">
      <div class="err" id="sifre-err">Şifre hatalı!</div>
      <div class="btn-row">
        <button class="btn btn-cancel" onclick="modalKapat()">İptal</button>
        <button class="btn btn-save" onclick="sifreKontrol()">Devam →</button>
      </div>
    </div>
    <div id="hedef-alan" style="display:none">
      <label>E-Ticaret Hedef (TL)</label>
      <input type="number" id="h-et" placeholder="3250000">
      <label>Mağaza Hedef (TL)</label>
      <input type="number" id="h-mg" placeholder="750000">
      <label>Toptan Hedef (TL)</label>
      <input type="number" id="h-tp" placeholder="500000">
      <div class="btn-row">
        <button class="btn btn-cancel" onclick="modalKapat()">İptal</button>
        <button class="btn btn-save" onclick="hedefKaydet()">💾 Kaydet</button>
      </div>
    </div>
  </div>
</div>

<script>
let H={et:0,mg:0,tp:0,top:0};
const AYLAR=['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'];
const GUNLER=['Pazar','Pazartesi','Salı','Çarşamba','Perşembe','Cuma','Cumartesi'];
function fmt(n){return Math.round(n).toLocaleString('tr-TR')}
function renk(o){return o>=100?'#22c55e':o>=75?'#facc15':'#ef4444'}

function guncelle(){
  fetch('/api/veri').then(r=>r.json()).then(d=>{
    H=d.hedefler;
    const now=new Date();
    document.getElementById('tarih').textContent=
      GUNLER[now.getDay()]+' '+now.getDate()+' '+AYLAR[now.getMonth()]+' '+now.getFullYear();
    document.getElementById('son-gun').textContent='Son: '+d.guncelleme;

    document.getElementById('bugun').innerHTML=fmt(d.bugun_ciro)+' <span class="u">TL</span>';
    document.getElementById('adet').textContent=fmt(d.toplam_adet)+' adet sipariş';

    const o=H.top>0?Math.round(d.bugun_ciro/H.top*100):0;
    const r=renk(o);
    document.getElementById('oran').textContent='%'+o;
    document.getElementById('oran').style.color=r;
    document.getElementById('hlbl').textContent='Hedef: '+fmt(H.top)+' TL';
    const ob=document.getElementById('obar');
    ob.style.width=Math.min(o,100)+'%';ob.style.background=r;

    document.getElementById('dun').textContent=fmt(d.dun_ciro)+' TL';
    const f=d.bugun_ciro-d.dun_ciro;
    const fe=document.getElementById('fark');
    fe.textContent=(f>=0?'▲ ':'▼ ')+fmt(Math.abs(f))+' TL';
    fe.className='fark '+(f>=0?'fp':'fn');

    const katlar=[
      {n:'E-Ticaret',c:d.eticaret_ciro,h:H.et,r:'#4f72f5'},
      {n:'Mağaza',   c:d.magaza_ciro,  h:H.mg,r:'#2ea84d'},
      {n:'Toptan',   c:d.toptan_ciro,  h:H.tp,r:'#e07c18'},
    ];
    document.getElementById('katlar').innerHTML=katlar.map(k=>{
      const o2=k.h>0?Math.round(k.c/k.h*100):0;
      const r2=renk(o2);
      return `<div class="kk">
        <div class="kku"><span class="kkisim">${k.n}</span><span class="kkoran" style="color:${r2}">%${o2}</span></div>
        <div class="kkciro" style="color:${k.r}">${fmt(k.c)} TL</div>
        <div class="kkhedef">Hedef: ${fmt(k.h)} TL</div>
        <div class="bar"><div class="barf" style="width:${Math.min(o2,100)}%;background:${k.r}"></div></div>
      </div>`;
    }).join('');
  }).catch(()=>{document.getElementById('son-gun').textContent='Bağlantı hatası'});
}

// MODAL
function modalAc(){
  document.getElementById('overlay').classList.add('open');
  document.getElementById('sifre-alan').style.display='block';
  document.getElementById('hedef-alan').style.display='none';
  document.getElementById('sifre-inp').value='';
  document.getElementById('sifre-err').style.display='none';
}
function modalKapat(){document.getElementById('overlay').classList.remove('open')}

function sifreKontrol(){
  const s=document.getElementById('sifre-inp').value;
  fetch('/api/sifre-kontrol',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sifre:s})})
  .then(r=>r.json()).then(d=>{
    if(d.ok){
      document.getElementById('sifre-alan').style.display='none';
      document.getElementById('hedef-alan').style.display='block';
      document.getElementById('h-et').value=H.et;
      document.getElementById('h-mg').value=H.mg;
      document.getElementById('h-tp').value=H.tp;
    } else {
      document.getElementById('sifre-err').style.display='block';
    }
  });
}

function hedefKaydet(){
  const et=parseInt(document.getElementById('h-et').value)||0;
  const mg=parseInt(document.getElementById('h-mg').value)||0;
  const tp=parseInt(document.getElementById('h-tp').value)||0;
  fetch('/api/hedef-guncelle',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({sifre:document.getElementById('sifre-inp').value,et,mg,tp})})
  .then(r=>r.json()).then(d=>{
    if(d.ok){modalKapat();guncelle();}
  });
}

guncelle();
setInterval(guncelle,60000);
</script>
</body>
</html>"""
# ═══════════════════════════════════════════════════════════════


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/veri")
def api_veri():
    return jsonify({
        **son_veri,
        "hedefler": {
            "et" : hedefler["eticaret"],
            "mg" : hedefler["magaza"],
            "tp" : hedefler["toptan"],
            "top": hedefler["eticaret"] + hedefler["magaza"] + hedefler["toptan"],
        }
    })


@app.route("/api/sifre-kontrol", methods=["POST"])
def sifre_kontrol():
    data = request.get_json()
    return jsonify({"ok": data.get("sifre") == ADMIN_SIFRE})


@app.route("/api/hedef-guncelle", methods=["POST"])
def hedef_guncelle():
    global hedefler
    data = request.get_json()
    if data.get("sifre") != ADMIN_SIFRE:
        return jsonify({"ok": False})
    hedefler["eticaret"] = int(data.get("et", hedefler["eticaret"]))
    hedefler["magaza"]   = int(data.get("mg", hedefler["magaza"]))
    hedefler["toptan"]   = int(data.get("tp", hedefler["toptan"]))
    print(f"✅ Hedefler güncellendi: ET={hedefler['eticaret']:,} MG={hedefler['magaza']:,} TP={hedefler['toptan']:,}")
    return jsonify({"ok": True})


@app.route("/api/saglik")
def saglik():
    return jsonify({"durum": "ok"})


if __name__ == "__main__":
    t = threading.Thread(target=guncelle_dongu, daemon=True)
    t.start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

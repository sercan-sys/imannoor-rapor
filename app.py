"""
IMANNOOR Canlı Ciro Dashboard v3
- Açık zemin, PNG görseli ile aynı tasarım
- Admin paneli ile günlük hedef değiştirme
- requests + BeautifulSoup (hafif, Railway ücretsiz plan)
"""

import os, time, threading, requests
from datetime import datetime
from flask import Flask, jsonify, render_template_string, request
from bs4 import BeautifulSoup

app = Flask(__name__)

KULLANICI_ADI = os.environ.get("IMANNOOR_USER", "")
SIFRE         = os.environ.get("IMANNOOR_PASS", "")
ADMIN_SIFRE   = os.environ.get("ADMIN_SIFRE", "imn26*")

hedefler = {
    "eticaret": int(os.environ.get("HEDEF_ETICARET", "3250000")),
    "magaza"  : int(os.environ.get("HEDEF_MAGAZA",   "750000")),
    "toptan"  : int(os.environ.get("HEDEF_TOPTAN",   "500000")),
}

son_veri = {
    "bugun_ciro": 0, "dun_ciro": 0, "toplam_adet": 0,
    "eticaret_ciro": 0, "magaza_ciro": 0, "toptan_ciro": 0,
    "guncelleme": "Henüz güncellenmedi", "hata": None,
}


def parse_sayi(m):
    if not m: return 0.0
    t = str(m).strip().replace('\xa0','').replace(' ','').replace('.','').replace(',','.')
    try: return float(t)
    except: return 0.0


def veri_cek():
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 Chrome/120"})
    r = s.get("https://rapor.imannoor.com/Account/Login/", timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    tok = soup.find("input", {"name": "__RequestVerificationToken"})
    r2 = s.post("https://rapor.imannoor.com/Account/Login/",
                data={"UserName": KULLANICI_ADI, "Password": SIFRE,
                      "__RequestVerificationToken": tok["value"] if tok else ""},
                timeout=15, allow_redirects=True)
    if "login" in r2.url.lower():
        raise Exception("Giriş başarısız")
    r3 = s.get("https://rapor.imannoor.com/Report/OrderReport", timeout=15)
    txt = BeautifulSoup(r3.text, "html.parser").get_text("\n")

    def p(etiket):
        lines = txt.split("\n")
        for i, l in enumerate(lines):
            if etiket.lower() in l.lower().strip():
                for j in range(i+1, min(i+4, len(lines))):
                    v = lines[j].strip()
                    if v: return parse_sayi(v)
        return 0.0

    return {
        "bugun_ciro": p("Bugün Ciro"), "dun_ciro": p("Dün Ciro"),
        "toplam_adet": int(p("Adet")),
        "eticaret_ciro": p("Eticaret Ciro"),
        "magaza_ciro": p("Mağaza Ciro"),
        "toptan_ciro": p("Toptan Ciro"),
    }


def guncelle_dongu():
    global son_veri
    while True:
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Veri çekiliyor...")
            v = veri_cek()
            AYLAR = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
                     "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]
            d = datetime.now()
            son_veri = {**v,
                "guncelleme": f"{d.day} {AYLAR[d.month-1]} {d.year}  {d.strftime('%H:%M')}",
                "hata": None}
            print(f"  ✅ {v['bugun_ciro']:,.0f} TL | {v['toplam_adet']} adet")
        except Exception as e:
            son_veri["hata"] = str(e)
            print(f"  ❌ {e}")
        time.sleep(300)


HTML = r"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Imannoor Ciro</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700;900&family=DM+Mono:wght@500;600&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'DM Sans',sans-serif;background:#f0ede6;color:#1a1a1a;min-height:100vh}
.page{max-width:640px;margin:0 auto;padding:0 0 40px}

/* TOP BAR — koyu */
.topbar{background:#111118;padding:22px 32px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px}
.topbar-title{font-size:26px;font-weight:900;color:#fff;letter-spacing:-.5px}
.topbar-right{text-align:right}
.topbar-tarih{font-size:13px;color:#555577;line-height:1.6}
.topbar-saat{font-size:12px;color:#333344}

/* HEDEF KARTLARI */
.hkartlar{background:#111118;padding:0 32px 24px;display:grid;grid-template-columns:1fr 1fr;gap:14px}
.hk{background:#1e1e2e;border:1px solid #2a2a44;border-radius:14px;padding:16px 20px}
.hk-lbl{font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#444466;margin-bottom:8px}
.hk-val{font-family:'DM Mono',monospace;font-size:22px;font-weight:600;letter-spacing:-.5px;color:#c9a84c}
.hk-sub{font-size:11px;color:#333344;margin-top:5px;font-family:'DM Mono',monospace}
.oran-val{font-family:'DM Mono',monospace;font-size:36px;font-weight:700;letter-spacing:-1px}
.mini-bar{width:100%;height:4px;background:#1a1a30;border-radius:99px;margin-top:10px;overflow:hidden}
.mini-barf{height:100%;border-radius:99px;transition:width .8s}

/* BODY */
.body{background:#f0ede6;padding:24px 32px}

/* BUGÜN — altın kart */
.bugun-kart{background:linear-gradient(135deg,#c9a84c,#a07830);border-radius:18px;padding:22px 26px;margin-bottom:16px;position:relative;overflow:hidden}
.bugun-kart::after{content:'';position:absolute;right:-20px;top:-20px;width:120px;height:120px;background:rgba(255,255,255,.08);border-radius:50%}
.bugun-lbl{font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:rgba(0,0,0,.45);margin-bottom:8px}
.bugun-val{font-family:'DM Mono',monospace;font-size:48px;font-weight:700;color:#1a1a1a;letter-spacing:-1.5px;line-height:1}
.bugun-adet{font-size:13px;color:rgba(0,0,0,.4);margin-top:8px;font-family:'DM Mono',monospace}

/* DÜN KART */
.dun-kart{background:#fff;border-radius:16px;padding:18px 22px;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 2px 12px rgba(0,0,0,.06)}
.dun-sol .dun-lbl{font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#bbb;margin-bottom:5px}
.dun-sol .dun-val{font-family:'DM Mono',monospace;font-size:26px;font-weight:600;color:#333}
.fark{font-family:'DM Mono',monospace;font-size:14px;font-weight:700;padding:7px 14px;border-radius:99px}
.fp{background:#e8faf0;color:#16a34a}
.fn{background:#fef2f2;color:#dc2626}

/* KATEGORİ */
.sec-lbl{font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#bbb;margin-bottom:12px}
.kat-grid{display:grid;gap:12px;margin-bottom:0}
.kat{background:#fff;border-radius:14px;padding:18px 22px;box-shadow:0 2px 12px rgba(0,0,0,.05)}
.kat-ust{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px}
.kat-isim{font-size:12px;font-weight:700;color:#999;letter-spacing:1px;text-transform:uppercase}
.kat-oran{font-family:'DM Mono',monospace;font-size:13px;font-weight:700}
.kat-ciro{font-family:'DM Mono',monospace;font-size:28px;font-weight:700;letter-spacing:-.5px;margin-bottom:3px}
.kat-hedef{font-size:11px;color:#ccc;margin-bottom:10px;font-family:'DM Mono',monospace}
.bar{width:100%;height:8px;background:#f0ece4;border-radius:99px;overflow:hidden}
.barf{height:100%;border-radius:99px;transition:width .8s}

/* FOOTER */
.foot{background:#111118;padding:14px 32px;display:flex;justify-content:space-between;align-items:center}
.foot-left{font-size:11px;color:#333344}
.foot-brand{font-size:13px;font-weight:700;letter-spacing:2px;color:#c9a84c}

/* AYAR BUTONU */
.ayar-btn{background:transparent;border:1px solid #333344;border-radius:99px;padding:6px 14px;font-size:12px;color:#555566;cursor:pointer;transition:.2s}
.ayar-btn:hover{border-color:#c9a84c;color:#c9a84c}
.live-row{display:flex;align-items:center;gap:10px}
.dot{width:7px;height:7px;background:#22c55e;border-radius:50%;animation:pu 2s infinite;flex-shrink:0}
@keyframes pu{0%,100%{opacity:1}50%{opacity:.3}}
.son-gun{font-size:11px;color:#333344}

/* MODAL */
.overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:100;justify-content:center;align-items:center}
.overlay.open{display:flex}
.modal{background:#fff;border-radius:20px;padding:28px;width:320px;max-width:94vw}
.modal h2{font-size:18px;font-weight:700;color:#1a1a1a;margin-bottom:4px}
.modal p{font-size:12px;color:#aaa;margin-bottom:18px}
.modal label{font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#bbb;display:block;margin-bottom:4px;margin-top:10px}
.modal input{width:100%;border:1.5px solid #e8e4dc;border-radius:10px;padding:10px 14px;font-size:14px;font-family:'DM Mono',monospace;color:#1a1a1a;outline:none}
.modal input:focus{border-color:#c9a84c}
.btn-row{display:flex;gap:10px;margin-top:18px}
.btn{flex:1;padding:10px;border-radius:10px;font-size:14px;font-weight:700;cursor:pointer;border:none}
.btn-iptal{background:#f0ece4;color:#888}
.btn-kaydet{background:#c9a84c;color:#fff}
.err{color:#dc2626;font-size:12px;margin-top:5px;display:none}

@media(max-width:480px){
  .topbar,.hkartlar,.body,.foot{padding-left:18px;padding-right:18px}
  .hkartlar{grid-template-columns:1fr}
  .bugun-val{font-size:36px}
  .oran-val{font-size:28px}
}
</style>
</head>
<body>
<div class="page">

  <!-- TOP BAR -->
  <div class="topbar">
    <div class="topbar-title">Günlük Ciro Raporu</div>
    <div class="topbar-right">
      <div class="topbar-tarih" id="tarih">—</div>
      <div class="topbar-saat" id="saat">—</div>
    </div>
  </div>

  <!-- HEDEF KARTLARI -->
  <div class="hkartlar">
    <div class="hk">
      <div class="hk-lbl">Toplam Hedef</div>
      <div class="hk-val" id="toplam-hedef">—</div>
      <div class="hk-sub" id="adet-sub">— adet sipariş</div>
    </div>
    <div class="hk">
      <div class="hk-lbl">Gerçekleştirme</div>
      <div class="oran-val" id="oran">—</div>
      <div class="mini-bar"><div class="mini-barf" id="obar" style="width:0%"></div></div>
    </div>
  </div>

  <!-- BODY -->
  <div class="body">

    <!-- BUGÜN -->
    <div class="bugun-kart">
      <div class="bugun-lbl">BUGÜN CİRO</div>
      <div class="bugun-val" id="bugun-ciro">0 TL</div>
      <div class="bugun-adet" id="bugun-adet">0 adet sipariş</div>
    </div>

    <!-- DÜN -->
    <div class="dun-kart">
      <div class="dun-sol">
        <div class="dun-lbl">DÜN CİRO</div>
        <div class="dun-val" id="dun-ciro">—</div>
      </div>
      <div class="fark" id="fark">—</div>
    </div>

    <!-- KATEGORİLER -->
    <div class="sec-lbl" style="margin-top:20px">KATEGORİ BAZINDA CİRO & HEDEF</div>
    <div class="kat-grid" id="katlar"></div>

  </div>

  <!-- FOOTER -->
  <div class="foot">
    <div>
      <div class="live-row">
        <div class="dot"></div>
        <span class="son-gun" id="son-gun">Bağlanıyor...</span>
      </div>
    </div>
    <div style="display:flex;align-items:center;gap:12px">
      <button class="ayar-btn" onclick="modalAc()">⚙️ Hedefler</button>
      <div class="foot-brand">IMANNOOR</div>
    </div>
  </div>

</div>

<!-- MODAL -->
<div class="overlay" id="overlay">
  <div class="modal">
    <h2>⚙️ Günlük Hedefler</h2>
    <p>Admin şifresiyle hedefleri güncelleyebilirsin.</p>
    <div id="sifre-alan">
      <label>Admin Şifresi</label>
      <input type="password" id="sifre-inp" placeholder="••••••">
      <div class="err" id="sifre-err">Şifre hatalı!</div>
      <div class="btn-row">
        <button class="btn btn-iptal" onclick="modalKapat()">İptal</button>
        <button class="btn btn-kaydet" onclick="sifreKontrol()">Devam →</button>
      </div>
    </div>
    <div id="hedef-alan" style="display:none">
      <label>E-Ticaret Hedef (TL)</label>
      <input type="number" id="h-et">
      <label>Mağaza Hedef (TL)</label>
      <input type="number" id="h-mg">
      <label>Toptan Hedef (TL)</label>
      <input type="number" id="h-tp">
      <div class="btn-row">
        <button class="btn btn-iptal" onclick="modalKapat()">İptal</button>
        <button class="btn btn-kaydet" onclick="hedefKaydet()">💾 Kaydet</button>
      </div>
    </div>
  </div>
</div>

<script>
let H={et:0,mg:0,tp:0,top:0};
const AYLAR=['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'];
const GUNLER=['Pazar','Pazartesi','Salı','Çarşamba','Perşembe','Cuma','Cumartesi'];
function fmt(n){return Math.round(n).toLocaleString('tr-TR')}
function renk(o){return o>=100?'#16a34a':o>=75?'#ca8a04':'#dc2626'}

function guncelle(){
  fetch('/api/veri').then(r=>r.json()).then(d=>{
    H=d.hedefler;
    const now=new Date();
    const tr=new Date(now.toLocaleString('en-US',{timeZone:'Europe/Istanbul'}));
    document.getElementById('tarih').textContent=
      GUNLER[tr.getDay()]+' '+tr.getDate()+' '+AYLAR[tr.getMonth()]+' '+tr.getFullYear();
    document.getElementById('saat').textContent=
      String(tr.getHours()).padStart(2,'0')+':'+String(tr.getMinutes()).padStart(2,'0');
    document.getElementById('son-gun').textContent='Son: '+d.guncelleme;

    document.getElementById('toplam-hedef').textContent=fmt(H.top)+' TL';
    document.getElementById('adet-sub').textContent=fmt(d.toplam_adet)+' adet sipariş';

    const o=H.top>0?Math.round(d.bugun_ciro/H.top*100):0;
    const r=renk(o);
    document.getElementById('oran').textContent='%'+o;
    document.getElementById('oran').style.color=r;
    const ob=document.getElementById('obar');
    ob.style.width=Math.min(o,100)+'%';ob.style.background=r;

    document.getElementById('bugun-ciro').textContent=fmt(d.bugun_ciro)+' TL';
    document.getElementById('bugun-adet').textContent=fmt(d.toplam_adet)+' adet sipariş';

    document.getElementById('dun-ciro').textContent=fmt(d.dun_ciro)+' TL';
    const f=d.bugun_ciro-d.dun_ciro;
    const fe=document.getElementById('fark');
    fe.textContent=(f>=0?'▲ ':'▼ ')+fmt(Math.abs(f))+' TL';
    fe.className='fark '+(f>=0?'fp':'fn');

    const katlar=[
      {n:'E-Ticaret',c:d.eticaret_ciro,h:H.et,r:'#3b5bdb'},
      {n:'Mağaza',   c:d.magaza_ciro,  h:H.mg,r:'#2b8a3e'},
      {n:'Toptan',   c:d.toptan_ciro,  h:H.tp,r:'#b45309'},
    ];
    document.getElementById('katlar').innerHTML=katlar.map(k=>{
      const o2=k.h>0?Math.round(k.c/k.h*100):0;
      const r2=renk(o2);
      const bw=Math.min(o2,100);
      return `<div class="kat">
        <div class="kat-ust"><span class="kat-isim">${k.n}</span><span class="kat-oran" style="color:${r2}">%${o2}</span></div>
        <div class="kat-ciro" style="color:${k.r}">${fmt(k.c)} TL</div>
        <div class="kat-hedef">Hedef: ${fmt(k.h)} TL</div>
        <div class="bar"><div class="barf" style="width:${bw}%;background:${k.r}"></div></div>
      </div>`;
    }).join('');
  }).catch(()=>{document.getElementById('son-gun').textContent='Bağlantı hatası'});
}

function modalAc(){
  document.getElementById('overlay').classList.add('open');
  document.getElementById('sifre-alan').style.display='block';
  document.getElementById('hedef-alan').style.display='none';
  document.getElementById('sifre-inp').value='';
  document.getElementById('sifre-err').style.display='none';
}
function modalKapat(){document.getElementById('overlay').classList.remove('open')}

function sifreKontrol(){
  fetch('/api/sifre-kontrol',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({sifre:document.getElementById('sifre-inp').value})})
  .then(r=>r.json()).then(d=>{
    if(d.ok){
      document.getElementById('sifre-alan').style.display='none';
      document.getElementById('hedef-alan').style.display='block';
      document.getElementById('h-et').value=H.et;
      document.getElementById('h-mg').value=H.mg;
      document.getElementById('h-tp').value=H.tp;
    } else {document.getElementById('sifre-err').style.display='block';}
  });
}

function hedefKaydet(){
  fetch('/api/hedef-guncelle',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({sifre:document.getElementById('sifre-inp').value,
      et:parseInt(document.getElementById('h-et').value)||0,
      mg:parseInt(document.getElementById('h-mg').value)||0,
      tp:parseInt(document.getElementById('h-tp').value)||0})})
  .then(r=>r.json()).then(d=>{if(d.ok){modalKapat();guncelle();}});
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
    print(f"✅ Hedefler: ET={hedefler['eticaret']:,} MG={hedefler['magaza']:,} TP={hedefler['toptan']:,}")
    return jsonify({"ok": True})

@app.route("/api/saglik")
def saglik():
    return jsonify({"durum": "ok"})

if __name__ == "__main__":
    threading.Thread(target=guncelle_dongu, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

"""
IMANNOOR Canlı Ciro Dashboard v5
- SQLite ile günlük kayıt
- Her 5dk bugünü günceller, 23:58'de kalıcı kaydeder
"""

import os, time, threading, requests, sqlite3
from datetime import datetime
from flask import Flask, jsonify, render_template_string, request
from bs4 import BeautifulSoup

app = Flask(__name__)

KULLANICI_ADI = os.environ.get("IMANNOOR_USER", "")
SIFRE         = os.environ.get("IMANNOOR_PASS", "")
ADMIN_SIFRE   = os.environ.get("ADMIN_SIFRE", "imn26*")
DB_PATH       = "/app/data/ciro.db"

hedefler = {
    "eticaret": int(os.environ.get("HEDEF_ETICARET", "3250000")),
    "magaza"  : int(os.environ.get("HEDEF_MAGAZA",   "750000")),
    "toptan"  : int(os.environ.get("HEDEF_TOPTAN",   "500000")),
    "aylik"   : int(os.environ.get("HEDEF_AYLIK",    "100000000")),
}

son_veri = {
    "bugun_ciro": 0, "dun_ciro": 0, "toplam_adet": 0,
    "eticaret_ciro": 0, "magaza_ciro": 0, "toptan_ciro": 0,
    "aylik_ciro": 0,
    "guncelleme": "Henüz güncellenmedi", "hata": None,
}


# ── VERİTABANI ─────────────────────────────────────────
def db_baglanti():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def db_olustur():
    with db_baglanti() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS gunluk (
                tarih       TEXT PRIMARY KEY,
                eticaret    REAL DEFAULT 0,
                magaza      REAL DEFAULT 0,
                toptan      REAL DEFAULT 0,
                toplam      REAL DEFAULT 0,
                adet        INTEGER DEFAULT 0,
                h_eticaret  REAL DEFAULT 0,
                h_magaza    REAL DEFAULT 0,
                h_toptan    REAL DEFAULT 0,
                h_toplam    REAL DEFAULT 0,
                gece_kayit  INTEGER DEFAULT 0
            )
        """)
        con.commit()

def db_kaydet(tarih, v, gece=False):
    htop = hedefler["eticaret"] + hedefler["magaza"] + hedefler["toptan"]
    with db_baglanti() as con:
        # Gece kaydı yapılmış mı kontrol et
        row = con.execute("SELECT gece_kayit FROM gunluk WHERE tarih=?", (tarih,)).fetchone()
        zaten_gece = row and row[0] == 1

        if zaten_gece and not gece:
            # Sadece ciro rakamlarını güncelle, hedeflere dokunma
            con.execute("""
                INSERT INTO gunluk (tarih,eticaret,magaza,toptan,toplam,adet,
                                    h_eticaret,h_magaza,h_toptan,h_toplam,gece_kayit)
                VALUES (?,?,?,?,?,?,?,?,?,?,0)
                ON CONFLICT(tarih) DO UPDATE SET
                    eticaret=excluded.eticaret, magaza=excluded.magaza,
                    toptan=excluded.toptan, toplam=excluded.toplam,
                    adet=excluded.adet
            """, (tarih,
                  v["eticaret_ciro"], v["magaza_ciro"], v["toptan_ciro"], v["bugun_ciro"],
                  v["toplam_adet"],
                  hedefler["eticaret"], hedefler["magaza"], hedefler["toptan"], htop))
        else:
            con.execute("""
                INSERT INTO gunluk (tarih,eticaret,magaza,toptan,toplam,adet,
                                    h_eticaret,h_magaza,h_toptan,h_toplam,gece_kayit)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(tarih) DO UPDATE SET
                    eticaret=excluded.eticaret, magaza=excluded.magaza,
                    toptan=excluded.toptan, toplam=excluded.toplam,
                    adet=excluded.adet, h_eticaret=excluded.h_eticaret,
                    h_magaza=excluded.h_magaza, h_toptan=excluded.h_toptan,
                    h_toplam=excluded.h_toplam,
                    gece_kayit=CASE WHEN excluded.gece_kayit=1 THEN 1 ELSE gunluk.gece_kayit END
            """, (tarih,
                  v["eticaret_ciro"], v["magaza_ciro"], v["toptan_ciro"], v["bugun_ciro"],
                  v["toplam_adet"],
                  hedefler["eticaret"], hedefler["magaza"], hedefler["toptan"], htop,
                  1 if gece else 0))
        con.commit()

def db_gecmis(limit=30):
    with db_baglanti() as con:
        rows = con.execute("""
            SELECT tarih,eticaret,magaza,toptan,toplam,adet,
                   h_eticaret,h_magaza,h_toptan,h_toplam
            FROM gunluk ORDER BY tarih DESC LIMIT ?
        """, (limit,)).fetchall()
    return rows


# ── VERİ ÇEKME ─────────────────────────────────────────
def parse_sayi(m):
    if not m: return 0.0
    t = str(m).strip().replace('\xa0','').replace(' ','').replace('.','').replace(',','.')
    try: return float(t)
    except: return 0.0

def veri_cek():
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 Chrome/120"})
    r = s.get("https://rapor.imannoor.com/Account/Login/", timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")
    tok = soup.find("input", {"name": "__RequestVerificationToken"})
    r2 = s.post("https://rapor.imannoor.com/Account/Login/",
                data={"UserName": KULLANICI_ADI, "Password": SIFRE,
                      "__RequestVerificationToken": tok["value"] if tok else ""},
                timeout=30, allow_redirects=True)
    if "login" in r2.url.lower():
        raise Exception("Giriş başarısız")
    r3 = s.get("https://rapor.imannoor.com/Report/OrderReport", timeout=30)
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
        "aylik_ciro": p("Bu Ay Ciro") or p("Aylık Ciro") or p("Bu Ay") or p("Aylık"),
    }

def tr_simdi():
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("Europe/Istanbul"))

def guncelle_dongu():
    global son_veri
    db_olustur()
    son_gece_kayit = None

    while True:
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Veri çekiliyor...")
            v = veri_cek()
            AYLAR = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
                     "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]
            d = tr_simdi()
            tarih_str = f"{d.year}-{d.month:02d}-{d.day:02d}"

            son_veri = {**v,
                "guncelleme": f"{d.day} {AYLAR[d.month-1]} {d.year}  {d.strftime('%H:%M')}",
                "hata": None}

            # Her 5dk: bugünü güncelle
            db_kaydet(tarih_str, v, gece=False)

            # Gece 23:58 → kalıcı gece kaydı
            if d.hour == 23 and d.minute >= 58:
                if son_gece_kayit != tarih_str:
                    db_kaydet(tarih_str, v, gece=True)
                    son_gece_kayit = tarih_str
                    print(f"  🌙 Gece kaydı yapıldı: {tarih_str}")

            print(f"  ✅ {v['bugun_ciro']:,.0f} TL | {v['toplam_adet']} adet")
        except Exception as e:
            son_veri["hata"] = str(e)
            print(f"  ❌ {e}")
            time.sleep(60)  # hata varsa 1 dk sonra tekrar dene
            continue
        time.sleep(300)


# ── HTML ────────────────────────────────────────────────
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
.page{max-width:480px;margin:0 auto;padding:0 0 20px}

.topbar{background:#111118;padding:14px 18px;display:flex;justify-content:space-between;align-items:center}
.topbar-title{font-size:18px;font-weight:900;color:#fff;letter-spacing:-.5px}
.topbar-right{text-align:right}
.topbar-tarih{font-size:11px;color:#555577;line-height:1.5}
.topbar-saat{font-size:11px;color:#333344}

.blok{margin:12px 14px;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,.06)}
.blok-header{padding:14px 16px 10px;border-bottom:1px solid #f0ece4}
.blok-baslik{font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#bbb}

.aylik-blok{margin:12px 14px;background:#111118;border-radius:16px;overflow:hidden}
.aylik-header{padding:14px 16px 6px}
.aylik-baslik{font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#444466}
.aylik-row{padding:0 16px 6px;display:flex;align-items:baseline;gap:10px}
.aylik-val{font-family:'DM Mono',monospace;font-size:28px;font-weight:700;color:#c9a84c;letter-spacing:-1px}
.aylik-oran{font-family:'DM Mono',monospace;font-size:15px;font-weight:700}
.aylik-hedef-txt{font-size:10px;color:#333344;padding:0 16px 6px;font-family:'DM Mono',monospace}
.tup-wrap{padding:0 16px 14px}
.tup-track{width:100%;height:10px;background:#1e1e2e;border-radius:99px;overflow:hidden}
.tup-fill{height:100%;border-radius:99px;transition:width 1s ease}
.tup-labels{display:flex;justify-content:space-between;margin-top:4px}
.tup-label{font-size:10px;color:#333344;font-family:'DM Mono',monospace}

.bugun-row{padding:14px 16px 6px;display:flex;align-items:baseline;gap:10px}
.bugun-val{font-family:'DM Mono',monospace;font-size:34px;font-weight:700;color:#1a1a1a;letter-spacing:-1px}
.bugun-adet{font-size:11px;color:#bbb;padding:0 16px 6px;font-family:'DM Mono',monospace}

.kat-list{padding:4px 16px 12px}
.kat-item{margin-bottom:10px}
.kat-item:last-child{margin-bottom:0}
.kat-ust{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:3px}
.kat-isim{font-size:11px;font-weight:700;color:#888;letter-spacing:.5px;text-transform:uppercase}
.kat-sag{display:flex;align-items:baseline;gap:8px}
.kat-ciro{font-family:'DM Mono',monospace;font-size:15px;font-weight:700}
.kat-oran{font-family:'DM Mono',monospace;font-size:12px;font-weight:700}
.kat-track{width:100%;height:8px;background:#f0ece4;border-radius:99px;overflow:hidden}
.kat-fill{height:100%;border-radius:99px;transition:width 1s ease}
.kat-hedef-txt{font-size:10px;color:#ccc;margin-top:3px;font-family:'DM Mono',monospace}

.gunluk-hedef{margin:0 16px 12px;background:#f7f4ee;border-radius:10px;padding:10px 14px;display:flex;justify-content:space-between;align-items:center}
.gh-lbl{font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#ccc}
.gh-val{font-family:'DM Mono',monospace;font-size:14px;font-weight:700;color:#888}

.dun-row{padding:8px 16px 14px;display:flex;justify-content:space-between;align-items:center;border-top:1px solid #f5f2ec}
.dun-lbl{font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#ccc}
.dun-val{font-family:'DM Mono',monospace;font-size:14px;color:#888}
.fark{font-family:'DM Mono',monospace;font-size:12px;font-weight:700;padding:4px 10px;border-radius:99px}
.fp{background:#e8faf0;color:#16a34a}
.fn{background:#fef2f2;color:#dc2626}

/* GEÇMİŞ TABLO */
.gecmis-blok{margin:12px 14px;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,.06)}
.gecmis-header{padding:14px 16px;border-bottom:1px solid #f0ece4}
.gecmis-baslik{font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#bbb}

/* GEÇMİŞ KARTLAR */
.g-kart{border-bottom:1px solid #f5f2ec;padding:12px 16px}
.g-kart:last-child{border-bottom:none}
.g-ust{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.g-tarih{font-size:13px;font-weight:700;color:#333}
.g-toplam-wrap{display:flex;align-items:baseline;gap:8px}
.g-toplam{font-family:'DM Mono',monospace;font-size:13px;font-weight:700;color:#1a1a1a}
.g-oran{font-family:'DM Mono',monospace;font-size:11px;font-weight:700;padding:2px 7px;border-radius:99px}
.ob-g{background:#e8faf0;color:#16a34a}
.ob-s{background:#fef9e7;color:#ca8a04}
.ob-r{background:#fef2f2;color:#dc2626}
.g-katlar{display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px}
.g-kat{background:#f7f4ee;border-radius:8px;padding:8px 10px}
.g-kat-isim{font-size:9px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;color:#bbb;margin-bottom:4px}
.g-kat-gercek{font-family:'DM Mono',monospace;font-size:12px;font-weight:700;color:#1a1a1a}
.g-kat-hedef{font-family:'DM Mono',monospace;font-size:10px;color:#ccc;margin-top:1px}
.g-kat-oran{font-size:10px;font-weight:700;margin-top:2px}

.foot{background:#111118;padding:10px 18px;display:flex;justify-content:space-between;align-items:center}
.live-row{display:flex;align-items:center;gap:7px}
.dot{width:6px;height:6px;background:#22c55e;border-radius:50%;animation:pu 2s infinite}
@keyframes pu{0%,100%{opacity:1}50%{opacity:.3}}
.son-gun{font-size:10px;color:#333344}
.foot-right{display:flex;align-items:center;gap:10px}
.ayar-btn{background:transparent;border:1px solid #2a2a3a;border-radius:99px;padding:5px 12px;font-size:11px;color:#444455;cursor:pointer;transition:.2s}
.ayar-btn:hover{border-color:#c9a84c;color:#c9a84c}
.foot-brand{font-size:12px;font-weight:700;letter-spacing:2px;color:#c9a84c}

.overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:100;justify-content:center;align-items:center}
.overlay.open{display:flex}
.modal{background:#fff;border-radius:20px;padding:24px;width:300px;max-width:90vw;max-height:90vh;overflow-y:auto}
.modal h2{font-size:16px;font-weight:700;margin-bottom:4px}
.modal p{font-size:11px;color:#aaa;margin-bottom:16px}
.modal label{font-size:9px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#bbb;display:block;margin-bottom:4px;margin-top:10px}
.modal input{width:100%;border:1.5px solid #e8e4dc;border-radius:10px;padding:9px 12px;font-size:14px;font-family:'DM Mono',monospace;color:#1a1a1a;outline:none}
.modal input:focus{border-color:#c9a84c}
.btn-row{display:flex;gap:8px;margin-top:16px}
.btn{flex:1;padding:9px;border-radius:10px;font-size:13px;font-weight:700;cursor:pointer;border:none}
.btn-iptal{background:#f0ece4;color:#888}
.btn-kaydet{background:#c9a84c;color:#fff}
.err{color:#dc2626;font-size:11px;margin-top:4px;display:none}
.modal-divider{height:1px;background:#f0ece4;margin:14px 0 4px}
.modal-sec{font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#aaa;margin-bottom:8px}
</style>
</head>
<body>
<div class="page">

  <div class="topbar">
    <div class="topbar-title">Günlük Ciro Raporu</div>
    <div class="topbar-right">
      <div class="topbar-tarih" id="tarih">—</div>
      <div class="topbar-saat" id="saat">—</div>
    </div>
  </div>

  <!-- AYLIK -->
  <div class="aylik-blok">
    <div class="aylik-header"><div class="aylik-baslik">Aylık Ciro</div></div>
    <div class="aylik-row">
      <div class="aylik-val" id="aylik-ciro">—</div>
      <div class="aylik-oran" id="aylik-oran"></div>
    </div>
    <div class="aylik-hedef-txt" id="aylik-hedef-txt">Hedef: —</div>
    <div class="tup-wrap">
      <div class="tup-track"><div class="tup-fill" id="aylik-bar" style="width:0%"></div></div>
      <div class="tup-labels">
        <span class="tup-label">0</span>
        <span class="tup-label" id="aylik-hedef-lbl">—</span>
      </div>
    </div>
  </div>

  <!-- BUGÜN -->
  <div class="blok">
    <div class="blok-header"><div class="blok-baslik">Bugün Gerçekleşen Ciro</div></div>
    <div class="bugun-row"><div class="bugun-val" id="bugun-ciro">—</div></div>
    <div class="bugun-adet" id="bugun-adet">—</div>
    <div class="kat-list" id="katlar"></div>
    <div class="gunluk-hedef">
      <div class="gh-lbl">Günlük Toplam Hedef</div>
      <div class="gh-val" id="gunluk-hedef">—</div>
    </div>
    <div class="dun-row">
      <div><div class="dun-lbl">Dün Ciro</div><div class="dun-val" id="dun-ciro">—</div></div>
      <div class="fark" id="fark">—</div>
    </div>
  </div>

  <!-- GEÇMİŞ -->
  <div class="gecmis-blok">
    <div class="gecmis-header">
      <div class="gecmis-baslik">Günlük Geçmiş</div>
    </div>
    <div id="gecmis-liste">
      <div style="text-align:center;color:#ccc;padding:24px;font-size:12px">Yükleniyor...</div>
    </div>
  </div>

  <div class="foot">
    <div class="live-row">
      <div class="dot"></div>
      <span class="son-gun" id="son-gun">Bağlanıyor...</span>
    </div>
    <div class="foot-right">
      <button class="ayar-btn" onclick="modalAc()">⚙️ Hedefler</button>
      <div class="foot-brand">IMANNOOR</div>
    </div>
  </div>

</div>

<!-- MODAL -->
<div class="overlay" id="overlay">
  <div class="modal">
    <h2>⚙️ Hedefler</h2>
    <p>Admin şifresiyle hedefleri güncelle.</p>
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
      <div class="modal-divider"></div>
      <div class="modal-sec">Günlük Hedefler</div>
      <label>E-Ticaret (TL)</label><input type="number" id="h-et">
      <label>Mağaza (TL)</label><input type="number" id="h-mg">
      <label>Toptan (TL)</label><input type="number" id="h-tp">
      <div class="modal-divider"></div>
      <div class="modal-sec">Aylık Hedef</div>
      <label>Aylık Toplam (TL)</label><input type="number" id="h-aylik">
      <div class="btn-row">
        <button class="btn btn-iptal" onclick="modalKapat()">İptal</button>
        <button class="btn btn-kaydet" onclick="hedefKaydet()">💾 Kaydet</button>
      </div>
    </div>
  </div>
</div>

<script>
let H={et:0,mg:0,tp:0,top:0,aylik:0};
const AYLAR=['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'];
const AYLAR_K=['Oca','Şub','Mar','Nis','May','Haz','Tem','Ağu','Eyl','Eki','Kas','Ara'];
const GUNLER=['Pazar','Pazartesi','Salı','Çarşamba','Perşembe','Cuma','Cumartesi'];
function fmt(n){return Math.round(n).toLocaleString('tr-TR')}
function fmtK(n){
  if(n>=1000000) return (n/1000000).toFixed(1).replace('.',',')+' M';
  if(n>=1000) return (n/1000).toFixed(0)+' B';
  return fmt(n);
}
function renk(o){return o>=100?'#16a34a':o>=75?'#ca8a04':'#dc2626'}
function renk2(o){return o>=100?'#22c55e':o>=75?'#facc15':'#ef4444'}
function obClass(o){return o>=100?'ob-g':o>=75?'ob-s':'ob-r'}

function gecmisGuncelle(){
  fetch('/api/gecmis').then(r=>r.json()).then(rows=>{
    const el = document.getElementById('gecmis-liste');
    if(!rows.length){
      el.innerHTML='<div style="text-align:center;color:#ccc;padding:24px;font-size:12px">Henüz kayıt yok</div>';
      return;
    }
    el.innerHTML = rows.map(r=>{
      const parts = r.tarih.split('-');
      const ay = AYLAR_K[parseInt(parts[1])-1];
      const gun = parseInt(parts[2]);
      const tarihStr = gun+' '+ay+' '+parts[0];
      const oran = r.h_toplam>0 ? Math.round(r.toplam/r.h_toplam*100) : 0;
      const obc = oran>=100?'ob-g':oran>=75?'ob-s':'ob-r';

      const katlar = [
        {n:'E-Tic', g:r.eticaret, h:r.h_eticaret, r:'#3b5bdb'},
        {n:'Mağaza', g:r.magaza,  h:r.h_magaza,   r:'#2b8a3e'},
        {n:'Toptan', g:r.toptan,  h:r.h_toptan,   r:'#b45309'},
      ];

      return `<div class="g-kart">
        <div class="g-ust">
          <div class="g-tarih">${tarihStr}</div>
          <div class="g-toplam-wrap">
            <div class="g-toplam">${fmtK(r.toplam)} TL</div>
            <span class="g-oran ${obc}">%${oran}</span>
          </div>
        </div>
        <div class="g-katlar">
          ${katlar.map(k=>{
            const ko = k.h>0?Math.round(k.g/k.h*100):0;
            const kc = ko>=100?'#16a34a':ko>=75?'#ca8a04':'#dc2626';
            return `<div class="g-kat">
              <div class="g-kat-isim">${k.n}</div>
              <div class="g-kat-gercek" style="color:${k.r}">${fmtK(k.g)}</div>
              <div class="g-kat-hedef">H: ${fmtK(k.h)}</div>
              <div class="g-kat-oran" style="color:${kc}">%${ko}</div>
            </div>`;
          }).join('')}
        </div>
      </div>`;
    }).join('');
  });
}

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

    // Aylık
    const ayO=H.aylik>0?Math.round(d.aylik_ciro/H.aylik*100):0;
    const ayR=renk2(ayO);
    document.getElementById('aylik-ciro').textContent=d.aylik_ciro>0?fmt(d.aylik_ciro)+' TL':'—';
    document.getElementById('aylik-oran').textContent=d.aylik_ciro>0?'%'+ayO:'';
    document.getElementById('aylik-oran').style.color=ayR;
    document.getElementById('aylik-hedef-txt').textContent='Hedef: '+fmt(H.aylik)+' TL';
    document.getElementById('aylik-hedef-lbl').textContent=fmtK(H.aylik);
    const ab=document.getElementById('aylik-bar');
    ab.style.width=Math.min(ayO,100)+'%'; ab.style.background=ayR;

    // Bugün
    document.getElementById('bugun-ciro').textContent=fmt(d.bugun_ciro)+' TL';
    document.getElementById('bugun-adet').textContent=fmt(d.toplam_adet)+' adet sipariş';
    document.getElementById('gunluk-hedef').textContent=fmt(H.top)+' TL';

    // Dün
    document.getElementById('dun-ciro').textContent=fmt(d.dun_ciro)+' TL';
    const f=d.bugun_ciro-d.dun_ciro;
    const fe=document.getElementById('fark');
    fe.textContent=(f>=0?'▲ ':'▼ ')+fmt(Math.abs(f))+' TL';
    fe.className='fark '+(f>=0?'fp':'fn');

    // Kategoriler
    const katlar=[
      {n:'E-Ticaret',c:d.eticaret_ciro,h:H.et,r:'#3b5bdb'},
      {n:'Mağaza',   c:d.magaza_ciro,  h:H.mg,r:'#2b8a3e'},
      {n:'Toptan',   c:d.toptan_ciro,  h:H.tp,r:'#b45309'},
    ];
    document.getElementById('katlar').innerHTML=katlar.map(k=>{
      const o=k.h>0?Math.round(k.c/k.h*100):0;
      const rc=renk(o);
      return `<div class="kat-item">
        <div class="kat-ust">
          <span class="kat-isim">${k.n}</span>
          <div class="kat-sag">
            <span class="kat-ciro" style="color:${k.r}">${fmt(k.c)} TL</span>
            <span class="kat-oran" style="color:${rc}">%${o}</span>
          </div>
        </div>
        <div class="kat-track"><div class="kat-fill" style="width:${Math.min(o,100)}%;background:${k.r}"></div></div>
        <div class="kat-hedef-txt">Hedef: ${fmt(k.h)} TL</div>
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
      document.getElementById('h-aylik').value=H.aylik;
    } else {document.getElementById('sifre-err').style.display='block';}
  });
}
function hedefKaydet(){
  fetch('/api/hedef-guncelle',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({
      sifre:document.getElementById('sifre-inp').value,
      et:parseInt(document.getElementById('h-et').value)||0,
      mg:parseInt(document.getElementById('h-mg').value)||0,
      tp:parseInt(document.getElementById('h-tp').value)||0,
      aylik:parseInt(document.getElementById('h-aylik').value)||0
    })}).then(r=>r.json()).then(d=>{if(d.ok){modalKapat();guncelle();}});
}

guncelle();
gecmisGuncelle();
setInterval(guncelle, 60000);
setInterval(gecmisGuncelle, 300000);
</script>
</body>
</html>"""


@app.route("/")
def ana():
    return '<meta http-equiv="refresh" content="0;url=/rapor">'

@app.route("/rapor")
def index():
    return render_template_string(HTML)

@app.route("/api/veri")
def api_veri():
    return jsonify({**son_veri,
        "hedefler": {
            "et": hedefler["eticaret"], "mg": hedefler["magaza"],
            "tp": hedefler["toptan"],
            "top": hedefler["eticaret"]+hedefler["magaza"]+hedefler["toptan"],
            "aylik": hedefler["aylik"],
        }
    })

@app.route("/api/gecmis")
def api_gecmis():
    rows = db_gecmis(30)
    return jsonify([{
        "tarih": r[0], "eticaret": r[1], "magaza": r[2], "toptan": r[3],
        "toplam": r[4], "adet": r[5],
        "h_eticaret": r[6], "h_magaza": r[7], "h_toptan": r[8], "h_toplam": r[9]
    } for r in rows])

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
    hedefler["eticaret"] = int(data.get("et",    hedefler["eticaret"]))
    hedefler["magaza"]   = int(data.get("mg",    hedefler["magaza"]))
    hedefler["toptan"]   = int(data.get("tp",    hedefler["toptan"]))
    hedefler["aylik"]    = int(data.get("aylik", hedefler["aylik"]))
    print(f"✅ Hedefler güncellendi")
    return jsonify({"ok": True})

@app.route("/api/manuel-kayit", methods=["POST"])
def manuel_kayit():
    data = request.get_json()
    if data.get("sifre") != ADMIN_SIFRE:
        return jsonify({"ok": False, "hata": "Şifre hatalı"})
    try:
        tarih    = data["tarih"]   # "2026-03-01"
        eticaret = float(data.get("eticaret", 0))
        magaza   = float(data.get("magaza", 0))
        toptan   = float(data.get("toptan", 0))
        toplam   = eticaret + magaza + toptan
        adet     = int(data.get("adet", 0))
        h_et     = float(data.get("h_eticaret", hedefler["eticaret"]))
        h_mg     = float(data.get("h_magaza",   hedefler["magaza"]))
        h_tp     = float(data.get("h_toptan",   hedefler["toptan"]))
        h_top    = h_et + h_mg + h_tp

        with db_baglanti() as con:
            con.execute("""
                INSERT INTO gunluk (tarih,eticaret,magaza,toptan,toplam,adet,
                                    h_eticaret,h_magaza,h_toptan,h_toplam,gece_kayit)
                VALUES (?,?,?,?,?,?,?,?,?,?,1)
                ON CONFLICT(tarih) DO UPDATE SET
                    eticaret=excluded.eticaret, magaza=excluded.magaza,
                    toptan=excluded.toptan, toplam=excluded.toplam,
                    adet=excluded.adet, h_eticaret=excluded.h_eticaret,
                    h_magaza=excluded.h_magaza, h_toptan=excluded.h_toptan,
                    h_toplam=excluded.h_toplam, gece_kayit=1
            """, (tarih, eticaret, magaza, toptan, toplam, adet, h_et, h_mg, h_tp, h_top))
            con.commit()
        print(f"✅ Manuel kayıt: {tarih} | ET={eticaret:,.0f} MG={magaza:,.0f} TP={toptan:,.0f}")
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "hata": str(e)})


@app.route("/api/saglik")
def saglik():
    return jsonify({"durum": "ok"})

if __name__ == "__main__":
    db_olustur()
    threading.Thread(target=guncelle_dongu, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

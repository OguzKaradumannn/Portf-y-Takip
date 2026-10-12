import yfinance as yf
import streamlit as st
import time
import requests
from pytefas import Crawler
from datetime import datetime, timedelta
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Portföy Analiz Platformu", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# GÜVENLİK DUVARI (LOGIN SİSTEMİ)
# ==========================================
def sifre_kontrol():
    def sifre_girildi():
        beklenen_sifre = str(st.secrets.get("sistem_sifresi", "123456")).strip()
        girilen_sifre = str(st.session_state["sifre_kutusu"]).strip()
        
        if girilen_sifre == beklenen_sifre:
            st.session_state["giris_basarili"] = True
            del st.session_state["sifre_kutusu"]
        else:
            st.session_state["giris_basarili"] = False

    if "giris_basarili" not in st.session_state:
        st.title("🔒 Sisteme Giriş")
        st.warning("Bu sistem özel finansal veriler içerir. Lütfen erişim şifrenizi giriniz.")
        st.text_input("Sistem Şifresi:", type="password", on_change=sifre_girildi, key="sifre_kutusu")
        return False
    elif not st.session_state["giris_basarili"]:
        st.title("🔒 Sisteme Giriş")
        st.text_input("Sistem Şifresi:", type="password", on_change=sifre_girildi, key="sifre_kutusu")
        st.error("❌ Hatalı şifre girdiniz. Lütfen tekrar deneyin.")
        return False
    else:
        return True

if not sifre_kontrol():
    st.stop()


# ==========================================
# DİALOG FONKSİYONU (AYRI PENCEREDE DETAYLAR)
# ==========================================
@st.dialog("🔍 Kapsamlı Varlık Analizi", width="large")
def varlik_detayi_goster(varlik_adi, alt_grup, row_data):
    st.markdown(f"### {varlik_adi}")
    st.caption("Bu pencerede ilgili varlığa ait genel özet bilgileri görebilirsiniz. Tüm işlem listesi için sol menüden 'Alım Detay' sekmesine gidebilirsiniz.")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("📦 Toplam Adet / Gram", f"{row_data.get('Toplam Adet', 0):,.2f}")
    c2.metric("💵 Ort. Maliyet (TL)", f"{row_data.get('Ort. Maliyet (TL)', 0):,.2f} ₺")
    c3.metric("📈 Güncel Fiyat (TL)", f"{row_data.get('Güncel (TL)', 0):,.2f} ₺")
    
    c4, c5, c6 = st.columns(3)
    c4.metric("💰 Yatırılan Toplam", f"{row_data.get('Toplam Maliyet (TL)', 0):,.2f} ₺")
    c5.metric("💳 Güncel Tutar", f"{row_data.get('Toplam Tutar (TL)', 0):,.2f} ₺")
    
    kz_tl = row_data.get('K/Z (TL)', 0)
    kz_yuzde = row_data.get('K/Z (%)', 0)
    c6.metric("🎯 Toplam K/Z (TL)", f"{kz_tl:,.2f} ₺", f"%{kz_yuzde:.2f}")


# ==========================================
# VERİ VE BAĞLANTI MOTORLARI
# ==========================================
def verileri_yukle_gsheets():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="Portfoy", usecols=[0, 1, 2, 3, 4], ttl=0)
        df = df.dropna(how="all")
        return df.to_dict('records')
    except:
        return []

def verileri_kaydet_gsheets(portfoy_listesi):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = pd.DataFrame(portfoy_listesi)
        conn.update(worksheet="Portfoy", data=df)
    except Exception as e:
        st.error(f"Kayıt hatası: {e}")

def izleme_listesini_yukle_gsheets():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="IzlemeListesi", usecols=[0, 1, 2], ttl=0)
        df = df.dropna(how="all")
        return df.to_dict('records')
    except:
        return []

def izleme_listesini_kaydet_gsheets(liste):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = pd.DataFrame(liste)
        conn.update(worksheet="IzlemeListesi", data=df)
    except Exception as e:
        pass

def tefas_fon_fiyati_getir(fon_kodu):
    try:
        bugun = datetime.now()
        bes_gun_once = (bugun - timedelta(days=5)).strftime("%Y-%m-%d")
        tefas = Crawler()
        df = tefas.fetch(start=bes_gun_once, kind="YAT", columns="info")
        if df is not None and not df.empty:
            fon_verisi = df[df['fund_code'] == fon_kodu.upper()]
            if not fon_verisi.empty:
                fon_verisi = fon_verisi.sort_values(by='date', ascending=False)
                return float(fon_verisi.iloc[0]['price'])
        return None
    except:
        return None

def piyasa_verilerini_getir():
    try:
        usd_try = float(yf.Ticker("TRY=X").history(period="1d")['Close'].iloc[0])
        ons_altin_yf = float(yf.Ticker("GC=F").history(period="1d")['Close'].iloc[0])
        ons_gumus = float(yf.Ticker("SI=F").history(period="1d")['Close'].iloc[0])
        
        gram_altin_yf = (ons_altin_yf / 31.1034768) * usd_try
        yirmiiki_ayar_yf = gram_altin_yf * 0.916
        gram_gumus_tl = (ons_gumus / 31.1034768) * usd_try
        
        gram_altin_tr = None
        yirmiiki_ayar_tr = None
        veri_kaynagi = "Yahoo Finance"
        
        try:
            url = "https://www.haremaltin.com/dashboard/ajax/doviz"
            headers = {
                "User-Agent": "Mozilla/5.0",
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/javascript, */*; q=0.01"
            }
            r = requests.post(url, headers=headers, timeout=5)
            if r.status_code == 200:
                json_veri = r.json()
                altinlar = json_veri.get("data", {})
                if "ALTIN" in altinlar:
                    gram_altin_tr = float(altinlar["ALTIN"]["satis"])
                if "AYAR22" in altinlar:
                    yirmiiki_ayar_tr = float(altinlar["AYAR22"]["satis"])
                if gram_altin_tr and gram_altin_tr > 0:
                    veri_kaynagi = "Harem Altın (Canlı)"
        except:
            pass

        return {
            "usd": usd_try,
            "ons_altin": ons_altin_yf,
            "gram_altin": gram_altin_tr if (gram_altin_tr and gram_altin_tr > 0) else gram_altin_yf,
            "yirmiiki_ayar": yirmiiki_ayar_tr if (yirmiiki_ayar_tr and yirmiiki_ayar_tr > 0) else yirmiiki_ayar_yf,
            "ons_gumus": ons_gumus,
            "gram_gumus": gram_gumus_tl,
            "kaynak": veri_kaynagi
        }
    except:
        return None

def degerli_maden_fiyati_getir(maden_turu, veriler):
    if not veriler: return None
    if maden_turu == "Gram Altın (TL)": return veriler["gram_altin"]
    elif maden_turu == "22 Ayar Altın (TL)": return veriler["yirmiiki_ayar"]
    elif maden_turu == "Gümüş (TL)": return veriler["gram_gumus"]
    return None

# Yüklemeler
piyasa = piyasa_verilerini_getir()
if piyasa:
    st.session_state.piyasa = piyasa
else:
    if 'piyasa' not in st.session_state:
        st.session_state.piyasa = {"usd": 35.0, "ons_altin": 2700.0, "gram_altin": 3000.0, "yirmiiki_ayar": 2750.0, "ons_gumus": 30.0, "gram_gumus": 35.0, "kaynak": "-"}

if 'portfoy' not in st.session_state:
    st.session_state.portfoy = verileri_yukle_gsheets()
if 'izleme_listesi' not in st.session_state:
    st.session_state.izleme_listesi = izleme_listesini_yukle_gsheets()
if 'canli_fiyatlar' not in st.session_state:
    st.session_state.canli_fiyatlar = {}

# ==========================================
# SOL MENÜ SİSTEMİ (TEMİZ & SADE)
# ==========================================
with st.sidebar:
    st.markdown("### 📊 FINBO-PORTFÖY")
    st.text_input("", placeholder="🔍 Şirket veya Varlık Ara...")
    
    sayfa_secimi = st.radio(
        "Menü",
        [
            "💼 Portföyüm", 
            "🧾 Alım Detay", 
            "⭐ İzleme Listesi"
        ],
        index=0 # Varsayılan olarak Portföyüm'ü açar
    )
    st.write("")
    st.button("👑 Hemen Pro Dene", type="primary", use_container_width=True)
    st.divider()
    if st.button("🚪 Çıkış Yap", type="secondary", use_container_width=True):
        st.session_state["giris_basarili"] = False
        st.rerun()

# ==========================================
# ARKA PLAN HESAPLAMALARI
# ==========================================
detayli_tablo = []
if len(st.session_state.portfoy) > 0:
    for kalem in st.session_state.portfoy:
        sembol = str(kalem.get("Sembol", ""))
        tur = str(kalem.get("Tür", ""))
        
        if sembol and sembol not in st.session_state.canli_fiyatlar:
            fiyat = None
            if tur in ["BİST Hisse Senedi", "ABD Hisse Senedi", "Yabancı Borsa Fonu (ETF)"]:
                try: fiyat = yf.Ticker(sembol).history(period="1d")['Close'].iloc[0]
                except: pass
            elif tur == "TEFAS Fonu":
                fiyat = tefas_fon_fiyati_getir(sembol)
            elif tur in ["Gram Altın (TL)", "22 Ayar Altın (TL)", "Gümüş (TL)"] or sembol in ["Gram Altın (TL)", "22 Ayar Altın (TL)", "Gümüş (TL)"]:
                maden_adi = tur if tur in ["Gram Altın (TL)", "22 Ayar Altın (TL)", "Gümüş (TL)"] else sembol
                fiyat = degerli_maden_fiyati_getir(maden_adi, st.session_state.piyasa)
            
            st.session_state.canli_fiyatlar[sembol] = fiyat
            
    for i, kalem in enumerate(st.session_state.portfoy):
        tarih = str(kalem.get("Tarih", "-"))
        tur = str(kalem.get("Tür", ""))
        sembol = str(kalem.get("Sembol", ""))
        if not sembol: continue
        try:
            maliyet = float(kalem.get("Maliyet", 0.0))
            adet = float(kalem.get("Adet", 0.0))
        except: maliyet, adet = 0.0, 0.0
            
        guncel_fiyat = st.session_state.canli_fiyatlar.get(sembol)
        
        if guncel_fiyat is not None:
            if tur in ["ABD Hisse Senedi", "Yabancı Borsa Fonu (ETF)"]:
                maliyet_tl = maliyet * st.session_state.piyasa['usd']
                guncel_fiyat_tl = guncel_fiyat * st.session_state.piyasa['usd']
                kar_zarar_usd = (guncel_fiyat - maliyet) * adet
                kar_zarar_tl = (guncel_fiyat_tl - maliyet_tl) * adet
                kz_yuzde = ((guncel_fiyat - maliyet) / maliyet * 100) if maliyet > 0 else 0
                
                detayli_tablo.append({
                    "İşlem No": i, "Tarih": tarih, "Varlık": sembol, "Tür": tur,
                    "Alış (USD)": maliyet, "Güncel (USD)": round(guncel_fiyat, 2),
                    "Alış (TL)": round(maliyet_tl, 2), "Güncel (TL)": round(guncel_fiyat_tl, 2),
                    "Adet": adet, "K/Z (USD)": round(kar_zarar_usd, 2), "K/Z (TL)": round(kar_zarar_tl, 2), "K/Z (%)": round(kz_yuzde, 2)
                })
            else:
                kar_zarar_tl = (guncel_fiyat - maliyet) * adet
                kz_yuzde = ((guncel_fiyat - maliyet) / maliyet * 100) if maliyet > 0 else 0
                detayli_tablo.append({
                    "İşlem No": i, "Tarih": tarih, "Varlık": sembol, "Tür": tur,
                    "Alış (USD)": None, "Güncel (USD)": None,
                    "Alış (TL)": maliyet, "Güncel (TL)": round(guncel_fiyat, 4),
                    "Adet": adet, "K/Z (USD)": None, "K/Z (TL)": round(kar_zarar_tl, 2), "K/Z (%)": round(kz_yuzde, 2)
                })

df_detay = pd.DataFrame(detayli_tablo)

# ==========================================
# EKRAN 1: PORTFÖYÜM (SADE ANA EKRAN)
# ==========================================
if sayfa_secimi == "💼 Portföyüm":
    st.title("💼 Portföyüm")
    p = st.session_state.piyasa
    st.markdown(f"> 💵 USD/TRY: **{p['usd']:.2f} ₺** &nbsp;|&nbsp; 🥇 Altın Ons: **${p['ons_altin']:.2f}** &nbsp;|&nbsp; 🟡 Gram Altın: **{p['gram_altin']:.2f} ₺** &nbsp;|&nbsp; ✨ 22 Ayar: **{p['yirmiiki_ayar']:.2f} ₺** &nbsp;|&nbsp; 🥈 Gümüş: **{p['gram_gumus']:.2f} ₺**")

    # --- YENİ VARLIK EKLEME BÖLÜMÜ ---
    with st.expander("➕ Yeni İşlem (Alım/Ekleme) Yap", expanded=False):
        ana_kategori = st.radio("Kategori", ("Hisse / ETF / Fon", "Değerli Madenler"), horizontal=True)
        if ana_kategori == "Hisse / ETF / Fon":
            varlik_turu = st.selectbox("Tür", ("BİST Hisse Senedi", "ABD Hisse Senedi", "Yabancı Borsa Fonu (ETF)", "TEFAS Fonu"))
        else:
            varlik_turu = st.selectbox("Maden", ("Gram Altın (TL)", "22 Ayar Altın (TL)", "Gümüş (TL)"))

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if ana_kategori == "Hisse / ETF / Fon":
                sembol_giris = st.text_input("Sembol", "THYAO.IS").upper()
            else:
                sembol_giris = varlik_turu 
                st.info(f"Seçilen: {varlik_turu}")
        with c2: maliyet_giris = st.number_input("Alış Fiyatı", min_value=0.0, format="%.4f")
        with c3: adet_giris = st.number_input("Adet / Gram", min_value=0.0, format="%.2f")
        with c4: tarih_giris = st.date_input("Tarih", datetime.now())

        if st.button("Cüzdana Kaydet", type="primary"):
            st.session_state.portfoy.append({
                "Tarih": tarih_giris.strftime("%Y-%m-%d"), "Tür": varlik_turu,
                "Sembol": sembol_giris, "Maliyet": maliyet_giris, "Adet": adet_giris
            })
            verileri_kaydet_gsheets(st.session_state.portfoy)
            st.success("Başarıyla eklendi!")
            time.sleep(0.5)
            st.rerun()

    st.divider()

    # --- SADELEŞTİRİLMİŞ (MODERN) PORTFÖY LİSTESİ ---
    genel_toplam_yatirilan_tl = 0.0
    genel_guncel_tutar_tl = 0.0
    
    if not df_detay.empty:
        for tur in df_detay['Tür'].unique():
            st.markdown(f"#### 🔹 {tur}")
            grup = df_detay[df_detay['Tür'] == tur]
            
            # Tablo Başlıkları
            hc1, hc2, hc3, hc4 = st.columns([3, 3, 2, 2])
            hc1.markdown("<span style='color:gray; font-size:14px'><b>VARLIK / SEMBOL</b></span>", unsafe_allow_html=True)
            hc2.markdown("<span style='color:gray; font-size:14px'><b>ŞU ANKİ TUTAR</b></span>", unsafe_allow_html=True)
            hc3.markdown("<span style='color:gray; font-size:14px'><b>K/Z (%)</b></span>", unsafe_allow_html=True)
            hc4.markdown("<span style='color:gray; font-size:14px'><b>AKSİYON</b></span>", unsafe_allow_html=True)
            st.markdown("<hr style='margin-top: 5px; margin-bottom: 10px;'>", unsafe_allow_html=True)
            
            for v in grup['Varlık'].unique():
                alt = grup[grup['Varlık'] == v]
                top_adet = alt['Adet'].sum()
                
                if top_adet > 0:
                    # Hesaplamalar
                    if tur in ["ABD Hisse Senedi", "Yabancı Borsa Fonu (ETF)"]:
                        top_yat_tl = (alt['Alış (TL)'] * alt['Adet']).sum()
                        guncel_tl = alt['Güncel (TL)'].iloc[0]
                        guncel_tut_tl = guncel_tl * top_adet
                        ort_tl = (alt['Alış (USD)'] * alt['Adet']).sum() / top_adet * st.session_state.piyasa['usd']
                    else:
                        top_yat_tl = (alt['Alış (TL)'] * alt['Adet']).sum()
                        guncel_tl = alt['Güncel (TL)'].iloc[0]
                        guncel_tut_tl = guncel_tl * top_adet
                        ort_tl = top_yat_tl / top_adet
                        
                    genel_toplam_yatirilan_tl += top_yat_tl
                    genel_guncel_tutar_tl += guncel_tut_tl
                    kz_yuzde = ((guncel_tut_tl - top_yat_tl) / top_yat_tl * 100) if top_yat_tl > 0 else 0
                    
                    row_data = {
                        "Toplam Adet": top_adet,
                        "Ort. Maliyet (TL)": ort_tl,
                        "Güncel (TL)": guncel_tl,
                        "Toplam Maliyet (TL)": top_yat_tl,
                        "Toplam Tutar (TL)": guncel_tut_tl,
                        "K/Z (TL)": (guncel_tut_tl - top_yat_tl),
                        "K/Z (%)": kz_yuzde
                    }

                    # Satır Görüntüsü
                    rc1, rc2, rc3, rc4 = st.columns([3, 3, 2, 2])
                    rc1.markdown(f"<div style='padding-top:8px; font-size:18px'><b>{v}</b></div>", unsafe_allow_html=True)
                    rc2.markdown(f"<div style='padding-top:8px; font-size:17px'>{guncel_tut_tl:,.2f} ₺</div>", unsafe_allow_html=True)
                    
                    renk = "#00d084" if kz_yuzde >= 0 else "#ff6b6b"
                    ok = "▲" if kz_yuzde >= 0 else "▼"
                    rc3.markdown(f"<div style='padding-top:8px; color:{renk}; font-weight:bold; font-size:16px'>{ok} %{kz_yuzde:.2f}</div>", unsafe_allow_html=True)
                    
                    if rc4.button("🔍 İncele", key=f"detay_{v}"):
                        varlik_detayi_goster(v, alt, row_data)
                        
            st.write("") # Boşluk
            
        # GENEL TOPLAM BİLGİSİ
        st.divider()
        genel_kz = genel_guncel_tutar_tl - genel_toplam_yatirilan_tl
        genel_yuzde = (genel_kz / genel_toplam_yatirilan_tl * 100) if genel_toplam_yatirilan_tl > 0 else 0
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 Toplam Portföy Maliyeti", f"{genel_toplam_yatirilan_tl:,.2f} ₺")
        c2.metric("📈 Güncel Portföy Değeri", f"{genel_guncel_tutar_tl:,.2f} ₺")
        c3.metric("🎯 Net Kâr / Zarar", f"{genel_kz:,.2f} ₺", f"%{genel_yuzde:.2f}")

    else:
        st.info("Portföyünüz boş, hemen işlem ekleyebilirsiniz.")

# ==========================================
# EKRAN 2: ALIM DETAY (TÜM İŞLEMLER VE SİLME)
# ==========================================
elif sayfa_secimi == "🧾 Alım Detay":
    st.title("🧾 İşlem Yönetimi ve Alım Detayları")
    col_tablo, col_sil = st.columns([3, 1])
    
    with col_tablo:
        if not df_detay.empty:
            for v in df_detay['Varlık'].unique():
                st.subheader(f"🔹 {v} Tüm Alım İşlemleri")
                gosterilecek_df = df_detay[df_detay['Varlık'] == v]
                
                if 'İşlem No' in gosterilecek_df.columns:
                    gosterilecek_df = gosterilecek_df.set_index('İşlem No')
                
                cols_to_drop = [c for c in gosterilecek_df.columns if "USD" in c and gosterilecek_df[c].isnull().all()]
                gosterilecek_df = gosterilecek_df.drop(columns=cols_to_drop, errors='ignore')
                
                st.dataframe(gosterilecek_df, use_container_width=True)
                st.divider()
        else:
            st.info("Sistemde henüz kayıtlı bir işleminiz bulunmuyor.")
            
    with col_sil:
        st.subheader("🗑️ Kayıt Sil")
        st.caption("İşlemi silmek için sol tablodaki **İşlem No**'yu girin.")
        silinecek_id = st.number_input("İşlem No:", min_value=0, step=1)
        if st.button("Seçili İşlemi Sil", type="primary"):
            if len(st.session_state.portfoy) > silinecek_id:
                st.session_state.portfoy.pop(silinecek_id)
                verileri_kaydet_gsheets(st.session_state.portfoy)
                st.success("İşlem silindi!")
                time.sleep(0.5)
                st.rerun()

# ==========================================
# EKRAN 3: İZLEME LİSTESİ
# ==========================================
elif sayfa_secimi == "⭐ İzleme Listesi":
    st.title("⭐ İzleme Listesi")
    with st.form("izleme_formu"):
        col_l1, col_l2, col_l3 = st.columns(3)
        with col_l1: liste_adi = st.text_input("Liste Adı (Örn: Teknoloji)").strip().title()
        with col_l2: takip_sembol = st.text_input("Sembol (Örn: NVDA)").strip().upper()
        with col_l3: takip_turu = st.selectbox("Tür", ("ABD Hisse / ETF", "BİST Hisse", "TEFAS Fonu"))
        if st.form_submit_button("Listeye Ekle", type="primary") and liste_adi and takip_sembol:
            st.session_state.izleme_listesi.append({"Liste Adi": liste_adi, "Sembol": takip_sembol, "Tur": takip_turu})
            izleme_listesini_kaydet_gsheets(st.session_state.izleme_listesi)
            st.success(f"{takip_sembol} başarıyla eklendi!")
            st.rerun()
            
    st.divider()
    if len(st.session_state.izleme_listesi) > 0:
        df_izleme = pd.DataFrame(st.session_state.izleme_listesi)
        for l_adi in df_izleme['Liste Adi'].unique():
            st.subheader(f"📂 {l_adi}")
            grup = df_izleme[df_izleme['Liste Adi'] == l_adi]
            tablo_v = []
            for idx, row in grup.iterrows():
                s, t = row['Sembol'], row['Tur']
                fiyat = None
                try:
                    if t in ["ABD Hisse / ETF", "BİST Hisse"]: fiyat = float(yf.Ticker(s).history(period="1d")['Close'].iloc[-1])
                    elif t == "TEFAS Fonu": fiyat = tefas_fon_fiyati_getir(s)
                except: pass
                tablo_v.append({"Sembol": s, "Fiyat": fiyat, "Tür": t})
            st.dataframe(tablo_v, use_container_width=True)
            
            # İzleme Listesinden silme butonu
            sil_id = st.selectbox(f"Silinecek Sembol ({l_adi}):", ["Seçiniz..."] + list(grup['Sembol']), key=f"sil_{l_adi}")
            if sil_id != "Seçiniz..." and st.button(f"Kaldır ({l_adi})", key=f"btn_{l_adi}"):
                st.session_state.izleme_listesi = [item for item in st.session_state.izleme_listesi if not (item['Liste Adi'] == l_adi and item['Sembol'] == sil_id)]
                izleme_listesini_kaydet_gsheets(st.session_state.izleme_listesi)
                st.rerun()
            st.divider()
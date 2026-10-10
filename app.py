import yfinance as yf
import streamlit as st
import time
from pytefas import Crawler
from datetime import datetime, timedelta
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- GOOGLE SHEETS BAĞLANTI MOTORU ---
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
        st.error(f"İzleme listesi kayıt hatası: {e}")

# --- VERİ ÇEKME MOTORLARI ---
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
        usd_try = yf.Ticker("TRY=X").history(period="1d")['Close'].iloc[0]
        ons_altin = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[0]
        ons_gumus = yf.Ticker("SI=F").history(period="1d")['Close'].iloc[0]
        
        gram_altin_tl = (ons_altin / 31.1034768) * usd_try
        yirmiiki_ayar_tl = gram_altin_tl * 0.916
        gram_gumus_tl = (ons_gumus / 31.1034768) * usd_try
        
        return {
            "usd": float(usd_try),
            "ons_altin": float(ons_altin),
            "gram_altin": float(gram_altin_tl),
            "yirmiiki_ayar": float(yirmiiki_ayar_tl),
            "ons_gumus": float(ons_gumus),
            "gram_gumus": float(gram_gumus_tl)
        }
    except:
        return None

def degerli_maden_fiyati_getir(maden_turu, veriler):
    if not veriler:
        return None
    if maden_turu == "Gram Altın (TL)":
        return veriler["gram_altin"]
    elif maden_turu == "22 Ayar Altın (TL)":
        return veriler["yirmiiki_ayar"]
    elif maden_turu == "Gümüş (TL)":
        return veriler["gram_gumus"]
    return None

# --- ARAYÜZ ---
st.set_page_config(page_title="Portföyüm", layout="wide")
st.title("Gelişmiş Yatırım Portföyü 🚀 (Google Sheets Senkronize)")

piyasa = piyasa_verilerini_getir()
if piyasa:
    st.session_state.piyasa = piyasa
else:
    if 'piyasa' not in st.session_state:
        st.session_state.piyasa = {"usd": 35.0, "ons_altin": 2700.0, "gram_altin": 3000.0, "yirmiiki_ayar": 2750.0, "ons_gumus": 30.0, "gram_gumus": 35.0}

with st.sidebar:
    st.header("📌 Menü")
    sayfa_secimi = st.radio(
        "Gitmek istediğiniz ekranı seçin:",
        ["📈 Portföy Özeti", "📝 İşlem Geçmişi ve Yönetimi", "⭐ İzleme Listesi"]
    )

if 'portfoy' not in st.session_state:
    st.session_state.portfoy = verileri_yukle_gsheets()
    
if 'izleme_listesi' not in st.session_state:
    st.session_state.izleme_listesi = izleme_listesini_yukle_gsheets()

if 'canli_fiyatlar' not in st.session_state:
    st.session_state.canli_fiyatlar = {}

# --- PORTFÖY HESAPLAMA MOTORU ---
detayli_tablo = []
if len(st.session_state.portfoy) > 0:
    for kalem in st.session_state.portfoy:
        sembol = str(kalem.get("Sembol", ""))
        tur = str(kalem.get("Tür", ""))
        
        if sembol and sembol not in st.session_state.canli_fiyatlar:
            fiyat = None
            if tur in ["BİST Hisse Senedi", "ABD Hisse Senedi", "Yabancı Borsa Fonu (ETF)"]:
                try:
                    fiyat = yf.Ticker(sembol).history(period="1d")['Close'].iloc[0]
                except:
                    pass
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
        if not sembol:
            continue
        try:
            maliyet = float(kalem.get("Maliyet", 0.0))
            adet = float(kalem.get("Adet", 0.0))
        except:
            maliyet, adet = 0.0, 0.0
            
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
# EKRAN 1: İŞLEM GEÇMİŞİ
# ==========================================
if sayfa_secimi == "📝 İşlem Geçmişi ve Yönetimi":
    st.header("📝 Tüm İşlem Geçmişi ve Yönetim Paneli")
    col_tablo, col_sil = st.columns([3, 1])
    
    with col_tablo:
        if not df_detay.empty:
            st.dataframe(df_detay, use_container_width=True, height=500)
        else:
            st.info("Henüz eklenmiş bir işlem bulunmuyor.")
            
    with col_sil:
        st.subheader("🗑️ Kayıt Sil")
        silinecek_id = st.number_input("İşlem No:", min_value=0, max_value=len(st.session_state.portfoy)-1 if len(st.session_state.portfoy)>0 else 0, step=1)
        if st.button("Seçili İşlemi Sil", type="primary"):
            if len(st.session_state.portfoy) > silinecek_id:
                silinen = st.session_state.portfoy.pop(silinecek_id)
                verileri_kaydet_gsheets(st.session_state.portfoy)
                st.success(f"{silinen.get('Sembol')} silindi!")
                time.sleep(0.5)
                st.rerun()

# ==========================================
# EKRAN 2: İZLEME LİSTESİ
# ==========================================
elif sayfa_secimi == "⭐ İzleme Listesi":
    st.header("⭐ Hisse ve Varlık İzleme Listeleri")
    
    with st.form("izleme_formu"):
        col_l1, col_l2, col_l3 = st.columns(3)
        with col_l1:
            liste_adi = st.text_input("İzleme Listesi Adı").strip().title()
        with col_l2:
            takip_sembol = st.text_input("Sembol / Kod (Örn: NVDA)").strip().upper()
        with col_l3:
            takip_turu = st.selectbox("Tür", ("ABD Hisse / ETF", "BİST Hisse", "TEFAS Fonu"))
            
        ekle_btn = st.form_submit_button("Listeye Ekle", type="primary")
        if ekle_btn and liste_adi and takip_sembol:
            st.session_state.izleme_listesi.append({
                "Liste Adi": liste_adi,
                "Sembol": takip_sembol,
                "Tur": takip_turu
            })
            izleme_listesini_kaydet_gsheets(st.session_state.izleme_listesi)
            st.success("Eklendi!")
            st.rerun()

    st.divider()
    if len(st.session_state.izleme_listesi) > 0:
        df_izleme = pd.DataFrame(st.session_state.izleme_listesi)
        for l_adi in df_izleme['Liste Adi'].unique():
            st.subheader(f"📂 {l_adi} Listesi")
            grup = df_izleme[df_izleme['Liste Adi'] == l_adi]
            tablo_v = []
            for idx, row in grup.iterrows():
                s, t = row['Sembol'], row['Tur']
                fiyat = None
                try:
                    if t in ["ABD Hisse / ETF", "BİST Hisse"]:
                        fiyat = float(yf.Ticker(s).history(period="1d")['Close'].iloc[-1])
                    elif t == "TEFAS Fonu":
                        fiyat = tefas_fon_fiyati_getir(s)
                except:
                    pass
                tablo_v.append({"ID": idx, "Sembol": s, "Fiyat": fiyat})
            st.dataframe(tablo_v)
            st.divider()

# ==========================================
# EKRAN 3: PORTFÖY ÖZETİ
# ==========================================
elif sayfa_secimi == "📈 Portföy Özeti":
    p = st.session_state.piyasa
    st.markdown(f"> 💵 **USD/TRY:** {p['usd']:.2f} ₺ | 🥇 **Altın Ons:** ${p['ons_altin']:.2f} | 🟡 **Gram Altın:** {p['gram_altin']:.2f} ₺ | ✨ **22 Ayar:** {p['yirmiiki_ayar']:.2f} ₺ | 🥈 **Gümüş Ons:** ${p['ons_gumus']:.2f} | ⚪ **Gümüş (TL):** {p['gram_gumus']:.2f} ₺")

    with st.expander("➕ Yeni Varlık Ekle (Alım Yap)", expanded=False):
        ana_kategori = st.radio("Kategori", ("Hisse / ETF / Fon", "Değerli Madenler"), horizontal=True)
        if ana_kategori == "Hisse / ETF / Fon":
            varlik_turu = st.selectbox("Tür", ("BİST Hisse Senedi", "ABD Hisse Senedi", "Yabancı Borsa Fonu (ETF)", "TEFAS Fonu"))
        else:
            varlik_turu = st.selectbox("Maden", ("Gram Altın (TL)", "22 Ayar Altın (TL)", "Gümüş (TL)"))

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if ana_kategori == "Hisse / ETF / Fon":
                sembol_giris = st.text_input("Sembol", "AAPL" if "ABD" in varlik_turu else "THYAO.IS").upper()
            else:
                sembol_giris = varlik_turu 
                st.info(f"Seçilen Maden: {varlik_turu}")
        with c2:
            maliyet_giris = st.number_input("Alış Fiyatı", min_value=0.0, format="%.4f")
        with c3:
            adet_giris = st.number_input("Adet / Gram", min_value=0.0, format="%.2f")
        with c4:
            tarih_giris = st.date_input("Tarih", datetime.now())

        if st.button("Portföye Kaydet", type="primary"):
            st.session_state.portfoy.append({
                "Tarih": tarih_giris.strftime("%Y-%m-%d"),
                "Tür": varlik_turu,
                "Sembol": sembol_giris,
                "Maliyet": maliyet_giris,
                "Adet": adet_giris
            })
            verileri_kaydet_gsheets(st.session_state.portfoy)
            st.success("Google E-Tabloya kaydedildi!")
            time.sleep(0.5)
            st.rerun()

    st.divider()
    st.header("📊 Konsolide Portföy Özeti")
    
    genel_toplam_yatirilan_tl = 0.0
    genel_guncel_tutar_tl = 0.0
    
    if not df_detay.empty:
        for tur in df_detay['Tür'].unique():
            st.subheader(f"🔹 {tur}")
            grup = df_detay[df_detay['Tür'] == tur]
            ozet = []
            for v in grup['Varlık'].unique():
                alt = grup[grup['Varlık'] == v]
                top_adet = alt['Adet'].sum()
                if top_adet > 0:
                    if tur in ["ABD Hisse Senedi", "Yabancı Borsa Fonu (ETF)"]:
                        top_yat_usd = (alt['Alış (USD)'] * alt['Adet']).sum()
                        ort_usd = top_yat_usd / top_adet
                        ort_tl = ort_usd * st.session_state.piyasa['usd']
                        guncel_usd = alt['Güncel (USD)'].iloc[0]
                        guncel_tl = alt['Güncel (TL)'].iloc[0]
                        top_yat_tl = (alt['Alış (TL)'] * alt['Adet']).sum()
                        guncel_tut_tl = guncel_tl * top_adet
                        genel_toplam_yatirilan_tl += top_yat_tl
                        genel_guncel_tutar_tl += guncel_tut_tl
                        kz_yuzde = ((guncel_tut_tl - top_yat_tl) / top_yat_tl * 100) if top_yat_tl > 0 else 0
                        
                        ozet.append({
                            "Varlık": v, "Toplam Adet": top_adet,
                            "Ort. Maliyet (USD)": round(ort_usd, 2), "Güncel (USD)": round(guncel_usd, 2),
                            "Toplam Maliyet (TL)": round(top_yat_tl, 2), "Toplam Tutar (TL)": round(guncel_tut_tl, 2),
                            "K/Z (%)": f"%{kz_yuzde:.2f}"
                        })
                    else:
                        top_yat_tl = (alt['Alış (TL)'] * alt['Adet']).sum()
                        ort_tl = top_yat_tl / top_adet
                        guncel_tl = alt['Güncel (TL)'].iloc[0]
                        guncel_tut_tl = guncel_tl * top_adet
                        genel_toplam_yatirilan_tl += top_yat_tl
                        genel_guncel_tutar_tl += guncel_tut_tl
                        kz_yuzde = ((guncel_tut_tl - top_yat_tl) / top_yat_tl * 100) if top_yat_tl > 0 else 0
                        
                        ozet.append({
                            "Varlık": v, "Toplam Adet": top_adet,
                            "Ort. Maliyet (TL)": round(ort_tl, 4), "Güncel (TL)": round(guncel_tl, 4),
                            "Toplam Maliyet (TL)": round(top_yat_tl, 2), "Toplam Tutar (TL)": round(guncel_tut_tl, 2),
                            "K/Z (%)": f"%{kz_yuzde:.2f}"
                        })
            st.dataframe(ozet, use_container_width=True)

        st.divider()
        genel_kz = genel_guncel_tutar_tl - genel_toplam_yatirilan_tl
        genel_yuzde = (genel_kz / genel_toplam_yatirilan_tl * 100) if genel_toplam_yatirilan_tl > 0 else 0
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 Yatırılan", f"{genel_toplam_yatirilan_tl:,.2f} ₺")
        c2.metric("📈 Güncel", f"{genel_guncel_tutar_tl:,.2f} ₺")
        c3.metric("🎯 Kâr / Zarar", f"{genel_kz:,.2f} ₺", f"{genel_yuzde:,.2f}%")
    else:
        st.info("Portföyünüz boş.")
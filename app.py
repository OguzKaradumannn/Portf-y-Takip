import yfinance as yf
import streamlit as st
import time
from pytefas import Crawler
from datetime import datetime, timedelta
import pandas as pd
import os

# --- VERİTABANI (KAYIT) SİSTEMİ ---
DOSYA_ADI = "portfoyum.csv"

def verileri_yukle():
    if os.path.exists(DOSYA_ADI):
        return pd.read_csv(DOSYA_ADI).to_dict('records')
    return []

def verileri_kaydet(portfoy_listesi):
    df = pd.DataFrame(portfoy_listesi)
    df.to_csv(DOSYA_ADI, index=False)

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
                fiyat = float(fon_verisi.iloc[0]['price'])
                return fiyat
        return None
    except:
        return None

def piyasa_verilerini_getir():
    """USD kuru, Altın/Gümüş ons ve gram fiyatlarını anlık çeker"""
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

# --- ARAYÜZ (FRONTEND) VE HAFIZA ---

st.set_page_config(page_title="Portföyüm", layout="wide")
st.title("Gelişmiş Yatırım Portföyü 🚀")

# Piyasa verilerini çek ve session'a kaydet
piyasa = piyasa_verilerini_getir()
if piyasa:
    st.session_state.piyasa = piyasa
else:
    if 'piyasa' not in st.session_state:
        st.session_state.piyasa = {"usd": 35.0, "ons_altin": 2700.0, "gram_altin": 3000.0, "yirmiiki_ayar": 2750.0, "ons_gumus": 30.0, "gram_gumus": 35.0}

# Üst Panel: Canlı Kurlar ve Maden Fiyatları
p = st.session_state.piyasa
st.markdown(f"""
> 💵 **USD/TRY:** {p['usd']:.2f} ₺ | 🥇 **Altın Ons:** ${p['ons_altin']:.2f} | 🟡 **Gram Altın:** {p['gram_altin']:.2f} ₺ | ✨ **22 Ayar:** {p['yirmiiki_ayar']:.2f} ₺ | 🥈 **Gümüş Ons:** ${p['ons_gumus']:.2f} | ⚪ **Gümüş (TL):** {p['gram_gumus']:.2f} ₺
""")

if 'portfoy' not in st.session_state:
    st.session_state.portfoy = verileri_yukle()
    
if 'canli_fiyatlar' not in st.session_state:
    st.session_state.canli_fiyatlar = {}

# --- SOL MENÜ (İstenmeyen yazı kaldırıldı) ---
with st.sidebar:
    st.header("📌 Menü")
    sayfa_secimi = st.radio(
        "Gitmek istediğiniz ekranı seçin:",
        ["📈 Portföy Özeti", "📝 İşlem Geçmişi ve Yönetimi"]
    )

# --- YENİ VARLIK EKLEME ---
with st.expander("➕ Yeni Varlık Ekle (Alım Yap)", expanded=False):
    ana_kategori = st.radio(
        "Ne eklemek istiyorsunuz?", 
        ("Hisse / ETF / Fon", "Değerli Madenler"),
        horizontal=True
    )

    if ana_kategori == "Hisse / ETF / Fon":
        varlik_turu = st.selectbox(
            "Tür Seçin:",
            ("BİST Hisse Senedi", "ABD Hisse Senedi", "Yabancı Borsa Fonu (ETF)", "TEFAS Fonu")
        )
    else:
        varlik_turu = st.selectbox(
            "Değerli Maden Seçin:",
            ("Gram Altın (TL)", "22 Ayar Altın (TL)", "Gümüş (TL)")
        )

    kolon1, kolon2, kolon3, kolon4 = st.columns(4)

    with kolon1:
        if varlik_turu == "BİST Hisse Senedi":
            sembol_giris = st.text_input("Sembol", "THYAO.IS").upper()
        elif varlik_turu == "ABD Hisse Senedi":
             sembol_giris = st.text_input("Sembol", "AAPL").upper()
             st.caption("Alış Fiyatı: USD")
        elif varlik_turu == "Yabancı Borsa Fonu (ETF)":
             sembol_giris = st.text_input("Sembol", "FDVV").upper()
             st.caption("Alış Fiyatı: USD")
        elif varlik_turu == "TEFAS Fonu":
            sembol_giris = st.text_input("Fon Kodu", "AFT").upper()
        else:
            sembol_giris = varlik_turu
            st.write(f"Seçilen: {varlik_turu}")

    with kolon2:
        maliyet_giris = st.number_input("Alış Fiyatınız", min_value=0.0, format="%.4f")
    with kolon3:
        adet_giris = st.number_input("Adet / Gram", min_value=0.0, format="%.2f")
    with kolon4:
        tarih_giris = st.date_input("Alım Tarihi", datetime.now())

    if st.button("Portföye Kaydet", type="primary"):
        yeni_islem = {
            "Tarih": tarih_giris.strftime("%Y-%m-%d"),
            "Tür": varlik_turu,
            "Sembol": sembol_giris,
            "Maliyet": maliyet_giris,
            "Adet": adet_giris
        }
        st.session_state.portfoy.append(yeni_islem)
        verileri_kaydet(st.session_state.portfoy)
        st.success(f"{sembol_giris} portföye kalıcı olarak eklendi!")
        time.sleep(0.5) 
        st.rerun() 

st.divider()

# --- PORTFÖY HESAPLAMA MOTORU ---

if len(st.session_state.portfoy) > 0:
    detayli_tablo = []
    
    for kalem in st.session_state.portfoy:
        sembol = kalem["Sembol"]
        tur = kalem["Tür"]
        
        if sembol not in st.session_state.canli_fiyatlar:
            fiyat = None
            if tur in ["BİST Hisse Senedi", "ABD Hisse Senedi", "Yabancı Borsa Fonu (ETF)"]:
                try:
                    fiyat = yf.Ticker(sembol).history(period="1d")['Close'].iloc[0]
                except:
                    pass
            elif tur == "TEFAS Fonu":
                fiyat = tefas_fon_fiyati_getir(sembol)
            elif tur in ["Gram Altın (TL)", "22 Ayar Altın (TL)", "Gümüş (TL)"]:
                fiyat = degerli_maden_fiyati_getir(tur, st.session_state.piyasa)
            
            st.session_state.canli_fiyatlar[sembol] = fiyat
            
    for i, kalem in enumerate(st.session_state.portfoy):
        tarih = kalem.get("Tarih", "-")
        tur = kalem["Tür"]
        sembol = kalem["Sembol"]
        maliyet = kalem["Maliyet"]
        adet = kalem["Adet"]
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
    # İŞLEM GEÇMİŞİ EKRANI
    # ==========================================
    if sayfa_secimi == "📝 İşlem Geçmişi ve Yönetimi":
        st.header("📝 Tüm İşlem Geçmişi ve Yönetim Paneli")
        col_tablo, col_sil = st.columns([3, 1])
        
        with col_tablo:
            if not df_detay.empty:
                st.dataframe(df_detay, use_container_width=True, height=500)
                
        with col_sil:
            st.subheader("🗑️ Kayıt Sil")
            st.caption("Tablodaki **İşlem No** numarasını girerek kaydı silebilirsiniz.")
            silinecek_id = st.number_input("İşlem No:", min_value=0, max_value=len(st.session_state.portfoy)-1 if len(st.session_state.portfoy)>0 else 0, step=1)
            if st.button("Seçili İşlemi Sil", type="primary"):
                if len(st.session_state.portfoy) > silinecek_id:
                    silinen = st.session_state.portfoy.pop(silinecek_id)
                    verileri_kaydet(st.session_state.portfoy)
                    st.success(f"{silinen['Sembol']} başarıyla silindi!")
                    time.sleep(0.5)
                    st.rerun()

    # ==========================================
    # KONSOLİDE PORTFÖY ÖZETİ (ANA EKRAN)
    # ==========================================
    elif sayfa_secimi == "📈 Portföy Özeti":
        genel_toplam_yatirilan_tl = 0.0
        genel_guncel_tutar_tl = 0.0
        
        st.header("📊 Konsolide Portföy Özeti")
        
        if not df_detay.empty:
            varlik_turleri = df_detay['Tür'].unique()
            
            for tur in varlik_turleri:
                st.subheader(f"🔹 {tur}")
                grup = df_detay[df_detay['Tür'] == tur]
                varliklar = grup['Varlık'].unique()
                ozet_tablo = []
                
                for v in varliklar:
                    alt_grup = grup[grup['Varlık'] == v]
                    toplam_adet = alt_grup['Adet'].sum()
                    
                    if toplam_adet > 0:
                        if tur in ["ABD Hisse Senedi", "Yabancı Borsa Fonu (ETF)"]:
                            toplam_yatirilan_usd = (alt_grup['Alış (USD)'] * alt_grup['Adet']).sum()
                            ort_maliyet_usd = toplam_yatirilan_usd / toplam_adet
                            ort_maliyet_tl = ort_maliyet_usd * st.session_state.piyasa['usd']
                            guncel_fiyat_usd = alt_grup['Güncel (USD)'].iloc[0]
                            guncel_fiyat_tl = alt_grup['Güncel (TL)'].iloc[0]
                            total_kz_usd = alt_grup['K/Z (USD)'].sum()
                            total_kz_tl = alt_grup['K/Z (TL)'].sum()
                            
                            toplam_yatirilan_tl_varlik = (alt_grup['Alış (TL)'] * alt_grup['Adet']).sum()
                            guncel_tutar_tl_varlik = guncel_fiyat_tl * toplam_adet
                            
                            genel_toplam_yatirilan_tl += toplam_yatirilan_tl_varlik
                            genel_guncel_tutar_tl += guncel_tutar_tl_varlik
                            
                            toplam_maliyet_tl = ort_maliyet_tl * toplam_adet
                            kz_yuzde = ((guncel_tutar_tl_varlik - toplam_maliyet_tl) / toplam_maliyet_tl * 100) if toplam_maliyet_tl > 0 else 0
                            
                            ozet_tablo.append({
                                "Varlık": v, "Toplam Adet": toplam_adet,
                                "Ort. Maliyet (USD)": round(ort_maliyet_usd, 2), "Güncel (USD)": round(guncel_fiyat_usd, 2),
                                "Toplam Maliyet (USD)": round(toplam_yatirilan_usd, 2), "Toplam Tutar (USD)": round(guncel_fiyat_usd * toplam_adet, 2),
                                "Ort. Maliyet (TL)": round(ort_maliyet_tl, 2), "Güncel (TL)": round(guncel_fiyat_tl, 2),
                                "Toplam Maliyet (TL)": round(toplam_maliyet_tl, 2), "Toplam Tutar (TL)": round(guncel_tutar_tl_varlik, 2),
                                "Total K/Z (USD)": round(total_kz_usd, 2), "Total K/Z (TL)": round(total_kz_tl, 2), "K/Z (%)": f"%{kz_yuzde:.2f}"
                            })
                        else:
                            toplam_yatirilan_tl_varlik = (alt_grup['Alış (TL)'] * alt_grup['Adet']).sum()
                            ort_maliyet_tl = toplam_yatirilan_tl_varlik / toplam_adet
                            guncel_fiyat_tl = alt_grup['Güncel (TL)'].iloc[0]
                            total_kz_tl = alt_grup['K/Z (TL)'].sum()
                            
                            guncel_tutar_tl_varlik = guncel_fiyat_tl * toplam_adet
                            
                            genel_toplam_yatirilan_tl += toplam_yatirilan_tl_varlik
                            genel_guncel_tutar_tl += guncel_tutar_tl_varlik
                            
                            toplam_maliyet_tl = toplam_yatirilan_tl_varlik
                            kz_yuzde = ((guncel_tutar_tl_varlik - toplam_maliyet_tl) / toplam_maliyet_tl * 100) if toplam_maliyet_tl > 0 else 0
                            
                            ozet_tablo.append({
                                "Varlık": v, "Toplam Adet": toplam_adet,
                                "Ort. Maliyet (TL)": round(ort_maliyet_tl, 4), "Güncel (TL)": round(guncel_fiyat_tl, 4),
                                "Toplam Maliyet (TL)": round(toplam_maliyet_tl, 2), "Toplam Tutar (TL)": round(guncel_tutar_tl_varlik, 2),
                                "Total K/Z (TL)": round(total_kz_tl, 2), "K/Z (%)": f"%{kz_yuzde:.2f}"
                            })
                
                st.dataframe(ozet_tablo, use_container_width=True)

        # --- GENEL TOPLAM GÖSTERGESİ ---
        st.divider()
        genel_kz_tl = genel_guncel_tutar_tl - genel_toplam_yatirilan_tl
        kz_yuzde = (genel_kz_tl / genel_toplam_yatirilan_tl * 100) if genel_toplam_yatirilan_tl > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💰 Toplam Yatırılan Tutar", f"{genel_toplam_yatirilan_tl:,.2f} ₺")
        with col2:
            st.metric("📈 Şu Anki Toplam Tutar", f"{genel_guncel_tutar_tl:,.2f} ₺")
        with col3:
            st.metric("🎯 Toplam Kâr / Zarar", f"{genel_kz_tl:,.2f} ₺", f"{kz_yuzde:,.2f}%")

else:
    st.info("Portföyünüz şu an boş. Sol menüden veya üstteki 'Yeni Varlık Ekle' alanından ekleme yapabilirsiniz.")
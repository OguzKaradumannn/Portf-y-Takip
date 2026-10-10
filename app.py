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
    """CSV dosyasından kayıtlı portföyü okur"""
    if os.path.exists(DOSYA_ADI):
        return pd.read_csv(DOSYA_ADI).to_dict('records')
    return []

def verileri_kaydet(portfoy_listesi):
    """Portföyü CSV dosyasına kalıcı olarak kaydeder"""
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

def anlik_usd_kuru_getir():
    try:
        usd_try = yf.Ticker("TRY=X").history(period="1d")['Close'].iloc[0]
        return float(usd_try)
    except:
        return None

def gram_altin_fiyati_getir(usd_kuru):
    try:
        ons_altin = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[0]
        if usd_kuru:
            return (ons_altin / 31.1034768) * usd_kuru
        return None
    except:
        return None

# --- ARAYÜZ (FRONTEND) VE HAFIZA ---

st.set_page_config(page_title="Portföyüm", layout="wide")
st.title("Gelişmiş Yatırım Portföyü 🚀")

if 'guncel_usd_kuru' not in st.session_state:
    kuru_cek = anlik_usd_kuru_getir()
    st.session_state.guncel_usd_kuru = kuru_cek if kuru_cek else 35.0

st.info(f"💵 Anlık USD/TRY Kuru: **{st.session_state.guncel_usd_kuru:.4f} ₺**")

# Sayfa açıldığında verileri dosyadan yükle
if 'portfoy' not in st.session_state:
    st.session_state.portfoy = verileri_yukle()
    
if 'canli_fiyatlar' not in st.session_state:
    st.session_state.canli_fiyatlar = {}

st.subheader("Yeni Varlık Ekle")

varlik_turu = st.radio(
    "Ne eklemek istiyorsunuz?", 
    ("BİST Hisse Senedi", "ABD Hisse Senedi", "Yabancı Borsa Fonu (ETF)", "TEFAS Fonu", "Gram Altın")
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
        sembol_giris = "ALTIN_GRAM"
        st.write("Gram Altın (TL)")

with kolon2:
    maliyet_giris = st.number_input("Alış Fiyatınız", min_value=0.0, format="%.4f")
with kolon3:
    adet_giris = st.number_input("Adet", min_value=0.0, format="%.2f")
with kolon4:
    tarih_giris = st.date_input("Alım Tarihi", datetime.now())

if st.button("Portföye Ekle"):
    yeni_islem = {
        "Tarih": tarih_giris.strftime("%Y-%m-%d"),
        "Tür": varlik_turu,
        "Sembol": sembol_giris,
        "Maliyet": maliyet_giris,
        "Adet": adet_giris
    }
    st.session_state.portfoy.append(yeni_islem)
    
    # Her eklemede veritabanını (CSV) güncelle
    verileri_kaydet(st.session_state.portfoy)
    
    st.success(f"{sembol_giris} portföye kalıcı olarak eklendi!")
    time.sleep(0.5) 
    st.rerun() 

st.divider()

# --- PORTFÖY HESAPLAMA MOTORU ---

st.subheader("Güncel Durum")

# Silme özelliği için iki kolon oluştur
tablo_kolonu, silme_kolonu = st.columns([4, 1])

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
            elif tur == "Gram Altın":
                fiyat = gram_altin_fiyati_getir(st.session_state.guncel_usd_kuru)
            
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
                maliyet_tl = maliyet * st.session_state.guncel_usd_kuru
                guncel_fiyat_tl = guncel_fiyat * st.session_state.guncel_usd_kuru
                kar_zarar_usd = (guncel_fiyat - maliyet) * adet
                kar_zarar_tl = (guncel_fiyat_tl - maliyet_tl) * adet
                
                detayli_tablo.append({
                    "İşlem No": i, "Tarih": tarih, "Varlık": sembol, "Tür": tur,
                    "Alış (USD)": maliyet, "Güncel (USD)": round(guncel_fiyat, 2),
                    "Alış (TL)": round(maliyet_tl, 2), "Güncel (TL)": round(guncel_fiyat_tl, 2),
                    "Adet": adet, "K/Z (USD)": round(kar_zarar_usd, 2), "K/Z (TL)": round(kar_zarar_tl, 2)
                })
            else:
                kar_zarar_tl = (guncel_fiyat - maliyet) * adet
                detayli_tablo.append({
                    "İşlem No": i, "Tarih": tarih, "Varlık": sembol, "Tür": tur,
                    "Alış (USD)": None, "Güncel (USD)": None,
                    "Alış (TL)": maliyet, "Güncel (TL)": round(guncel_fiyat, 4),
                    "Adet": adet, "K/Z (USD)": None, "K/Z (TL)": round(kar_zarar_tl, 2)
                })

    with tablo_kolonu:
        st.markdown("#### 📊 Konsolide Portföy Özeti")
        df_detay = pd.DataFrame(detayli_tablo)
        
        if not df_detay.empty:
            ozet_tablo = []
            varliklar = df_detay['Varlık'].unique()
            
            for v in varliklar:
                grup = df_detay[df_detay['Varlık'] == v]
                tur = grup['Tür'].iloc[0]
                toplam_adet = grup['Adet'].sum()
                
                if toplam_adet > 0:
                    if tur in ["ABD Hisse Senedi", "Yabancı Borsa Fonu (ETF)"]:
                        toplam_yatirilan_usd = (grup['Alış (USD)'] * grup['Adet']).sum()
                        ort_maliyet_usd = toplam_yatirilan_usd / toplam_adet
                        ort_maliyet_tl = ort_maliyet_usd * st.session_state.guncel_usd_kuru
                        guncel_fiyat_usd = grup['Güncel (USD)'].iloc[0]
                        guncel_fiyat_tl = grup['Güncel (TL)'].iloc[0]
                        total_kz_usd = grup['K/Z (USD)'].sum()
                        total_kz_tl = grup['K/Z (TL)'].sum()
                        
                        ozet_tablo.append({
                            "Varlık": v, "Tür": tur, "Toplam Adet": toplam_adet,
                            "Ort. Maliyet (USD)": round(ort_maliyet_usd, 2), "Güncel (USD)": round(guncel_fiyat_usd, 2),
                            "Ort. Maliyet (TL)": round(ort_maliyet_tl, 2), "Güncel (TL)": round(guncel_fiyat_tl, 2),
                            "Total K/Z (USD)": round(total_kz_usd, 2), "Total K/Z (TL)": round(total_kz_tl, 2)
                        })
                    else:
                        toplam_yatirilan_tl = (grup['Alış (TL)'] * grup['Adet']).sum()
                        ort_maliyet_tl = toplam_yatirilan_tl / toplam_adet
                        guncel_fiyat_tl = grup['Güncel (TL)'].iloc[0]
                        total_kz_tl = grup['K/Z (TL)'].sum()
                        
                        ozet_tablo.append({
                            "Varlık": v, "Tür": tur, "Toplam Adet": toplam_adet,
                            "Ort. Maliyet (USD)": "-", "Güncel (USD)": "-",
                            "Ort. Maliyet (TL)": round(ort_maliyet_tl, 4), "Güncel (TL)": round(guncel_fiyat_tl, 4),
                            "Total K/Z (USD)": "-", "Total K/Z (TL)": round(total_kz_tl, 2)
                        })
                        
            st.dataframe(ozet_tablo, width=1200)
        
        st.divider()
        st.markdown("#### 📝 İşlem Geçmişi (Tarihsel Tüm Alımlar)")
        if detayli_tablo:
            st.dataframe(detayli_tablo, width=1200)

    # Yan tarafa işlemi silme modülü ekledik (hatalı kayıtları silmek için)
    with silme_kolonu:
        st.markdown("#### Kayıt Sil")
        st.caption("İşlem Geçmişi tablosundaki 'İşlem No' bilgisini girerek hatalı kaydı silebilirsiniz.")
        silinecek_id = st.number_input("İşlem No", min_value=0, max_value=len(st.session_state.portfoy)-1 if len(st.session_state.portfoy)>0 else 0, step=1)
        if st.button("İşlemi Sil", type="primary"):
            if len(st.session_state.portfoy) > silinecek_id:
                silinen = st.session_state.portfoy.pop(silinecek_id)
                verileri_kaydet(st.session_state.portfoy) # Dosyayı yeni haliyle güncelle
                st.success(f"{silinen['Sembol']} silindi.")
                time.sleep(0.5)
                st.rerun()

else:
    st.info("Portföyünüz şu an boş. Yukarıdan ekleme yapabilirsiniz.")
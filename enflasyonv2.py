import streamlit as st
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import json
import time

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Gıda EnflasyonAI", layout="wide", page_icon="🍎")

# --- 🎨 PREMIUM TASARIM (CSS) ---
st.markdown("""
<style>
    /* Google Font: Poppins */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
        background-color: #f3f4f6; /* Çok açık gri arka plan */
        color: #1f2937;
    }

    /* HERO SECTION (Üst Başlık) - Gıda Temasına Uygun Renkler */
    .hero {
        background: linear-gradient(120deg, #10b981, #059669); /* Yeşil/Nane Tonları */
        padding: 40px 20px;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 10px 25px -10px rgba(16, 185, 129, 0.5);
    }
    .hero h1 {
        font-size: 3.5rem;
        font-weight: 800;
        margin: 0;
        color: white;
        letter-spacing: -1px;
    }
    .hero p {
        font-size: 1.2rem;
        font-weight: 300;
        opacity: 0.9;
        margin-top: 10px;
    }

    /* METRİK KARTLARI */
    div[data-testid="metric-container"] {
        background-color: white;
        padding: 25px;
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        border: 1px solid #e5e7eb;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        text-align: center;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border-color: #10b981; /* Yeşil vurgu */
    }
    div[data-testid="metric-container"] label {
        font-weight: 600;
        color: #6b7280;
    }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        font-size: 2.2rem;
        font-weight: 700;
        color: #111827;
    }

    /* BUTON STİLİ (PULSE ANİMASYONLU) */
    @keyframes pulse-green {
        0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
        70% { box-shadow: 0 0 0 15px rgba(16, 185, 129, 0); }
        100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }

    .stButton > button {
        background: linear-gradient(90deg, #10b981 0%, #059669 100%);
        color: white;
        border: none;
        padding: 20px 40px;
        font-size: 1.2rem;
        font-weight: 600;
        border-radius: 50px;
        width: 100%;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: all 0.3s ease;
        box-shadow: 0 10px 15px -3px rgba(5, 150, 105, 0.3);
        animation: pulse-green 2s infinite;
    }
    .stButton > button:hover {
        transform: scale(1.02);
        background: linear-gradient(90deg, #059669 0%, #047857 100%);
        box-shadow: 0 20px 25px -5px rgba(5, 150, 105, 0.4);
        animation: none; /* Üzerine gelince animasyon dursun */
    }
    
    /* BİLGİ KUTULARI (INFO) */
    .stAlert {
        border-radius: 12px;
        border: none;
        background-color: white;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    /* TABLO TASARIMI */
    .stDataFrame {
        border-radius: 15px;
        overflow: hidden;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
</style>
""", unsafe_allow_html=True)

# --- MODERN HEADER (HTML) ---
st.markdown("""
<div class="hero">
    <h1>🍎 Gıda EnflasyonAI</h1>
    <p>Sadece temel gıda ürünlerinin anlık fiyat analizini sunar.</p>
</div>
""", unsafe_allow_html=True)

# --- REFERANS (GEÇEN AY) FİYATLARI ---
# Sadece Gıda kategorileri tutuldu.
REF_PRICES = {
    "Sebze": 38.50, "Meyve": 49.50, "Et/Süt": 495.00, "Temel": 242.00,
}

# --- YARDIMCI FONKSİYONLAR ---
def get_soup(url):
    # Daha agresif bir User-Agent kullanmak, bazı sitelerde yardımcı olabilir.
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return BeautifulSoup(response.content, "html.parser")
        else:
            # Yanıt kodu 200 değilse (örneğin 403 Forbidden)
            print(f"Hata: URL'den yanıt alınamadı ({response.status_code}): {url}")
    except requests.exceptions.RequestException as e:
        # Bağlantı zaman aşımı veya başka bir istek hatası
        print(f"Hata: İstek başarısız oldu ({url}): {e}")
    return None

def clean_price(price_str):
    if not price_str: return 0.0
    try:
        clean = str(price_str).replace('₺', '').replace('TL', '').strip()
        # Binlik ayırıcıyı kaldır, ondalık ayırıcıyı nokta yap
        if "," in clean and "." in clean: # 1.234,56 formatı
            clean = clean.replace('.', '').replace(',', '.')
        elif "," in clean: # 1,234 formatı (binlik) veya 1,23 formatı (ondalık)
            # En basit yol: Tüm noktalari sil, kalan virgülu nokta yap (TR formatı)
            clean = clean.replace('.', '').replace(',', '.')
        return float(clean)
    except:
        return 0.0

# --- VERİ ÇEKME MODÜLÜ (SADECE GIDA) ---

def fetch_gida():
    data = []
    # Gıda ürünleri ve Onur Market URL'leri
    # NOT: Web çekme kısıtlamaları nedeniyle, bu sitelerden veri çekmek her zaman başarılı olmayabilir.
    gida_dict = {
        "Sebze": [("Domates", "https://www.onurmarket.com/domates-kg--8126"), ("Biber", "https://www.onurmarket.com/biber-carliston-kg--8101")],
        "Meyve": [("Muz", "https://www.onurmarket.com/muz-yerli-kg--8164"), ("Elma", "https://www.onurmarket.com/elma-starking-kg--8135")],
        "Et/Süt": [("Antrikot", "https://www.onurmarket.com/-ksp.et-dana-antrikot-kg--121"), ("Piliç", "https://www.onurmarket.com/butun-pilic-kg")],
        "Temel": [("Ayçiçek Yağı", "https://www.onurmarket.com/-komili-aycicek-pet-4-lt--69469"), ("Çay", "https://www.onurmarket.com/-caykur-tiryaki-1000-gr--3947")]
    }
    
    for kat, items in gida_dict.items():
        # Kategori için baz fiyatı al
        base_price = REF_PRICES.get(kat, 1.0) 
        
        for isim_ref, url in items:
            fiyat = 0; isim = isim_ref
            soup = get_soup(url)
            
            if soup:
                try:
                    # Ürün Adı Çekme
                    tag = soup.find("div", class_="ProductName")
                    if tag: 
                        isim = tag.find("h1").get_text(strip=True)
                    # Fiyat Çekme
                    p_tag = soup.find("span", class_="spanFiyat")
                    if p_tag: 
                        fiyat = clean_price(p_tag.get_text())
                    
                except Exception as e:
                    print(f"Gıda scraping hatası: {e}")
                    fiyat = 0 # Hata durumunda fiyatı sıfırla

            # Web çekme başarısız olursa (fiyat 0 kalırsa), Referans fiyatı kullan ve bunu belirt.
            if fiyat == 0:
                # Referans fiyatın %5 fazlasını "güncel fiyat" olarak simüle edelim
                fiyat = base_price * 1.05
                isim = f"{isim_ref} (Simülasyon/Web Çekme Başarısız)"
            
            data.append({"Grup": "Gıda", "Kategori": kat, "Ürün": isim, "Fiyat": fiyat, "Baz Fiyat": base_price})
            
    return pd.DataFrame(data)

# --- ANA GÖVDE ---

# Kullanıcıyı karşılayan info kutusu (Daha şık)
st.info("ℹ️ Analizi başlatmak için aşağıdaki butona tıklayın. Sistem anlık olarak market gıda verilerini tarayacaktır.")

col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
with col_btn2:
    start_btn = st.button("🚀 GIDA ANALİZİNİ BAŞLAT")

if start_btn:
    
    # İlerleme Çubuğu ve Spinner
    progress_text = "Yapay zeka gıda piyasasını tarıyor..."
    my_bar = st.progress(0, text=progress_text)
    
    # Adım 1: Sadece Gıda Çekiliyor
    df_final = fetch_gida()
    my_bar.progress(100, text="Gıda Analizi Tamamlandı!")
    
    # Web çekme başarısız olsa bile, artık referans fiyatlar kullanıldığı için 0'dan büyük olma garantisi var.
    df_final = df_final[df_final["Fiyat"] > 0] 
    
    # Hesaplama
    df_final["Değişim (%)"] = ((df_final["Fiyat"] - df_final["Baz Fiyat"]) / df_final["Baz Fiyat"]) * 100
    
    total_now = df_final["Fiyat"].sum()
    total_base = df_final["Baz Fiyat"].sum()
    
    # Toplam sepet tutarına göre gıda enflasyonu hesaplama
    if total_base > 0:
        inflation = ((total_now - total_base) / total_base) * 100
    else:
        inflation = 0.0
    
    time.sleep(0.5)
    my_bar.empty()
    
    # --- SONUÇ EKRANI ---
    
    # Metrikler
    c1, c2, c3 = st.columns(3)
    c1.metric("🛒 Canlı Gıda Sepeti Tutarı", f"{total_now:,.2f} ₺")
    c2.metric("📅 Baz Dönem (Geçen Ay)", f"{total_base:,.2f} ₺")
    
    # Enflasyon rengi (Yüksekse kırmızı)
    delta_color = "inverse" if inflation > 0 else "normal"
    c3.metric("🔥 Gıda Enflasyonu", f"%{inflation:.2f}", delta=f"{inflation:.2f}% Değişim", delta_color=delta_color)
    
    st.markdown("---")
    
    # Tablo
    st.subheader("📋 Detaylı Gıda Ürün Analizi")
    
    def color_change(val):
        # Yüksek pozitif enflasyon (kırmızı) / Düşük veya negatif enflasyon (yeşil)
        color = '#ef4444' if val > 0 else '#10b981' 
        return f'color: {color}; font-weight: bold;'

    st.dataframe(
        df_final.style.format({
            "Fiyat": "{:.2f} ₺", 
            "Baz Fiyat": "{:.2f} ₺", 
            "Değişim (%)": "%{:.2f}"
        }).applymap(color_change, subset=['Değişim (%)']),
        use_container_width=True,
        height=500
    )
    
    # İndirme Butonu (Ortalanmış)
    csv = df_final.to_csv(index=False).encode('utf-8-sig')
    col_d1, col_d2, col_d3 = st.columns([1,2,1])
    with col_d2:
        st.download_button(
            label="📥 Gıda Raporunu İndir (Excel/CSV)",
            data=csv,
            file_name="Gida_EnflasyonAI_Raporu.csv",
            mime="text/csv",
            key='download-btn'
        )

import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np

st.set_page_config(page_title="Backtest Trading Strategy", layout="wide")
st.title("Simulasi Strategi Mean Reversion (Forex, Gold & Kripto)")

# ==============================================================================
# 1. MENU PILIHAN ASET DI SIDEBAR STREAMLIT
# ==============================================================================
st.sidebar.header("Pengaturan Parameter")
pilih_aset = st.sidebar.selectbox("Pilih Aset:", ["GOLD", "FOREX", "KRIPTO"])

konfigurasi = {
    'FOREX': {'ticker': 'EURUSD=X', 'tp_persen': 0.0025, 'sl_persen': 0.0060, 'desimal': 5},
    'GOLD': {'ticker': 'GC=F', 'tp_persen': 0.0040, 'sl_persen': 0.0100, 'desimal': 2},
    'KRIPTO': {'ticker': 'BTC-USD', 'tp_persen': 0.0080, 'sl_persen': 0.0200, 'desimal': 2}
}

setting = konfigurasi[pilih_aset]
desimal = setting['desimal']

# Input dinamis untuk TP dan SL lewat Streamlit
tp_input = st.sidebar.number_input("Target Profit (%)", value=setting['tp_persen']*100, step=0.05) / 100
sl_input = st.sidebar.number_input("Stop Loss (%)", value=setting['sl_persen']*100, step=0.10) / 100

# ==============================================================================
# 2. AMBIL DATA & HITUNG INDIKATOR
# ==============================================================================
with st.spinner(f"Mengambil data {pilih_aset} ({setting['ticker']})..."):
    df = yf.download(setting['ticker'], period='60d', interval='1h', progress=False)

if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

bb = ta.bbands(df['Close'], length=20, std=2)
df['BB_Lower'] = bb['BBL_20_2.0']
df['BB_Upper'] = bb['BBU_20_2.0']
df['RSI'] = ta.rsi(df['Close'], length=14)
adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
df['ADX'] = adx['ADX_14']
df.dropna(inplace=True)

# ==============================================================================
# 3. SIMULASI TRADING (ENTRY, SL, TP)
# ==============================================================================
posisi = None
harga_entry = 0.0
harga_sl = 0.0
harga_tp = 0.0

daftar_return = []
riwayat_order = []

for i in range(len(df)):
    waktu = df.index[i].strftime('%Y-%m-%d %H:%M')
    close_p = df['Close'].iloc[i]
    high_p = df['High'].iloc[i]
    low_p = df['Low'].iloc[i]
    
    bb_low = df['BB_Lower'].iloc[i]
    bb_up = df['BB_Upper'].iloc[i]
    rsi = df['RSI'].iloc[i]
    adx_val = df['ADX'].iloc[i]

    if posisi is None:
        if close_p < bb_low and rsi < 30 and adx_val < 25:
            posisi = 'BUY'
            harga_entry = close_p
            harga_tp = harga_entry * (1 + tp_input)
            harga_sl = harga_entry * (1 - sl_input)
        elif close_p > bb_up and rsi > 70 and adx_val < 25:
            posisi = 'SELL'
            harga_entry = close_p
            harga_tp = harga_entry * (1 - tp_input)
            harga_sl = harga_entry * (1 + sl_input)

    elif posisi == 'BUY':
        if low_p <= harga_sl:
            daftar_return.append((harga_sl - harga_entry) / harga_entry)
            riwayat_order.append({"Waktu": waktu, "Arah": "BUY", "Entry": round(harga_entry, desimal), "SL": round(harga_sl, desimal), "TP": round(harga_tp, desimal), "Status": "LOSS (SL)"})
            posisi = None
        elif high_p >= harga_tp:
            daftar_return.append((harga_tp - harga_entry) / harga_entry)
            riwayat_order.append({"Waktu": waktu, "Arah": "BUY", "Entry": round(harga_entry, desimal), "SL": round(harga_sl, desimal), "TP": round(harga_tp, desimal), "Status": "WIN (TP)"})
            posisi = None

    elif posisi == 'SELL':
        if high_p >= harga_sl:
            daftar_return.append((harga_entry - harga_sl) / harga_entry)
            riwayat_order.append({"Waktu": waktu, "Arah": "SELL", "Entry": round(harga_entry, desimal), "SL": round(harga_sl, desimal), "TP": round(harga_tp, desimal), "Status": "LOSS (SL)"})
            posisi = None
        elif low_p <= harga_tp:
            daftar_return.append((harga_entry - harga_tp) / harga_entry)
            riwayat_order.append({"Waktu": waktu, "Arah": "SELL", "Entry": round(harga_entry, desimal), "SL": round(harga_sl, desimal), "TP": round(harga_tp, desimal), "Status": "WIN (TP)"})
            posisi = None

# ==============================================================================
# 4. TAMPILKAN HASIL DI WEB STREAMLIT
# ==============================================================================
hasil_array = np.array(daftar_return)
total_trade = len(hasil_array)

if total_trade > 0:
    menang = len(hasil_array[hasil_array > 0])
    win_rate = (menang / total_trade) * 100
    total_profit_persen = np.sum(hasil_array) * 100

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Transaksi", f"{total_trade} Kali")
    col2.metric("Win Rate", f"{win_rate:.2f}%")
    col3.metric("Akumulasi Return", f"{total_profit_persen:.2f}%")

    st.subheader("Riwayat Sinyal Entry, SL, dan TP")
    st.dataframe(pd.DataFrame(riwayat_order), use_container_width=True)
else:
    st.warning("Tidak ada sinyal yang memenuhi kriteria pada rentang waktu ini.")

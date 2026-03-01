import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

# --- 1. 設定與試算表連結 ---
# 這裡填入您剛才複製的 Google Sheet ID
SHEET_ID = '1bXhvJ5ZKweviuq_LbnwHQPcUfNZdL5DRM-cAOG0N3NM' 
SHEET_URL = f'https://docs.google.com/spreadsheets/d/1bXhvJ5ZKweviuq_LbnwHQPcUfNZdL5DRM-cAOG0N3NM/gviz/tq?tqx=out:csv'
# 這是為了寫入資料用的簡易 Web App 連結 (之後可補強)
# 目前我們先實現「讀取」與「透過連結手動維護」

st.set_page_config(page_title="雲端股票管理", layout="wide")

# --- 2. 讀取雲端資料 ---
@st.cache_data(ttl=60) # 每分鐘自動更新一次資料
def load_data():
    try:
        df = pd.read_csv(SHEET_URL)
        return df
    except:
        return pd.DataFrame(columns=['symbol', 'name', 'type', 'date', 'qty', 'unit', 'amount', 'split_ratio'])

df_cloud = load_data()

# --- 3. 側邊欄：試算看板 (與 v15 邏輯一致) ---
with st.sidebar:
    st.header("📈 雲端回報試算")
    all_syms = sorted(df_cloud['symbol'].unique().tolist()) if not df_cloud.empty else []
    calc_sym = st.selectbox("選擇代號", options=[""] + all_syms)
    
    current_price = st.number_input("目前股價", value=0.0)
    
    if st.button("🔍 抓取股價") and calc_sym:
        ticker = f"{calc_sym}.TW" if calc_sym.isdigit() else calc_sym
        price_data = yf.Ticker(ticker).history(period="1d")
        if not price_data.empty:
            current_price = round(price_data['Close'].iloc[-1], 2)
            st.success(f"最新價: {current_price}")

    st.divider()
    
    # 統計邏輯 (紅正綠負)
    if not df_cloud.empty:
        df_target = df_cloud[df_cloud['symbol'] == calc_sym] if calc_sym else df_cloud
        sq, sc, sd, ss = 0, 0, 0, 0
        for _, r in df_target.iterrows():
            q, a, s = r['qty'], r['amount'], r['split_ratio']
            if r['type'] == "買入": sq += (q * s); sc += a
            elif r['type'] == "賣出": sq -= (q * s); ss += a
            elif r['type'] == "股息": sd += a
        
        mv = sq * current_price
        gain = (mv + sd + ss) - sc
        roi = (gain / sc * 100) if sc > 0 else 0
        
        # 顯示看板
        st.metric("持股張數", f"{sq/1000:.3f} 張")
        st.metric("總獲利 (紅正綠負)", f"${gain:,.0f}", delta=f"{roi:.2f}%", delta_color="inverse")

# --- 4. 主區域 ---
tab1, tab2 = st.tabs(["📊 數據總覽", "📜 歷史明細"])

with tab1:
    st.write("### 雲端同步狀態: ✅ 正常")
    st.dataframe(df_cloud, use_container_width=True)
    st.info("💡 提示：若要新增資料，請直接打開您的 Google 試算表 App 輸入，網頁會自動同步。")
    st.link_button("👉 開啟我的 Google 試算表", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}")

with tab2:
    st.write("### 歷史明細篩選")
    # 這裡放原本的篩選邏輯...

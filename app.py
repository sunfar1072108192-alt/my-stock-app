import streamlit as st
import pandas as pd
import yfinance as yf
import sqlite3
from datetime import datetime
import threading

# --- 1. 頁面配置 (自動適應手機與電腦) ---
st.set_page_config(page_title="股票資產管理 v16.0", layout="wide")

# --- 2. 資料庫初始化 ---
DB_PATH = "stocks_mobile.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS records 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT, name TEXT, type TEXT, date TEXT, 
                       qty REAL, unit TEXT, amount REAL, split_ratio REAL DEFAULT 1.0)''')
    conn.commit()
    conn.close()

init_db()

# --- 3. 核心功能函數 ---
def get_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM records ORDER BY date DESC, id DESC", conn)
    conn.close()
    return df

# --- 4. 側邊欄：投資回報試算 (手機端會收納在左上角選單) ---
with st.sidebar:
    st.header("📈 投資回報試算")
    
    # 從資料庫抓取已有的代號供選擇
    existing_data = get_data()
    all_symbols = sorted(existing_data['symbol'].unique().tolist()) if not existing_data.empty else []
    
    calc_sym = st.selectbox("選擇試算代號", options=[""] + all_symbols)
    
    current_price = st.number_input("目前股價", value=0.0, step=0.1)
    
    if st.button("🔍 自動抓取最新股價") and calc_sym:
        ticker_sym = f"{calc_sym}.TW" if calc_sym.isdigit() else calc_sym
        try:
            data = yf.Ticker(ticker_sym).history(period="1d")
            if not data.empty:
                current_price = round(data['Close'].iloc[-1], 2)
                st.success(f"抓取成功: {current_price}")
            else:
                st.error("抓取失敗，請手動輸入")
        except:
            st.error("網路連線異常")

    st.divider()
    
    # --- 數據看板計算 ---
    if calc_sym:
        df_target = existing_data[existing_data['symbol'] == calc_sym]
        title_prefix = "ETF" if calc_sym.startswith("00") and calc_sym.isdigit() else "個股"
        st.subheader(f"📊 {title_prefix}: {calc_sym}")
    else:
        df_target = existing_data
        st.subheader("📊 全帳戶綜合統計")

    sq, sc, sd, ss = 0, 0, 0, 0
    for _, r in df_target.iterrows():
        q, a, s = r['qty'], r['amount'], r['split_ratio']
        if r['type'] == "買入": sq += (q * s); sc += a
        elif r['type'] == "賣出": sq -= (q * s); ss += a
        elif r['type'] == "股息": sd += a

    mv = sq * current_price
    gain = (mv + sd + ss) - sc
    roi = (gain / sc * 100) if sc > 0 else 0

    # 顏色邏輯 (台股：正紅負綠)
    gain_color = "normal" if gain == 0 else "inverse" # Streamlit metric 預設綠正紅負，需反轉
    
    st.metric("持股張數", f"{sq/1000:.3f} 張")
    st.metric("當前市值", f"${mv:,.0f}")
    st.metric("總獲利", f"${gain:,.0f}", delta=f"{roi:.2f}%", delta_color=gain_color)
    st.write(f"淨成本: ${sc:,.0f} | 累計股息: ${sd:,.0f}")

# --- 5. 主區域：三欄式佈局 (在手機上會自動垂直排列) ---
tab1, tab2 = st.tabs(["📝 交易輸入", "📜 歷史明細與篩選"])

with tab1:
    st.subheader("輸入交易明細")
    with st.form("input_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            in_sym = st.text_input("代號")
            in_name = st.text_input("名稱")
            in_type = st.selectbox("類型", ["買入", "賣出", "股息"])
            in_date = st.date_input("日期", datetime.now())
        with c2:
            in_qty = st.number_input("數量", min_value=0.0)
            in_unit = st.selectbox("單位", ["張", "股"])
            in_amt = st.number_input("金額", min_value=0.0)
            in_split = st.number_input("分割倍率", value=1.0)
        
        if st.form_submit_button("儲存資料"):
            actual_qty = in_qty * 1000 if (in_unit == "張" and in_type != "股息") else in_qty
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO records (symbol, name, type, date, qty, unit, amount, split_ratio) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           (in_sym, in_name, in_type, str(in_date), actual_qty, in_unit, in_amt, in_split))
            conn.commit()
            conn.close()
            st.success("儲存成功！")
            st.rerun()

with tab2:
    st.subheader("歷史明細查詢")
    # 篩選器
    f1, f2, f3 = st.columns(3)
    with f1:
        f_sym = st.multiselect("代號篩選", all_symbols)
    with f2:
        f_type = st.multiselect("類型篩選", ["買入", "賣出", "股息"])
    
    display_df = existing_data.copy()
    if f_sym:
        display_df = display_df[display_df['symbol'].isin(f_sym)]
    if f_type:
        display_df = display_df[display_df['type'].isin(f_type)]
    
    # 格式化顯示
    st.dataframe(display_df.drop(columns=['id']), use_container_width=True)
    
    # 匯入匯出
    c_exp, c_imp = st.columns(2)
    with c_exp:
        csv = display_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 匯出 CSV 備份", data=csv, file_name="stock_backup.csv")
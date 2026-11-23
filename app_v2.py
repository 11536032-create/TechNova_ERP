import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# 系統設定 (加上 Icon 與寬螢幕)
st.set_page_config(page_title="TechNova ERP Pro", page_icon="🏢", layout="wide")

# 輔助函數：讀取資料庫
def get_data(query):
    with sqlite3.connect('erp_system_v2.db') as conn:
        df = pd.read_sql_query(query, conn)
    return df

# 側邊欄設計
st.sidebar.title("🏢 TechNova ERP")
st.sidebar.markdown("---")
menu = ["📊 總覽儀表板 (Dashboard)", "👥 人資管理 (HR)", "💰 財會管理 (Finance)", "📈 行銷業務 (Marketing)", "⚙️ 生產製造 (Production)"]
choice = st.sidebar.radio("請選擇模組：", menu)
st.sidebar.markdown("---")
st.sidebar.info("🎓 2026 期末專題報告\n\n開發者：[您的姓名]")

if choice == "📊 總覽儀表板 (Dashboard)":
    st.title("📊 企業營運總覽儀表板")
    st.markdown("快速掌握 TechNova 智能辦公設備公司即時營運狀況。")
    
    # 頂部四個關鍵指標 (KPIs)
    col1, col2, col3, col4 = st.columns(4)
    df_fin = get_data("SELECT type, amount FROM transactions")
    revenue = df_fin[df_fin['type'] == '收入']['amount'].sum()
    expense = df_fin[df_fin['type'] == '支出']['amount'].sum()
    net_income = revenue - expense
    emp_count = get_data("SELECT COUNT(*) as cnt FROM employees").iloc[0]['cnt']
    low_stock = get_data("SELECT COUNT(*) as cnt FROM products WHERE stock_quantity < safe_stock").iloc[0]['cnt']

    col1.metric("總營收", f"${revenue:,.0f}", "本季累計")
    col2.metric("公司淨利", f"${net_income:,.0f}", f"{'盈利' if net_income > 0 else '虧損'}")
    col3.metric("員工總數", f"{emp_count} 人")
    col4.metric("庫存警告", f"{low_stock} 項", "-需補貨", delta_color="inverse")

    st.markdown("---")
    
    # 放置兩個圖表並排
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📈 近期銷售趨勢")
        df_sales = get_data("SELECT sale_date, revenue FROM sales ORDER BY sale_date")
        if not df_sales.empty:
            df_sales_group = df_sales.groupby('sale_date').sum().reset_index()
            df_sales_group.set_index('sale_date', inplace=True)
            st.line_chart(df_sales_group)
    
    with c2:
        st.subheader("👥 各部門人數佔比")
        df_dept = get_data("SELECT department, COUNT(*) as 人數 FROM employees GROUP BY department")
        df_dept.set_index('department', inplace=True)
        st.bar_chart(df_dept)

elif choice == "👥 人資管理 (HR)":
    st.title("👥 人資管理模組 (HR)")
    tab1, tab2 = st.tabs(["📋 員工名冊", "➕ 新增員工"])
    
    with tab1:
        df_emp = get_data("SELECT emp_id as 編號, name as 姓名, department as 部門, role as 職稱, salary as 月薪, join_date as 到職日 FROM employees")
        st.dataframe(df_emp, use_container_width=True)
        
        # 部門薪資統計圖
        st.markdown("**各部門薪資總額統計**")
        df_salary = get_data("SELECT department, sum(salary) as total_salary FROM employees GROUP BY department")
        df_salary.set_index('department', inplace=True)
        st.bar_chart(df_salary)

    with tab2:
        st.subheader("辦理新進員工入職")
        with st.form("add_emp_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            name = col1.text_input("員工姓名")
            dept = col1.selectbox("所屬部門", ["行銷部", "生產部", "財會部", "人資部", "資訊部"])
            role = col2.text_input("職稱 (例如: 專員、經理)")
            salary = col2.number_input("核定月薪", min_value=27470, step=1000) # 用 2024 台灣基本薪資作為下限
            
            submitted = st.form_submit_button("✅ 確認建檔")
            if submitted and name and role:
                today = datetime.now().strftime('%Y-%m-%d')
                with sqlite3.connect('erp_system_v2.db') as conn:
                    conn.execute("INSERT INTO employees (name, department, role, salary, join_date) VALUES (?, ?, ?, ?, ?)", 
                                 (name, dept, role, salary, today))
                st.success(f"🎊 {name} 已成功入職！請切換至「員工名冊」查看。")
                st.balloons() # 加入彩蛋特效

elif choice == "💰 財會管理 (Finance)":
    st.title("💰 財會管理模組 (Finance)")
    
    df_fin = get_data("SELECT trans_date as 日期, type as 收支, category as 類別, amount as 金額, description as 項目說明 FROM transactions ORDER BY trans_date DESC")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("收支分佈")
        df_pie = df_fin.groupby('收支')['金額'].sum().reset_index()
        df_pie.set_index('收支', inplace=True)
        st.bar_chart(df_pie, color=["#FF4B4B"]) # Streamlit 預設圖表
        
    with col2:
        st.subheader("帳簿明細")
        # 利用 pandas style 標色
        def color_type(val):
            color = '#e6ffed' if val == '收入' else '#ffe6e6'
            return f'background-color: {color}'
        st.dataframe(df_fin.style.map(color_type, subset=['收支']), use_container_width=True)

elif choice == "📈 行銷業務 (Marketing)":
    st.title("📈 行銷業務模組 (Marketing)")
    tab1, tab2 = st.tabs(["🛒 歷史訂單紀錄", "📝 建立新訂單"])
    
    with tab1:
        df_sales = get_data("""
            SELECT s.sale_date as 交易日期, s.sale_id as 訂單編號, s.customer_name as 客戶名稱, 
                   p.product_name as 產品, s.quantity as 數量, s.revenue as 總金額 
            FROM sales s JOIN products p ON s.product_id = p.product_id
            ORDER BY s.sale_date DESC
        """)
        st.dataframe(df_sales, use_container_width=True)
        
    with tab2:
        df_prod = get_data("SELECT product_id, product_name, unit_price FROM products")
        st.subheader("新增 B2B 客戶銷售訂單")
        
        c1, c2 = st.columns(2)
        customer = c1.text_input("客戶/企業名稱")
        prod_name = c2.selectbox("選擇銷售產品", df_prod['product_name'].tolist())
        qty = c1.number_input("訂購數量", min_value=1, step=1)
        
        # 自動計算金額
        price = df_prod[df_prod['product_name'] == prod_name].iloc[0]['unit_price']
        prod_id = int(df_prod[df_prod['product_name'] == prod_name].iloc[0]['product_id'])
        total_rev = price * qty
        c2.info(f"💰 預估訂單總額：${total_rev:,.0f}")
        
        if st.button("💾 送出訂單並扣除庫存"):
            if customer:
                today = datetime.now().strftime('%Y-%m-%d')
                with sqlite3.connect('erp_system_v2.db') as conn:
                    # 1. 新增訂單
                    conn.execute("INSERT INTO sales (product_id, customer_name, quantity, revenue, sale_date) VALUES (?, ?, ?, ?, ?)", 
                                 (prod_id, customer, qty, total_rev, today))
                    # 2. 扣除庫存
                    conn.execute("UPDATE products SET stock_quantity = stock_quantity - ? WHERE product_id = ?", (qty, prod_id))
                    # 3. 財會入帳
                    conn.execute("INSERT INTO transactions (type, category, amount, trans_date, description) VALUES (?, ?, ?, ?, ?)", 
                                 ('收入', '產品銷售', total_rev, today, f'訂單收入-{customer}'))
                st.success("✅ 訂單建立成功！系統已自動扣除庫存並將收入寫入財會帳簿。")
            else:
                st.error("⚠️ 請填寫客戶名稱")

elif choice == "⚙️ 生產製造 (Production)":
    st.title("⚙️ 生產製造模組 (Production)")
    
    # 庫存警報器
    df_prod = get_data("SELECT product_id, product_name as 產品名稱, category as 分類, stock_quantity as 當前庫存, safe_stock as 安全庫存, unit_price as 單價 FROM products")
    low_stock_df = df_prod[df_prod['當前庫存'] < df_prod['安全庫存']]
    
    if not low_stock_df.empty:
        st.warning(f"⚠️ 警告：有 {len(low_stock_df)} 項產品庫存低於安全水位，請盡速安排生產！")
        st.dataframe(low_stock_df[['產品名稱', '當前庫存', '安全庫存']], use_container_width=True)
    
    st.markdown("---")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📦 產品與庫存清單")
        st.dataframe(df_prod, use_container_width=True)
        
    with col2:
        st.subheader("🔨 建立生產工單")
        with st.form("production_form"):
            p_name = st.selectbox("選擇生產產品", df_prod['產品名稱'].tolist())
            add_qty = st.number_input("預計生產數量", min_value=10, step=10)
            cost = st.number_input("預估生產成本(總計)", min_value=1000, step=1000)
            
            if st.form_submit_button("🚀 完工入庫"):
                p_id = int(df_prod[df_prod['產品名稱'] == p_name].iloc[0]['product_id'])
                today = datetime.now().strftime('%Y-%m-%d')
                with sqlite3.connect('erp_system_v2.db') as conn:
                    # 1. 增加庫存
                    conn.execute("UPDATE products SET stock_quantity = stock_quantity + ? WHERE product_id = ?", (add_qty, p_id))
                    # 2. 財會支出 (生產成本)
                    conn.execute("INSERT INTO transactions (type, category, amount, trans_date, description) VALUES (?, ?, ?, ?, ?)", 
                                 ('支出', '生產成本', cost, today, f'工單成本-{p_name}'))
                st.success("✅ 產品已完工入庫，並記錄生產成本至財會模組！")
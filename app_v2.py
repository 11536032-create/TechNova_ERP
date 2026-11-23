import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime, timedelta

# --- 頁面設定 ---
st.set_page_config(page_title="TechNova ERP 雲端企業版", page_icon="☁️", layout="wide")

# --- 專屬 Neon 雲端資料庫連線字串 ---
DB_URL = "postgresql://neondb_owner:npg_tWDPnJ6q0cYd@ep-morning-hat-bi7uof0y-pooler.c-5.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# 建立資料庫連線
def get_conn():
    return psycopg2.connect(DB_URL)

# 讀取資料並轉為 Pandas DataFrame
def get_data(query):
    with get_conn() as conn:
        return pd.read_sql_query(query, conn)

# 自動初始化雲端資料表 (第一次連線時會自動建立結構與示範資料)
def init_cloud_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            # 1. 人資表
            cur.execute('''CREATE TABLE IF NOT EXISTS employees (
                emp_id SERIAL PRIMARY KEY,
                name VARCHAR(50) NOT NULL,
                department VARCHAR(50) NOT NULL,
                role VARCHAR(50) NOT NULL,
                salary INTEGER NOT NULL,
                join_date DATE
            )''')
            
            # 2. 產品表
            cur.execute('''CREATE TABLE IF NOT EXISTS products (
                product_id SERIAL PRIMARY KEY,
                product_name VARCHAR(100) NOT NULL,
                category VARCHAR(50) NOT NULL,
                stock_quantity INTEGER NOT NULL,
                safe_stock INTEGER NOT NULL,
                unit_price INTEGER NOT NULL
            )''')
            
            # 3. 銷售表
            cur.execute('''CREATE TABLE IF NOT EXISTS sales (
                sale_id SERIAL PRIMARY KEY,
                product_id INTEGER REFERENCES products(product_id),
                customer_name VARCHAR(100),
                quantity INTEGER,
                revenue INTEGER,
                sale_date DATE
            )''')
            
            # 4. 財會表
            cur.execute('''CREATE TABLE IF NOT EXISTS transactions (
                trans_id SERIAL PRIMARY KEY,
                type VARCHAR(20) NOT NULL,
                category VARCHAR(50) NOT NULL,
                amount INTEGER NOT NULL,
                trans_date DATE,
                description TEXT
            )''')
            
            # 檢查員工表是否為空，若為空則寫入初始示範資料
            cur.execute("SELECT COUNT(*) FROM employees")
            if cur.fetchone()[0] == 0:
                today = datetime.now().date()
                cur.executemany(
                    "INSERT INTO employees (name, department, role, salary, join_date) VALUES (%s, %s, %s, %s, %s)",
                    [
                        ('王小明', '行銷部', '行銷經理', 65000, today - timedelta(days=365)),
                        ('李大華', '生產部', '廠長', 70000, today - timedelta(days=500)),
                        ('陳美玲', '財會部', '會計師', 55000, today - timedelta(days=200)),
                        ('林建國', '生產部', '技術員', 40000, today - timedelta(days=150)),
                        ('張雅婷', '人資部', '人資專員', 45000, today - timedelta(days=100))
                    ]
                )
                cur.executemany(
                    "INSERT INTO products (product_name, category, stock_quantity, safe_stock, unit_price) VALUES (%s, %s, %s, %s, %s)",
                    [
                        ('人體工學椅 Pro', '辦公家具', 150, 50, 5000),
                        ('升降辦公桌 Max', '辦公家具', 30, 40, 12000),
                        ('無線靜音滑鼠', '電子配件', 300, 100, 800),
                        ('護眼智慧檯燈', '電子配件', 120, 50, 2500)
                    ]
                )
                for i in range(1, 5):
                    d = today - timedelta(days=i*4)
                    cur.execute("INSERT INTO sales (product_id, customer_name, quantity, revenue, sale_date) VALUES (1, %s, 10, 50000, %s)", (f'企業客戶_{i}', d))
                    cur.execute("INSERT INTO transactions (type, category, amount, trans_date, description) VALUES ('收入', '產品銷售', 50000, %s, %s)", (d, f'訂單收入-企業客戶_{i}'))
                
                cur.execute("INSERT INTO transactions (type, category, amount, trans_date, description) VALUES ('支出', '薪資發放', 275000, %s, '本月員工薪資總額')", (today,))
        conn.commit()

# 啟動時檢查並初始化雲端資料庫
try:
    init_cloud_db()
except Exception as e:
    st.error(f"雲端資料庫連線失敗，請檢查網路狀態或連線字串。錯誤訊息：{e}")
    st.stop()

# --- 側邊欄導覽 ---
st.sidebar.title("☁️ TechNova 雲端 ERP")
st.sidebar.caption("資料庫狀態：🟢 已連線至 Neon PostgreSQL")
st.sidebar.markdown("---")
menu = ["📊 總覽儀表板 (Dashboard)", "👥 人資管理 (HR)", "💰 財會管理 (Finance)", "📈 行銷業務 (Marketing)", "⚙️ 生產製造 (Production)"]
choice = st.sidebar.radio("請選擇系統模組：", menu)

# --- 1. 總覽儀表板 ---
if choice == "📊 總覽儀表板 (Dashboard)":
    st.title("📊 企業即時營運總覽")
    
    df_fin = get_data("SELECT type, amount FROM transactions")
    revenue = df_fin[df_fin['type'] == '收入']['amount'].sum() if not df_fin[df_fin['type'] == '收入'].empty else 0
    expense = df_fin[df_fin['type'] == '支出']['amount'].sum() if not df_fin[df_fin['type'] == '支出'].empty else 0
    net_income = revenue - expense
    emp_count = get_data("SELECT COUNT(*) as cnt FROM employees").iloc[0]['cnt']
    low_stock = get_data("SELECT COUNT(*) as cnt FROM products WHERE stock_quantity < safe_stock").iloc[0]['cnt']

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("總營收", f"${revenue:,.0f}")
    col2.metric("公司淨利", f"${net_income:,.0f}", f"{'盈利' if net_income >= 0 else '虧損'}")
    col3.metric("員工總數", f"{emp_count} 人")
    col4.metric("庫存警告", f"{low_stock} 項", "-需補貨", delta_color="inverse")

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📈 銷售營收趨勢")
        df_sales = get_data("SELECT sale_date, revenue FROM sales ORDER BY sale_date")
        if not df_sales.empty:
            df_sales_group = df_sales.groupby('sale_date')['revenue'].sum()
            st.line_chart(df_sales_group)
    with c2:
        st.subheader("👥 各部門人力配置")
        df_dept = get_data("SELECT department, COUNT(*) as 人數 FROM employees GROUP BY department").set_index('department')
        st.bar_chart(df_dept)

# --- 2. 人資管理 ---
elif choice == "👥 人資管理 (HR)":
    st.title("👥 人資管理模組 (HR)")
    tab1, tab2 = st.tabs(["📋 員工名冊", "➕ 新增員工"])
    
    with tab1:
        df_emp = get_data("SELECT emp_id as 編號, name as 姓名, department as 部門, role as 職稱, salary as 月薪, join_date as 到職日 FROM employees ORDER BY emp_id")
        st.dataframe(df_emp, use_container_width=True)
        
    with tab2:
        with st.form("add_emp", clear_on_submit=True):
            c1, c2 = st.columns(2)
            name = c1.text_input("員工姓名")
            dept = c1.selectbox("所屬部門", ["行銷部", "生產部", "財會部", "人資部", "資訊部"])
            role = c2.text_input("職稱")
            salary = c2.number_input("核定月薪", min_value=28590, step=1000)
            
            if st.form_submit_button("✅ 寫入雲端資料庫"):
                if name and role:
                    today = datetime.now().date()
                    with get_conn() as conn:
                        with conn.cursor() as cur:
                            cur.execute("INSERT INTO employees (name, department, role, salary, join_date) VALUES (%s, %s, %s, %s, %s)", 
                                        (name, dept, role, salary, today))
                        conn.commit()
                    st.success(f"🎊 {name} 已永久寫入雲端資料庫！")
                    st.balloons()
                else:
                    st.error("⚠️ 請完整填寫姓名與職稱！")

# --- 3. 財會管理 ---
elif choice == "💰 財會管理 (Finance)":
    st.title("💰 財會管理模組 (Finance)")
    df_fin = get_data("SELECT trans_date as 日期, type as 收支, category as 類別, amount as 金額, description as 項目說明 FROM transactions ORDER BY trans_id DESC")
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("收支結構")
        if not df_fin.empty:
            df_sum = df_fin.groupby('收支')['金額'].sum()
            st.bar_chart(df_sum)
    with c2:
        st.subheader("即時雲端帳簿")
        st.dataframe(df_fin, use_container_width=True)

# --- 4. 行銷業務 ---
elif choice == "📈 行銷業務 (Marketing)":
    st.title("📈 行銷業務模組 (Marketing)")
    tab1, tab2 = st.tabs(["🛒 歷史訂單", "📝 建立新訂單"])
    
    with tab1:
        df_sales = get_data("""
            SELECT s.sale_date as 日期, s.sale_id as 單號, s.customer_name as 客戶, 
                   p.product_name as 產品, s.quantity as 數量, s.revenue as 總金額 
            FROM sales s JOIN products p ON s.product_id = p.product_id ORDER BY s.sale_id DESC
        """)
        st.dataframe(df_sales, use_container_width=True)
        
    with tab2:
        df_prod = get_data("SELECT product_id, product_name, unit_price, stock_quantity FROM products ORDER BY product_id")
        c1, c2 = st.columns(2)
        customer = c1.text_input("客戶名稱")
        prod_name = c2.selectbox("選擇產品", df_prod['product_name'].tolist())
        
        selected_prod = df_prod[df_prod['product_name'] == prod_name].iloc[0]
        max_stock = int(selected_prod['stock_quantity'])
        
        qty = c1.number_input(f"訂購數量 (目前庫存: {max_stock})", min_value=1, max_value=max(1, max_stock), step=1)
        total_rev = int(selected_prod['unit_price']) * qty
        c2.info(f"💰 訂單總額：${total_rev:,.0f}")
        
        if st.button("💾 送出訂單 (同步更新庫存與財會)"):
            if customer and max_stock >= qty:
                today = datetime.now().date()
                p_id = int(selected_prod['product_id'])
                with get_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute("INSERT INTO sales (product_id, customer_name, quantity, revenue, sale_date) VALUES (%s, %s, %s, %s, %s)", (p_id, customer, qty, total_rev, today))
                        cur.execute("UPDATE products SET stock_quantity = stock_quantity - %s WHERE product_id = %s", (qty, p_id))
                        cur.execute("INSERT INTO transactions (type, category, amount, trans_date, description) VALUES ('收入', '產品銷售', %s, %s, %s)", (total_rev, today, f'訂單-{customer}'))
                    conn.commit()
                st.success("✅ 訂單已成立！雲端庫存已扣除，財會帳簿已入帳。")
            elif max_stock < qty:
                st.error("⚠️ 庫存不足，無法出貨！")
            else:
                st.error("⚠️ 請輸入客戶名稱！")

# --- 5. 生產製造 ---
elif choice == "⚙️ 生產製造 (Production)":
    st.title("⚙️ 生產製造模組 (Production)")
    df_prod = get_data("SELECT product_id, product_name as 產品名稱, category as 分類, stock_quantity as 當前庫存, safe_stock as 安全庫存, unit_price as 單價 FROM products ORDER BY product_id")
    
    low_stock_df = df_prod[df_prod['當前庫存'] < df_prod['安全庫存']]
    if not low_stock_df.empty:
        st.warning(f"⚠️ 警告：有 {len(low_stock_df)} 項產品低於安全庫存，請盡速排程生產！")
        st.dataframe(low_stock_df[['產品名稱', '當前庫存', '安全庫存']], use_container_width=True)
    
    st.markdown("---")
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("📦 產品庫存狀態")
        st.dataframe(df_prod, use_container_width=True)
    with c2:
        st.subheader("🔨 建立生產工單")
        with st.form("prod_form", clear_on_submit=True):
            p_name = st.selectbox("生產產品", df_prod['產品名稱'].tolist())
            add_qty = st.number_input("生產數量", min_value=10, step=10)
            cost = st.number_input("生產總成本", min_value=1000, step=1000)
            
            if st.form_submit_button("🚀 完工入庫"):
                p_id = int(df_prod[df_prod['產品名稱'] == p_name].iloc[0]['product_id'])
                today = datetime.now().date()
                with get_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute("UPDATE products SET stock_quantity = stock_quantity + %s WHERE product_id = %s", (add_qty, p_id))
                        cur.execute("INSERT INTO transactions (type, category, amount, trans_date, description) VALUES ('支出', '生產成本', %s, %s, %s)", (cost, today, f'工單成本-{p_name}'))
                    conn.commit()
                st.success("✅ 完工入庫！雲端庫存已增加，成本已計入財會支出。")
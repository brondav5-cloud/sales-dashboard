import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import io
from pathlib import Path

# ========================================
# הגדרות
# ========================================
st.set_page_config(page_title="דשבורד מכירות", page_icon="📊", layout="wide")

# סיסמה
PASSWORD = "sales2025"

# CSS
st.markdown("""
<style>
.main > div {direction: rtl; text-align: right;}
h1, h2, h3, p {direction: rtl; text-align: right;}
.stTabs [data-baseweb="tab-list"] {direction: rtl;}
</style>
""", unsafe_allow_html=True)

# ========================================
# בדיקת סיסמה
# ========================================
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.title("🔐 כניסה למערכת")
        password = st.text_input("הכנס סיסמה:", type="password")
        if st.button("כניסה"):
            if password == PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("סיסמה שגויה!")
        return False
    return True

# ========================================
# טעינת נתונים
# ========================================
@st.cache_data
def load_data():
    base_path = Path(__file__).parent
    
    with open(base_path / 'data_stores.json', 'r', encoding='utf-8') as f:
        stores = pd.DataFrame(json.load(f))
    with open(base_path / 'data_products.json', 'r', encoding='utf-8') as f:
        products = pd.DataFrame(json.load(f))
    with open(base_path / 'data_sp.json', 'r', encoding='utf-8') as f:
        sp = pd.DataFrame(json.load(f))
    
    return stores, products, sp

# ========================================
# פונקציות עזר
# ========================================
def calc_change(new, old):
    if old > 0:
        return (new - old) / old
    return 0

def calculate_status(row):
    if row['שנה1'] == 0:
        return 'חדש/ה'
    change = calc_change(row['שנה2'], row['שנה1'])
    change_6v6 = calc_change(row['6v6_H2'], row['6v6_H1']) if row['6v6_H1'] > 0 else 0
    
    if change < -0.15 and change_6v6 < -0.10:
        return 'סכנה'
    elif change > 0.05 and change_6v6 > -0.05:
        return 'צמיחה'
    elif change >= -0.05 and change <= 0.05:
        return 'יציב'
    elif change < -0.05 and change_6v6 > 0.05:
        return 'התאוששות'
    else:
        return 'שחיקה'

def format_pct(val):
    if pd.isna(val): return ""
    return f"{val:.1%}"

def format_num(val):
    if pd.isna(val): return ""
    return f"{val:,.0f}"

def create_excel(df, sheet):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as w:
        df.to_excel(w, sheet_name=sheet, index=False)
    return output.getvalue()

# ========================================
# Main
# ========================================
if not check_password():
    st.stop()

# טעינת נתונים
stores, products, sp = load_data()

# חישובים
stores['שינוי_שנתי'] = stores.apply(lambda r: calc_change(r['שנה2'], r['שנה1']), axis=1)
stores['שינוי_6v6'] = stores.apply(lambda r: calc_change(r['6v6_H2'], r['6v6_H1']), axis=1)
stores['שינוי_3v3'] = stores.apply(lambda r: calc_change(r['3v3_שנה2'], r['3v3_שנה1']), axis=1)
stores['שינוי_רבעוני'] = stores.apply(lambda r: calc_change(r['3v3_Q3'], r['3v3_Q2']), axis=1)
stores['שינוי_2v2'] = stores.apply(lambda r: calc_change(r['2v2_אחרון'], r['2v2_קודם']), axis=1)
stores['סטטוס'] = stores.apply(calculate_status, axis=1)
stores['דירוג'] = stores['שנה2'].rank(ascending=False, method='min').astype(int)

# פעילות/סגורות
active = stores[stores['2v2_אחרון'] > 0].copy()
closed = stores[stores['2v2_אחרון'] == 0].copy()

# סרגל צד
st.sidebar.title("📊 דשבורד מכירות")
st.sidebar.markdown(f"**חנויות פעילות:** {len(active)}")
st.sidebar.markdown(f"**חנויות סגורות:** {len(closed)}")
st.sidebar.markdown("---")

cities = ['הכל'] + sorted([c for c in active['עיר'].dropna().unique() if c])
sel_city = st.sidebar.selectbox("עיר", cities)

statuses = ['הכל'] + list(active['סטטוס'].unique())
sel_status = st.sidebar.selectbox("סטטוס", statuses)

filtered = active.copy()
if sel_city != 'הכל':
    filtered = filtered[filtered['עיר'] == sel_city]
if sel_status != 'הכל':
    filtered = filtered[filtered['סטטוס'] == sel_status]

# טאבים
tabs = st.tabs(["📊 דשבורד", "🏪 חנויות", "📦 מוצרים", "🔍 בחירת חנות", "🔎 בחירת מוצר", "🚫 סגורות", "📈 מגמות", "⚠️ אזעקות", "🎯 פוטנציאל"])

# ========================================
# טאב 1: דשבורד
# ========================================
with tabs[0]:
    st.title("📊 דשבורד ראשי")
    
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        total = filtered['שנה2'].sum()
        prev = filtered['שנה1'].sum()
        ch = (total-prev)/prev*100 if prev > 0 else 0
        st.metric("סה״כ מכירות", format_num(total), f"{ch:.1f}%")
    with c2:
        st.metric("חנויות פעילות", len(filtered))
    with c3:
        st.metric("חנויות סגורות", len(closed))
    with c4:
        growth = len(filtered[filtered['סטטוס'] == 'צמיחה'])
        st.metric("בצמיחה", growth)
    with c5:
        danger = len(filtered[filtered['סטטוס'].isin(['סכנה', 'שחיקה'])])
        st.metric("בסיכון", danger)
    
    st.markdown("---")
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("📊 התפלגות סטטוסים")
        status_counts = filtered['סטטוס'].value_counts()
        colors = {'צמיחה': '#28a745', 'יציב': '#17a2b8', 'שחיקה': '#ffc107', 'התאוששות': '#9c27b0', 'סכנה': '#dc3545', 'חדש/ה': '#ff9800'}
        fig = px.pie(values=status_counts.values, names=status_counts.index, color=status_counts.index, color_discrete_map=colors, hole=0.4)
        st.plotly_chart(fig, use_container_width=True)
    
    with c2:
        st.subheader("🏙️ Top 10 ערים")
        city_sales = filtered.groupby('עיר')['שנה2'].sum().nlargest(10).reset_index()
        fig = px.bar(city_sales, x='שנה2', y='עיר', orientation='h', color='שנה2', color_continuous_scale='Blues')
        fig.update_layout(yaxis={'categoryorder': 'total ascending'}, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🏆 Top 10 חנויות")
        top = filtered.nlargest(10, 'שנה2')[['שם חנות', 'עיר', 'שנה2', 'שינוי_שנתי', 'סטטוס']].copy()
        top['שינוי_שנתי'] = top['שינוי_שנתי'].apply(format_pct)
        top['שנה2'] = top['שנה2'].apply(format_num)
        st.dataframe(top, use_container_width=True, hide_index=True)
    
    with c2:
        st.subheader("⚠️ Bottom 10")
        bottom = filtered[filtered['שנה1'] > 0].nsmallest(10, 'שינוי_שנתי')[['שם חנות', 'עיר', 'שנה2', 'שינוי_שנתי', 'סטטוס']].copy()
        bottom['שינוי_שנתי'] = bottom['שינוי_שנתי'].apply(format_pct)
        bottom['שנה2'] = bottom['שנה2'].apply(format_num)
        st.dataframe(bottom, use_container_width=True, hide_index=True)

# ========================================
# טאב 2: חנויות
# ========================================
with tabs[1]:
    st.title("🏪 ניתוח חנויות - כל הנתונים")
    
    st.subheader("📊 סיכום לפי סטטוס")
    summary = filtered.groupby('סטטוס').agg({'מזהה': 'count', 'שנה1': 'sum', 'שנה2': 'sum'}).reset_index()
    summary.columns = ['סטטוס', 'כמות', 'שנה1', 'שנה2']
    st.dataframe(summary, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.subheader("📋 כל החנויות")
    
    cols = ['מזהה', 'שם חנות', 'עיר', 'שנה1', 'שנה2', 'שינוי_שנתי', '6v6_H1', '6v6_H2', 'שינוי_6v6', '3v3_שנה1', '3v3_שנה2', 'שינוי_3v3', '3v3_Q2', '3v3_Q3', 'שינוי_רבעוני', '2v2_קודם', '2v2_אחרון', 'שינוי_2v2', 'סטטוס', 'דירוג']
    display = filtered[[c for c in cols if c in filtered.columns]].copy()
    st.dataframe(display, use_container_width=True, hide_index=True, height=500)
    
    st.download_button("📥 הורד לאקסל", create_excel(filtered, 'חנויות'), "חנויות.xlsx")

# ========================================
# טאב 3: מוצרים
# ========================================
with tabs[2]:
    st.title("📦 ניתוח מוצרים")
    
    products['שינוי'] = products.apply(lambda r: calc_change(r['שנה2'], r['שנה1']), axis=1)
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🏆 Top 10 מוצרים")
        top_p = products.nlargest(10, 'שנה2')[['מוצר', 'סיווג', 'שנה2', 'שינוי']].copy()
        top_p['שינוי'] = top_p['שינוי'].apply(format_pct)
        st.dataframe(top_p, use_container_width=True, hide_index=True)
    
    with c2:
        st.subheader("📊 לפי סיווג")
        class_sales = products.groupby('סיווג')['שנה2'].sum().reset_index()
        fig = px.pie(class_sales, values='שנה2', names='סיווג', hole=0.3)
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    st.subheader("📋 כל המוצרים")
    st.dataframe(products[['מזהה', 'מוצר', 'סיווג', 'שנה1', 'שנה2', 'שינוי', 'חנויות_שנה1', 'חנויות_שנה2']], use_container_width=True, hide_index=True)

# ========================================
# טאב 4: בחירת חנות
# ========================================
with tabs[3]:
    st.title("🔍 בחירת חנות")
    
    store_opts = active.apply(lambda r: f"{r['מזהה']} - {r['שם חנות']} ({r['עיר']})", axis=1).tolist()
    sel = st.selectbox("בחר חנות:", [''] + store_opts)
    
    if sel:
        sid = int(sel.split(' - ')[0])
        info = active[active['מזהה'] == sid].iloc[0]
        
        st.subheader("📋 פרטי חנות")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("מזהה", info['מזהה'])
            st.metric("שם", info['שם חנות'])
        with c2:
            st.metric("עיר", info['עיר'] if pd.notna(info['עיר']) else '-')
            st.metric("דירוג", f"#{int(info['דירוג'])}")
        with c3:
            st.metric("שנה1", format_num(info['שנה1']))
            st.metric("שנה2", format_num(info['שנה2']))
        with c4:
            st.metric("שינוי שנתי", format_pct(info['שינוי_שנתי']))
            st.metric("סטטוס", info['סטטוס'])
        
        st.markdown("---")
        st.subheader("📊 כל המדדים")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("6v6 H1", format_num(info['6v6_H1']))
            st.metric("6v6 H2", format_num(info['6v6_H2']))
            st.metric("שינוי 6v6", format_pct(info['שינוי_6v6']))
        with c2:
            st.metric("3v3 שנה1", format_num(info['3v3_שנה1']))
            st.metric("3v3 שנה2", format_num(info['3v3_שנה2']))
            st.metric("שינוי 3v3", format_pct(info['שינוי_3v3']))
        with c3:
            st.metric("Q2", format_num(info['3v3_Q2']))
            st.metric("Q3", format_num(info['3v3_Q3']))
            st.metric("שינוי רבעוני", format_pct(info['שינוי_רבעוני']))
        with c4:
            st.metric("2v2 קודם", format_num(info['2v2_קודם']))
            st.metric("2v2 אחרון", format_num(info['2v2_אחרון']))
            st.metric("שינוי 2v2", format_pct(info['שינוי_2v2']))
        
        st.markdown("---")
        st.subheader("📦 מוצרים בחנות")
        store_prods = sp[sp['מזהה_חנות'] == sid].copy()
        store_prods['שינוי'] = store_prods.apply(lambda r: calc_change(r['שנה2'], r['שנה1']), axis=1)
        store_prods = store_prods.sort_values('שנה2', ascending=False)
        st.dataframe(store_prods[['מזהה_מוצר', 'מוצר', 'סיווג', 'שנה1', 'שנה2', 'שינוי']], use_container_width=True, hide_index=True)

# ========================================
# טאב 5: בחירת מוצר
# ========================================
with tabs[4]:
    st.title("🔎 בחירת מוצר")
    
    prod_opts = products.apply(lambda r: f"{r['מזהה']} - {r['מוצר']}", axis=1).tolist()
    sel_p = st.selectbox("בחר מוצר:", [''] + prod_opts)
    
    if sel_p:
        pid = int(sel_p.split(' - ')[0])
        pinfo = products[products['מזהה'] == pid].iloc[0]
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("מוצר", pinfo['מוצר'])
        with c2:
            st.metric("סיווג", pinfo['סיווג'] if pd.notna(pinfo['סיווג']) else '-')
        with c3:
            st.metric("מכירות שנה2", format_num(pinfo['שנה2']))
        with c4:
            ch = calc_change(pinfo['שנה2'], pinfo['שנה1'])
            st.metric("שינוי", format_pct(ch))
        
        st.markdown("---")
        st.subheader("🏪 חנויות שמוכרות")
        prod_stores = sp[sp['מזהה_מוצר'] == pid].copy()
        prod_stores = prod_stores[prod_stores['מזהה_חנות'].isin(active['מזהה'])]
        
        pen = len(prod_stores[prod_stores['שנה2'] > 0]) / len(active) * 100 if len(active) > 0 else 0
        st.info(f"📊 חדירה: **{pen:.1f}%** ({len(prod_stores[prod_stores['שנה2'] > 0])} מתוך {len(active)} חנויות)")
        
        prod_stores['שינוי'] = prod_stores.apply(lambda r: calc_change(r['שנה2'], r['שנה1']), axis=1)
        prod_stores = prod_stores.sort_values('שנה2', ascending=False)
        st.dataframe(prod_stores[['מזהה_חנות', 'שם_חנות', 'עיר', 'שנה1', 'שנה2', 'שינוי']], use_container_width=True, hide_index=True)

# ========================================
# טאב 6: חנויות סגורות
# ========================================
with tabs[5]:
    st.title("🚫 חנויות סגורות")
    
    if len(closed) > 0:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("סה״כ סגורות", len(closed))
        with c2:
            st.metric("מכירות שאבדו", format_num(closed['שנה1'].sum()))
        with c3:
            pct = len(closed) / (len(active) + len(closed)) * 100
            st.metric("אחוז מסה״כ", f"{pct:.1f}%")
        
        st.markdown("---")
        st.dataframe(closed[['מזהה', 'שם חנות', 'עיר', 'שנה1', 'שנה2']].sort_values('שנה1', ascending=False), use_container_width=True, hide_index=True)
    else:
        st.success("🎉 אין חנויות סגורות!")

# ========================================
# טאב 7: מגמות
# ========================================
with tabs[6]:
    st.title("📈 מגמות והשוואת תקופות")
    
    st.subheader("📊 מגמת מכירות")
    periods = ['שנה1', '6v6_H1', '6v6_H2', '3v3_Q2', '3v3_Q3']
    labels = ['שנה 1', 'H1 שנה2', 'H2 שנה2', 'Q2', 'Q3']
    values = [active[p].sum() for p in periods]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=labels, y=values, mode='lines+markers+text', text=[format_num(v) for v in values], textposition='top center', line=dict(width=3), marker=dict(size=12)))
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("שנה1 vs שנה2")
        comp = pd.DataFrame({'תקופה': ['שנה 1', 'שנה 2'], 'מכירות': [active['שנה1'].sum(), active['שנה2'].sum()]})
        fig = px.bar(comp, x='תקופה', y='מכירות', color='תקופה', text='מכירות')
        fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
    
    with c2:
        st.subheader("Q2 vs Q3")
        q2 = active['3v3_Q2'].sum()
        q3 = active['3v3_Q3'].sum()
        comp2 = pd.DataFrame({'תקופה': ['Q2', 'Q3'], 'מכירות': [q2, q3]})
        fig = px.bar(comp2, x='תקופה', y='מכירות', color='תקופה', text='מכירות')
        fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

# ========================================
# טאב 8: אזעקות
# ========================================
with tabs[7]:
    st.title("⚠️ אזעקות ו-Recovery")
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("🚨 אזעקות (ירידה > 15%)")
        alerts = active[active['שינוי_2v2'] < -0.15].sort_values('שינוי_2v2')
        if len(alerts) > 0:
            st.error(f"נמצאו {len(alerts)} חנויות!")
            disp = alerts[['שם חנות', 'עיר', 'שנה2', 'שינוי_2v2', 'סטטוס']].head(20).copy()
            disp['שינוי_2v2'] = disp['שינוי_2v2'].apply(lambda x: f"{x:.1%} ⚠️")
            st.dataframe(disp, use_container_width=True, hide_index=True)
        else:
            st.success("✅ אין אזעקות!")
    
    with c2:
        st.subheader("💚 Recovery")
        recovery = active[(active['סטטוס'].isin(['שחיקה', 'סכנה'])) & (active['שינוי_2v2'] > 0)].sort_values('שינוי_2v2', ascending=False)
        if len(recovery) > 0:
            st.success(f"נמצאו {len(recovery)} חנויות!")
            disp = recovery[['שם חנות', 'עיר', 'שנה2', 'שינוי_2v2', 'סטטוס']].head(20).copy()
            disp['שינוי_2v2'] = disp['שינוי_2v2'].apply(lambda x: f"{x:.1%} ↑")
            st.dataframe(disp, use_container_width=True, hide_index=True)
        else:
            st.info("אין התאוששות כרגע")

# ========================================
# טאב 9: פוטנציאל
# ========================================
with tabs[8]:
    st.title("🎯 פוטנציאל חנויות")
    
    min_pen = st.slider("סף חדירה", 0.5, 0.9, 0.7, 0.05)
    
    # חישוב חדירה
    prod_stats = sp[sp['שנה2'] > 0].groupby('מזהה_מוצר').agg({'מזהה_חנות': 'nunique', 'שנה2': 'mean'}).reset_index()
    prod_stats.columns = ['מזהה_מוצר', 'חנויות', 'ממוצע']
    prod_stats['חדירה'] = prod_stats['חנויות'] / len(active)
    
    high_pen = prod_stats[prod_stats['חדירה'] >= min_pen]
    high_pen_ids = set(high_pen['מזהה_מוצר'])
    
    store_prods = sp[sp['שנה2'] > 0].groupby('מזהה_חנות')['מזהה_מוצר'].apply(set).to_dict()
    
    pot_data = []
    for _, store in active.iterrows():
        sprods = store_prods.get(store['מזהה'], set())
        missing = high_pen_ids - sprods
        if len(missing) > 0:
            pot = sum(high_pen[high_pen['מזהה_מוצר'] == pid]['ממוצע'].values[0] for pid in missing if pid in high_pen['מזהה_מוצר'].values)
            pot_data.append({'מזהה': store['מזהה'], 'חנות': store['שם חנות'], 'עיר': store['עיר'], 'מכירות': store['שנה2'], 'מוצרים_חסרים': len(missing), 'פוטנציאל': round(pot)})
    
    pot_df = pd.DataFrame(pot_data).sort_values('פוטנציאל', ascending=False)
    
    if len(pot_df) > 0:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("חנויות", len(pot_df))
        with c2:
            st.metric("סה״כ פוטנציאל", format_num(pot_df['פוטנציאל'].sum()))
        with c3:
            st.metric("ממוצע", format_num(pot_df['פוטנציאל'].mean()))
        
        st.markdown("---")
        st.dataframe(pot_df, use_container_width=True, hide_index=True)
        st.download_button("📥 הורד", create_excel(pot_df, 'פוטנציאל'), "פוטנציאל.xlsx")
    else:
        st.info("אין חנויות עם פוטנציאל")

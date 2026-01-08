import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import io
from pathlib import Path
from fpdf import FPDF
import base64

st.set_page_config(page_title="דשבורד מכירות", page_icon="📊", layout="wide")

# ========================================
# נתוני סוכנים
# ========================================
AGENTS_DATA = {
    "יוסף": {"password": "Agen148", "stores": [67, 834, 291, 262, 685, 702, 638, 664, 1299, 1300, 1303, 1316, 1317, 1318, 1319, 1320, 1321, 1325, 1326, 1330, 1331, 1332, 1333, 1334, 1335, 1337, 1340, 1341]},
    "ניקול": {"password": "Agen148", "stores": [665, 441, 1094, 340, 1106, 1122, 1093, 62, 599, 263, 1084, 309, 624, 1227]},
}
ADMIN_PASSWORD = "admin2025"

st.markdown("""
<style>
.main > div {direction: rtl; text-align: right;}
h1, h2, h3, p {direction: rtl; text-align: right;}
div[data-testid="metric-container"] {background: #f8f9fa; border-radius: 10px; padding: 15px; border: 1px solid #e9ecef;}
.agent-header {background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); color: white; padding: 10px 20px; border-radius: 10px; margin-bottom: 20px;}
</style>
""", unsafe_allow_html=True)

# ========================================
# מערכת התחברות
# ========================================
def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user_type = None
        st.session_state.user_name = None
        st.session_state.user_stores = None
    
    if not st.session_state.logged_in:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.title("🔐 דשבורד מכירות")
            st.markdown("---")
            
            login_type = st.radio("סוג כניסה:", ["סוכן", "מנהל"], horizontal=True)
            
            if login_type == "סוכן":
                agent_name = st.selectbox("בחר סוכן:", ["בחר..."] + list(AGENTS_DATA.keys()))
                password = st.text_input("סיסמה:", type="password")
                
                if st.button("🚀 כניסה", use_container_width=True):
                    if agent_name != "בחר..." and agent_name in AGENTS_DATA:
                        if password == AGENTS_DATA[agent_name]["password"]:
                            st.session_state.logged_in = True
                            st.session_state.user_type = "agent"
                            st.session_state.user_name = agent_name
                            st.session_state.user_stores = AGENTS_DATA[agent_name]["stores"]
                            st.rerun()
                        else:
                            st.error("❌ סיסמה שגויה!")
                    else:
                        st.error("❌ בחר סוכן!")
            else:
                password = st.text_input("סיסמת מנהל:", type="password")
                if st.button("🚀 כניסה כמנהל", use_container_width=True):
                    if password == ADMIN_PASSWORD:
                        st.session_state.logged_in = True
                        st.session_state.user_type = "admin"
                        st.session_state.user_name = "מנהל"
                        st.session_state.user_stores = None
                        st.rerun()
                    else:
                        st.error("❌ סיסמה שגויה!")
        return False
    return True

@st.cache_data
def load_data():
    p = Path(__file__).parent
    with open(p/'data_stores.json', 'r', encoding='utf-8') as f:
        stores = pd.DataFrame(json.load(f))
    with open(p/'data_products.json', 'r', encoding='utf-8') as f:
        products = pd.DataFrame(json.load(f))
    with open(p/'data_sp.json', 'r', encoding='utf-8') as f:
        sp = pd.DataFrame(json.load(f))
    return stores, products, sp

def chg(new, old):
    if pd.isna(old) or old == 0:
        return 0
    return (new - old) / old

def fmt_pct(v):
    if pd.isna(v) or v == 0:
        return "0.0%"
    return f"{v:+.1%}"

def fmt_num(v):
    if pd.isna(v):
        return "0"
    return f"{v:,.0f}"

def calc_status(r, th):
    if r['שנה1'] == 0:
        return 'חדש/ה'
    c = chg(r['שנה2'], r['שנה1'])
    c6 = chg(r['6v6_H2'], r['6v6_H1'])
    if c < th['סכנה'] and c6 < th['סכנה_6v6']:
        return 'סכנה'
    elif c > th['צמיחה'] and c6 > th['צמיחה_6v6']:
        return 'צמיחה'
    elif c >= th['יציב_תחתון'] and c <= th['יציב_עליון']:
        return 'יציב'
    elif c < th['יציב_תחתון'] and c6 > 0.05:
        return 'התאוששות'
    else:
        return 'שחיקה'

def to_excel(df, sheet):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as w:
        df.to_excel(w, sheet_name=sheet, index=False)
    return out.getvalue()

def reverse_hebrew(text):
    """הפיכת טקסט עברי לתצוגה ב-PDF"""
    if pd.isna(text):
        return '-'
    return str(text)[::-1]

def create_store_pdf(store_info, store_products, missing_products):
    """יצירת PDF לחנות בודדת"""
    pdf = FPDF()
    pdf.add_page()
    
    # הוספת פונט עברי
    font_path = Path(__file__).parent / 'FreeSerif.ttf'
    if font_path.exists():
        pdf.add_font('Hebrew', '', str(font_path))
        pdf.add_font('Hebrew', 'B', str(font_path.parent / 'FreeSerifBold.ttf'))
    else:
        pdf.add_font('Hebrew', '', '/usr/share/fonts/truetype/freefont/FreeSerif.ttf')
        pdf.add_font('Hebrew', 'B', '/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf')
    
    # כותרת
    pdf.set_font('Hebrew', 'B', 24)
    pdf.cell(0, 15, reverse_hebrew("דוח חנות"), new_x='LMARGIN', new_y='NEXT', align='C')
    
    # פרטי חנות
    pdf.set_font('Hebrew', 'B', 16)
    pdf.cell(0, 10, reverse_hebrew(f"שם: {store_info['שם חנות']}"), new_x='LMARGIN', new_y='NEXT', align='R')
    
    pdf.set_font('Hebrew', '', 12)
    pdf.cell(0, 8, reverse_hebrew(f"מזהה: {store_info['מזהה']} | עיר: {store_info['עיר'] if pd.notna(store_info['עיר']) else '-'}"), new_x='LMARGIN', new_y='NEXT', align='R')
    pdf.cell(0, 8, reverse_hebrew(f"דירוג: #{int(store_info['דירוג'])} | סטטוס: {store_info['סטטוס']}"), new_x='LMARGIN', new_y='NEXT', align='R')
    
    pdf.ln(5)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    # מדדים
    pdf.set_font('Hebrew', 'B', 14)
    pdf.cell(0, 10, reverse_hebrew("מדדי מכירות"), new_x='LMARGIN', new_y='NEXT', align='R')
    
    pdf.set_font('Hebrew', '', 11)
    metrics = [
        f"שנה קודמת: {store_info['שנה1']:,.0f} | שנה נוכחית: {store_info['שנה2']:,.0f} | שינוי: {store_info['שינוי_שנתי']:+.1%}",
        f"H1: {store_info['6v6_H1']:,.0f} | H2: {store_info['6v6_H2']:,.0f} | שינוי: {store_info['שינוי_6v6']:+.1%}",
        f"Q2: {store_info['3v3_Q2']:,.0f} | Q3: {store_info['3v3_Q3']:,.0f} | שינוי: {store_info['שינוי_רבעוני']:+.1%}",
        f"2v2 קודם: {store_info['2v2_קודם']:,.0f} | 2v2 אחרון: {store_info['2v2_אחרון']:,.0f} | שינוי: {store_info['שינוי_2v2']:+.1%}",
    ]
    for m in metrics:
        pdf.cell(0, 7, reverse_hebrew(m), new_x='LMARGIN', new_y='NEXT', align='R')
    
    pdf.ln(5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    # מוצרים בחנות - Top 10
    if len(store_products) > 0:
        pdf.set_font('Hebrew', 'B', 14)
        pdf.cell(0, 10, reverse_hebrew("Top 10 מוצרים בחנות"), new_x='LMARGIN', new_y='NEXT', align='R')
        
        pdf.set_font('Hebrew', '', 10)
        top10 = store_products.nlargest(10, 'שנה2')
        for _, row in top10.iterrows():
            line = f"{row['מוצר']}: {row['שנה2']:,.0f}"
            pdf.cell(0, 6, reverse_hebrew(line), new_x='LMARGIN', new_y='NEXT', align='R')
    
    pdf.ln(5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    # מוצרים חסרים - Top 10
    if len(missing_products) > 0:
        pdf.set_font('Hebrew', 'B', 14)
        pdf.cell(0, 10, reverse_hebrew("Top 10 מוצרים חסרים (לפי מכירות כלליות)"), new_x='LMARGIN', new_y='NEXT', align='R')
        
        pdf.set_font('Hebrew', '', 10)
        for _, row in missing_products.head(10).iterrows():
            line = f"{row['מוצר']}: {row['שנה2']:,.0f} (מכירות כלליות)"
            pdf.cell(0, 6, reverse_hebrew(line), new_x='LMARGIN', new_y='NEXT', align='R')
    
    return bytes(pdf.output())

if not check_login():
    st.stop()

# כפתור התנתקות
col1, col2 = st.columns([6, 1])
with col2:
    if st.button("🚪 יציאה"):
        st.session_state.logged_in = False
        st.session_state.user_type = None
        st.session_state.user_name = None
        st.session_state.user_stores = None
        st.rerun()

# הצגת פרטי משתמש
if st.session_state.user_type == "agent":
    st.markdown(f'<div class="agent-header">👤 שלום <b>{st.session_state.user_name}</b> | החנויות שלך: <b>{len(st.session_state.user_stores)}</b> | מזהים: {st.session_state.user_stores[:5]}...</div>', unsafe_allow_html=True)
else:
    st.markdown(f'<div class="agent-header">👑 מצב מנהל - גישה לכל הנתונים</div>', unsafe_allow_html=True)

stores, products, sp = load_data()

# סרגל צד
st.sidebar.title("📊 דשבורד מכירות")
st.sidebar.markdown(f"**משתמש:** {st.session_state.user_name}")
st.sidebar.markdown("---")

st.sidebar.subheader("⚙️ הגדרות ספים")
with st.sidebar.expander("🎚️ שנה ספים"):
    th = {}
    th['צמיחה'] = st.slider("צמיחה שנתי", 0.0, 0.20, 0.05, 0.01)
    th['צמיחה_6v6'] = st.slider("צמיחה 6v6", -0.20, 0.10, -0.05, 0.01)
    th['יציב_עליון'] = th['צמיחה']
    th['יציב_תחתון'] = st.slider("יציב תחתון", -0.15, 0.0, -0.05, 0.01)
    th['סכנה'] = st.slider("סכנה שנתי", -0.30, 0.0, -0.15, 0.01)
    th['סכנה_6v6'] = st.slider("סכנה 6v6", -0.30, 0.0, -0.10, 0.01)
    th['אזעקה'] = st.slider("אזעקה 2v2", -0.30, 0.0, -0.15, 0.01)

st.sidebar.markdown("---")

# חישובים
stores['שינוי_שנתי'] = stores.apply(lambda r: chg(r['שנה2'], r['שנה1']), axis=1)
stores['שינוי_6v6'] = stores.apply(lambda r: chg(r['6v6_H2'], r['6v6_H1']), axis=1)
stores['שינוי_3v3'] = stores.apply(lambda r: chg(r['3v3_שנה2'], r['3v3_שנה1']), axis=1)
stores['שינוי_רבעוני'] = stores.apply(lambda r: chg(r['3v3_Q3'], r['3v3_Q2']), axis=1)
stores['שינוי_2v2'] = stores.apply(lambda r: chg(r['2v2_אחרון'], r['2v2_קודם']), axis=1)
stores['סטטוס'] = stores.apply(lambda r: calc_status(r, th), axis=1)
stores['דירוג'] = stores['שנה2'].rank(ascending=False, method='min').astype(int)

# סינון לפי סוכן
all_active = stores[stores['2v2_אחרון'] > 0].copy()
all_closed = stores[stores['2v2_אחרון'] == 0].copy()

if st.session_state.user_type == "agent":
    active = all_active[all_active['מזהה'].isin(st.session_state.user_stores)].copy()
    closed = all_closed[all_closed['מזהה'].isin(st.session_state.user_stores)].copy()
    sp_filtered = sp[sp['מזהה_חנות'].isin(st.session_state.user_stores)].copy()
else:
    active = all_active.copy()
    closed = all_closed.copy()
    sp_filtered = sp.copy()

# החרגת חנויות
st.sidebar.subheader("🚫 החרגת חנויות")
exclude_options = active.apply(lambda r: f"{r['מזהה']} - {r['שם חנות']}", axis=1).tolist()
excluded_stores = st.sidebar.multiselect("בחר חנויות להחרגה:", sorted(exclude_options), key="exclude_stores")
if excluded_stores:
    excluded_ids = [int(x.split(' - ')[0]) for x in excluded_stores]
    active = active[~active['מזהה'].isin(excluded_ids)].copy()
    sp_filtered = sp_filtered[~sp_filtered['מזהה_חנות'].isin(excluded_ids)].copy()
    st.sidebar.warning(f"הוחרגו {len(excluded_ids)} חנויות")

# סינונים נוספים
st.sidebar.subheader("🔍 סינונים")
cities = ['הכל'] + sorted([c for c in active['עיר'].dropna().unique() if c])
sel_city = st.sidebar.selectbox("עיר", cities)
statuses = ['הכל'] + list(active['סטטוס'].unique())
sel_status = st.sidebar.selectbox("סטטוס", statuses)

filtered = active.copy()
if sel_city != 'הכל':
    filtered = filtered[filtered['עיר'] == sel_city]
if sel_status != 'הכל':
    filtered = filtered[filtered['סטטוס'] == sel_status]

st.sidebar.markdown("---")
st.sidebar.metric("פעילות", len(active))
st.sidebar.metric("סגורות", len(closed))

# טאבים
tabs = st.tabs(["📊 דשבורד", "🏪 החנויות שלי", "📦 מוצרים", "🔍 בחירת חנות", "🔎 בחירת מוצר", "🚫 סגורות", "📈 מגמות", "⚠️ אזעקות", "🎯 פוטנציאל"])

with tabs[0]:
    st.title("📊 דשבורד ראשי")
    c1, c2, c3, c4, c5 = st.columns(5)
    total = filtered['שנה2'].sum()
    prev = filtered['שנה1'].sum()
    c1.metric("💰 מכירות", fmt_num(total), fmt_pct(chg(total, prev)))
    c2.metric("🏪 פעילות", len(filtered))
    c3.metric("🚫 סגורות", len(closed))
    c4.metric("📈 צמיחה", len(filtered[filtered['סטטוס'] == 'צמיחה']))
    c5.metric("⚠️ סיכון", len(filtered[filtered['סטטוס'].isin(['סכנה', 'שחיקה'])]))
    
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📊 סטטוסים")
        if len(filtered) > 0:
            sc = filtered['סטטוס'].value_counts()
            colors = {'צמיחה': '#28a745', 'יציב': '#17a2b8', 'שחיקה': '#ffc107', 'התאוששות': '#9c27b0', 'סכנה': '#dc3545', 'חדש/ה': '#ff9800'}
            fig = px.pie(values=sc.values, names=sc.index, color=sc.index, color_discrete_map=colors, hole=0.4)
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.subheader("🏙️ ערים")
        if len(filtered) > 0:
            filtered_with_city = filtered[filtered['עיר'].notna() & (filtered['עיר'] != '')]
            if len(filtered_with_city) > 0:
                cs = filtered_with_city.groupby('עיר')['שנה2'].sum().nlargest(10).reset_index()
                fig = px.bar(cs, x='שנה2', y='עיר', orientation='h', text=cs['שנה2'].apply(fmt_num))
                fig.update_layout(yaxis={'categoryorder': 'total ascending'})
                fig.update_traces(textposition='outside')
                st.plotly_chart(fig, use_container_width=True)

with tabs[1]:
    st.title("🏪 החנויות שלי")
    if st.session_state.user_type == "agent":
        st.info(f"📋 מציג {len(filtered)} חנויות המשויכות ל-{st.session_state.user_name}")
    
    d = filtered[['מזהה', 'שם חנות', 'עיר', 'שנה1', 'שנה2', 'שינוי_שנתי', '6v6_H1', '6v6_H2', 'שינוי_6v6', '3v3_Q2', '3v3_Q3', 'שינוי_רבעוני', '2v2_קודם', '2v2_אחרון', 'שינוי_2v2', 'סטטוס', 'דירוג']].copy()
    for c in ['שנה1', 'שנה2', '6v6_H1', '6v6_H2', '3v3_Q2', '3v3_Q3', '2v2_קודם', '2v2_אחרון']:
        d[c] = d[c].apply(fmt_num)
    for c in ['שינוי_שנתי', 'שינוי_6v6', 'שינוי_רבעוני', 'שינוי_2v2']:
        d[c] = d[c].apply(fmt_pct)
    st.dataframe(d, hide_index=True, use_container_width=True, height=600)
    st.download_button("📥 הורד", to_excel(filtered, 'חנויות'), "חנויות.xlsx")

with tabs[2]:
    st.title("📦 מוצרים")
    products['שינוי'] = products.apply(lambda r: chg(r['שנה2'], r['שנה1']), axis=1)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🏆 Top 10")
        tp = products.nlargest(10, 'שנה2')[['מוצר', 'סיווג', 'שנה2', 'שינוי']].copy()
        tp['שנה2'] = tp['שנה2'].apply(fmt_num)
        tp['שינוי'] = tp['שינוי'].apply(fmt_pct)
        st.dataframe(tp, hide_index=True, use_container_width=True)
    with c2:
        st.subheader("📊 לפי סיווג")
        cs = products.groupby('סיווג')['שנה2'].sum().reset_index()
        fig = px.pie(cs, values='שנה2', names='סיווג', hole=0.3)
        st.plotly_chart(fig, use_container_width=True)

with tabs[3]:
    st.title("🔍 בחירת חנות")
    opts = filtered.apply(lambda r: f"{r['מזהה']} - {r['שם חנות']}", axis=1).tolist()
    sel = st.selectbox("בחר:", ['בחר...'] + sorted(opts))
    if sel != 'בחר...':
        sid = int(sel.split(' - ')[0])
        info = filtered[filtered['מזהה'] == sid].iloc[0]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("מזהה", info['מזהה'])
        c1.metric("עיר", info['עיר'] if pd.notna(info['עיר']) else '-')
        c2.metric("דירוג", f"#{int(info['דירוג'])}")
        c2.metric("סטטוס", info['סטטוס'])
        c3.metric("שנה1", fmt_num(info['שנה1']))
        c3.metric("שנה2", fmt_num(info['שנה2']))
        c4.metric("שינוי שנתי", fmt_pct(info['שינוי_שנתי']))
        c4.metric("שינוי 2v2", fmt_pct(info['שינוי_2v2']))
        
        st.markdown("---")
        st.subheader("📊 כל המדדים")
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown("**H1 (דצמבר-מאי)**")
        c1.metric("H1", fmt_num(info['6v6_H1']))
        c1.metric("H2", fmt_num(info['6v6_H2']))
        c1.metric("שינוי", fmt_pct(info['שינוי_6v6']))
        c2.markdown("**H2 (יוני-נובמבר)**")
        c2.metric("שנה1", fmt_num(info['3v3_שנה1']))
        c2.metric("שנה2", fmt_num(info['3v3_שנה2']))
        c2.metric("שינוי", fmt_pct(info['שינוי_3v3']))
        c3.markdown("**רבעונים**")
        c3.metric("Q2", fmt_num(info['3v3_Q2']))
        c3.metric("Q3", fmt_num(info['3v3_Q3']))
        c3.metric("שינוי", fmt_pct(info['שינוי_רבעוני']))
        c4.markdown("**2v2**")
        c4.metric("8-9/2025", fmt_num(info['2v2_קודם']))
        c4.metric("10-11/2025", fmt_num(info['2v2_אחרון']))
        c4.metric("שינוי", fmt_pct(info['שינוי_2v2']))
        
        st.markdown("---")
        st.subheader("📦 מוצרים בחנות")
        sp2 = sp_filtered[sp_filtered['מזהה_חנות'] == sid].copy()
        
        # חישוב מוצרים חסרים
        store_product_ids = set(sp2['מזהה_מוצר'].unique())
        all_product_ids = set(products['מזהה'].unique())
        missing_ids = all_product_ids - store_product_ids
        missing_products = products[products['מזהה'].isin(missing_ids)].sort_values('שנה2', ascending=False).copy()
        
        if len(sp2) > 0:
            sp2['שינוי'] = sp2.apply(lambda r: chg(r['שנה2'], r['שנה1']), axis=1)
            sp2 = sp2.sort_values('שנה2', ascending=False)
            
            # טבלה
            d = sp2[['מוצר', 'סיווג', 'שנה1', 'שנה2', 'שינוי', '2v2_קודם', '2v2_אחרון']].copy()
            d['שנה1'] = d['שנה1'].apply(fmt_num)
            d['שנה2'] = d['שנה2'].apply(fmt_num)
            d['שינוי'] = d['שינוי'].apply(fmt_pct)
            d['2v2_קודם'] = d['2v2_קודם'].apply(fmt_num)
            d['2v2_אחרון'] = d['2v2_אחרון'].apply(fmt_num)
            st.dataframe(d, hide_index=True, use_container_width=True, height=400)
            
            # גרף Top 15
            st.subheader("📊 Top 15 מוצרים")
            top15 = sp2.nlargest(15, 'שנה2')
            fig = px.bar(top15, x='מוצר', y='שנה2', color='סיווג', text=top15['שנה2'].apply(fmt_num))
            fig.update_layout(xaxis_tickangle=-45)
            fig.update_traces(textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("לא נמצאו מוצרים")
        
        # מוצרים חסרים
        st.markdown("---")
        st.subheader("🚨 מוצרים שהחנות לא מקבלת")
        st.info(f"נמצאו {len(missing_products)} מוצרים שהחנות לא מקבלת (ממוינים לפי מכירות כלליות)")
        if len(missing_products) > 0:
            md = missing_products[['מוצר', 'סיווג', 'שנה2']].copy()
            md.columns = ['מוצר', 'סיווג', 'מכירות כלליות']
            md['מכירות כלליות'] = md['מכירות כלליות'].apply(fmt_num)
            st.dataframe(md, hide_index=True, use_container_width=True, height=300)
        
        # כפתור PDF
        st.markdown("---")
        st.subheader("📄 הורדת דוח PDF")
        if st.button("📥 צור והורד PDF", key="pdf_btn"):
            try:
                pdf_bytes = create_store_pdf(info, sp2, missing_products)
                st.download_button(
                    label="💾 לחץ להורדה",
                    data=pdf_bytes,
                    file_name=f"דוח_חנות_{info['מזהה']}_{info['שם חנות']}.pdf",
                    mime="application/pdf",
                    key="pdf_download"
                )
                st.success("✅ הדוח נוצר בהצלחה!")
            except Exception as e:
                st.error(f"❌ שגיאה ביצירת PDF: {e}")

with tabs[4]:
    st.title("🔎 בחירת מוצר")
    opts = products.apply(lambda r: f"{r['מזהה']} - {r['מוצר']}", axis=1).tolist()
    sel = st.selectbox("בחר:", ['בחר...'] + sorted(opts), key="prod")
    if sel != 'בחר...':
        pid = int(sel.split(' - ')[0])
        pinfo = products[products['מזהה'] == pid].iloc[0]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("מוצר", pinfo['מוצר'])
        c2.metric("סיווג", pinfo['סיווג'] if pd.notna(pinfo['סיווג']) else '-')
        c3.metric("מכירות", fmt_num(pinfo['שנה2']))
        c4.metric("שינוי", fmt_pct(chg(pinfo['שנה2'], pinfo['שנה1'])))
        
        st.markdown("---")
        ps = sp_filtered[sp_filtered['מזהה_מוצר'] == pid].copy()
        ps = ps[ps['מזהה_חנות'].isin(active['מזהה'])]
        if len(ps) > 0:
            selling = len(ps[ps['שנה2'] > 0])
            pen = selling / len(active) * 100 if len(active) > 0 else 0
            c1, c2, c3 = st.columns(3)
            c1.metric("חנויות מוכרות", selling)
            c2.metric("חדירה", f"{pen:.1f}%")
            c3.metric("סה״כ חנויות", len(active))
            
            ps['שינוי'] = ps.apply(lambda r: chg(r['שנה2'], r['שנה1']), axis=1)
            ps = ps.sort_values('שנה2', ascending=False)
            d = ps[['שם_חנות', 'עיר', 'שנה1', 'שנה2', 'שינוי']].copy()
            d['שנה1'] = d['שנה1'].apply(fmt_num)
            d['שנה2'] = d['שנה2'].apply(fmt_num)
            d['שינוי'] = d['שינוי'].apply(fmt_pct)
            st.dataframe(d, hide_index=True, use_container_width=True, height=400)

with tabs[5]:
    st.title("🚫 חנויות סגורות")
    if len(closed) > 0:
        c1, c2, c3 = st.columns(3)
        c1.metric("סה״כ", len(closed))
        c2.metric("מכירות שאבדו", fmt_num(closed['שנה1'].sum()))
        c3.metric("אחוז", f"{len(closed)/(len(active)+len(closed))*100:.1f}%")
        
        d = closed[['מזהה', 'שם חנות', 'עיר', 'שנה1']].sort_values('שנה1', ascending=False).copy()
        d['שנה1'] = d['שנה1'].apply(fmt_num)
        st.dataframe(d, hide_index=True, use_container_width=True)
    else:
        st.success("אין חנויות סגורות!")

with tabs[6]:
    st.title("📈 מגמות")
    if len(active) > 0:
        periods = ['שנה1', '6v6_H1', '6v6_H2', '3v3_Q2', '3v3_Q3']
        labels = ['שנה1', 'H1', 'H2', 'Q2', 'Q3']
        vals = [active[p].sum() for p in periods]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=labels, y=vals, mode='lines+markers+text', text=[fmt_num(v) for v in vals], textposition='top center', line=dict(width=4, color='#ff4b4b'), marker=dict(size=12)))
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("שנה1 vs שנה2")
            y1, y2 = active['שנה1'].sum(), active['שנה2'].sum()
            st.metric("שינוי", fmt_pct(chg(y2, y1)))
        with c2:
            st.subheader("Q2 vs Q3")
            q2, q3 = active['3v3_Q2'].sum(), active['3v3_Q3'].sum()
            st.metric("שינוי", fmt_pct(chg(q3, q2)))

with tabs[7]:
    st.title("⚠️ אזעקות ו-Recovery")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🚨 אזעקות")
        alerts = active[active['שינוי_2v2'] < th['אזעקה']].sort_values('שינוי_2v2')
        if len(alerts) > 0:
            st.error(f"{len(alerts)} חנויות!")
            d = alerts[['שם חנות', 'עיר', 'שנה2', 'שינוי_2v2']].head(20).copy()
            d['שנה2'] = d['שנה2'].apply(fmt_num)
            d['שינוי_2v2'] = d['שינוי_2v2'].apply(lambda x: f"{x:.1%} ⚠️")
            st.dataframe(d, hide_index=True, use_container_width=True)
        else:
            st.success("אין אזעקות!")
    with c2:
        st.subheader("💚 Recovery")
        rec = active[(active['סטטוס'].isin(['שחיקה', 'סכנה'])) & (active['שינוי_2v2'] > 0)].sort_values('שינוי_2v2', ascending=False)
        if len(rec) > 0:
            st.success(f"{len(rec)} חנויות!")
            d = rec[['שם חנות', 'עיר', 'שנה2', 'שינוי_2v2']].head(20).copy()
            d['שנה2'] = d['שנה2'].apply(fmt_num)
            d['שינוי_2v2'] = d['שינוי_2v2'].apply(lambda x: f"{x:+.1%} ↑")
            st.dataframe(d, hide_index=True, use_container_width=True)
        else:
            st.info("אין התאוששות")

with tabs[8]:
    st.title("🎯 פוטנציאל")
    min_pen = st.slider("סף חדירה", 0.5, 0.9, 0.7, 0.05)
    
    sp_act = sp_filtered[sp_filtered['מזהה_חנות'].isin(active['מזהה'])]
    if len(sp_act) > 0 and len(active) > 0:
        ps = sp_act[sp_act['שנה2'] > 0].groupby('מזהה_מוצר').agg({'מזהה_חנות': 'nunique', 'שנה2': 'mean'}).reset_index()
        ps.columns = ['מזהה_מוצר', 'חנויות', 'ממוצע']
        ps['חדירה'] = ps['חנויות'] / len(active)
        hp = ps[ps['חדירה'] >= min_pen]
        hp_ids = set(hp['מזהה_מוצר'])
        
        st.info(f"{len(hp)} מוצרים עם חדירה > {min_pen*100:.0f}%")
        
        store_prods = sp_act[sp_act['שנה2'] > 0].groupby('מזהה_חנות')['מזהה_מוצר'].apply(set).to_dict()
        
        pot = []
        for _, s in active.iterrows():
            sp_s = store_prods.get(s['מזהה'], set())
            miss = hp_ids - sp_s
            if len(miss) > 0:
                p = sum(hp[hp['מזהה_מוצר'] == m]['ממוצע'].values[0] for m in miss if m in hp['מזהה_מוצר'].values)
                pot.append({'חנות': s['שם חנות'], 'עיר': s['עיר'], 'מכירות': s['שנה2'], 'חסרים': len(miss), 'פוטנציאל': round(p)})
        
        pot_df = pd.DataFrame(pot).sort_values('פוטנציאל', ascending=False)
        
        if len(pot_df) > 0:
            c1, c2, c3 = st.columns(3)
            c1.metric("חנויות", len(pot_df))
            c2.metric("סה״כ", fmt_num(pot_df['פוטנציאל'].sum()))
            c3.metric("ממוצע", fmt_num(pot_df['פוטנציאל'].mean()))
            
            d = pot_df.head(20).copy()
            d['מכירות'] = d['מכירות'].apply(fmt_num)
            d['פוטנציאל'] = d['פוטנציאל'].apply(fmt_num)
            st.dataframe(d, hide_index=True, use_container_width=True)
            st.download_button("📥 הורד", to_excel(pot_df, 'פוטנציאל'), "פוטנציאל.xlsx")
        else:
            st.warning("אין פוטנציאל בסף הנבחר")

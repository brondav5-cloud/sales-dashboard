import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import io
from pathlib import Path

# ========================================
# הגדרות בסיסיות
# ========================================
st.set_page_config(page_title="טאוברד", page_icon="🌾", layout="wide")

# תאריכי התקופות - להצגה
PERIOD_LABELS = {
    'year1': 'דצמ׳23-נוב׳24',
    'year2': 'דצמ׳24-נוב׳25',
    'H1': 'דצמ׳24-מאי׳25',
    'H2': 'יונ׳25-נוב׳25',
    'Q3': 'יונ׳-אוג׳25',
    'Q4': 'ספט׳-נוב׳25',
    'QY1': 'ספט׳-נוב׳24',
    'QY2': 'ספט׳-נוב׳25',
    '2v2_prev': 'אוג׳-ספט׳25',
    '2v2_last': 'אוק׳-נוב׳25',
}

PERIOD_TITLES = {
    'year': 'השוואה שנתית',
    'half': 'מחצית שנה',
    'third': 'שליש שנה',
    'third_yoy': 'שליש שנה (שנה מול שנה)',
    'month2': 'חודשיים אחרונים',
}

# PWA Icon meta tags
st.markdown('''
<head>
    <link rel="apple-touch-icon" href="https://raw.githubusercontent.com/brondav5-cloud/sales-dashboard/main/taubread_logo.jpg">
    <link rel="icon" type="image/jpeg" href="https://raw.githubusercontent.com/brondav5-cloud/sales-dashboard/main/taubread_logo.jpg">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="טאוברד">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
''', unsafe_allow_html=True)

# ========================================
# נתוני סוכנים
# ========================================
AGENTS_DATA = {
    "יוסף": {"password": "Agen148", "stores": [67, 834, 291, 262, 685, 702, 638, 664, 1299, 1300, 1303, 1316, 1317, 1318, 1319, 1320, 1321, 1325, 1326, 1330, 1331, 1332, 1333, 1334, 1335, 1337, 1340, 1341]},
    "ניקול": {"password": "Agen148", "stores": [665, 441, 1094, 340, 1106, 1122, 1093, 62, 599, 263, 1084, 309, 624, 1227]},
}
ADMIN_PASSWORD = "admin2025"

# ========================================
# CSS - כולל מצב כהה ותמיכה במובייל
# ========================================
def get_css(dark_mode=False):
    if dark_mode:
        bg_color = "#1a1a2e"
        card_bg = "#16213e"
        text_color = "#eaeaea"
        border_color = "#0f3460"
        accent = "#e94560"
        header_gradient = "linear-gradient(90deg, #e94560 0%, #0f3460 100%)"
    else:
        bg_color = "#ffffff"
        card_bg = "#f8f9fa"
        text_color = "#333333"
        border_color = "#e9ecef"
        accent = "#667eea"
        header_gradient = "linear-gradient(90deg, #667eea 0%, #764ba2 100%)"
    
    return f"""
    <style>
    /* הסתרת תפריט Streamlit */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    .stDeployButton {{display: none;}}
    [data-testid="stToolbar"] {{display: none;}}
    
    /* RTL וסגנון כללי */
    .main > div {{direction: rtl; text-align: right;}}
    h1, h2, h3, p, span, div {{direction: rtl; text-align: right;}}
    
    /* כרטיסי מדדים */
    div[data-testid="metric-container"] {{
        background: {card_bg}; 
        border-radius: 10px; 
        padding: 15px; 
        border: 1px solid {border_color};
        color: {text_color};
    }}
    
    /* כותרת סוכן/מנהל */
    .agent-header {{
        background: {header_gradient}; 
        color: white; 
        padding: 10px 20px; 
        border-radius: 10px; 
        margin-bottom: 20px;
        text-align: center;
    }}
    
    /* כרטיסי תקופות */
    .period-card {{
        background: {card_bg};
        border-radius: 8px;
        padding: 12px;
        margin: 5px 0;
        border-right: 4px solid {accent};
    }}
    .period-title {{
        font-size: 12px;
        color: #888;
        margin-bottom: 5px;
    }}
    .period-dates {{
        font-size: 11px;
        color: #aaa;
    }}
    .period-value {{
        font-size: 18px;
        font-weight: bold;
        color: {text_color};
    }}
    .period-change {{
        font-size: 14px;
        font-weight: bold;
    }}
    .positive {{ color: #28a745; }}
    .negative {{ color: #dc3545; }}
    .neutral {{ color: #6c757d; }}
    
    /* אזהרת חריגים */
    .outlier-warning {{
        background: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 8px;
        padding: 10px;
        margin: 10px 0;
        color: #856404;
    }}
    
    /* תמיכה במובייל */
    @media (max-width: 768px) {{
        div[data-testid="metric-container"] {{
            padding: 10px;
            margin: 5px 0;
        }}
        .agent-header {{
            padding: 8px 15px;
            font-size: 14px;
        }}
        h1 {{ font-size: 1.5rem !important; }}
        h2 {{ font-size: 1.2rem !important; }}
        h3 {{ font-size: 1rem !important; }}
    }}
    </style>
    """

# ========================================
# פונקציות עזר
# ========================================
def chg(new, old):
    """חישוב אחוז שינוי"""
    if pd.isna(old) or old == 0:
        return 0
    return (new - old) / old

def fmt_pct(v):
    """עיצוב אחוזים"""
    if pd.isna(v) or v == 0:
        return "0.0%"
    return f"{v:+.1%}"

def fmt_num(v):
    """עיצוב מספרים"""
    if pd.isna(v):
        return "0"
    return f"{v:,.0f}"

def get_change_class(v):
    """קבלת class לפי כיוון השינוי"""
    if v > 0.01:
        return "positive"
    elif v < -0.01:
        return "negative"
    return "neutral"

def calc_status(r, th):
    """חישוב סטטוס חנות"""
    if r['year1'] == 0:
        return 'חדש/ה'
    c = chg(r['year2'], r['year1'])
    c_half = chg(r['H2'], r['H1'])
    if c < th['סכנה'] and c_half < th['סכנה_חצי']:
        return 'סכנה'
    elif c > th['צמיחה'] and c_half > th['צמיחה_חצי']:
        return 'צמיחה'
    elif c >= th['יציב_תחתון'] and c <= th['יציב_עליון']:
        return 'יציב'
    elif c < th['יציב_תחתון'] and c_half > 0.05:
        return 'התאוששות'
    else:
        return 'שחיקה'

def to_excel(df, sheet):
    """המרה לאקסל"""
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as w:
        df.to_excel(w, sheet_name=sheet, index=False)
    return out.getvalue()

def to_excel_multi(dfs_dict):
    """המרה לאקסל עם מספר גליונות"""
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as w:
        for sheet_name, df in dfs_dict.items():
            df.to_excel(w, sheet_name=sheet_name, index=False)
    return out.getvalue()

# ========================================
# מערכת התחברות
# ========================================
def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user_type = None
        st.session_state.user_name = None
        st.session_state.user_stores = None
        st.session_state.dark_mode = False
        st.session_state.excluded_stores = []
    
    if not st.session_state.logged_in:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.title("🌾 דשבורד מכירות טאוברד")
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

# ========================================
# טעינת נתונים
# ========================================
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

# ========================================
# בדיקת התחברות
# ========================================
if not check_login():
    st.stop()

# החלת CSS
st.markdown(get_css(st.session_state.get('dark_mode', False)), unsafe_allow_html=True)

# ========================================
# סרגל עליון - יציאה ומצב כהה
# ========================================
col1, col2, col3 = st.columns([5, 1, 1])
with col2:
    if st.button("🌙" if not st.session_state.get('dark_mode') else "☀️", help="מצב כהה/בהיר"):
        st.session_state.dark_mode = not st.session_state.get('dark_mode', False)
        st.rerun()
with col3:
    if st.button("🚪 יציאה"):
        st.session_state.logged_in = False
        st.session_state.user_type = None
        st.session_state.user_name = None
        st.session_state.user_stores = None
        st.rerun()

# הצגת פרטי משתמש
if st.session_state.user_type == "agent":
    st.markdown(f'<div class="agent-header">👤 שלום <b>{st.session_state.user_name}</b> | החנויות שלך: <b>{len(st.session_state.user_stores)}</b></div>', unsafe_allow_html=True)
else:
    st.markdown(f'<div class="agent-header">👑 מצב מנהל - גישה לכל הנתונים</div>', unsafe_allow_html=True)

# טעינת נתונים
stores, products, sp = load_data()

# ========================================
# סרגל צד
# ========================================
st.sidebar.title("🌾 טאוברד")
st.sidebar.markdown(f"**משתמש:** {st.session_state.user_name}")
st.sidebar.markdown("---")

# הגדרות חריגים (רק למנהל)
if st.session_state.user_type == "admin":
    st.sidebar.subheader("⚠️ ניהול חריגים")
    with st.sidebar.expander("🔧 הגדרת חנויות חריגות"):
        # חישוב אחוז מכירות
        total_sales = stores['year2'].sum()
        stores_with_pct = stores[['מזהה', 'שם_חנות', 'year2']].copy()
        stores_with_pct['אחוז'] = stores_with_pct['year2'] / total_sales * 100
        stores_with_pct = stores_with_pct.sort_values('אחוז', ascending=False)
        
        # סף להצגה
        threshold = st.slider("הצג חנויות מעל (%):", 0.5, 10.0, 2.0, 0.5)
        
        # הצגת חנויות מעל הסף
        big_stores = stores_with_pct[stores_with_pct['אחוז'] >= threshold]
        
        if len(big_stores) > 0:
            st.markdown(f"**{len(big_stores)} חנויות מעל {threshold}%:**")
            
            for _, row in big_stores.iterrows():
                store_id = row['מזהה']
                is_excluded = store_id in st.session_state.excluded_stores
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{row['שם_חנות'][:20]}** ({row['אחוז']:.1f}%)")
                with col2:
                    if st.checkbox("החרג", value=is_excluded, key=f"exc_{store_id}"):
                        if store_id not in st.session_state.excluded_stores:
                            st.session_state.excluded_stores.append(store_id)
                    else:
                        if store_id in st.session_state.excluded_stores:
                            st.session_state.excluded_stores.remove(store_id)
            
            if len(st.session_state.excluded_stores) > 0:
                st.warning(f"🚫 {len(st.session_state.excluded_stores)} חנויות מוחרגות מהממוצעים")
        else:
            st.info("אין חנויות מעל הסף")

st.sidebar.markdown("---")

# הגדרות ספים
st.sidebar.subheader("⚙️ הגדרות ספים")
with st.sidebar.expander("🎚️ שנה ספים"):
    th = {}
    th['צמיחה'] = st.slider("צמיחה שנתי", 0.0, 0.20, 0.05, 0.01)
    th['צמיחה_חצי'] = st.slider("צמיחה חצי שנה", -0.20, 0.10, -0.05, 0.01)
    th['יציב_עליון'] = th['צמיחה']
    th['יציב_תחתון'] = st.slider("יציב תחתון", -0.15, 0.0, -0.05, 0.01)
    th['סכנה'] = st.slider("סכנה שנתי", -0.30, 0.0, -0.15, 0.01)
    th['סכנה_חצי'] = st.slider("סכנה חצי שנה", -0.30, 0.0, -0.10, 0.01)
    th['אזעקה'] = st.slider("אזעקה 2v2", -0.30, 0.0, -0.15, 0.01)

st.sidebar.markdown("---")

# ========================================
# חישובים
# ========================================
# שינויים
stores['שינוי_שנתי'] = stores.apply(lambda r: chg(r['year2'], r['year1']), axis=1)
stores['שינוי_חצי'] = stores.apply(lambda r: chg(r['H2'], r['H1']), axis=1)
stores['שינוי_שליש'] = stores.apply(lambda r: chg(r['Q4'], r['Q3']), axis=1)
stores['שינוי_שליש_שנתי'] = stores.apply(lambda r: chg(r['QY2'], r['QY1']), axis=1)  # חדש!
stores['שינוי_2v2'] = stores.apply(lambda r: chg(r['2v2_last'], r['2v2_prev']), axis=1)
stores['סטטוס'] = stores.apply(lambda r: calc_status(r, th), axis=1)
stores['דירוג'] = stores['year2'].rank(ascending=False, method='min').astype(int)

# סינון לפי סוכן
all_active = stores[stores['2v2_last'] > 0].copy()
all_closed = stores[stores['2v2_last'] == 0].copy()

if st.session_state.user_type == "agent":
    active = all_active[all_active['מזהה'].isin(st.session_state.user_stores)].copy()
    closed = all_closed[all_closed['מזהה'].isin(st.session_state.user_stores)].copy()
    sp_filtered = sp[sp['מזהה_חנות'].isin(st.session_state.user_stores)].copy()
else:
    active = all_active.copy()
    closed = all_closed.copy()
    sp_filtered = sp.copy()

# סינון חנויות להתעלמות בחישוב ממוצעים (רק למנהל)
active_for_avg = active[~active['מזהה'].isin(st.session_state.excluded_stores)].copy()

# סינונים נוספים
st.sidebar.subheader("🔍 סינונים")
cities = ['הכל'] + sorted([c for c in active['עיר'].dropna().unique() if c and str(c) != 'nan'])
sel_city = st.sidebar.selectbox("עיר", cities)
statuses = ['הכל'] + list(active['סטטוס'].unique())
sel_status = st.sidebar.selectbox("סטטוס", statuses)

# החלת סינונים
filtered = active.copy()
if sel_city != 'הכל':
    filtered = filtered[filtered['עיר'] == sel_city]
if sel_status != 'הכל':
    filtered = filtered[filtered['סטטוס'] == sel_status]

# ========================================
# טאבים
# ========================================
tabs = st.tabs(["📊 סיכום", "📋 חנויות", "📈 סטטוסים", "🔎 בחירת חנות", "🔍 בחירת מוצר", "🚫 סגורות", "📉 מגמות", "⚠️ אזעקות", "🎯 פוטנציאל", "📥 הורדות"])

# ========================================
# טאב 0: סיכום
# ========================================
with tabs[0]:
    st.title("📊 סיכום ביצועים")
    
    # הודעת חריגים
    if len(st.session_state.excluded_stores) > 0:
        excluded_names = stores[stores['מזהה'].isin(st.session_state.excluded_stores)]['שם_חנות'].tolist()
        st.markdown(f'<div class="outlier-warning">⚠️ הממוצעים מחושבים ללא: {", ".join(excluded_names)}</div>', unsafe_allow_html=True)
    
    # שורה עליונה - מדדים ראשיים
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("חנויות פעילות", len(active))
    c2.metric(f"מכירות {PERIOD_LABELS['year2']}", fmt_num(active['year2'].sum()))
    c3.metric("שינוי שנתי", fmt_pct(chg(active['year2'].sum(), active['year1'].sum())))
    c4.metric("חנויות סגורות", len(closed))
    
    st.markdown("---")
    
    # השוואות תקופות
    st.subheader("📅 השוואות תקופות")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"**{PERIOD_TITLES['year']}**")
        st.markdown(f"<span class='period-dates'>{PERIOD_LABELS['year1']} ← {PERIOD_LABELS['year2']}</span>", unsafe_allow_html=True)
        y1, y2 = active_for_avg['year1'].sum(), active_for_avg['year2'].sum()
        change = chg(y2, y1)
        st.metric("שינוי", fmt_pct(change), delta=fmt_num(y2-y1))
    
    with col2:
        st.markdown(f"**{PERIOD_TITLES['half']}**")
        st.markdown(f"<span class='period-dates'>{PERIOD_LABELS['H1']} ← {PERIOD_LABELS['H2']}</span>", unsafe_allow_html=True)
        h1, h2 = active_for_avg['H1'].sum(), active_for_avg['H2'].sum()
        change = chg(h2, h1)
        st.metric("שינוי", fmt_pct(change), delta=fmt_num(h2-h1))
    
    with col3:
        st.markdown(f"**{PERIOD_TITLES['third']}**")
        st.markdown(f"<span class='period-dates'>{PERIOD_LABELS['Q3']} ← {PERIOD_LABELS['Q4']}</span>", unsafe_allow_html=True)
        q3, q4 = active_for_avg['Q3'].sum(), active_for_avg['Q4'].sum()
        change = chg(q4, q3)
        st.metric("שינוי", fmt_pct(change), delta=fmt_num(q4-q3))
    
    with col4:
        st.markdown(f"**{PERIOD_TITLES['third_yoy']}** 🆕")
        st.markdown(f"<span class='period-dates'>{PERIOD_LABELS['QY1']} ← {PERIOD_LABELS['QY2']}</span>", unsafe_allow_html=True)
        qy1, qy2 = active_for_avg['QY1'].sum(), active_for_avg['QY2'].sum()
        change = chg(qy2, qy1)
        st.metric("שינוי", fmt_pct(change), delta=fmt_num(qy2-qy1))
    
    st.markdown("---")
    
    # חודשיים אחרונים
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**{PERIOD_TITLES['month2']}**")
        st.markdown(f"<span class='period-dates'>{PERIOD_LABELS['2v2_prev']} ← {PERIOD_LABELS['2v2_last']}</span>", unsafe_allow_html=True)
        m1, m2 = active_for_avg['2v2_prev'].sum(), active_for_avg['2v2_last'].sum()
        change = chg(m2, m1)
        st.metric("שינוי", fmt_pct(change), delta=fmt_num(m2-m1))
    
    with col2:
        # גרף פאי סטטוסים
        st.markdown("**התפלגות סטטוסים**")
        status_counts = active['סטטוס'].value_counts()
        fig = px.pie(values=status_counts.values, names=status_counts.index, 
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(height=200, margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)

# ========================================
# טאב 1: חנויות
# ========================================
with tabs[1]:
    st.title("📋 רשימת חנויות")
    st.markdown(f"*מציג {len(filtered)} חנויות*")
    
    # עמודות להצגה עם כותרות ברורות
    display_df = filtered[['מזהה', 'שם_חנות', 'עיר', 'סטטוס', 'דירוג', 'year1', 'year2', 'שינוי_שנתי', 'שינוי_שליש_שנתי', '2v2_last', 'שינוי_2v2']].copy()
    display_df.columns = ['מזהה', 'שם חנות', 'עיר', 'סטטוס', 'דירוג', 
                          PERIOD_LABELS['year1'], PERIOD_LABELS['year2'], 'שינוי שנתי',
                          f'שינוי שליש ({PERIOD_LABELS["QY1"]} vs {PERIOD_LABELS["QY2"]})',
                          PERIOD_LABELS['2v2_last'], 'שינוי 2v2']
    
    # עיצוב
    display_df[PERIOD_LABELS['year1']] = display_df[PERIOD_LABELS['year1']].apply(fmt_num)
    display_df[PERIOD_LABELS['year2']] = display_df[PERIOD_LABELS['year2']].apply(fmt_num)
    display_df['שינוי שנתי'] = display_df['שינוי שנתי'].apply(fmt_pct)
    display_df[f'שינוי שליש ({PERIOD_LABELS["QY1"]} vs {PERIOD_LABELS["QY2"]})'] = display_df[f'שינוי שליש ({PERIOD_LABELS["QY1"]} vs {PERIOD_LABELS["QY2"]})'].apply(fmt_pct)
    display_df[PERIOD_LABELS['2v2_last']] = display_df[PERIOD_LABELS['2v2_last']].apply(fmt_num)
    display_df['שינוי 2v2'] = display_df['שינוי 2v2'].apply(fmt_pct)
    
    st.dataframe(display_df, hide_index=True, use_container_width=True, height=500)

# ========================================
# טאב 2: סטטוסים
# ========================================
with tabs[2]:
    st.title("📈 חנויות לפי סטטוס")
    
    status_tabs = st.tabs(["🚀 צמיחה", "✅ יציב", "📉 שחיקה", "⚠️ סכנה", "🔄 התאוששות", "🆕 חדשים"])
    
    for i, (status, emoji) in enumerate([("צמיחה", "🚀"), ("יציב", "✅"), ("שחיקה", "📉"), ("סכנה", "⚠️"), ("התאוששות", "🔄"), ("חדש/ה", "🆕")]):
        with status_tabs[i]:
            status_df = filtered[filtered['סטטוס'] == status].sort_values('year2', ascending=False)
            st.markdown(f"**{len(status_df)} חנויות**")
            
            if len(status_df) > 0:
                d = status_df[['שם_חנות', 'עיר', 'year2', 'שינוי_שנתי', 'שינוי_שליש_שנתי']].copy()
                d.columns = ['שם חנות', 'עיר', PERIOD_LABELS['year2'], 'שינוי שנתי', 'שינוי שליש שנתי']
                d[PERIOD_LABELS['year2']] = d[PERIOD_LABELS['year2']].apply(fmt_num)
                d['שינוי שנתי'] = d['שינוי שנתי'].apply(fmt_pct)
                d['שינוי שליש שנתי'] = d['שינוי שליש שנתי'].apply(fmt_pct)
                st.dataframe(d, hide_index=True, use_container_width=True)

# ========================================
# טאב 3: בחירת חנות
# ========================================
with tabs[3]:
    st.title("🔎 פרטי חנות")
    
    opts = filtered.apply(lambda r: f"{r['מזהה']} - {r['שם_חנות']}", axis=1).tolist()
    sel = st.selectbox("בחר חנות:", ['בחר...'] + sorted(opts), key="store")
    
    if sel != 'בחר...':
        sid = int(sel.split(' - ')[0])
        info = filtered[filtered['מזהה'] == sid].iloc[0]
        
        # מידע בסיסי
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("מזהה", info['מזהה'])
        c1.metric("עיר", info['עיר'] if pd.notna(info['עיר']) else '-')
        c2.metric(f"דירוג (מתוך {len(all_active)})", f"#{int(info['דירוג'])}")
        c2.metric("סטטוס", info['סטטוס'])
        c3.metric(PERIOD_LABELS['year1'], fmt_num(info['year1']))
        c3.metric(PERIOD_LABELS['year2'], fmt_num(info['year2']))
        c4.metric("שינוי שנתי", fmt_pct(info['שינוי_שנתי']))
        c4.metric("שינוי 2v2", fmt_pct(info['שינוי_2v2']))
        
        st.markdown("---")
        st.subheader("📊 כל המדדים")
        
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            st.markdown(f"**מחצית שנה**")
            st.metric(f"{PERIOD_LABELS['H1']}", fmt_num(info['H1']))
            st.metric(f"{PERIOD_LABELS['H2']}", fmt_num(info['H2']))
            st.metric("שינוי", fmt_pct(info['שינוי_חצי']))
        
        with c2:
            st.markdown(f"**שליש שנה (רציף)**")
            st.metric(f"{PERIOD_LABELS['Q3']}", fmt_num(info['Q3']))
            st.metric(f"{PERIOD_LABELS['Q4']}", fmt_num(info['Q4']))
            st.metric("שינוי", fmt_pct(info['שינוי_שליש']))
        
        with c3:
            st.markdown(f"**שליש שנה (שנתי)** 🆕")
            st.metric(f"{PERIOD_LABELS['QY1']}", fmt_num(info['QY1']))
            st.metric(f"{PERIOD_LABELS['QY2']}", fmt_num(info['QY2']))
            st.metric("שינוי", fmt_pct(info['שינוי_שליש_שנתי']))
        
        with c4:
            st.markdown(f"**חודשיים**")
            st.metric(f"{PERIOD_LABELS['2v2_prev']}", fmt_num(info['2v2_prev']))
            st.metric(f"{PERIOD_LABELS['2v2_last']}", fmt_num(info['2v2_last']))
            st.metric("שינוי", fmt_pct(info['שינוי_2v2']))
        
        st.markdown("---")
        st.subheader("📦 מוצרים בחנות")
        sp2 = sp_filtered[sp_filtered['מזהה_חנות'] == sid].copy()
        if len(sp2) > 0:
            sp2['שינוי'] = sp2.apply(lambda r: chg(r['year2'], r['year1']), axis=1)
            sp2 = sp2.sort_values('year2', ascending=False)
            
            d = sp2[['מוצר', 'סיווג', 'year1', 'year2', 'שינוי', '2v2_prev', '2v2_last']].copy()
            d.columns = ['מוצר', 'סיווג', PERIOD_LABELS['year1'], PERIOD_LABELS['year2'], 'שינוי', PERIOD_LABELS['2v2_prev'], PERIOD_LABELS['2v2_last']]
            d[PERIOD_LABELS['year1']] = d[PERIOD_LABELS['year1']].apply(fmt_num)
            d[PERIOD_LABELS['year2']] = d[PERIOD_LABELS['year2']].apply(fmt_num)
            d['שינוי'] = d['שינוי'].apply(fmt_pct)
            d[PERIOD_LABELS['2v2_prev']] = d[PERIOD_LABELS['2v2_prev']].apply(fmt_num)
            d[PERIOD_LABELS['2v2_last']] = d[PERIOD_LABELS['2v2_last']].apply(fmt_num)
            
            # Column config for better display
            col_config = {
                'מוצר': st.column_config.TextColumn('מוצר', width='large'),
                'סיווג': st.column_config.TextColumn('סיווג', width='medium'),
                PERIOD_LABELS['year1']: st.column_config.TextColumn(PERIOD_LABELS['year1'], width='small'),
                PERIOD_LABELS['year2']: st.column_config.TextColumn(PERIOD_LABELS['year2'], width='small'),
                'שינוי': st.column_config.TextColumn('שינוי', width='small'),
                PERIOD_LABELS['2v2_prev']: st.column_config.TextColumn(PERIOD_LABELS['2v2_prev'], width='small'),
                PERIOD_LABELS['2v2_last']: st.column_config.TextColumn(PERIOD_LABELS['2v2_last'], width='small'),
            }
            st.dataframe(d, hide_index=True, use_container_width=True, height=400, column_config=col_config)
            
            st.subheader("📊 Top 15 מוצרים")
            top15 = sp2.nlargest(15, 'year2')
            fig = px.bar(top15, x='מוצר', y='year2', color='סיווג', text=top15['year2'].apply(fmt_num))
            fig.update_layout(xaxis_tickangle=-45, yaxis_title=PERIOD_LABELS['year2'])
            fig.update_traces(textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("לא נמצאו מוצרים")

# ========================================
# טאב 4: בחירת מוצר
# ========================================
with tabs[4]:
    st.title("🔍 פרטי מוצר")
    opts = products.apply(lambda r: f"{r['מזהה']} - {r['מוצר']}", axis=1).tolist()
    sel = st.selectbox("בחר מוצר:", ['בחר...'] + sorted(opts), key="prod")
    
    if sel != 'בחר...':
        pid = int(sel.split(' - ')[0])
        pinfo = products[products['מזהה'] == pid].iloc[0]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("מוצר", pinfo['מוצר'])
        c2.metric("סיווג", pinfo['סיווג'] if pd.notna(pinfo['סיווג']) else '-')
        c3.metric(f"מכירות {PERIOD_LABELS['year2']}", fmt_num(pinfo['year2']))
        c4.metric("שינוי שנתי", fmt_pct(chg(pinfo['year2'], pinfo['year1'])))
        
        st.markdown("---")
        ps = sp_filtered[sp_filtered['מזהה_מוצר'] == pid].copy()
        ps = ps[ps['מזהה_חנות'].isin(active['מזהה'])]
        if len(ps) > 0:
            selling = len(ps[ps['year2'] > 0])
            pen = selling / len(active) * 100 if len(active) > 0 else 0
            c1, c2, c3 = st.columns(3)
            c1.metric("חנויות מוכרות", selling)
            c2.metric("חדירה", f"{pen:.1f}%")
            c3.metric("סה״כ חנויות", len(active))
            
            ps['שינוי'] = ps.apply(lambda r: chg(r['year2'], r['year1']), axis=1)
            ps = ps.sort_values('year2', ascending=False)
            d = ps[['שם_חנות', 'עיר', 'year1', 'year2', 'שינוי']].copy()
            d.columns = ['שם חנות', 'עיר', PERIOD_LABELS['year1'], PERIOD_LABELS['year2'], 'שינוי']
            d[PERIOD_LABELS['year1']] = d[PERIOD_LABELS['year1']].apply(fmt_num)
            d[PERIOD_LABELS['year2']] = d[PERIOD_LABELS['year2']].apply(fmt_num)
            d['שינוי'] = d['שינוי'].apply(fmt_pct)
            st.dataframe(d, hide_index=True, use_container_width=True, height=400)

# ========================================
# טאב 5: חנויות סגורות
# ========================================
with tabs[5]:
    st.title("🚫 חנויות סגורות")
    if len(closed) > 0:
        c1, c2, c3 = st.columns(3)
        c1.metric("סה״כ סגורות", len(closed))
        c2.metric("מכירות שאבדו", fmt_num(closed['year1'].sum()))
        c3.metric("אחוז מהכלל", f"{len(closed)/(len(active)+len(closed))*100:.1f}%")
        
        d = closed[['מזהה', 'שם_חנות', 'עיר', 'year1']].sort_values('year1', ascending=False).copy()
        d.columns = ['מזהה', 'שם חנות', 'עיר', PERIOD_LABELS['year1']]
        d[PERIOD_LABELS['year1']] = d[PERIOD_LABELS['year1']].apply(fmt_num)
        st.dataframe(d, hide_index=True, use_container_width=True)
    else:
        st.success("🎉 אין חנויות סגורות!")

# ========================================
# טאב 6: מגמות
# ========================================
with tabs[6]:
    st.title("📉 מגמות")
    
    if len(active_for_avg) > 0:
        # גרף מגמה
        periods_order = ['year1', 'H1', 'H2', 'Q3', 'Q4']
        labels = [PERIOD_LABELS[p] for p in periods_order]
        vals = [active_for_avg[p].sum() for p in periods_order]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=labels, y=vals, 
            mode='lines+markers+text', 
            text=[fmt_num(v) for v in vals], 
            textposition='top center', 
            line=dict(width=4, color='#667eea'), 
            marker=dict(size=12)
        ))
        fig.update_layout(height=400, title="מגמת מכירות לאורך זמן")
        st.plotly_chart(fig, use_container_width=True)
        
        # השוואות
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader(f"{PERIOD_LABELS['year1']} vs {PERIOD_LABELS['year2']}")
            y1, y2 = active_for_avg['year1'].sum(), active_for_avg['year2'].sum()
            st.metric("שינוי", fmt_pct(chg(y2, y1)))
        with col2:
            st.subheader(f"{PERIOD_LABELS['Q3']} vs {PERIOD_LABELS['Q4']}")
            q3, q4 = active_for_avg['Q3'].sum(), active_for_avg['Q4'].sum()
            st.metric("שינוי", fmt_pct(chg(q4, q3)))
        with col3:
            st.subheader(f"{PERIOD_LABELS['QY1']} vs {PERIOD_LABELS['QY2']} 🆕")
            qy1, qy2 = active_for_avg['QY1'].sum(), active_for_avg['QY2'].sum()
            st.metric("שינוי", fmt_pct(chg(qy2, qy1)))

# ========================================
# טאב 7: אזעקות
# ========================================
with tabs[7]:
    st.title("⚠️ אזעקות ו-Recovery")
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("🚨 אזעקות")
        st.caption(f"חנויות עם ירידה של יותר מ-{abs(th['אזעקה'])*100:.0f}% ב-2 החודשים האחרונים")
        alerts = active[active['שינוי_2v2'] < th['אזעקה']].sort_values('שינוי_2v2')
        if len(alerts) > 0:
            st.error(f"🚨 {len(alerts)} חנויות באזעקה!")
            d = alerts[['שם_חנות', 'עיר', 'year2', 'שינוי_2v2']].head(20).copy()
            d.columns = ['שם חנות', 'עיר', PERIOD_LABELS['year2'], 'שינוי 2v2']
            d[PERIOD_LABELS['year2']] = d[PERIOD_LABELS['year2']].apply(fmt_num)
            d['שינוי 2v2'] = d['שינוי 2v2'].apply(lambda x: f"{x:.1%} ⚠️")
            st.dataframe(d, hide_index=True, use_container_width=True)
        else:
            st.success("✅ אין אזעקות!")
    
    with c2:
        st.subheader("💚 Recovery")
        st.caption("חנויות בסטטוס שחיקה/סכנה שמראות שיפור")
        rec = active[(active['סטטוס'].isin(['שחיקה', 'סכנה'])) & (active['שינוי_2v2'] > 0)].sort_values('שינוי_2v2', ascending=False)
        if len(rec) > 0:
            st.success(f"💚 {len(rec)} חנויות בהתאוששות!")
            d = rec[['שם_חנות', 'עיר', 'year2', 'שינוי_2v2']].head(20).copy()
            d.columns = ['שם חנות', 'עיר', PERIOD_LABELS['year2'], 'שינוי 2v2']
            d[PERIOD_LABELS['year2']] = d[PERIOD_LABELS['year2']].apply(fmt_num)
            d['שינוי 2v2'] = d['שינוי 2v2'].apply(lambda x: f"{x:+.1%} ↑")
            st.dataframe(d, hide_index=True, use_container_width=True)
        else:
            st.info("אין חנויות בהתאוששות")

# ========================================
# טאב 8: פוטנציאל
# ========================================
with tabs[8]:
    st.title("🎯 פוטנציאל")
    min_pen = st.slider("סף חדירה", 0.5, 0.9, 0.7, 0.05)
    
    sp_act = sp_filtered[sp_filtered['מזהה_חנות'].isin(active['מזהה'])]
    if len(sp_act) > 0 and len(active) > 0:
        ps = sp_act[sp_act['year2'] > 0].groupby('מזהה_מוצר').agg({'מזהה_חנות': 'nunique', 'year2': 'mean'}).reset_index()
        ps.columns = ['מזהה_מוצר', 'חנויות', 'ממוצע']
        ps['חדירה'] = ps['חנויות'] / len(active)
        hp = ps[ps['חדירה'] >= min_pen]
        hp_ids = set(hp['מזהה_מוצר'])
        
        st.info(f"📊 {len(hp)} מוצרים עם חדירה > {min_pen*100:.0f}%")
        
        store_prods = sp_act[sp_act['year2'] > 0].groupby('מזהה_חנות')['מזהה_מוצר'].apply(set).to_dict()
        
        pot = []
        for _, s in active.iterrows():
            sp_s = store_prods.get(s['מזהה'], set())
            miss = hp_ids - sp_s
            if len(miss) > 0:
                p = sum(hp[hp['מזהה_מוצר'] == m]['ממוצע'].values[0] for m in miss if m in hp['מזהה_מוצר'].values)
                pot.append({'חנות': s['שם_חנות'], 'עיר': s['עיר'], 'מכירות': s['year2'], 'חסרים': len(miss), 'פוטנציאל': round(p)})
        
        pot_df = pd.DataFrame(pot).sort_values('פוטנציאל', ascending=False)
        
        if len(pot_df) > 0:
            c1, c2, c3 = st.columns(3)
            c1.metric("חנויות עם פוטנציאל", len(pot_df))
            c2.metric("סה״כ פוטנציאל", fmt_num(pot_df['פוטנציאל'].sum()))
            c3.metric("ממוצע לחנות", fmt_num(pot_df['פוטנציאל'].mean()))
            
            d = pot_df.head(20).copy()
            d['מכירות'] = d['מכירות'].apply(fmt_num)
            d['פוטנציאל'] = d['פוטנציאל'].apply(fmt_num)
            st.dataframe(d, hide_index=True, use_container_width=True)
            st.download_button("📥 הורד Excel", to_excel(pot_df, 'פוטנציאל'), "פוטנציאל.xlsx")
        else:
            st.warning("אין פוטנציאל בסף הנבחר")

# ========================================
# טאב 9: הורדות
# ========================================
with tabs[9]:
    st.title("📥 הורדת דוחות")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 דוח חנויות מלא")
        export_stores = active[['מזהה', 'שם_חנות', 'עיר', 'סטטוס', 'דירוג', 
                                'year1', 'year2', 'שינוי_שנתי',
                                'H1', 'H2', 'שינוי_חצי',
                                'Q3', 'Q4', 'שינוי_שליש',
                                'QY1', 'QY2', 'שינוי_שליש_שנתי',
                                '2v2_prev', '2v2_last', 'שינוי_2v2']].copy()
        export_stores.columns = ['מזהה', 'שם חנות', 'עיר', 'סטטוס', 'דירוג',
                                 PERIOD_LABELS['year1'], PERIOD_LABELS['year2'], 'שינוי שנתי',
                                 PERIOD_LABELS['H1'], PERIOD_LABELS['H2'], 'שינוי מחצית',
                                 PERIOD_LABELS['Q3'], PERIOD_LABELS['Q4'], 'שינוי שליש',
                                 PERIOD_LABELS['QY1'], PERIOD_LABELS['QY2'], 'שינוי שליש שנתי',
                                 PERIOD_LABELS['2v2_prev'], PERIOD_LABELS['2v2_last'], 'שינוי 2v2']
        
        st.download_button(
            "📥 הורד Excel - חנויות",
            to_excel(export_stores, 'חנויות'),
            "דוח_חנויות.xlsx",
            use_container_width=True
        )
    
    with col2:
        st.subheader("📦 דוח מוצרים")
        export_products = products[['מזהה', 'מוצר', 'סיווג', 'year1', 'year2']].copy()
        export_products['שינוי'] = export_products.apply(lambda r: chg(r['year2'], r['year1']), axis=1)
        export_products.columns = ['מזהה', 'מוצר', 'סיווג', PERIOD_LABELS['year1'], PERIOD_LABELS['year2'], 'שינוי']
        
        st.download_button(
            "📥 הורד Excel - מוצרים",
            to_excel(export_products, 'מוצרים'),
            "דוח_מוצרים.xlsx",
            use_container_width=True
        )
    
    st.markdown("---")
    
    st.subheader("📋 דוח מלא (כל הגליונות)")
    
    # יצירת דוח מלא עם כל הגליונות
    all_sheets = {
        'חנויות': export_stores,
        'מוצרים': export_products,
        'סגורות': closed[['מזהה', 'שם_חנות', 'עיר', 'year1']].copy() if len(closed) > 0 else pd.DataFrame(),
    }
    
    st.download_button(
        "📥 הורד דוח מלא (Excel)",
        to_excel_multi(all_sheets),
        "דוח_מלא_טאוברד.xlsx",
        use_container_width=True
    )

# FIX: Add custom CSS for better table display at the end
st.markdown("""
<style>
/* Fix table columns width */
[data-testid="stDataFrame"] {
    width: 100%;
}
[data-testid="stDataFrame"] table {
    width: 100% !important;
}
[data-testid="stDataFrame"] th, 
[data-testid="stDataFrame"] td {
    min-width: 80px !important;
    white-space: nowrap !important;
    text-align: right !important;
}
</style>
""", unsafe_allow_html=True)

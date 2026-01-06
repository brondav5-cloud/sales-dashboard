import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import io
from pathlib import Path

st.set_page_config(page_title="דשבורד מכירות", page_icon="📊", layout="wide")
PASSWORD = "sales2025"

st.markdown("""
<style>
.main > div {direction: rtl; text-align: right;}
h1, h2, h3, p {direction: rtl; text-align: right;}
div[data-testid="metric-container"] {background: #f8f9fa; border-radius: 10px; padding: 15px; border: 1px solid #e9ecef;}
</style>
""", unsafe_allow_html=True)

def check_password():
    if "auth" not in st.session_state:
        st.session_state.auth = False
    if not st.session_state.auth:
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            st.title("🔐 דשבורד מכירות")
            pwd = st.text_input("סיסמה:", type="password")
            if st.button("כניסה"):
                if pwd == PASSWORD:
                    st.session_state.auth = True
                    st.rerun()
                else:
                    st.error("סיסמה שגויה!")
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

if not check_password():
    st.stop()

stores, products, sp = load_data()

st.sidebar.title("📊 דשבורד מכירות")
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

stores['שינוי_שנתי'] = stores.apply(lambda r: chg(r['שנה2'], r['שנה1']), axis=1)
stores['שינוי_6v6'] = stores.apply(lambda r: chg(r['6v6_H2'], r['6v6_H1']), axis=1)
stores['שינוי_3v3'] = stores.apply(lambda r: chg(r['3v3_שנה2'], r['3v3_שנה1']), axis=1)
stores['שינוי_רבעוני'] = stores.apply(lambda r: chg(r['3v3_Q3'], r['3v3_Q2']), axis=1)
stores['שינוי_2v2'] = stores.apply(lambda r: chg(r['2v2_אחרון'], r['2v2_קודם']), axis=1)
stores['סטטוס'] = stores.apply(lambda r: calc_status(r, th), axis=1)
stores['דירוג'] = stores['שנה2'].rank(ascending=False, method='min').astype(int)

active = stores[stores['2v2_אחרון'] > 0].copy()
closed = stores[stores['2v2_אחרון'] == 0].copy()

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

tabs = st.tabs(["📊 דשבורד", "🏪 חנויות", "📦 מוצרים", "🔍 בחירת חנות", "🔎 בחירת מוצר", "🚫 סגורות", "📈 מגמות", "⚠️ אזעקות", "🎯 פוטנציאל"])

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
        sc = filtered['סטטוס'].value_counts()
        colors = {'צמיחה': '#28a745', 'יציב': '#17a2b8', 'שחיקה': '#ffc107', 'התאוששות': '#9c27b0', 'סכנה': '#dc3545', 'חדש/ה': '#ff9800'}
        fig = px.pie(values=sc.values, names=sc.index, color=sc.index, color_discrete_map=colors, hole=0.4)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.subheader("🏙️ Top 10 ערים")
        cs = filtered.groupby('עיר')['שנה2'].sum().nlargest(10).reset_index()
        fig = px.bar(cs, x='שנה2', y='עיר', orientation='h', text=cs['שנה2'].apply(fmt_num))
        fig.update_layout(yaxis={'categoryorder': 'total ascending'})
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🏆 Top 10")
        t = filtered.nlargest(10, 'שנה2')[['שם חנות', 'עיר', 'שנה2', 'שינוי_שנתי', 'סטטוס']].copy()
        t['שנה2'] = t['שנה2'].apply(fmt_num)
        t['שינוי_שנתי'] = t['שינוי_שנתי'].apply(fmt_pct)
        st.dataframe(t, hide_index=True, use_container_width=True)
    with c2:
        st.subheader("⚠️ Bottom 10")
        b = filtered[filtered['שנה1'] > 0].nsmallest(10, 'שינוי_שנתי')[['שם חנות', 'עיר', 'שנה2', 'שינוי_שנתי', 'סטטוס']].copy()
        b['שנה2'] = b['שנה2'].apply(fmt_num)
        b['שינוי_שנתי'] = b['שינוי_שנתי'].apply(fmt_pct)
        st.dataframe(b, hide_index=True, use_container_width=True)

with tabs[1]:
    st.title("🏪 חנויות - כל הנתונים")
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
    
    st.markdown("---")
    pd2 = products[['מזהה', 'מוצר', 'סיווג', 'שנה1', 'שנה2', 'שינוי', 'חנויות_שנה2']].copy()
    pd2['שנה1'] = pd2['שנה1'].apply(fmt_num)
    pd2['שנה2'] = pd2['שנה2'].apply(fmt_num)
    pd2['שינוי'] = pd2['שינוי'].apply(fmt_pct)
    st.dataframe(pd2, hide_index=True, use_container_width=True)

with tabs[3]:
    st.title("🔍 בחירת חנות")
    opts = active.apply(lambda r: f"{r['מזהה']} - {r['שם חנות']}", axis=1).tolist()
    sel = st.selectbox("בחר:", ['בחר...'] + sorted(opts))
    if sel != 'בחר...':
        sid = int(sel.split(' - ')[0])
        info = active[active['מזהה'] == sid].iloc[0]
        
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
        st.subheader("📊 מדדים")
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown("**6v6**")
        c1.metric("H1", fmt_num(info['6v6_H1']))
        c1.metric("H2", fmt_num(info['6v6_H2']))
        c1.metric("שינוי", fmt_pct(info['שינוי_6v6']))
        c2.markdown("**3v3**")
        c2.metric("שנה1", fmt_num(info['3v3_שנה1']))
        c2.metric("שנה2", fmt_num(info['3v3_שנה2']))
        c2.metric("שינוי", fmt_pct(info['שינוי_3v3']))
        c3.markdown("**רבעונים**")
        c3.metric("Q2", fmt_num(info['3v3_Q2']))
        c3.metric("Q3", fmt_num(info['3v3_Q3']))
        c3.metric("שינוי", fmt_pct(info['שינוי_רבעוני']))
        c4.markdown("**2v2**")
        c4.metric("קודם", fmt_num(info['2v2_קודם']))
        c4.metric("אחרון", fmt_num(info['2v2_אחרון']))
        c4.metric("שינוי", fmt_pct(info['שינוי_2v2']))
        
        st.markdown("---")
        st.subheader("📦 מוצרים בחנות")
        sp2 = sp[sp['מזהה_חנות'] == sid].copy()
        if len(sp2) > 0:
            sp2['שינוי'] = sp2.apply(lambda r: chg(r['שנה2'], r['שנה1']), axis=1)
            sp2 = sp2.sort_values('שנה2', ascending=False)
            d = sp2[['מוצר', 'סיווג', 'שנה1', 'שנה2', 'שינוי', '2v2_קודם', '2v2_אחרון']].copy()
            d['שנה1'] = d['שנה1'].apply(fmt_num)
            d['שנה2'] = d['שנה2'].apply(fmt_num)
            d['שינוי'] = d['שינוי'].apply(fmt_pct)
            d['2v2_קודם'] = d['2v2_קודם'].apply(fmt_num)
            d['2v2_אחרון'] = d['2v2_אחרון'].apply(fmt_num)
            st.dataframe(d, hide_index=True, use_container_width=True, height=400)

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
        ps = sp[sp['מזהה_מוצר'] == pid].copy()
        ps = ps[ps['מזהה_חנות'].isin(active['מזהה'])]
        if len(ps) > 0:
            selling = len(ps[ps['שנה2'] > 0])
            pen = selling / len(active) * 100
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
        
        st.markdown("---")
        cc = closed.groupby('עיר').size().reset_index(name='כמות').sort_values('כמות', ascending=False)
        fig = px.bar(cc.head(10), x='עיר', y='כמות', text='כמות')
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
        
        d = closed[['מזהה', 'שם חנות', 'עיר', 'שנה1']].sort_values('שנה1', ascending=False).copy()
        d['שנה1'] = d['שנה1'].apply(fmt_num)
        st.dataframe(d, hide_index=True, use_container_width=True)
    else:
        st.success("אין חנויות סגורות!")

with tabs[6]:
    st.title("📈 מגמות")
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
        fig = px.bar(pd.DataFrame({'תקופה': ['שנה1', 'שנה2'], 'מכירות': [y1, y2]}), x='תקופה', y='מכירות', text='מכירות', color='תקופה')
        fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.subheader("Q2 vs Q3")
        q2, q3 = active['3v3_Q2'].sum(), active['3v3_Q3'].sum()
        st.metric("שינוי", fmt_pct(chg(q3, q2)))
        fig = px.bar(pd.DataFrame({'תקופה': ['Q2', 'Q3'], 'מכירות': [q2, q3]}), x='תקופה', y='מכירות', text='מכירות', color='תקופה')
        fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

with tabs[7]:
    st.title("⚠️ אזעקות ו-Recovery")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🚨 אזעקות")
        st.caption(f"ירידה > {abs(th['אזעקה'])*100:.0f}%")
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
    
    sp_act = sp[sp['מזהה_חנות'].isin(active['מזהה'])]
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
        
        fig = px.bar(pot_df.head(20), x='חנות', y='פוטנציאל', color='חסרים', text=pot_df.head(20)['פוטנציאל'].apply(fmt_num))
        fig.update_layout(xaxis_tickangle=-45)
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
        
        d = pot_df.copy()
        d['מכירות'] = d['מכירות'].apply(fmt_num)
        d['פוטנציאל'] = d['פוטנציאל'].apply(fmt_num)
        st.dataframe(d, hide_index=True, use_container_width=True)
        st.download_button("📥 הורד", to_excel(pot_df, 'פוטנציאל'), "פוטנציאל.xlsx")
    else:
        st.warning("אין פוטנציאל בסף הנבחר")

#!/usr/bin/env python3
"""
דשבורד ניתוח מכירות - גרסה מלאה V4
עם חיבור ל-Google Sheets והיסטוריה
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
from datetime import datetime

# הגדרות עמוד
st.set_page_config(
    page_title="דשבורד ניתוח מכירות",
    page_icon="📊",
    layout="wide"
)

# CSS
st.markdown("""
<style>
    .main > div { direction: rtl; text-align: right; }
    h1, h2, h3, p { direction: rtl; text-align: right; }
    .stTabs [data-baseweb="tab-list"] { direction: rtl; }
</style>
""", unsafe_allow_html=True)


# ========================================
# הגדרות ברירת מחדל
# ========================================
DEFAULT_THRESHOLDS = {
    'צמיחה_שנתי': 0.05,
    'צמיחה_6v6': -0.05,
    'יציב_עליון': 0.05,
    'יציב_תחתון': -0.05,
    'יציב_6v6': -0.10,
    'שחיקה_שנתי': -0.05,
    'סכנה_שנתי': -0.15,
    'סכנה_6v6': -0.10,
    'אזעקה_2v2': -0.15,
    'recovery_2v2': 0.0
}


# ========================================
# פונקציות עזר
# ========================================
@st.cache_data
def load_data(uploaded_file):
    stores = pd.read_excel(uploaded_file, sheet_name='נתוני בסיס חנויות')
    products = pd.read_excel(uploaded_file, sheet_name='נתוני בסיס מוצרים')
    sp = pd.read_excel(uploaded_file, sheet_name='מוצרים-חנויות')
    return stores, products, sp


def calculate_status(row, thresholds):
    if row['שנה1'] == 0:
        return 'חדש/ה'
    
    change = row['שינוי_שנתי']
    change_6v6 = row.get('שינוי_6v6', 0)
    change_3v3 = row.get('שינוי_3v3', 0)
    
    if change < thresholds['סכנה_שנתי'] and change_6v6 < thresholds['סכנה_6v6']:
        return 'סכנה'
    elif change < thresholds['שחיקה_שנתי'] and change_6v6 > 0.05 and change_3v3 > 0:
        return 'התאוששות'
    elif change > thresholds['צמיחה_שנתי'] and change_6v6 > thresholds['צמיחה_6v6']:
        return 'צמיחה'
    elif change >= thresholds['יציב_תחתון'] and change <= thresholds['יציב_עליון']:
        return 'יציב'
    else:
        return 'שחיקה'


def calculate_all_metrics(stores, thresholds):
    """חישוב כל המדדים לחנויות"""
    df = stores.copy()
    
    # שינוי שנתי
    df['שינוי_שנתי'] = df.apply(
        lambda r: (r['שנה2'] - r['שנה1']) / r['שנה1'] if r['שנה1'] > 0 else 0,
        axis=1
    )
    
    # שינוי 6v6
    if '6v6_H1' in df.columns and '6v6_H2' in df.columns:
        df['שינוי_6v6'] = df.apply(
            lambda r: (r['6v6_H2'] - r['6v6_H1']) / r['6v6_H1'] if r['6v6_H1'] > 0 else 0,
            axis=1
        )
    
    # שינוי 3v3
    if '3v3_שנה1' in df.columns and '3v3_שנה2' in df.columns:
        df['שינוי_3v3'] = df.apply(
            lambda r: (r['3v3_שנה2'] - r['3v3_שנה1']) / r['3v3_שנה1'] if r['3v3_שנה1'] > 0 else 0,
            axis=1
        )
    
    # שינוי רבעוני Q2 vs Q3
    if '3v3_Q2' in df.columns and '3v3_Q3' in df.columns:
        df['שינוי_רבעוני'] = df.apply(
            lambda r: (r['3v3_Q3'] - r['3v3_Q2']) / r['3v3_Q2'] if r['3v3_Q2'] > 0 else 0,
            axis=1
        )
    
    # שינוי 2v2
    if '2v2_קודם' in df.columns and '2v2_אחרון' in df.columns:
        df['שינוי_2v2'] = df.apply(
            lambda r: (r['2v2_אחרון'] - r['2v2_קודם']) / r['2v2_קודם'] if r['2v2_קודם'] > 0 else 0,
            axis=1
        )
    
    # סטטוס
    df['סטטוס'] = df.apply(lambda r: calculate_status(r, thresholds), axis=1)
    
    # דירוג
    df['דירוג'] = df['שנה2'].rank(ascending=False, method='min').astype(int)
    
    return df


def calculate_potential(stores, sp, min_penetration=0.7):
    if '2v2_אחרון' in stores.columns:
        active_stores = stores[stores['2v2_אחרון'] > 0]
    else:
        active_stores = stores[stores['שנה2'] > 0]
    
    num_active = len(active_stores)
    if num_active == 0:
        return pd.DataFrame()
    
    active_ids = set(active_stores['מזהה'])
    sp_active = sp[sp['מזהה_חנות'].isin(active_ids)]
    
    product_stats = sp_active[sp_active['שנה2'] > 0].groupby('מזהה_מוצר').agg({
        'מזהה_חנות': 'nunique',
        'שנה2': 'mean'
    }).reset_index()
    product_stats.columns = ['מזהה_מוצר', 'חנויות', 'ממוצע']
    product_stats['חדירה'] = product_stats['חנויות'] / num_active
    
    high_pen = product_stats[product_stats['חדירה'] >= min_penetration]
    high_pen_ids = set(high_pen['מזהה_מוצר'])
    
    store_products = sp_active[sp_active['שנה2'] > 0].groupby('מזהה_חנות')['מזהה_מוצר'].apply(set).to_dict()
    
    potential_data = []
    for _, store in active_stores.iterrows():
        store_prods = store_products.get(store['מזהה'], set())
        missing = high_pen_ids - store_prods
        
        if len(missing) > 0:
            potential = sum(
                high_pen[high_pen['מזהה_מוצר'] == pid]['ממוצע'].values[0]
                for pid in missing
                if pid in high_pen['מזהה_מוצר'].values
            )
            
            potential_data.append({
                'מזהה': store['מזהה'],
                'חנות': store['שם חנות'],
                'עיר': store.get('עיר', ''),
                'מכירות': store['שנה2'],
                'מוצרים_חסרים': len(missing),
                'פוטנציאל': round(potential)
            })
    
    return pd.DataFrame(potential_data).sort_values('פוטנציאל', ascending=False)


def create_download_excel(df, sheet_name='נתונים'):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    return output.getvalue()


def get_store_products(sp, store_id):
    store_data = sp[sp['מזהה_חנות'] == store_id].copy()
    if len(store_data) == 0:
        return pd.DataFrame()
    
    store_data['שינוי_שנתי'] = store_data.apply(
        lambda r: (r['שנה2'] - r['שנה1']) / r['שנה1'] if r['שנה1'] > 0 else 0,
        axis=1
    )
    
    if '6v6_H1' in store_data.columns and '6v6_H2' in store_data.columns:
        store_data['שינוי_6v6'] = store_data.apply(
            lambda r: (r['6v6_H2'] - r['6v6_H1']) / r['6v6_H1'] if r['6v6_H1'] > 0 else 0,
            axis=1
        )
    
    if '3v3_שנה1' in store_data.columns and '3v3_שנה2' in store_data.columns:
        store_data['שינוי_3v3'] = store_data.apply(
            lambda r: (r['3v3_שנה2'] - r['3v3_שנה1']) / r['3v3_שנה1'] if r['3v3_שנה1'] > 0 else 0,
            axis=1
        )
    
    if '2v2_קודם' in store_data.columns and '2v2_אחרון' in store_data.columns:
        store_data['שינוי_2v2'] = store_data.apply(
            lambda r: (r['2v2_אחרון'] - r['2v2_קודם']) / r['2v2_קודם'] if r['2v2_קודם'] > 0 else 0,
            axis=1
        )
    
    return store_data.sort_values('שנה2', ascending=False)


def get_product_stores(sp, product_id):
    product_data = sp[sp['מזהה_מוצר'] == product_id].copy()
    if len(product_data) == 0:
        return pd.DataFrame()
    
    product_data['שינוי_שנתי'] = product_data.apply(
        lambda r: (r['שנה2'] - r['שנה1']) / r['שנה1'] if r['שנה1'] > 0 else 0,
        axis=1
    )
    
    return product_data.sort_values('שנה2', ascending=False)


def format_percent(val):
    if pd.isna(val):
        return ""
    return f"{val:.1%}"


def format_number(val):
    if pd.isna(val):
        return ""
    return f"{val:,.0f}"


# ========================================
# סרגל צד
# ========================================
st.sidebar.title("📊 דשבורד מכירות V4")
st.sidebar.markdown("---")

uploaded_file = st.sidebar.file_uploader(
    "📁 העלה קובץ סיכומים",
    type=['xlsx']
)

# הגדרות ספים
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ הגדרות ספים")

with st.sidebar.expander("שנה ספי סטטוס"):
    thresholds = {}
    thresholds['צמיחה_שנתי'] = st.slider("סף צמיחה (שנתי)", 0.0, 0.20, 0.05, 0.01)
    thresholds['צמיחה_6v6'] = st.slider("סף צמיחה (6v6)", -0.20, 0.10, -0.05, 0.01)
    thresholds['יציב_עליון'] = thresholds['צמיחה_שנתי']
    thresholds['יציב_תחתון'] = st.slider("סף יציב תחתון", -0.15, 0.0, -0.05, 0.01)
    thresholds['יציב_6v6'] = st.slider("סף יציב (6v6)", -0.20, 0.0, -0.10, 0.01)
    thresholds['שחיקה_שנתי'] = thresholds['יציב_תחתון']
    thresholds['סכנה_שנתי'] = st.slider("סף סכנה (שנתי)", -0.30, 0.0, -0.15, 0.01)
    thresholds['סכנה_6v6'] = st.slider("סף סכנה (6v6)", -0.30, 0.0, -0.10, 0.01)
    thresholds['אזעקה_2v2'] = st.slider("סף אזעקה (2v2)", -0.30, 0.0, -0.15, 0.01)
    thresholds['recovery_2v2'] = st.slider("סף Recovery (2v2)", -0.10, 0.10, 0.0, 0.01)


if uploaded_file is not None:
    # טעינת נתונים
    stores, products, sp = load_data(uploaded_file)
    
    # חישוב מדדים
    stores = calculate_all_metrics(stores, thresholds)
    
    # סינון חנויות פעילות/סגורות
    if '2v2_אחרון' in stores.columns:
        active_stores = stores[stores['2v2_אחרון'] > 0].copy()
        closed_stores = stores[stores['2v2_אחרון'] == 0].copy()
    else:
        active_stores = stores[stores['שנה2'] > 0].copy()
        closed_stores = stores[stores['שנה2'] == 0].copy()
    
    # סינונים בסרגל צד
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 סינונים")
    
    cities = ['הכל'] + sorted([c for c in active_stores['עיר'].dropna().unique().tolist() if c])
    selected_city = st.sidebar.selectbox("עיר", cities)
    
    statuses = ['הכל'] + list(active_stores['סטטוס'].unique())
    selected_status = st.sidebar.selectbox("סטטוס", statuses)
    
    filtered = active_stores.copy()
    if selected_city != 'הכל':
        filtered = filtered[filtered['עיר'] == selected_city]
    if selected_status != 'הכל':
        filtered = filtered[filtered['סטטוס'] == selected_status]
    
    # סטטיסטיקות
    st.sidebar.markdown("---")
    st.sidebar.subheader("📈 סטטיסטיקות")
    st.sidebar.write(f"חנויות פעילות: **{len(active_stores)}**")
    st.sidebar.write(f"חנויות סגורות: **{len(closed_stores)}**")
    st.sidebar.write(f"מוצרים: **{len(products)}**")
    
    # ========================================
    # טאבים
    # ========================================
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "📊 דשבורד",
        "🏪 חנויות",
        "📦 מוצרים",
        "🔍 בחירת חנות",
        "🔎 בחירת מוצר",
        "🚫 חנויות סגורות",
        "📈 מגמות",
        "⚠️ אזעקות",
        "🎯 פוטנציאל"
    ])
    
    # ========================================
    # טאב 1: דשבורד
    # ========================================
    with tab1:
        st.title("📊 דשבורד ראשי")
        
        # KPIs
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            total_sales = filtered['שנה2'].sum()
            prev_sales = filtered['שנה1'].sum()
            change = (total_sales - prev_sales) / prev_sales * 100 if prev_sales > 0 else 0
            st.metric("סה״כ מכירות", format_number(total_sales), f"{change:.1f}%")
        
        with col2:
            st.metric("חנויות פעילות", len(filtered))
        
        with col3:
            st.metric("חנויות סגורות", len(closed_stores))
        
        with col4:
            growth = len(filtered[filtered['סטטוס'] == 'צמיחה'])
            st.metric("בצמיחה", growth, f"{growth/len(filtered)*100:.0f}%" if len(filtered) > 0 else "0%")
        
        with col5:
            danger = len(filtered[filtered['סטטוס'].isin(['סכנה', 'שחיקה'])])
            st.metric("בסיכון", danger, f"-{danger/len(filtered)*100:.0f}%" if len(filtered) > 0 else "0%", delta_color="inverse")
        
        st.markdown("---")
        
        # גרפים
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 התפלגות סטטוסים")
            status_counts = filtered['סטטוס'].value_counts()
            colors = {
                'צמיחה': '#28a745', 'יציב': '#17a2b8', 'שחיקה': '#ffc107',
                'התאוששות': '#9c27b0', 'סכנה': '#dc3545', 'חדש/ה': '#ff9800'
            }
            fig = px.pie(values=status_counts.values, names=status_counts.index,
                        color=status_counts.index, color_discrete_map=colors, hole=0.4)
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("🏙️ Top 10 ערים")
            city_sales = filtered.groupby('עיר')['שנה2'].sum().nlargest(10).reset_index()
            fig = px.bar(city_sales, x='שנה2', y='עיר', orientation='h',
                        color='שנה2', color_continuous_scale='Blues')
            fig.update_layout(yaxis={'categoryorder': 'total ascending'}, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        # Top/Bottom
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏆 Top 10 חנויות")
            top = filtered.nlargest(10, 'שנה2')[['שם חנות', 'עיר', 'שנה2', 'שינוי_שנתי', 'סטטוס', 'דירוג']].copy()
            top['שינוי_שנתי'] = top['שינוי_שנתי'].apply(format_percent)
            top['שנה2'] = top['שנה2'].apply(format_number)
            st.dataframe(top, use_container_width=True, hide_index=True)
        
        with col2:
            st.subheader("⚠️ Bottom 10 חנויות")
            bottom = filtered[filtered['שנה1'] > 0].nsmallest(10, 'שינוי_שנתי')
            bottom = bottom[['שם חנות', 'עיר', 'שנה2', 'שינוי_שנתי', 'סטטוס', 'דירוג']].copy()
            bottom['שינוי_שנתי'] = bottom['שינוי_שנתי'].apply(format_percent)
            bottom['שנה2'] = bottom['שנה2'].apply(format_number)
            st.dataframe(bottom, use_container_width=True, hide_index=True)
    
    # ========================================
    # טאב 2: חנויות (עם כל העמודות)
    # ========================================
    with tab2:
        st.title("🏪 ניתוח חנויות - כל הנתונים")
        
        # סיכום סטטוסים
        st.subheader("📊 סיכום לפי סטטוס")
        status_summary = filtered.groupby('סטטוס').agg({
            'מזהה': 'count',
            'שנה1': 'sum',
            'שנה2': 'sum'
        }).reset_index()
        status_summary.columns = ['סטטוס', 'כמות', 'שנה1', 'שנה2']
        status_summary['שינוי'] = (status_summary['שנה2'] - status_summary['שנה1']) / status_summary['שנה1']
        status_summary['שינוי'] = status_summary['שינוי'].apply(format_percent)
        status_summary['שנה1'] = status_summary['שנה1'].apply(format_number)
        status_summary['שנה2'] = status_summary['שנה2'].apply(format_number)
        st.dataframe(status_summary, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # טבלה מלאה עם כל העמודות
        st.subheader("📋 כל החנויות - נתונים מלאים")
        
        # בחירת עמודות להצגה
        all_columns = ['מזהה', 'שם חנות', 'עיר', 'שנה1', 'שנה2', 'שינוי_שנתי']
        
        if '6v6_H1' in filtered.columns:
            all_columns.extend(['6v6_H1', '6v6_H2', 'שינוי_6v6'])
        if '3v3_שנה1' in filtered.columns:
            all_columns.extend(['3v3_שנה1', '3v3_שנה2', 'שינוי_3v3'])
        if '3v3_Q2' in filtered.columns:
            all_columns.extend(['3v3_Q2', '3v3_Q3', 'שינוי_רבעוני'])
        if '2v2_קודם' in filtered.columns:
            all_columns.extend(['2v2_קודם', '2v2_אחרון', 'שינוי_2v2'])
        
        all_columns.extend(['סטטוס', 'דירוג'])
        
        # הצגה
        display_df = filtered[[c for c in all_columns if c in filtered.columns]].copy()
        
        # פורמט
        for col in display_df.columns:
            if 'שינוי' in col:
                display_df[col] = display_df[col].apply(format_percent)
        
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=500)
        
        # הורדה
        excel_data = create_download_excel(filtered, 'חנויות')
        st.download_button("📥 הורד לאקסל", excel_data, "חנויות_מלא.xlsx",
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
    # ========================================
    # טאב 3: מוצרים
    # ========================================
    with tab3:
        st.title("📦 ניתוח מוצרים")
        
        products_calc = products.copy()
        products_calc['שינוי'] = products_calc.apply(
            lambda r: (r['שנה2'] - r['שנה1']) / r['שנה1'] if r['שנה1'] > 0 else 0,
            axis=1
        )
        products_calc['דירוג'] = products_calc['שנה2'].rank(ascending=False, method='min').astype(int)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏆 Top 10 מוצרים")
            top_p = products_calc.nlargest(10, 'שנה2')[['מוצר', 'סיווג', 'שנה2', 'שינוי', 'דירוג']].copy()
            top_p['שינוי'] = top_p['שינוי'].apply(format_percent)
            top_p['שנה2'] = top_p['שנה2'].apply(format_number)
            st.dataframe(top_p, use_container_width=True, hide_index=True)
        
        with col2:
            st.subheader("📊 מכירות לפי סיווג")
            class_sales = products_calc.groupby('סיווג')['שנה2'].sum().reset_index()
            fig = px.pie(class_sales, values='שנה2', names='סיווג', hole=0.3)
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.subheader("📋 כל המוצרים")
        
        display_p = products_calc[['מזהה', 'מוצר', 'סיווג', 'שנה1', 'שנה2', 'שינוי', 'דירוג']].copy()
        display_p['שינוי'] = display_p['שינוי'].apply(format_percent)
        st.dataframe(display_p, use_container_width=True, hide_index=True)
    
    # ========================================
    # טאב 4: בחירת חנות (מלא כמו באקסל)
    # ========================================
    with tab4:
        st.title("🔍 בחירת חנות - ניתוח מלא")
        
        store_options = active_stores.apply(
            lambda r: f"{r['מזהה']} - {r['שם חנות']} ({r['עיר'] if pd.notna(r['עיר']) else ''})",
            axis=1
        ).tolist()
        
        selected_store_str = st.selectbox("בחר חנות:", [''] + store_options)
        
        if selected_store_str:
            store_id = int(selected_store_str.split(' - ')[0])
            store_info = active_stores[active_stores['מזהה'] == store_id].iloc[0]
            
            # פרטי חנות
            st.subheader("📋 פרטי חנות")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("מזהה", store_info['מזהה'])
            with col2:
                st.metric("שם", store_info['שם חנות'])
            with col3:
                st.metric("עיר", store_info['עיר'] if pd.notna(store_info['עיר']) else '-')
            with col4:
                st.metric("דירוג", f"#{int(store_info['דירוג'])}")
            
            st.markdown("---")
            
            # מדדים מלאים
            st.subheader("📊 מדדים")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("שנה1", format_number(store_info['שנה1']))
                st.metric("שנה2", format_number(store_info['שנה2']))
                st.metric("שינוי שנתי", format_percent(store_info['שינוי_שנתי']))
            
            with col2:
                if '6v6_H1' in store_info:
                    st.metric("6v6 H1", format_number(store_info['6v6_H1']))
                    st.metric("6v6 H2", format_number(store_info['6v6_H2']))
                    st.metric("שינוי 6v6", format_percent(store_info.get('שינוי_6v6', 0)))
            
            with col3:
                if '3v3_שנה1' in store_info:
                    st.metric("3v3 שנה1", format_number(store_info['3v3_שנה1']))
                    st.metric("3v3 שנה2", format_number(store_info['3v3_שנה2']))
                    st.metric("שינוי 3v3", format_percent(store_info.get('שינוי_3v3', 0)))
            
            with col4:
                if '2v2_קודם' in store_info:
                    st.metric("2v2 קודם", format_number(store_info['2v2_קודם']))
                    st.metric("2v2 אחרון", format_number(store_info['2v2_אחרון']))
                    st.metric("שינוי 2v2", format_percent(store_info.get('שינוי_2v2', 0)))
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("סטטוס", store_info['סטטוס'])
            with col2:
                if '3v3_Q2' in store_info:
                    st.metric("שינוי רבעוני (Q2→Q3)", format_percent(store_info.get('שינוי_רבעוני', 0)))
            
            st.markdown("---")
            
            # מוצרים של החנות
            st.subheader("📦 מוצרים בחנות")
            store_products_df = get_store_products(sp, store_id)
            
            if len(store_products_df) > 0:
                # עמודות להצגה
                sp_cols = ['מזהה_מוצר', 'מוצר', 'סיווג', 'שנה1', 'שנה2', 'שינוי_שנתי']
                if 'שינוי_6v6' in store_products_df.columns:
                    sp_cols.append('שינוי_6v6')
                if 'שינוי_3v3' in store_products_df.columns:
                    sp_cols.append('שינוי_3v3')
                if 'שינוי_2v2' in store_products_df.columns:
                    sp_cols.append('שינוי_2v2')
                
                display_sp = store_products_df[[c for c in sp_cols if c in store_products_df.columns]].copy()
                
                for col in display_sp.columns:
                    if 'שינוי' in col:
                        display_sp[col] = display_sp[col].apply(format_percent)
                
                st.dataframe(display_sp, use_container_width=True, hide_index=True, height=400)
                
                # גרף
                fig = px.bar(
                    store_products_df.nlargest(15, 'שנה2'),
                    x='מוצר', y='שנה2', color='סיווג',
                    title='Top 15 מוצרים בחנות'
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
    
    # ========================================
    # טאב 5: בחירת מוצר
    # ========================================
    with tab5:
        st.title("🔎 בחירת מוצר - ניתוח מלא")
        
        product_options = products.apply(
            lambda r: f"{r['מזהה']} - {r['מוצר']}",
            axis=1
        ).tolist()
        
        selected_product_str = st.selectbox("בחר מוצר:", [''] + product_options)
        
        if selected_product_str:
            product_id = int(selected_product_str.split(' - ')[0])
            product_info = products[products['מזהה'] == product_id].iloc[0]
            
            # פרטי מוצר
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("מוצר", product_info['מוצר'])
            with col2:
                st.metric("סיווג", product_info['סיווג'] if pd.notna(product_info['סיווג']) else '-')
            with col3:
                st.metric("מכירות שנה2", format_number(product_info['שנה2']))
            with col4:
                change = (product_info['שנה2'] - product_info['שנה1']) / product_info['שנה1'] if product_info['שנה1'] > 0 else 0
                st.metric("שינוי", format_percent(change))
            
            st.markdown("---")
            
            # חנויות
            st.subheader("🏪 חנויות שמוכרות את המוצר")
            product_stores_df = get_product_stores(sp, product_id)
            product_stores_df = product_stores_df[product_stores_df['מזהה_חנות'].isin(active_stores['מזהה'])]
            
            if len(product_stores_df) > 0:
                penetration = len(product_stores_df[product_stores_df['שנה2'] > 0]) / len(active_stores) * 100
                st.info(f"📊 חדירה: **{penetration:.1f}%** ({len(product_stores_df[product_stores_df['שנה2'] > 0])} מתוך {len(active_stores)} חנויות)")
                
                display_ps = product_stores_df[['מזהה_חנות', 'שם_חנות', 'עיר', 'שנה1', 'שנה2', 'שינוי_שנתי']].copy()
                display_ps.columns = ['מזהה', 'חנות', 'עיר', 'שנה1', 'שנה2', 'שינוי']
                display_ps['שינוי'] = display_ps['שינוי'].apply(format_percent)
                st.dataframe(display_ps, use_container_width=True, hide_index=True, height=400)
    
    # ========================================
    # טאב 6: חנויות סגורות
    # ========================================
    with tab6:
        st.title("🚫 חנויות סגורות")
        
        if len(closed_stores) > 0:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("סה״כ סגורות", len(closed_stores))
            with col2:
                st.metric("מכירות שאבדו", format_number(closed_stores['שנה1'].sum()))
            with col3:
                pct = len(closed_stores) / (len(active_stores) + len(closed_stores)) * 100
                st.metric("אחוז מסה״כ", f"{pct:.1f}%")
            
            st.markdown("---")
            
            display_closed = closed_stores[['מזהה', 'שם חנות', 'עיר', 'שנה1', 'שנה2']].copy()
            display_closed = display_closed.sort_values('שנה1', ascending=False)
            st.dataframe(display_closed, use_container_width=True, hide_index=True)
        else:
            st.success("🎉 אין חנויות סגורות!")
    
    # ========================================
    # טאב 7: מגמות
    # ========================================
    with tab7:
        st.title("📈 מגמות והשוואת תקופות")
        
        has_periods = '6v6_H1' in active_stores.columns
        
        if has_periods:
            # גרף מגמות
            st.subheader("📊 מגמת מכירות")
            
            periods = ['שנה1', '6v6_H1', '6v6_H2']
            labels = ['שנה 1', 'H1 שנה2', 'H2 שנה2']
            
            if '3v3_Q2' in active_stores.columns:
                periods.extend(['3v3_Q2', '3v3_Q3'])
                labels.extend(['Q2', 'Q3'])
            
            values = [active_stores[p].sum() for p in periods]
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=labels, y=values,
                mode='lines+markers+text',
                text=[format_number(v) for v in values],
                textposition='top center',
                line=dict(width=3),
                marker=dict(size=12)
            ))
            fig.update_layout(title='מגמת מכירות לאורך זמן', height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            # השוואות
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("שנה1 vs שנה2")
                comp1 = pd.DataFrame({
                    'תקופה': ['שנה 1', 'שנה 2'],
                    'מכירות': [active_stores['שנה1'].sum(), active_stores['שנה2'].sum()]
                })
                fig1 = px.bar(comp1, x='תקופה', y='מכירות', color='תקופה', text='מכירות')
                fig1.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                st.subheader("H1 vs H2")
                comp2 = pd.DataFrame({
                    'תקופה': ['H1', 'H2'],
                    'מכירות': [active_stores['6v6_H1'].sum(), active_stores['6v6_H2'].sum()]
                })
                fig2 = px.bar(comp2, x='תקופה', y='מכירות', color='תקופה', text='מכירות')
                fig2.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                st.plotly_chart(fig2, use_container_width=True)
            
            # Q2 vs Q3
            if '3v3_Q2' in active_stores.columns:
                st.markdown("---")
                st.subheader("📊 Q2 vs Q3")
                
                q2 = active_stores['3v3_Q2'].sum()
                q3 = active_stores['3v3_Q3'].sum()
                q_change = (q3 - q2) / q2 * 100 if q2 > 0 else 0
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Q2 (6-8/25)", format_number(q2))
                with col2:
                    st.metric("Q3 (9-11/25)", format_number(q3))
                with col3:
                    st.metric("שינוי", f"{q_change:.1f}%")
    
    # ========================================
    # טאב 8: אזעקות
    # ========================================
    with tab8:
        st.title("⚠️ אזעקות ו-Recovery")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🚨 אזעקות")
            if 'שינוי_2v2' in active_stores.columns:
                alerts = active_stores[active_stores['שינוי_2v2'] < thresholds['אזעקה_2v2']].copy()
                alerts = alerts.sort_values('שינוי_2v2')
                
                if len(alerts) > 0:
                    st.error(f"נמצאו {len(alerts)} חנויות!")
                    display_alerts = alerts[['שם חנות', 'עיר', 'שנה2', 'שינוי_2v2', 'סטטוס']].head(20).copy()
                    display_alerts['שינוי_2v2'] = display_alerts['שינוי_2v2'].apply(lambda x: f"{x:.1%} ⚠️")
                    st.dataframe(display_alerts, use_container_width=True, hide_index=True)
                else:
                    st.success("אין אזעקות!")
        
        with col2:
            st.subheader("💚 Recovery")
            if 'שינוי_2v2' in active_stores.columns:
                recovery = active_stores[
                    (active_stores['סטטוס'].isin(['שחיקה', 'סכנה'])) &
                    (active_stores['שינוי_2v2'] > thresholds['recovery_2v2'])
                ].copy()
                recovery = recovery.sort_values('שינוי_2v2', ascending=False)
                
                if len(recovery) > 0:
                    st.success(f"נמצאו {len(recovery)} חנויות!")
                    display_rec = recovery[['שם חנות', 'עיר', 'שנה2', 'שינוי_2v2', 'סטטוס']].head(20).copy()
                    display_rec['שינוי_2v2'] = display_rec['שינוי_2v2'].apply(lambda x: f"{x:.1%} ↑")
                    st.dataframe(display_rec, use_container_width=True, hide_index=True)
                else:
                    st.info("אין חנויות בהתאוששות")
    
    # ========================================
    # טאב 9: פוטנציאל
    # ========================================
    with tab9:
        st.title("🎯 פוטנציאל חנויות")
        
        min_pen = st.slider("סף חדירה", 0.5, 0.9, 0.7, 0.05)
        potential_df = calculate_potential(stores, sp, min_pen)
        
        if len(potential_df) > 0:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("חנויות", len(potential_df))
            with col2:
                st.metric("סה״כ פוטנציאל", format_number(potential_df['פוטנציאל'].sum()))
            with col3:
                st.metric("ממוצע", format_number(potential_df['פוטנציאל'].mean()))
            
            st.markdown("---")
            st.dataframe(potential_df, use_container_width=True, hide_index=True)
            
            excel_data = create_download_excel(potential_df, 'פוטנציאל')
            st.download_button("📥 הורד", excel_data, "פוטנציאל.xlsx")

else:
    st.title("📊 דשבורד ניתוח מכירות V4")
    st.info("👋 העלה קובץ סיכומים בסרגל הצד כדי להתחיל")

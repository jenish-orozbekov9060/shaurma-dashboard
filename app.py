import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ============================================================
# НАСТРОЙКИ ШАУРМЫ
# ============================================================
PARTNER_NAME = "Шаурма на углях"
EXCEL_PATH = "data.xlsx" # Файл с причинами отмен
REASON_COLUMN = "Причина отмены" # Колонка в Excel

GREEN = "#2E9E4F"
RED = "#D64545"

# ТАРГЕТЫ
TARGETS = {"cancels": 0.80, "wrongs": 0.60, "bf": 0.30}

# ДАННЫЕ (взяты из ваших скриншотов BI)
KPI = {
    "cancels": {"label": "Отмены", "pct": 0.80, "count": 2885},
    "wrongs": {"label": "Вронги", "pct": 0.66, "count": 2361},
    "bf": {"label": "БФ", "pct": 0.32, "count": 1151},
}

POINTS = {
    "Сухомлинова, 19": {"wrongs": (0.46, 2, 438), "bf": (0.68, 3, 438)},
    "Дэн Сяопина, 34": {"wrongs": (0.59, 4, 674), "bf": (0.59, 4, 674)},
}

DYNAMICS = {
    "months": ["Октябрь", "Ноябрь"],
    "wrongs": [0.56, 0.66],
    "bf": [0.22, 0.45],
}

# ============================================================
# ФУНКЦИИ
# ============================================================
def fmt_pct(value: float) -> str:
    return f"{value:.2f}".replace(".", ",") + "%"

def render_metric_card(col, label, value, target, count):
    color = GREEN if value <= target else RED
    diff = value - target
    diff_text = f"+{diff:.2f}%" if diff > 0 else f"{diff:.2f}%"
    count_str = format(count, ",").replace(",", " ")
    
    col.markdown(
        f"""
        <div style="padding:10px; border-radius:8px; background-color:#f8f9fa; text-align:center; border: 1px solid #ddd;">
            <div style="font-size:14px; color:#666; margin-bottom:4px; font-weight:bold;">{label}</div>
            <div style="font-size:28px; font-weight:bold; color:{color};">{fmt_pct(value)}</div>
            <div style="font-size:12px; color:#888;">{count_str} шт.</div>
            <div style="font-size:12px; color:#888; margin-top:4px;">Цель: ≤ {target}%</div>
            <div style="font-size:12px; color:{color}; font-weight:bold;">({diff_text})</div>
        </div>
        """,
        unsafe_allow_html=True
    )

@st.cache_data(show_spinner=False)
def load_cancels(path: str) -> pd.DataFrame:
    try:
        raw = pd.read_excel(path, header=None)
        header_row = raw.index[raw.apply(lambda r: REASON_COLUMN in r.values, axis=1)]
        if len(header_row) == 0:
            return pd.DataFrame()
        df = pd.read_excel(path, header=int(header_row[0]))
        return df.dropna(subset=[REASON_COLUMN])
    except Exception:
        return pd.DataFrame()

# ============================================================
# ОТРИСОВКА
# ============================================================
st.set_page_config(page_title=f"Пульт Качества ({PARTNER_NAME})", layout="wide")
st.title(f"Пульт Качества: {PARTNER_NAME}")
st.caption("Период анализа: 19 октября — 15 ноября 2026 года")

# 1. ВЕРХНИЙ БЛОК KPI
st.subheader(f"🏢 Общая картина: {PARTNER_NAME}")
c1, c2, c3 = st.columns(3)

render_metric_card(c1, KPI["cancels"]["label"], KPI["cancels"]["pct"], TARGETS["cancels"], KPI["cancels"]["count"])
render_metric_card(c2, KPI["wrongs"]["label"], KPI["wrongs"]["pct"], TARGETS["wrongs"], KPI["wrongs"]["count"])
render_metric_card(c3, KPI["bf"]["label"], KPI["bf"]["pct"], TARGETS["bf"], KPI["bf"]["count"])

st.divider()

# 2. ГРАФИКИ (Сравнение точек и Динамика)
st.subheader("📍 Детализация по точкам и Динамика")
col_left, col_right = st.columns(2)

with col_left:
    names = list(POINTS.keys())
    wrongs = [POINTS[n]["wrongs"][0] for n in names]
    bfs = [POINTS[n]["bf"][0] for n in names]

    fig = go.Figure()
    fig.add_bar(name="Вронги, %", x=names, y=wrongs, marker_color=[GREEN if v <= TARGETS["wrongs"] else RED for v in wrongs], text=[fmt_pct(v) for v in wrongs], textposition="outside")
    fig.add_bar(name="БФ, %", x=names, y=bfs, marker_color=[GREEN if v <= TARGETS["bf"] else RED for v in bfs], marker_pattern_shape="/", text=[fmt_pct(v) for v in bfs], textposition="outside")
    
    fig.add_hline(y=TARGETS["wrongs"], line_dash="dash", line_color="#E6A700", annotation_text="Цель вронгов 0,60%", annotation_position="top left")
    fig.add_hline(y=TARGETS["bf"], line_dash="dash", line_color="#2E9E4F", annotation_text="Цель БФ 0,30%", annotation_position="bottom left")
    
    fig.update_layout(barmode="group", title="Сравнение точек с таргетами", yaxis_title="%", yaxis_range=[0, 0.9], legend=dict(orientation="h", y=-0.15), margin=dict(t=40))
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    fig2 = go.Figure()
    fig2.add_scatter(x=DYNAMICS["months"], y=DYNAMICS["wrongs"], mode="lines+markers+text", name="Вронги, %", line=dict(color="#1f77b4", width=3), text=[fmt_pct(v) for v in DYNAMICS["wrongs"]], textposition="top center")
    fig2.add_scatter(x=DYNAMICS["months"], y=DYNAMICS["bf"], mode="lines+markers+text", name="БФ, %", line=dict(color="#9467bd", width=3), text=[fmt_pct(v) for v in DYNAMICS["bf"]], textposition="top center")
    
    fig2.add_hline(y=TARGETS["wrongs"], line_dash="dash", line_color="#1f77b4", annotation_text="Цель вронгов", annotation_position="top left")
    fig2.add_hline(y=TARGETS["bf"], line_dash="dash", line_color="#9467bd", annotation_text="Цель БФ", annotation_position="bottom left")
    
    fig2.update_layout(title="Динамика: Октябрь → Ноябрь", yaxis_title="%", yaxis_range=[0, 0.85], legend=dict(orientation="h", y=-0.15), margin=dict(t=40))
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# 3. ПРИЧИНЫ ОТМЕН И АНАЛИТИКА
st.subheader("📝 Причины отмен и Аналитика")
col_bot_left, col_bot_right = st.columns(2)

with col_bot_left:
    cancels_df = load_cancels(EXCEL_PATH)
    if not cancels_df.empty:
        top5 = cancels_df[REASON_COLUMN].value_counts().head(5).reset_index()
        top5.columns = ["Причина", "Кол-во"]
        
        fig3 = go.Figure(go.Bar(
            x=top5["Кол-во"], y=top5["Причина"], orientation='h',
            marker_color='#4C78A8', text=top5["Кол-во"], textposition='auto',
            textfont=dict(size=14, color='white')
        ))
        fig3.update_layout(xaxis_title="Количество отмен", yaxis=dict(autorange="reversed"), margin=dict(t=20, l=0, r=0, b=0), height=350)
        st.plotly_chart(fig3, use_container_width=True)
        st.caption(f"Всего отмен в Excel: {len(cancels_df)}")
    else:
        st.warning("Excel-файл с причинами отмен не найден или структура не совпадает (ожидается колонка 'Причина отмены').")

with col_bot_right:
    st.success(f"**Общая картина по бренду:** Отмены ровно в таргете (0,80%). Это отличный показатель!")
    st.markdown("---")
    
    for name, d in POINTS.items():
        st.markdown(f"#### {name}")
        
        wr_val = d["wrongs"][0]
        if wr_val <= TARGETS["wrongs"]:
            st.markdown(f"🟢 **Вронги (сборка): {fmt_pct(wr_val)}** — *В норме. Молодцы.*")
        else:
            st.markdown(f"🟡 **Вронги (сборка): {fmt_pct(wr_val)}** — *Выше цели. Нужен инструктаж.*")

        bf_val, bf_bad, bf_total = d["bf"]
        if bf_val <= TARGETS["bf"]:
            st.markdown(f"🟢 **БФ (качество): {fmt_pct(bf_val)}** — *Качество в норме.*")
        else:
            st.markdown(f"🔴 **БФ (качество): {fmt_pct(bf_val)}** — *Выше цели ({bf_bad} из {bf_total} заказов). Проверьте стандарты.*")
        st.write("")

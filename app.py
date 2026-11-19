import os
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# SETTINGS
# ============================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_PATH = os.path.join(CURRENT_DIR, "data.xlsx")

REASON_COLUMN = "Причина отмены"
GREEN = "#2E9E4F"
RED = "#D64545"

TARGETS = {"cancels": 0.80, "wrongs": 0.60, "bf": 0.30}

KPI = {
    "cancels": {"label": "Отмены", "pct": 0.80, "count": 2885},
    "wrongs": {"label": "Вронги", "pct": 0.66, "count": 2361},
    "bf": {"label": "БФ", "pct": 0.32, "count": 1151},
}

POINTS = {
    "Сухомлинова, 19": {"wrongs": (0.46, 2, 438), "bf": (0.68, 3, 438)},
    "Дэн Сяопина, 34": {"wrongs": (0.59, 4, 674), "bf": (0.59, 4, 674)},
}

# ОБНОВЛЕНО: Данные по неделям для детального графика
DYNAMICS_WEEKLY = {
    "weeks": ["19-25 окт", "26 окт - 1 ноя", "2-8 ноя", "9-15 ноя"],
    "wrongs": [0.60, 0.66, 0.74, 0.60], # Примерные данные из первого скрина
    "bf": [0.30, 0.37, 0.47, 0.47],     # Примерные данные из первого скрина
}

# ============================================================
# HELPERS
# ============================================================
def fmt_pct(value: float) -> str:
    return f"{value:.2f}".replace(".", ",") + "%"

def color_for(value: float, target: float) -> str:
    return GREEN if value <= target else RED

@st.cache_data(show_spinner=False)
def load_cancels(path: str) -> pd.DataFrame:
    raw = pd.read_excel(path, header=None)
    header_row = raw.index[raw.apply(lambda r: REASON_COLUMN in r.values, axis=1)]
    if len(header_row) == 0:
        raise ValueError(f"Колонка «{REASON_COLUMN}» не найдена в файле")
    df = pd.read_excel(path, header=int(header_row[0]))
    return df.dropna(subset=[REASON_COLUMN])

def kpi_card(col, key: str, breakdown: str):
    k = KPI[key]
    target = TARGETS[key]
    color = color_for(k["pct"], target)
    count = format(k["count"], ",").replace(",", " ")
    
    diff = k["pct"] - target
    if diff > 0:
        diff_text = f"<span style='color:{RED};font-weight:bold;'>+{diff:.2f}%</span>"
    elif diff < 0:
        diff_text = f"<span style='color:{GREEN};font-weight:bold;'>{diff:.2f}%</span>"
    else:
        diff_text = f"<span style='color:{GREEN};font-weight:bold;'>0,00%</span>"

    col.markdown(
        f"""
        <div style="padding:16px;border-radius:12px;background:#F5F6F8;text-align:center;color:#000;box-shadow: 0 4px 6px rgba(0,0,0,0.1); height: 100%;">
            <div style="font-size:18px;color:#555;">{k['label']}</div>
            <div style="font-size:44px;font-weight:700;color:{color};">{fmt_pct(k['pct'])}</div>
            <div style="font-size:14px;color:#777;margin-bottom:8px;">{count} шт.</div>
            <div style="font-size:14px;color:#333;border-top: 1px solid #ddd; padding-top: 8px;">
                Цель: {fmt_pct(target)} <br>
                Отклонение: {diff_text} <br>
                <div style="margin-top: 8px; font-size: 13px; color: #555; line-height: 1.3; background: #eef1f4; padding: 4px; border-radius: 6px;">
                    <b>Детализация по точкам:</b><br>
                    {breakdown}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# PAGE
# ============================================================
st.set_page_config(page_title="Шаурма на углях KG", layout="wide")
st.title("Дашборд: Шаурма на углях KG")
st.caption("Период: 19.10.2026 – 15.11.2026")

# --- БЛОК 1: KPI КАРТОЧКИ ---
c1, c2, c3 = st.columns(3)
kpi_card(c1, "cancels", "Сух., 19: <b>0,60%</b><br>Дэн Сяопина: <b>0,60%</b>")
kpi_card(c2, "wrongs", "Сух., 19: <b>0,46%</b><br>Дэн Сяопина: <b>0,59%</b>")
kpi_card(c3, "bf", "Сух., 19: <b>0,68%</b><br>Дэн Сяопина: <b>0,59%</b>")

st.divider()

# --- БЛОК 2: ВКЛАДКИ ---
PLOT_CONFIG = {'displayModeBar': False}

# Добавили третью вкладку для детального разбора
tab1, tab2, tab3 = st.tabs(["📊 Сравнение точек", "📈 Детальный разбор (Вронги и БФ)", "📝 Отмены и Выводы"])

with tab1:
    st.subheader("Сравнение точек: Вронги и БФ")
    names = list(POINTS.keys())
    wrongs = [POINTS[n]["wrongs"][0] for n in names]
    bfs = [POINTS[n]["bf"][0] for n in names]

    fig = go.Figure()
    fig.add_bar(
        name="Вронги, %", x=names, y=wrongs,
        marker_color=[color_for(v, TARGETS["wrongs"]) for v in wrongs],
        text=[fmt_pct(v) for v in wrongs], textposition="outside",
    )
    fig.add_bar(
        name="БФ, %", x=names, y=bfs,
        marker_color=[color_for(v, TARGETS["bf"]) for v in bfs],
        marker_pattern_shape="/", 
        text=[fmt_pct(v) for v in bfs], textposition="outside",
    )
    fig.add_hline(y=TARGETS["wrongs"], line_dash="dash", line_color="#444",
                  annotation_text="Цель вронгов 0,60%", annotation_position="top left")
    fig.add_hline(y=TARGETS["bf"], line_dash="dot", line_color="#444",
                  annotation_text="Цель БФ 0,30%", annotation_position="bottom left")
    fig.update_layout(barmode="group", yaxis_title="%", yaxis_range=[0, 0.9],
                      legend=dict(orientation="h", y=-0.15), margin=dict(t=20), height=450)
    st.plotly_chart(fig, width="stretch", config=PLOT_CONFIG)
    st.caption("Столбцы: красный — выше цели, зелёный — в норме. Вронги — сплошные, БФ — штриховка.")

with tab2:
    st.subheader("Динамика по неделям: Когда мы пробили потолок?")
    st.markdown("На этом графике видно, в какую именно неделю показатели вышли за пределы нормы.")
    
    fig = go.Figure()
    fig.add_scatter(x=DYNAMICS_WEEKLY["weeks"], y=DYNAMICS_WEEKLY["wrongs"], mode="lines+markers+text",
                    name="Вронги, %", line=dict(color="#1f77b4", width=3),
                    text=[fmt_pct(v) for v in DYNAMICS_WEEKLY["wrongs"]], textposition="bottom center")
    fig.add_scatter(x=DYNAMICS_WEEKLY["weeks"], y=DYNAMICS_WEEKLY["bf"], mode="lines+markers+text",
                    name="БФ, %", line=dict(color="#9467bd", width=3),
                    text=[fmt_pct(v) for v in DYNAMICS_WEEKLY["bf"]], textposition="top center")
    
    fig.add_hline(y=TARGETS["wrongs"], line_dash="dash", line_color="#1f77b4",
                  annotation_text="Цель вронгов 0,60%", annotation_position="top left")
    fig.add_hline(y=TARGETS["bf"], line_dash="dash", line_color="#9467bd",
                  annotation_text="Цель БФ 0,30%", annotation_position="bottom left")
    
    fig.update_layout(yaxis_title="%", yaxis_range=[0, 0.85],
                      legend=dict(orientation="h", y=-0.15), margin=dict(t=20), height=400)
    st.plotly_chart(fig, width="stretch", config=PLOT_CONFIG)

    st.divider()
    st.subheader("Почему это произошло? (Что сказать партнеру)")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.info("**🔴 Всплеск БФ (Брак еды) в начале ноября**\n\n"
                "*На 3-й неделе БФ достиг 0,47% (почти в 1,5 раза выше нормы).*\n\n"
                "**Возможные причины (о чем спросить управляющего):**\n"
                "1. Смена поваров или выход новичков на линию.\n"
                "2. Проблемы с поставками (испорченные продукты, смена поставщика).\n"
                "3. Сбой в работе оборудования (например, гриль не держит температуру).\n"
                "*Рекомендация:* Внедрить чек-лист проверки качества блюда перед упаковкой.")
    with col_b:
        st.warning("**🟡 Скачок Вронгов в начале ноября**\n\n"
                   "*На 3-й неделе вронги выросли до 0,74%.*\n\n"
                   "**Возможные причины:**\n"
                   "1. Высокая загрузка в часы пик (повара путают заказы из-за спешки).\n"
                   "2. Схожие по составу блюда (неправильно клеят стикеры).\n"
                   "3. Человеческий фактор (новые сборщики).\n"
                   "*Рекомендация:* Провести аудит упаковочной зоны и убедиться, что все стикеры читаемы.")

with tab3:
    left, right = st.columns([1, 1]) 
    with left:
        st.subheader("Топ-5 причин отмен")
        try:
            cancels = load_cancels(EXCEL_PATH)
            top5 = cancels[REASON_COLUMN].value_counts().head(5).reset_index()
            top5.columns = ["Причина", "Кол-во"]
            
            fig = go.Figure(go.Bar(
                x=top5["Кол-во"], 
                y=top5["Причина"], 
                orientation='h',
                marker_color='#4C78A8',
                text=top5["Кол-во"],
                textposition='auto',
                textfont=dict(size=14, color='white')
            ))
            fig.update_layout(
                xaxis_title="Количество отмен",
                yaxis=dict(autorange="reversed"), 
                margin=dict(t=20, l=0, r=0, b=0),
                height=500
            )
            st.plotly_chart(fig, width="stretch", config=PLOT_CONFIG)
            st.caption(f"Всего отмен в Excel-файле: {len(cancels)}")
        except FileNotFoundError:
            st.error(f"Файл не найден: {EXCEL_PATH}")
        except Exception as e:
            st.error(f"Ошибка чтения Excel: {e}")

    with right:
        st.subheader("Итоговая аналитика")
        st.success(f"**Общая картина по бренду:** Отмены ровно в таргете (0,80%). Это отличный показатель!")
        st.markdown("---")
        
        for name, d in POINTS.items():
            st.markdown(f"#### Точка: {name}")
            
            wr_val = d["wrongs"][0]
            if wr_val <= TARGETS["wrongs"]:
                st.markdown(f"🟢 **Вронги (сборка): {fmt_pct(wr_val)}** — *В пределах нормы. Молодцы.*")
            else:
                st.markdown(f"🟡 **Вронги (сборка): {fmt_pct(wr_val)}** — *Выше цели. Стоит провести инструктаж.*")

            bf_val, bf_bad, bf_total = d["bf"]
            if bf_val <= TARGETS["bf"]:
                st.markdown(f"🟢 **БФ (качество): {fmt_pct(bf_val)}** — *Качество еды в норме.*")
            else:
                st.markdown(f"🔴 **БФ (качество): {fmt_pct(bf_val)}** — *Выше цели. Зафиксировано {bf_bad} случая из {bf_total} заказов. Проверьте стандарты.*")
            st.write("") 

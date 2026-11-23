import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ============================================================
# НАСТРОЙКИ  (KPI и точки — из BI; Excel содержит только список отмен)
# ============================================================
PARTNER_NAME = "Шаурма на углях"
EXCEL_PATH = "data.xlsx"
PERIOD = "19 октября — 15 ноября 2026 года"

GREEN, RED, YELLOW = "#2E9E4F", "#D64545", "#E6A700"
TARGETS = {"cancels": 0.80, "wrongs": 0.60, "bf": 0.30}

KPI = {
    "cancels": {"label": "Отмены", "pct": 0.80, "count": 2885},
    "wrongs": {"label": "Вронги", "pct": 0.66, "count": 2361},
    "bf": {"label": "БФ (Брак)", "pct": 0.32, "count": 1151},
}
POINTS = {  # название: {метрика: (процент, случаев, заказов)}
    "Сухомлинова, 19": {"wrongs": (0.46, 2, 438), "bf": (0.68, 3, 438)},
    "Дэн Сяопина, 34": {"wrongs": (0.59, 4, 674), "bf": (0.59, 4, 674)},
}
DYNAMICS = {"months": ["Октябрь", "Ноябрь"], "wrongs": [0.56, 0.66], "bf": [0.22, 0.45]}

st.set_page_config(page_title=f"Пульт Качества ({PARTNER_NAME})", layout="wide")


# ============================================================
# ФУНКЦИИ
# ============================================================
def fmt_pct(v):
    return f"{v:.2f}".replace(".", ",") + "%"


def card(col, label, value, target, sub=""):
    color = GREEN if value <= target else RED
    col.markdown(
        f"""
        <div style="padding:10px;border-radius:8px;background:#1f2128;text-align:center;
                    border:1px solid {color};margin-bottom:8px;">
            <div style="font-size:13px;color:#aaa;font-weight:bold;">{label}</div>
            <div style="font-size:26px;font-weight:bold;color:{color};">{fmt_pct(value)}</div>
            <div style="font-size:12px;color:#888;">{sub}</div>
            <div style="font-size:12px;color:#888;">Цель: ≤ {str(target).replace('.', ',')}%
              <span style="color:{color};font-weight:bold;">({value - target:+.2f}%)</span></div>
        </div>""",
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner="Загрузка данных…")
def load_cancels(path):
    raw = pd.read_excel(path, header=None)
    hdr = None
    for i, row in raw.iterrows():
        vals = {str(v).strip() for v in row.values}
        if {"Причина отмены", "Группа отмены"} <= vals:
            hdr = i
            break
    if hdr is None:
        return pd.DataFrame(), ""
    title = str(raw.iat[1, 0]) if len(raw) > 1 and pd.notna(raw.iat[1, 0]) else ""
    df = raw.iloc[hdr + 1:].copy()
    df.columns = [str(c).strip() for c in raw.iloc[hdr].values]
    df = df.dropna(subset=["Причина отмены"])
    df["Создан"] = pd.to_datetime(df["Создан (местное время)"], errors="coerce")
    df = df.dropna(subset=["Создан"])
    df["Час"] = df["Создан"].dt.hour
    df["День"] = df["Создан"].dt.dayofweek.map(dict(enumerate(["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"])))
    df["Месяц"] = df["Создан"].dt.month.map({10: "Октябрь", 11: "Ноябрь"}).fillna(df["Создан"].dt.strftime("%m.%Y"))
    df["Партнёрская"] = df["Группа отмены"].astype(str).str.startswith("Партнер")
    return df, title


# ============================================================
# ЗАГОЛОВОК И KPI
# ============================================================
st.title(f"Пульт Качества: {PARTNER_NAME}")
st.caption(f"Период анализа: {PERIOD}")

st.subheader("🏢 Общая картина")
c = st.columns(3)
for col, k in zip(c, ["cancels", "wrongs", "bf"]):
    d = KPI[k]
    card(col, d["label"], d["pct"], TARGETS[k], f"{format(d['count'], ',').replace(',', ' ')} шт.")

tab_pts, tab_cancel, tab_when, tab_list = st.tabs(
    ["📍 Точки и динамика", "📝 Причины отмен", "⏰ Когда отменяют", "📋 Список"])

# ============================================================
# ТОЧКИ И ДИНАМИКА
# ============================================================
with tab_pts:
    left, right = st.columns(2)
    with left:
        names = list(POINTS)
        wr = [POINTS[n]["wrongs"][0] for n in names]
        bf = [POINTS[n]["bf"][0] for n in names]
        fig = go.Figure()
        fig.add_bar(name="Вронги, %", x=names, y=wr, text=[fmt_pct(v) for v in wr], textposition="outside",
                    marker_color=[GREEN if v <= TARGETS["wrongs"] else RED for v in wr])
        fig.add_bar(name="БФ, %", x=names, y=bf, text=[fmt_pct(v) for v in bf], textposition="outside",
                    marker_color=[GREEN if v <= TARGETS["bf"] else RED for v in bf], marker_pattern_shape="/")
        fig.add_hline(y=TARGETS["wrongs"], line_dash="dash", line_color=YELLOW,
                      annotation_text="Цель вронгов 0,60%", annotation_position="top left")
        fig.add_hline(y=TARGETS["bf"], line_dash="dash", line_color=GREEN,
                      annotation_text="Цель БФ 0,30%", annotation_position="bottom left")
        fig.update_layout(barmode="group", title="Сравнение точек с целями", yaxis_title="%",
                          yaxis_range=[0, max(wr + bf) * 1.3], template="plotly_dark",
                          legend=dict(orientation="h", y=-0.15), margin=dict(t=40))
        st.plotly_chart(fig, width="stretch")
    with right:
        fig2 = go.Figure()
        fig2.add_scatter(x=DYNAMICS["months"], y=DYNAMICS["wrongs"], mode="lines+markers+text", name="Вронги, %",
                         line=dict(color="#4C9BE8", width=3), text=[fmt_pct(v) for v in DYNAMICS["wrongs"]],
                         textposition="top center")
        fig2.add_scatter(x=DYNAMICS["months"], y=DYNAMICS["bf"], mode="lines+markers+text", name="БФ, %",
                         line=dict(color="#B58AE6", width=3), text=[fmt_pct(v) for v in DYNAMICS["bf"]],
                         textposition="top center")
        fig2.add_hline(y=TARGETS["wrongs"], line_dash="dash", line_color="#4C9BE8",
                       annotation_text="Цель вронгов", annotation_position="top left")
        fig2.add_hline(y=TARGETS["bf"], line_dash="dash", line_color="#B58AE6",
                       annotation_text="Цель БФ", annotation_position="bottom left")
        fig2.update_layout(title="Динамика: октябрь → ноябрь", yaxis_title="%", template="plotly_dark",
                           yaxis_range=[0, max(DYNAMICS["wrongs"] + DYNAMICS["bf"]) * 1.4],
                           legend=dict(orientation="h", y=-0.15), margin=dict(t=40))
        st.plotly_chart(fig2, width="stretch")

    st.markdown("### Выводы по точкам")
    if KPI["cancels"]["pct"] <= TARGETS["cancels"]:
        st.success("Отмены в пределах цели (0,80%).")
    for name, d in POINTS.items():
        st.markdown(f"**{name}**")
        w, w_bad, w_tot = d["wrongs"]
        b, b_bad, b_tot = d["bf"]
        st.markdown(f"{'🟢' if w <= TARGETS['wrongs'] else '🟡'} Вронги (сборка): **{fmt_pct(w)}** "
                    f"({w_bad} из {w_tot}) — {'в норме' if w <= TARGETS['wrongs'] else 'выше цели, нужен инструктаж'}")
        st.markdown(f"{'🟢' if b <= TARGETS['bf'] else '🔴'} БФ (качество): **{fmt_pct(b)}** "
                    f"({b_bad} из {b_tot}) — {'в норме' if b <= TARGETS['bf'] else 'выше цели, проверьте стандарты'}")

# ============================================================
# EXCEL: отмены
# ============================================================
try:
    df, _ = load_cancels(EXCEL_PATH)
except Exception as e:
    df = pd.DataFrame()
    st.sidebar.error(f"Ошибка чтения {EXCEL_PATH}: {type(e).__name__}: {e}")

EMPTY = "Файл с отменами не найден или нет колонок «Причина отмены» / «Группа отмены»."

with tab_cancel:
    if df.empty:
        st.warning(EMPTY)
    else:
        n_all, n_p = len(df), int(df["Партнёрская"].sum())
        m1, m2, m3 = st.columns(3)
        m1.metric("Всего отмен в файле", n_all)
        m2.metric("Партнёрских отмен", n_p, f"{n_p / n_all * 100:.1f}% от всех", delta_color="off")
        m3.metric("Топ-причина", df["Причина отмены"].value_counts().index[0])

        a, b = st.columns(2)
        grp = df["Группа отмены"].value_counts().reset_index()
        grp.columns = ["Группа", "Кол-во"]
        a.plotly_chart(px.pie(grp, names="Группа", values="Кол-во", hole=0.45, template="plotly_dark",
                              title="Кто отменяет"), width="stretch")
        top = df["Причина отмены"].value_counts().head(8).reset_index()
        top.columns = ["Причина", "Кол-во"]
        f = go.Figure(go.Bar(x=top["Кол-во"], y=top["Причина"], orientation="h", marker_color="#4C78A8",
                             text=top["Кол-во"], textposition="auto"))
        f.update_layout(title="Топ причин (все отмены)", yaxis=dict(autorange="reversed"),
                        template="plotly_dark", margin=dict(t=40))
        b.plotly_chart(f, width="stretch")

        st.markdown("#### Партнёрские отмены — то, на что влияет точка")
        part = df[df["Партнёрская"]]
        if part.empty:
            st.info("Партнёрских отмен нет.")
        else:
            pr = part["Причина отмены"].value_counts().reset_index()
            pr.columns = ["Причина", "Кол-во"]
            f = px.bar(pr.sort_values("Кол-во"), x="Кол-во", y="Причина", orientation="h",
                       template="plotly_dark", text="Кол-во", color_discrete_sequence=[RED])
            st.plotly_chart(f, width="stretch")

with tab_when:
    if df.empty:
        st.warning(EMPTY)
    else:
        scope = st.radio("Какие отмены", ["Партнёрские", "Все"], horizontal=True)
        s = df[df["Партнёрская"]] if scope == "Партнёрские" else df
        if s.empty:
            st.info("Нет данных.")
        else:
            order = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
            pv = s.pivot_table(index="День", columns="Час", values="Номер заказа", aggfunc="count").reindex(order)
            pv = pv.reindex(columns=range(24))
            f = px.imshow(pv, aspect="auto", color_continuous_scale="Reds", template="plotly_dark",
                          labels=dict(x="Час", y="День", color="Отмен"), title=f"{scope} отмены: день × час")
            st.plotly_chart(f, width="stretch")
            a, b = st.columns(2)
            h = s.groupby("Час").size().reindex(range(24), fill_value=0).reset_index(name="Отмен")
            a.plotly_chart(px.bar(h, x="Час", y="Отмен", template="plotly_dark", title="По часам"), width="stretch")
            d = s.groupby("День").size().reindex(order, fill_value=0).reset_index(name="Отмен")
            b.plotly_chart(px.bar(d, x="День", y="Отмен", template="plotly_dark", title="По дням недели"),
                           width="stretch")

with tab_list:
    if df.empty:
        st.warning(EMPTY)
    else:
        groups = sorted(df["Группа отмены"].unique())
        pick = st.multiselect("Группа отмены", groups, default=groups)
        view = df[df["Группа отмены"].isin(pick)][
            ["Номер заказа", "Создан", "Группа отмены", "Причина отмены"]].sort_values("Создан", ascending=False)
        st.dataframe(view, hide_index=True, width="stretch")
        st.download_button("Скачать CSV", view.to_csv(index=False).encode("utf-8-sig"), "cancels.csv", "text/csv")

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Универсальный дашборд: имя партнёра берётся из заголовка первой строки data.xlsx
# ("Ди-2 · Качество заказов", "Дом плова · Качество заказов", ...). Менять код под партнёра не нужно.
PARTNER_NAME = "Партнёр"  # запасное значение
FILE_PATH = "data.xlsx"
TARGETS = {"cancels": 0.80, "wrongs": 0.60, "bf": 0.30}
DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

st.set_page_config(page_title="Пульт Качества", layout="wide")


# ---------------------------------------------------------------- helpers
def card(col, label, value, target, sub=""):
    ok = value <= target
    color = "#2E9E4F" if ok else "#D64545"
    col.markdown(
        f"""
        <div style="padding:10px;border-radius:8px;background:#1f2128;text-align:center;
                    border:1px solid {color};margin-bottom:8px;">
            <div style="font-size:13px;color:#aaa;font-weight:bold;">{label}</div>
            <div style="font-size:26px;font-weight:bold;color:{color};">{value:.2f}%</div>
            <div style="font-size:12px;color:#888;">Цель: ≤ {target}%
              <span style="color:{color};font-weight:bold;">({value - target:+.2f}%)</span></div>
            <div style="font-size:12px;color:#888;">{sub}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def pct(a, b):
    return (a / b.where(b != 0)).fillna(0) * 100


def read_block(raw, header_idx):
    """Таблица от шапки до первой пустой строки."""
    body = raw.iloc[header_idx + 1:]
    empty = body.isna().all(axis=1).to_numpy()
    stop = int(empty.argmax()) if empty.any() else len(body)
    df = body.iloc[:stop].copy()
    cols, seen = [], {}
    for i, c in enumerate(raw.iloc[header_idx].values):
        s = "" if pd.isna(c) else str(c).strip()
        s = s or f"Unnamed_{i}"
        seen[s] = seen.get(s, -1) + 1
        cols.append(s if seen[s] == 0 else f"{s}_{seen[s]}")
    df.columns = cols
    return df.dropna(axis=1, how="all")


def find_header(raw, *needles):
    for i, row in raw.iterrows():
        vals = {str(v).strip() for v in row.values}
        if all(n in vals for n in needles):
            return i
    return None


def to_num(df, cols):
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0) if c in df.columns else 0
    return df


@st.cache_data(show_spinner="Загрузка данных…")
def load(path):
    raw = pd.read_excel(path, sheet_name=0, header=None)
    out = {}

    out["title"] = str(raw.iat[0, 0])
    out["subtitle"] = str(raw.iat[1, 0])
    first = find_header(raw, "Филиал", "Заказы с ID")
    out["insights"] = [str(raw.iat[i, 0]).strip() for i in range(2, first or 2)
                       if pd.notna(raw.iat[i, 0]) and str(raw.iat[i, 0]).strip()
                       and not str(raw.iat[i, 0]).startswith("Филиалы")]

    # 1. филиалы (строка «Итого» не имеет названия филиала — отбрасываем)
    num = ["Заказы с ID", "Все отмены", "Партн. отмены", "Неверные", "Бэдфуд", "Заказы с инцидентом"]
    br = read_block(raw, first)
    br = br[br["Филиал"].notna()].copy()
    br["Филиал"] = br["Филиал"].astype(str).str.strip()
    br = to_num(br, num)
    br["% Отмен"] = pct(br["Партн. отмены"], br["Заказы с ID"])
    br["% Неверных"] = pct(br["Неверные"], br["Заказы с ID"])
    br["% БФ"] = pct(br["Бэдфуд"], br["Заказы с ID"])
    out["branches"] = br.reset_index(drop=True)

    # 2. причины по часам
    h = find_header(raw, "Час", "Метрика", "Причина", "Случаев")
    if h is not None:
        d = to_num(read_block(raw, h), ["Случаев", "Дат", "Заказы с ID"])
        d["Час_n"] = d["Час"].astype(str).str.extract(r"(\d+)")[0].astype(float)
        out["hours"] = d.sort_values("Час_n")

    # 3. все причины
    a = find_header(raw, "Метрика", "Группа", "Причина", "Заказов")
    if a is not None:
        out["reasons"] = to_num(read_block(raw, a), ["Заказов"])

    # 4. срезы день / час / день×час
    s = find_header(raw, "Срез", "День", "Час", "Заказы с ID")
    if s is not None:
        out["slices"] = to_num(read_block(raw, s), num)
    return out


# ---------------------------------------------------------------- load
try:
    data = load(FILE_PATH)
except Exception as e:
    st.error(f"Не удалось прочитать {FILE_PATH}: {type(e).__name__}")
    st.exception(e)
    st.stop()

br = data["branches"]
if br.empty:
    st.error("Не найдена таблица филиалов.")
    st.stop()

PARTNER_NAME = data["title"].split("·")[0].strip() or PARTNER_NAME
st.title(f"Пульт Качества: {PARTNER_NAME}")
st.caption(data["subtitle"])

if data["insights"]:
    with st.expander("🔎 Приоритеты и выводы", expanded=True):
        for t in data["insights"]:
            st.markdown(f"- {t}")

# ---------------------------------------------------------------- итого
tot = br[["Заказы с ID", "Партн. отмены", "Неверные", "Бэдфуд", "Заказы с инцидентом"]].sum()
n = tot["Заказы с ID"]
st.subheader("Итого по партнёру")
c0, c1, c2, c3 = st.columns(4)
c0.metric("Заказов с ID", f"{int(n):,}".replace(",", " "), f"{int(tot['Заказы с инцидентом'])} с инцидентом", delta_color="off")
card(c1, "Отмены", tot["Партн. отмены"] / n * 100, TARGETS["cancels"], f"{int(tot['Партн. отмены'])} шт.")
card(c2, "Вронги", tot["Неверные"] / n * 100, TARGETS["wrongs"], f"{int(tot['Неверные'])} шт.")
card(c3, "БФ (Брак)", tot["Бэдфуд"] / n * 100, TARGETS["bf"], f"{int(tot['Бэдфуд'])} шт.")

tab_pts, tab_hours, tab_reasons, tab_heat = st.tabs(
    ["📍 Точки", "⏰ Когда и почему", "📋 Все причины", "🗓 День × час"])

# ---------------------------------------------------------------- точки
with tab_pts:
    for i in range(0, len(br), 3):
        cols = st.columns(3)
        for col, (_, r) in zip(cols, br.iloc[i:i + 3].iterrows()):
            with col:
                st.markdown(f"#### {r['Филиал']}")
                st.caption(f"Заказов: {int(r['Заказы с ID'])} · с инцидентом: {int(r['Заказы с инцидентом'])}")
                card(st, "Отмены", r["% Отмен"], TARGETS["cancels"], f"{int(r['Партн. отмены'])} шт.")
                card(st, "Вронги", r["% Неверных"], TARGETS["wrongs"], f"{int(r['Неверные'])} шт.")
                card(st, "БФ (Брак)", r["% БФ"], TARGETS["bf"], f"{int(r['Бэдфуд'])} шт.")

    fig = go.Figure()
    for name, col, color in [("Отмены, %", "% Отмен", "#ef4444"),
                             ("Вронги, %", "% Неверных", "#f59e0b"),
                             ("БФ, %", "% БФ", "#10b981")]:
        fig.add_trace(go.Bar(name=name, x=br["Филиал"], y=br[col], marker_color=color,
                             text=br[col].map(lambda v: f"{v:.2f}%"), textposition="outside"))
    for k, color, label in [("cancels", "#ef4444", "отмен"), ("wrongs", "#f59e0b", "вронгов"), ("bf", "#10b981", "БФ")]:
        fig.add_hline(y=TARGETS[k], line_dash="dash", line_color=color,
                      annotation_text=f"Цель {label} {TARGETS[k]}%", annotation_position="top right")
    fig.update_layout(barmode="group", yaxis_title="%", template="plotly_dark",
                      margin=dict(t=50, b=40, l=40, r=40),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------- часы и причины
with tab_hours:
    hrs = data.get("hours")
    if hrs is None or hrs.empty:
        st.info("Нет данных по причинам по часам.")
    else:
        c1, c2 = st.columns(2)
        sel = c1.selectbox("Точка", ["Все"] + sorted(hrs["Филиал"].unique()), key="h_br")
        mets = sorted(hrs["Метрика"].unique())
        chosen = c2.multiselect("Тип", mets, default=mets)
        h = hrs[hrs["Метрика"].isin(chosen)]
        if sel != "Все":
            h = h[h["Филиал"] == sel]
        if h.empty:
            st.info("Нет данных по выбранным фильтрам.")
        else:
            order = h.sort_values("Час_n")["Час"].unique()
            f = px.bar(h, x="Час", y="Случаев", color="Причина", template="plotly_dark",
                       title="Случаи по часам суток", category_orders={"Час": list(order)},
                       hover_data=["Филиал", "Метрика", "Дат"])
            f.update_xaxes(tickangle=-45)
            st.plotly_chart(f, width="stretch")

            top = h.groupby(["Метрика", "Причина"], as_index=False)["Случаев"].sum().sort_values("Случаев")
            f = px.bar(top, x="Случаев", y="Причина", color="Метрика", orientation="h",
                       template="plotly_dark", title="Топ причин")
            st.plotly_chart(f, width="stretch")

            show = h[["Филиал", "Час", "Метрика", "Причина", "Случаев", "Дат", "Заказы с ID"]]
            st.dataframe(show.rename(columns={"Дат": "В скольких датах", "Случаев": "Кол-во"}),
                         hide_index=True, width="stretch")

# ---------------------------------------------------------------- все причины
with tab_reasons:
    rs = data.get("reasons")
    if rs is None or rs.empty:
        st.info("Нет данных.")
    else:
        c1, c2 = st.columns(2)
        sel = c1.selectbox("Точка", ["Все"] + sorted(rs["Филиал"].unique()), key="r_br")
        mlist = sorted(rs["Метрика"].unique())
        metric = c2.selectbox("Метрика", mlist, index=mlist.index("Все отмены") if "Все отмены" in mlist else 0)
        r = rs[rs["Метрика"] == metric]
        if sel != "Все":
            r = r[r["Филиал"] == sel]
        g = r.groupby(["Группа", "Причина"], as_index=False)["Заказов"].sum().sort_values("Заказов")
        f = px.bar(g, x="Заказов", y="Причина", color="Группа", orientation="h",
                   template="plotly_dark", title=f"{metric}: причины ({sel})",
                   height=max(300, 28 * len(g) + 120))
        st.plotly_chart(f, width="stretch")

# ---------------------------------------------------------------- день × час
with tab_heat:
    sl = data.get("slices")
    if sl is None or sl.empty:
        st.info("Нет данных по срезам.")
    else:
        c1, c2 = st.columns(2)
        sel = c1.selectbox("Точка", sorted(sl["Филиал"].unique()), key="s_br")
        measure = c2.selectbox("Показатель", ["Заказы с инцидентом", "Партн. отмены", "Неверные",
                                              "Бэдфуд", "Все отмены", "Заказы с ID"])
        s = sl[sl["Филиал"] == sel]
        dh = s[s["Срез"] == "День × час"]
        if not dh.empty:
            pv = dh.pivot_table(index="День", columns="Час", values=measure, aggfunc="sum").reindex(DAYS)
            pv = pv[sorted(pv.columns, key=lambda x: int(str(x)[:2]))]
            f = px.imshow(pv, aspect="auto", color_continuous_scale="Reds", template="plotly_dark",
                          labels=dict(x="Час", y="День", color=measure), title=f"{measure}: день × час")
            f.update_xaxes(tickangle=-45)
            st.plotly_chart(f, width="stretch")

        c1, c2 = st.columns(2)
        d = s[s["Срез"] == "День"].set_index("День").reindex(DAYS).reset_index()
        if not d.empty:
            c1.plotly_chart(px.bar(d, x="День", y=measure, template="plotly_dark", title="По дням недели"),
                            width="stretch")
        hh = s[s["Срез"] == "Час"].copy()
        if not hh.empty:
            hh["n"] = hh["Час"].astype(str).str[:2].astype(int)
            f = px.bar(hh.sort_values("n"), x="Час", y=measure, template="plotly_dark", title="По часам суток")
            f.update_xaxes(tickangle=-45)
            c2.plotly_chart(f, width="stretch")

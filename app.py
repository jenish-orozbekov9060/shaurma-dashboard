import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Пульт Качества", layout="wide")
st.title("Пульт Качества")
st.caption("Период анализа: 19 октября — 15 ноября 2026 года")

# --- ТАРГЕТЫ (ЦЕЛИ) ---
TARGETS = {
    "cancels": 0.80,
    "wrongs": 0.60,
    "bf": 0.30
}

# Функция для отрисовки мини-карточки с таргетом
def render_metric_card(col, label, value, target):
    color = "#2E9E4F" if value <= target else "#D64545"
    diff = value - target
    diff_text = f"+{diff:.2f}%" if diff > 0 else f"{diff:.2f}%"
    
    col.markdown(
        f"""
        <div style="padding:10px; border-radius:8px; background-color:#f8f9fa; text-align:center; border: 1px solid #ddd;">
            <div style="font-size:12px; color:#666; margin-bottom:4px;">{label}</div>
            <div style="font-size:24px; font-weight:bold; color:{color};">{value:.2f}%</div>
            <div style="font-size:11px; color:#888;">Цель: ≤ {target}%</div>
            <div style="font-size:11px; color:{color}; font-weight:bold;">({diff_text})</div>
        </div>
        """,
        unsafe_allow_html=True
    )

file_path = "data.xlsx"

try:
    raw_df = pd.read_excel(file_path, sheet_name="Сводная", header=None)

    # ============================================================
    # 1. ПОИСК ТАБЛИЦЫ ФИЛИАЛОВ И РАСЧЕТ ПРОЦЕНТОВ
    # ============================================================
    start_row = None
    for i, row in raw_df.iterrows():
        if str(row[0]).strip() == "Итого":
            start_row = i
            break
            
    if start_row is not None:
        header_row = start_row - 1
        # Берем "Итого" и все филиалы
        df_branches = raw_df.iloc[start_row : start_row + 10].copy() 
        df_branches.columns = raw_df.iloc[header_row].values
        
        # Очищаем от пустых строк и оставляем нужные колонки
        cols_to_keep = ['Филиал', 'Заказы с ID', 'Все отмены', 'Партн. отмены', 'Неверные', 'Бэдфуд']
        available_cols = [c for c in cols_to_keep if c in df_branches.columns]
        df_branches = df_branches[available_cols].dropna(subset=['Филиал'])
        df_branches = df_branches[df_branches['Филиал'] != ''] # Убираем пустые строки

        # Переводим в числа
        for col in cols_to_keep[1:]:
            if col in df_branches.columns:
                df_branches[col] = pd.to_numeric(df_branches[col], errors='coerce').fillna(0)

        # Защита от деления на ноль
        df_branches['Заказы с ID'] = df_branches['Заказы с ID'].replace(0, 1) 
        
        # Считаем проценты
        df_branches['% Отмен'] = (df_branches['Партн. отмены'] / df_branches['Заказы с ID']) * 100
        df_branches['% Неверных'] = (df_branches['Неверные'] / df_branches['Заказы с ID']) * 100
        df_branches['% БФ'] = (df_branches['Бэдфуд'] / df_branches['Заказы с ID']) * 100

        # ============================================================
        # 2. ВЕРХНИЙ БЛОК: ОБЩИЙ ТАРГЕТ ПО БРЕНДУ
        # ============================================================
        st.subheader("🏢 Общая картина по бренду")
        total_row = df_branches[df_branches['Филиал'].str.contains('Итого', case=False, na=False)]
        
        if not total_row.empty:
            c1, c2, c3 = st.columns(3)
            render_metric_card(c1, "Отмены", total_row['% Отмен'].values[0], TARGETS['cancels'])
            render_metric_card(c2, "Вронги", total_row['% Неверных'].values[0], TARGETS['wrongs'])
            render_metric_card(c3, "БФ (Брак)", total_row['% БФ'].values[0], TARGETS['bf'])
        else:
            st.warning("Строка 'Итого' не найдена.")

        st.divider()

        # ============================================================
        # 3. БЛОК: ТАРГЕТЫ ПО КАЖДОЙ ТОЧКЕ ОТДЕЛЬНО
        # ============================================================
        st.subheader("📍 Детализация по точкам")
        
        # Берем только филиалы (исключаем "Итого")
        df_points = df_branches[~df_branches['Филиал'].str.contains('Итого', case=False, na=False)].copy()
        
        if not df_points.empty:
            # Создаем колонки для каждой точки (максимум 3-4 колонки)
            cols = st.columns(len(df_points))
            
            for idx, (index, row) in enumerate(df_points.iterrows()):
                with cols[idx]:
                    st.markdown(f"### {row['Филиал']}")
                    st.markdown("---")
                    # Мини-карточки для каждой метрики этой точки
                    render_metric_card(st, "Отмены", row['% Отмен'], TARGETS['cancels'])
                    st.write("") # Отступ
                    render_metric_card(st, "Вронги", row['% Неверных'], TARGETS['wrongs'])
                    st.write("")
                    render_metric_card(st, "БФ (Брак)", row['% БФ'], TARGETS['bf'])
        else:
            st.info("Нет данных по отдельным филиалам.")

        st.divider()

        # ============================================================
        # 4. ГРАФИК С ТАРГЕТАМИ
        # ============================================================
        st.subheader("📊 Визуальное сравнение с таргетами")
        
        fig = go.Figure()
        fig.add_bar(name="Отмены, %", x=df_points['Филиал'], y=df_points['% Отмен'], 
                    marker_color='#D64545', text=df_points['% Отмен'].apply(lambda x: f"{x:.2f}%"), textposition="outside")
        fig.add_bar(name="Вронги, %", x=df_points['Филиал'], y=df_points['% Неверных'], 
                    marker_color='#E6A700', text=df_points['% Неверных'].apply(lambda x: f"{x:.2f}%"), textposition="outside")
        fig.add_bar(name="БФ, %", x=df_points['Филиал'], y=df_points['% БФ'], 
                    marker_color='#2E9E4F', text=df_points['% БФ'].apply(lambda x: f"{x:.2f}%"), textposition="outside")
        
        # Линии общих таргетов
        fig.add_hline(y=TARGETS['cancels'], line_dash="dash", line_color="#D64545", annotation_text=f"Цель отмен {TARGETS['cancels']}%", annotation_position="top left")
        fig.add_hline(y=TARGETS['wrongs'], line_dash="dash", line_color="#E6A700", annotation_text=f"Цель вронгов {TARGETS['wrongs']}%", annotation_position="top left")
        fig.add_hline(y=TARGETS['bf'], line_dash="dash", line_color="#2E9E4F", annotation_text=f"Цель БФ {TARGETS['bf']}%", annotation_position="bottom left")
        
        fig.update_layout(barmode='group', title="Сравнение филиалов с общими таргетами", yaxis_title="%")
        st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # ============================================================
        # 5. БЛОК ПРИЧИН ПО ЧАСАМ (как было)
        # ============================================================
        hour_header_idx = None
        for i, row in raw_df.iterrows():
            if 'Час' in row.values and 'Причина' in row.values:
                hour_header_idx = i
                break

        if hour_header_idx is not None:
            df_hours = raw_df.iloc[hour_header_idx + 1:].copy()
            df_hours.columns = raw_df.iloc[hour_header_idx].values
            
            cols_to_keep_h = ['Филиал', 'Час', 'Метрика', 'Причина', 'Случаев', 'Дат']
            available_cols_h = [c for c in cols_to_keep_h if c in df_hours.columns]
            df_hours = df_hours[available_cols_h].dropna(subset=['Час', 'Причина', 'Случаев'])
            
            df_hours['Случаев'] = pd.to_numeric(df_hours['Случаев'], errors='coerce').fillna(0)
            df_hours['Дат'] = pd.to_numeric(df_hours['Дат'], errors='coerce').fillna(0)

            df_hours_clean = df_hours[
                (~df_hours['Час'].astype(str).str.contains('Все', case=False, na=False)) &
                (~df_hours['Причина'].astype(str).str.contains('Все', case=False, na=False)) &
                (df_hours['Час'].astype(str).str.contains(':', na=False))
            ]

            st.subheader("⏰ Когда и почему происходят инциденты?")
            if not df_hours_clean.empty:
                branches_in_hours = df_hours_clean['Филиал'].dropna().unique()
                selected_branch = st.selectbox("Выберите точку для детального анализа:", branches_in_hours)
                
                filtered_hours = df_hours_clean[df_hours_clean['Филиал'] == selected_branch]
                
                if not filtered_hours.empty:
                    fig_reasons = px.bar(filtered_hours, x='Час', y='Случаев', color='Причина', 
                                         title=f"Причины по часам: {selected_branch}",
                                         labels={'Случаев': 'Количество'})
                    st.plotly_chart(fig_reasons, use_container_width=True)
                    
                    st.markdown("---")
                    st.subheader("📋 Детальный список")
                    display_df_h = filtered_hours[['Час', 'Метрика', 'Причина', 'Случаев', 'Дат']].copy()
                    display_df_h.columns = ['Время', 'Тип', 'Причина', 'Кол-во', 'Дней']
                    st.dataframe(display_df_h, hide_index=True, use_container_width=True)

except Exception as e:
    st.error(f"Ошибка при чтении файла: {e}")

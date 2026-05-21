"""
Компонент итогов и аналитики
============================
Отображает:
- Выбор периода анализа
- Графики с аномалиями
- Статистика по простоям (гистограмма + pie chart)
- Данные по воде
- Средние значения и отклонения
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_service import DataService
from utils import (
    create_time_series,
    create_multi_line,
    create_bar_chart,
    create_pie_chart,
    create_sunburst,
    create_area_with_threshold,
    create_dual_axis,
    SEVERITY_COLORS
)


def render_period_selector() -> tuple:
    """Рендер селектора периода"""
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        preset = st.selectbox(
            "Период",
            options=["day", "week", "month", "custom"],
            format_func=lambda x: {
                "day": "Сутки",
                "week": "Неделя", 
                "month": "Месяц",
                "custom": "Свой период"
            }[x],
            key="period_preset"
        )
    
    now = datetime.now()
    
    if preset == "day":
        start_date = now - timedelta(days=1)
        end_date = now
    elif preset == "week":
        start_date = now - timedelta(weeks=1)
        end_date = now
    elif preset == "month":
        start_date = now - timedelta(days=30)
        end_date = now
    else:
        with col2:
            start_date = st.date_input("С", value=now - timedelta(days=7), key="start_date")
            start_date = datetime.combine(start_date, datetime.min.time())
        with col3:
            end_date = st.date_input("По", value=now, key="end_date")
            end_date = datetime.combine(end_date, datetime.max.time())
    
    return start_date, end_date


def render_stats_card(title: str, value: float, unit: str, delta: float = None, subtitle: str = None):
    """Рендер карточки со статистикой"""
    delta_html = ''
    if delta is not None:
        delta_color = "#27AE60" if delta >= 0 else "#E74C3C"
        delta_sign = "+" if delta >= 0 else ""
        delta_html = f'<span style="color: {delta_color}; font-size: 0.9em; margin-left: 8px;">{delta_sign}{delta:.1f}%</span>'
    
    subtitle_html = f'<div style="color: #7F8C8D; font-size: 1em; margin-top: 4px;">{subtitle}</div>' if subtitle else ''
    
    st.html(f"""
    <div style="
        background: linear-gradient(145deg, #1e3a5f, #16213e);
        border-radius: 10px;
        padding: 14px;
        border: 1px solid rgba(255,255,255,0.1);
    ">
        <div style="color: #95A5A6; font-size: 0.8em; margin-bottom: 4px;">{title}</div>
        <div style="font-size: 1.5em; font-weight: 600; color: #EAECEE;">
            {value:.2f} <span style="font-size: 0.6em; color: #95A5A6;">{unit}</span>
            {delta_html}
        </div>
        {subtitle_html}
    </div>
    """)#, unsafe_allow_html=True)


def render_tech_analytics(data_service: DataService, start_date: datetime, end_date: datetime):
    """Рендер раздела технической аналитики"""
    st.markdown("#### 📈 Технические показатели")
    
    config = data_service.config
    
    # Выбор типа данных и агрегата
    col1, col2 = st.columns(2)
    with col1:
        data_types = ['производительность', 'плотность', 'ph', 'слив_гидроциклон', 'влага_руды']
        data_type = st.selectbox("Показатель", data_types, key="tech_data_type")
    
    with col2:
        # Определяем доступные агрегаты для выбранного типа
        df_all = data_service.get_tech_data(data_type=data_type, start_date=start_date, end_date=end_date)
        available_aggregates = ['Все'] + sorted(df_all['агрегат'].unique().tolist()) if not df_all.empty else ['Все']
        if 'мельница_2' in available_aggregates:
            available_aggregates.remove('мельница_2') # NOTE knludge

        aggregate = st.selectbox("Агрегат", available_aggregates, key="tech_aggregate")
    
    # Получаем данные с аномалиями
    if aggregate == 'Все':
        df = data_service.get_data_with_anomalies(data_type, start_date=start_date, end_date=end_date)
    else:
        df = data_service.get_data_with_anomalies(data_type, aggregate=aggregate, start_date=start_date, end_date=end_date)
    
    if df.empty:
        st.info("Нет данных за выбранный период")
        return
    
    # Статистика
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)

    unit = {
        'производительность':"т/ч", 
        'плотность':"%", 
        'ph':"", 
        'слив_гидроциклон':"%", 
        'влага_руды':"%"
    }.get(data_type, '')
    
    with col_s1:
        render_stats_card("Среднее", df['значение'].mean(), unit, subtitle=f"N = {len(df)}")
    with col_s2:
        render_stats_card("Медиана", df['значение'].median(), unit)
    with col_s3:
        render_stats_card("Станд. откл.", df['значение'].std(), unit)
    with col_s4:
        anomaly_count = df['is_anomaly'].sum() if 'is_anomaly' in df.columns else 0
        render_stats_card("Аномалий", anomaly_count, "шт", subtitle=f"{anomaly_count/len(df)*100:.1f}% от всех")
    
    st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)
    
    # Определяем пороги для графика
    threshold_lines = []
    if data_type == 'плотность' and aggregate != 'Все':
        th = config['thresholds']['density'].get(aggregate, config['thresholds']['density']['default'])
        threshold_lines = [
            {"value": th['min'], "color": "#F39C12", "label": f"Мин: {th['min']}"},
            {"value": th['max'], "color": "#F39C12", "label": f"Макс: {th['max']}"}
        ]
    elif data_type == 'ph':
        th = config['thresholds']['ph']
        threshold_lines = [
            {"value": th['min'], "color": "#F39C12", "label": f"Мин: {th['min']}"},
            {"value": th['max'], "color": "#F39C12", "label": f"Макс: {th['max']}"}
        ]
    
    # График с аномалиями
    if 'timestamp' in df.columns:
        fig = create_time_series(
            df, 
            x='timestamp', 
            y='значение',
            title=f"{data_type.capitalize()} — {aggregate}",
            show_anomalies=True,
            anomaly_col='severity',
            threshold_lines=threshold_lines,
            y_label=data_type,
            height=380
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Сравнение агрегатов (если выбрано "Все")
    if aggregate == 'Все' and 'агрегат' in df.columns:
        st.markdown("##### Сравнение по агрегатам")
        
        # Pivot для мульти-линейного графика
        pivot_df = df.pivot_table(
            index='timestamp', 
            columns='агрегат', 
            values='значение',
            aggfunc='mean'
        ).reset_index()
        
        if len(pivot_df.columns) > 1:
            y_cols = [c for c in pivot_df.columns if c != 'timestamp']
            fig_multi = create_multi_line(
                pivot_df,
                x='timestamp',
                y_columns=y_cols,
                title=f"Сравнение {data_type} по агрегатам",
                height=350
            )
            st.plotly_chart(fig_multi, use_container_width=True)


def render_downtime_analytics(data_service: DataService, start_date: datetime, end_date: datetime):
    """Рендер раздела аналитики простоев"""
    st.markdown("#### ⏱️ Анализ простоев")
    
    config = data_service.config
    
    # Фильтр по агрегату
    col1, col2 = st.columns([1, 3])
    with col1:
        mills = ['Все'] + config['aggregates']['active_mills']
        selected_mill = st.selectbox("Агрегат", mills, key="downtime_aggregate")
    
    # Получаем данные
    if selected_mill == 'Все':
        df = data_service.get_downtime_data(start_date=start_date, end_date=end_date)
    else:
        df = data_service.get_downtime_data(aggregate=selected_mill, start_date=start_date, end_date=end_date)
    
    if df.empty:
        st.info("Нет данных о простоях за выбранный период")
        return
    
    # Сводная статистика
    total_minutes = df['time_span'].sum() if 'time_span' in df.columns else 0
    total_hours = total_minutes / 60
    count = len(df)
    avg_duration = df['time_span'].mean() if 'time_span' in df.columns else 0
    
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        render_stats_card("Всего простоев", total_hours, "ч", subtitle=f"{total_minutes:.0f} мин")
    with col_s2:
        render_stats_card("Количество", count, "случаев")
    with col_s3:
        render_stats_card("Средняя длительность", avg_duration, "мин")
    
    st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)
    
    # Графики: гистограмма + pie chart
    col_bar, col_pie = st.columns([1.5, 1])
    
    with col_bar:
        # Группировка по категориям
        if 'category' in df.columns and 'time_span' in df.columns:
            by_cat = df.groupby('category')['time_span'].sum().reset_index()
            by_cat.columns = ['Категория', 'Время (мин)']
            by_cat = by_cat.sort_values('Время (мин)', ascending=False)
            
            color_map = config['downtime']['colors']
            fig_bar = create_bar_chart(
                by_cat,
                x='Категория',
                y='Время (мин)',
                title="Простои по категориям",
                color_column='Категория',
                color_map=color_map,
                height=350
            )
            st.plotly_chart(fig_bar, use_container_width=True)
    
    with col_pie:
        if 'category' in df.columns and 'time_span' in df.columns:
            by_cat = df.groupby('category')['time_span'].sum().reset_index()
            by_cat.columns = ['Категория', 'Время']
            
            color_map = config['downtime']['colors']
            fig_pie = create_pie_chart(
                by_cat,
                values='Время',
                names='Категория',
                title="Распределение",
                color_map=color_map,
                height=350
            )
            st.plotly_chart(fig_pie, use_container_width=True)
    
    # Sunburst: категория -> подкатегория
    if 'category' in df.columns and 'subcategory' in df.columns and 'time_span' in df.columns:
        st.markdown("##### Детализация по подкатегориям")
        
        # Подготовка данных для sunburst
        sunburst_df = df.groupby(['category', 'subcategory'])['time_span'].sum().reset_index()
        sunburst_df.columns = ['Категория', 'Подкатегория', 'Время']
        
        color_map = config['downtime']['colors']
        fig_sun = create_sunburst(
            sunburst_df,
            path=['Категория', 'Подкатегория'],
            values='Время',
            title="Иерархия простоев (категория → подкатегория)",
            color_map=color_map,
            height=450
        )
        st.plotly_chart(fig_sun, use_container_width=True)
    
    # Простои по агрегатам (если выбрано "Все")
    if selected_mill == 'Все' and 'aggregate_normalized' in df.columns:
        st.markdown("##### Простои по агрегатам")
        by_agg = df.groupby('aggregate_normalized')['time_span'].sum().reset_index()
        by_agg.columns = ['Агрегат', 'Время (мин)']
        by_agg = by_agg.sort_values('Время (мин)', ascending=True)
        
        fig_agg = create_bar_chart(
            by_agg,
            x='Агрегат',
            y='Время (мин)',
            title="Простои по агрегатам",
            orientation='h',
            color='#3498DB',
            height=300
        )
        st.plotly_chart(fig_agg, use_container_width=True)


def render_water_analytics(data_service: DataService, start_date: datetime, end_date: datetime):
    """Рендер раздела аналитики по воде"""
    st.markdown("#### 💧 Потребление воды")
    
    config = data_service.config
    
    df = data_service.get_water_data(start_date=start_date, end_date=end_date)
    
    if df.empty:
        st.info("Нет данных по воде за выбранный период")
        return
    
    # Убираем строки с нулевым или NaN фактическим расходом для статистики
    df_valid = df[df['actual'] > 0].copy() if 'actual' in df.columns else df
    
    # Статистика
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    
    with col_s1:
        avg_actual = df_valid['actual'].mean() if not df_valid.empty else 0
        render_stats_card("Средний расход", avg_actual, "м³/сут")
    
    with col_s2:
        total_actual = df_valid['actual'].sum() if not df_valid.empty else 0
        render_stats_card("Всего за период", total_actual, "м³")
    
    with col_s3:
        # Среднее отклонение от номинала
        if 'nominal' in df_valid.columns and 'actual' in df_valid.columns:
            df_valid['deviation'] = ((df_valid['actual'] - df_valid['nominal']) / df_valid['nominal'] * 100).replace([np.inf, -np.inf], np.nan)
            avg_deviation = df_valid['deviation'].mean()
            render_stats_card("Откл. от нормы", avg_deviation if not pd.isna(avg_deviation) else 0, "%")
        else:
            render_stats_card("Откл. от нормы", 0, "%")
    
    with col_s4:
        max_actual = df_valid['actual'].max() if not df_valid.empty else 0
        render_stats_card("Макс. расход", max_actual, "м³/сут")
    
    st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)
    
    # График факт vs номинал
    if 'date' in df.columns and 'actual' in df.columns:
        # Создаем dual axis если есть nominal
        if 'nominal' in df.columns:
            fig = create_dual_axis(
                df,
                x='date',
                y1='actual',
                y2='nominal',
                title="Фактический vs Номинальный расход воды",
                y1_label="Фактический (м³)",
                y2_label="Номинальный (м³)",
                y1_color="#3498DB",
                y2_color="#E74C3C",
                height=380
            )
        else:
            fig = create_time_series(
                df,
                x='date',
                y='actual',
                title="Фактический расход воды",
                y_label="Расход (м³/сут)",
                height=380
            )
        st.plotly_chart(fig, use_container_width=True)
    
    # График отклонений
    if 'deviation' in df_valid.columns and not df_valid['deviation'].isna().all():
        st.markdown("##### Отклонение от номинала")
        
        water_th = config['thresholds']['water']
        fig_dev = create_area_with_threshold(
            df_valid,
            x='date',
            y='deviation',
            title="Отклонение расхода воды от номинала (%)",
            threshold_min=-water_th['deviation_warning'],
            threshold_max=water_th['deviation_warning'],
            height=300
        )
        st.plotly_chart(fig_dev, use_container_width=True)


def render_summary(data_service: DataService):
    """Главная функция рендера вкладки итогов"""
    
    st.markdown("### 📊 Итоги и аналитика")
    
    # Выбор периода
    start_date, end_date = render_period_selector()
    
    st.markdown("---")
    
    # Техническая аналитика
    render_tech_analytics(data_service, start_date, end_date)
    
    st.markdown("---")
    
    # Аналитика простоев
    render_downtime_analytics(data_service, start_date, end_date)
    
    st.markdown("---")
    
    # Аналитика по воде
    render_water_analytics(data_service, start_date, end_date)

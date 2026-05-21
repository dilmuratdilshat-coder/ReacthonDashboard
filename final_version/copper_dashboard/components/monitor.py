"""
Компонент монитора (главная вкладка)
====================================
Отображает:
- Алерты (угрозы)
- KPI с переключением периода
- Статус мельниц с цветовой индикацией
"""

import streamlit as st
from datetime import datetime
from data_service import DataService
from utils import SEVERITY_COLORS


def render_alerts(data_service: DataService):
    """Рендер блока алертов"""
    alerts = data_service.get_alerts()
    
    if not alerts:
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, rgba(39, 174, 96, 0.2), rgba(39, 174, 96, 0.1));
            border-left: 4px solid #27AE60;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 16px;
        ">
            <span style="font-size: 1.1em;">✅ Все показатели в норме</span>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Группируем по severity
    critical = [a for a in alerts if a['severity'] == 'critical']
    warnings = [a for a in alerts if a['severity'] == 'warning']
    
    if critical:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, rgba(231, 76, 60, 0.25), rgba(231, 76, 60, 0.1));
            border-left: 4px solid #E74C3C;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 12px;
        ">
            <div style="font-weight: 600; color: #E74C3C; margin-bottom: 8px;">
                🔴 Критические ({len(critical)})
            </div>
            {''.join([f'<div style="margin: 4px 0; font-size: 0.95em;">• {a["message"]}</div>' for a in critical])}
        </div>
        """, unsafe_allow_html=True)
    
    if warnings:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, rgba(243, 156, 18, 0.2), rgba(243, 156, 18, 0.1));
            border-left: 4px solid #F39C12;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 12px;
        ">
            <div style="font-weight: 600; color: #F39C12; margin-bottom: 8px;">
                ⚠️ Предупреждения ({len(warnings)})
            </div>
            {''.join([f'<div style="margin: 4px 0; font-size: 0.95em;">• {a["message"]}</div>' for a in warnings])}
        </div>
        """, unsafe_allow_html=True)


def render_kpi_cards(data_service: DataService, period: str):
    """Рендер KPI карточек"""
    prod_kpi = data_service.get_productivity_kpi(period)
    downtime_kpi = data_service.get_downtime_kpi(period)

    #st.button('STOP', on_click=lambda x:10/0)

    print(prod_kpi)
    
    col1, col2, col3 = st.columns(3)
    
    # Карточка производительности
    with col1:
        delta_color = "#27AE60" if prod_kpi['delta'] >= 0 else "#E74C3C"
        delta_sign = "+" if prod_kpi['delta'] >= 0 else ""
        plan_color = "#27AE60" if prod_kpi['plan_percent'] >= 90 else ("#F39C12" if prod_kpi['plan_percent'] >= 70 else "#E74C3C")
        
        st.markdown(f"""
        <div style="
            background: linear-gradient(145deg, #1e3a5f, #16213e);
            border-radius: 12px;
            padding: 16px;
            border: 1px solid rgba(255,255,255,0.1);
            height: 145px;
        ">
            <div style="color: #95A5A6; font-size: 0.85em; margin-bottom: 4px;">ПРОИЗВОДИТЕЛЬНОСТЬ</div>
            <div style="font-size: 2em; font-weight: 700; color: #EAECEE;">
                {prod_kpi['current']:.1f} <span style="font-size: 0.5em; color: #95A5A6;">т/ч</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 8px;">
                <span style="color: {delta_color}; font-size: 0.9em;">{delta_sign}{prod_kpi['delta']:.1f}%</span>
                <span style="color: {plan_color}; font-size: 0.9em;">План: {prod_kpi['plan_percent']:.0f}%</span>
            </div>
            <div style="color: #7F8C8D; font-size: 0.75em; margin-top: 4px;">
                Плановое: {prod_kpi['planned']} т/ч
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Карточка простоев
    with col2:
        downtime_color = "#27AE60" if downtime_kpi['total_hours'] < 1 else ("#F39C12" if downtime_kpi['total_hours'] < 3 else "#E74C3C")
        
        st.markdown(f"""
        <div style="
            background: linear-gradient(145deg, #1e3a5f, #16213e);
            border-radius: 12px;
            padding: 16px;
            border: 1px solid rgba(255,255,255,0.1);
            height: 140px;
        ">
            <div style="color: #95A5A6; font-size: 0.85em; margin-bottom: 4px;">ПРОСТОИ</div>
            <div style="font-size: 2em; font-weight: 700; color: {downtime_color};">
                {downtime_kpi['total_hours']:.1f} <span style="font-size: 0.5em; color: #95A5A6;">ч</span>
            </div>
            <div style="color: #95A5A6; font-size: 0.9em; margin-top: 8px;">
                {downtime_kpi['count']} случаев
            </div>
            <div style="color: #7F8C8D; font-size: 0.75em; margin-top: 4px;">
                {downtime_kpi['total_minutes']:.0f} минут
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Карточка смены
    with col3:
        shift_num, shift_start, shift_end = data_service.get_current_shift()
        now = datetime.now()
        elapsed = (now - shift_start).total_seconds() / 3600
        remaining = (shift_end - now).total_seconds() / 3600
        progress = min(elapsed / 12 * 100, 100)
        
        st.markdown(f"""
        <div style="
            background: linear-gradient(145deg, #1e3a5f, #16213e);
            border-radius: 12px;
            padding: 16px;
            border: 1px solid rgba(255,255,255,0.1);
            height: 140px;
        ">
            <div style="color: #95A5A6; font-size: 0.85em; margin-bottom: 4px;">СМЕНА</div>
            <div style="font-size: 2em; font-weight: 700; color: #EAECEE;">
                №{shift_num}
            </div>
            <div style="
                background: rgba(255,255,255,0.1);
                border-radius: 4px;
                height: 6px;
                margin-top: 12px;
                overflow: hidden;
            ">
                <div style="
                    background: linear-gradient(90deg, #3498DB, #2980B9);
                    width: {progress}%;
                    height: 100%;
                    border-radius: 4px;
                "></div>
            </div>
            <div style="color: #7F8C8D; font-size: 0.75em; margin-top: 6px;">
                Осталось: {remaining:.1f} ч
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_mill_card(mill_status: dict, config: dict):
    """Рендер карточки одной мельницы"""
    status_colors = {
        'ok': {'bg': 'rgba(39, 174, 96, 0.15)', 'border': '#27AE60', 'icon': '🟢'},
        'warning': {'bg': 'rgba(243, 156, 18, 0.15)', 'border': '#F39C12', 'icon': '🟡'},
        'critical': {'bg': 'rgba(231, 76, 60, 0.15)', 'border': '#E74C3C', 'icon': '🔴'},
        'neutral': {'bg': 'rgba(127, 140, 141, 0.15)', 'border': '#7F8C8D', 'icon': '⚪'}
    }
    
    status = mill_status['overall_status']
    colors = status_colors.get(status, status_colors['neutral'])
    
    mill_name = mill_status['mill'].replace('мельница_', 'Мельница ')
    
    prod_val = f"{mill_status['productivity']:.1f}" if mill_status['productivity'] is not None else "—"
    dens_val = f"{mill_status['density']:.1f}" if mill_status['density'] is not None else "—"
    
    prod_status_color = SEVERITY_COLORS.get(mill_status['productivity_status'], '#7F8C8D')
    dens_status_color = SEVERITY_COLORS.get(mill_status['density_status'], '#7F8C8D')
    
    st.markdown(f"""
    <div style="
        background: {colors['bg']};
        border: 1px solid {colors['border']};
        border-radius: 12px;
        padding: 14px;
        height: 130px;
    ">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <span style="font-weight: 600; color: #EAECEE;">{mill_name}</span>
            <span>{colors['icon']}</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
            <span style="color: #95A5A6; font-size: 0.85em;">Выработка:</span>
            <span style="color: {prod_status_color}; font-weight: 500;">{prod_val} т/ч</span>
        </div>
        <div style="display: flex; justify-content: space-between;">
            <span style="color: #95A5A6; font-size: 0.85em;">Плотность:</span>
            <span style="color: {dens_status_color}; font-weight: 500;">{dens_val}%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_mills_grid(data_service: DataService):
    """Рендер сетки мельниц"""
    mills = data_service.config['aggregates']['active_mills']
    
    # 4 мельницы в ряд
    cols = st.columns(4)
    
    for i, mill in enumerate(mills):
        with cols[i % 4]:
            status = data_service.get_mill_status(mill)
            render_mill_card(status, data_service.config)


def render_monitor(data_service: DataService):
    """Главная функция рендера вкладки монитора"""
    
    # Заголовок с временем обновления
    col_title, col_time = st.columns([3, 1])
    with col_title:
        st.markdown("### 📊 Монитор производства")
    with col_time:
        st.markdown(f"""
        <div style="text-align: right; color: #7F8C8D; font-size: 0.85em; padding-top: 8px;">
            Обновлено: {datetime.now().strftime('%H:%M:%S')}
        </div>
        """, unsafe_allow_html=True)
    
    # Алерты
    st.markdown("#### ⚠️ Оповещения")
    render_alerts(data_service)
    
    st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)
    
    # KPI с переключателем периода
    col_kpi_title, col_period = st.columns([3, 1])
    with col_kpi_title:
        st.markdown("#### 📈 Ключевые показатели")
    with col_period:
        period = st.selectbox(
            "Период",
            options=["shift", "day", "hour"],
            format_func=lambda x: {"shift": "За смену", "day": "За сутки", "hour": "За час"}[x],
            key="kpi_period",
            label_visibility="collapsed"
        )
    
    render_kpi_cards(data_service, period)
    
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    
    # Статус мельниц
    st.markdown("#### 🏭 Состояние мельниц")
    render_mills_grid(data_service)
    
    st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)
    
    # Легенда
    st.markdown("""
    <div style="
        display: flex; 
        gap: 20px; 
        justify-content: center; 
        color: #95A5A6; 
        font-size: 0.8em;
        padding: 10px;
        background: rgba(255,255,255,0.02);
        border-radius: 8px;
    ">
        <span>🟢 Норма</span>
        <span>🟡 Предупреждение</span>
        <span>🔴 Критично</span>
        <span>⚪ Нет данных</span>
    </div>
    """, unsafe_allow_html=True)

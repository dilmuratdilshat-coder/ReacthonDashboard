## import streamlit as st
## 
## st.set_page_config(page_title="Page Title", layout="wide")
## 
## st.markdown("""
##     <style>
##         .reportview-container {
##             margin-top: -2em;
##         }
##         #MainMenu {visibility: hidden;}
##         .stAppDeployButton {display:none;}
##         footer {visibility: hidden;}
##         #stDecoration {display:none;}
##     </style>
## """, unsafe_allow_html=True)
## 
## x = st.slider("Select a value")
## st.write(x, "squared is", x * x)
## st.write(x, "cubed is", x ** 3)
## if x > 50:
##     st.badge("МШР 1 остановлена", icon='❗', color='red')
## 
## 
## 
## def my_callback_function():
##     st.session_state['my_data'] = "Button was clicked!"
## 
## st.button('Click me', on_click=my_callback_function)
## 
## if 'my_data' in st.session_state:
##     st.write(st.session_state['my_data'])

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

# Конфигурация страницы
st.set_page_config(page_title="Дашборд ОФ", layout="wide", initial_sidebar_state="collapsed")

# Стили
st.markdown("""
<style>
    .stMetric {text-align: center;}
    .alert-critical {padding: 1rem; background: #ff4444; color: white; border-radius: 8px; margin-bottom: 1rem;}
    .alert-warning {padding: 1rem; background: #ff9800; color: white; border-radius: 8px; margin-bottom: 1rem;}
    .mill-card {padding: 1rem; border: 2px solid; border-radius: 8px; text-align: center;}
    .status-ok {border-color: #4caf50; background: #f1f8f4;}
    .status-warning {border-color: #ff9800; background: #fff8e1;}
    .status-critical {border-color: #f44336; background: #ffebee;}
</style>
""", unsafe_allow_html=True)

# ===== МОКОВЫЕ ДАННЫЕ (замените на API) =====
def get_kpi_data():
    return {
        "plan": 127,
        "productivity": 1430,
        "downtime": 84,
        "extraction": 98.58,
        "hse_status": "OK"
    }

def get_mills_data():
    return [
        {"id": 1, "status": "running", "productivity": 41.3, "color": "ok"},
        {"id": 2, "status": "idle", "productivity": 0, "color": "critical", "reason": "Нет данных"},
        {"id": 3, "status": "running", "productivity": 42.0, "color": "ok"},
        {"id": 4, "status": "error", "productivity": 0, "color": "critical", "reason": "Сбой счётчика"},
        {"id": 5, "status": "running", "productivity": 12.5, "color": "ok"}
    ]

def get_productivity_history():
    times = pd.date_range(end=datetime.now(), periods=8, freq='H')
    return pd.DataFrame({
        'Время': times,
        'МШР#1': np.random.randint(35, 43, 8),
        'МШР#2': np.random.randint(30, 40, 8),
        'МШР#3': np.random.randint(38, 44, 8),
        'МШР#4': np.random.randint(8, 13, 8),
        'МШР#5': np.random.randint(11, 14, 8)
    })

def get_downtime_data():
    return pd.DataFrame({
        'Причина': ['Шуровка бункера', 'Сбой счётчика', 'Плановый ремонт', 'Прочее'],
        'Минуты': [47, 23, 10, 4]
    })

def get_events():
    return [
        {"time": "05:15", "mill": "МШР#1", "event": "Шуровка бункера", "duration": "8 мин"},
        {"time": "02:26", "mill": "МШР#1", "event": "Шуровка бункера", "duration": "11 мин"},
        {"time": "01:32", "mill": "МШР#3", "event": "Шуровка бункера", "duration": "10 мин"},
        {"time": "01:00", "mill": "МШР#4", "event": "Сбой счётчика", "duration": "—"},
        {"time": "21:15", "mill": "МШР#1", "event": "Шуровка бункера", "duration": "8 мин"}
    ]

# ===== АЛЕРТЫ =====
kpi = get_kpi_data()
mills = get_mills_data()

critical_mills = [m for m in mills if m["color"] == "critical"]
if critical_mills:
    alerts = " | ".join([f"МШР#{m['id']}: {m.get('reason', 'Простой')}" for m in critical_mills])
    st.markdown(f'<div class="alert-critical">⚠️ КРИТИЧНО: {alerts}</div>', unsafe_allow_html=True)

# ===== KPI КАРТОЧКИ =====
st.markdown("### 📊 Ключевые показатели")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Выполнение плана", f"{kpi['plan']}%", "+27%", delta_color="normal")
with col2:
    st.metric("Производительность", f"{kpi['productivity']} т/см", "—")
with col3:
    delta_color = "inverse" if kpi['downtime'] > 60 else "off"
    st.metric("Простои за смену", f"{kpi['downtime']} мин", "—", delta_color=delta_color)
with col4:
    st.metric("Извлечение", f"{kpi['extraction']}%", "+0.3%", delta_color="normal")
with col5:
    st.metric("HSE статус", kpi['hse_status'], "—")

# ===== СОСТОЯНИЕ МЕЛЬНИЦ =====
st.markdown("### ⚙️ Состояние мельниц")
cols = st.columns(5)

for i, mill in enumerate(mills):
    with cols[i]:
        status_class = f"status-{mill['color']}"
        status_emoji = {"ok": "🟢", "warning": "🟡", "critical": "🔴"}[mill['color']]
        status_text = {"running": "Работает", "idle": "Простой", "error": "Ошибка"}[mill['status']]
        
        reason_text = f"<br><small>{mill.get('reason', '')}</small>" if mill.get('reason') else ""
        
        st.markdown(f"""
        <div class="mill-card {status_class}">
            <h4>МШР#{mill['id']}</h4>
            {status_emoji} {status_text}{reason_text}
            <h3>{mill['productivity']} т/ч</h3>
        </div>
        """, unsafe_allow_html=True)

# ===== ГРАФИКИ И АНАЛИТИКА =====
st.markdown("### 📈 Аналитика")
col_left, col_center, col_right = st.columns([2, 1, 1])

# График производительности
with col_left:
    st.markdown("**Производительность мельниц за смену**")
    df_prod = get_productivity_history()
    fig_prod = px.line(df_prod, x='Время', y=['МШР#1', 'МШР#2', 'МШР#3', 'МШР#4', 'МШР#5'],
                       labels={'value': 'т/ч', 'variable': 'Мельница'})
    fig_prod.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0), legend=dict(orientation="h"))
    st.plotly_chart(fig_prod, use_container_width=True)

# Круговая диаграмма простоев
with col_center:
    st.markdown("**Структура простоев**")
    df_downtime = get_downtime_data()
    fig_downtime = px.pie(df_downtime, values='Минуты', names='Причина', hole=0.4)
    fig_downtime.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
    st.plotly_chart(fig_downtime, use_container_width=True)

# Таблица событий
with col_right:
    st.markdown("**События за смену**")
    events = get_events()
    df_events = pd.DataFrame(events)
    st.dataframe(df_events, height=300, use_container_width=True, hide_index=True)

# ===== ПОДВАЛ =====
st.markdown("---")
st.caption(f"🔄 Обновлено: {datetime.now().strftime('%H:%M:%S')} | Смена 1 | Дата: {datetime.now().strftime('%d.%m.%Y')}")
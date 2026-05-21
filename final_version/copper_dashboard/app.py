"""
Дашборд обогатительной фабрики
==============================
Аналитика и визуализация производственных данных в реальном времени.

Запуск: streamlit run app.py
"""

import streamlit as st
import os
import sys

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_service import get_data_service
from components.monitor import render_monitor
from components.summary import render_summary


# ═══════════════════════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ СТРАНИЦЫ
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Дашборд ОФ | Медь",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ═══════════════════════════════════════════════════════════════════════════════
# КАСТОМНЫЕ СТИЛИ
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
    /* Основной фон */
    .stApp {
        background: linear-gradient(180deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
    }
    
    /* Убираем стандартные отступы */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 100%;
    }
    
    /* Стили для табов */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(255,255,255,0.03);
        border-radius: 12px;
        padding: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: #95A5A6;
        font-weight: 500;
        padding: 10px 24px;
        background: transparent;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #3498DB, #2980B9);
        color: white !important;
    }
    
    /* Стили для метрик */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        color: #EAECEE;
    }
    
    [data-testid="stMetricLabel"] {
        color: #95A5A6;
    }
    
    /* Убираем рамки у селектов */
    .stSelectbox > div > div {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 8px;
    }
    
    /* Кнопки */
    .stButton > button {
        background: linear-gradient(135deg, #3498DB, #2980B9);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 20px;
        font-weight: 500;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #2980B9, #1a5276);
    }
    
    /* Скрываем Streamlit меню и футер */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}/*!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!:*/
    
    /* Разделители */
    hr {
        border: none;
        border-top: 1px solid rgba(255,255,255,0.1);
        margin: 16px 0;
    }
    
    /* Заголовки */
    h1, h2, h3, h4 {
        color: #EAECEE !important;
    }
    
    /* Selectbox label */
    .stSelectbox label {
        color: #95A5A6 !important;
    }
    
    /* Date input */
    .stDateInput > div > div {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 8px;
    }
    
    /* Info/Warning boxes */
    .stAlert {
        background: rgba(255,255,255,0.05);
        border-radius: 8px;
    }
    
    /* Plotly charts background */
    .js-plotly-plot {
        border-radius: 12px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# ИНИЦИАЛИЗАЦИЯ
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def init_data_service():
    """Инициализация сервиса данных (кэшируется)"""
    service = get_data_service("config.yaml")
    #service.streamlit_inst = st
    service.start_watching()  # Запускаем watchdog
    return service


# Получаем сервис данных
data_service = init_data_service()


# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════

col_logo, col_title, col_refresh = st.columns([0.5, 4, 1])

#with col_logo:
#    st.markdown("""
#    <div style="font-size: 2.5em; text-align: center;">🏭</div>
#    """, unsafe_allow_html=True)

with col_title:
    st.markdown("""
    <div>
        <h2 style="margin: 0; padding: 0; color: #EAECEE;">Yer-Tai Monitoring Dashboard</h2>
        <p style="margin: 0; color: #7F8C8D; font-size: 0.9em;">Аналитика и мониторинг производственных данных</p>
    </div>
    """, unsafe_allow_html=True)

with col_refresh:
    if st.button("🔄 Обновить", key="refresh_btn"):
        data_service.reload_all()
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# ОСНОВНОЙ КОНТЕНТ
# ═══════════════════════════════════════════════════════════════════════════════

tab_monitor, tab_summary = st.tabs(["📊 Монитор", "📈 Итоги"])

with tab_monitor:
    render_monitor(data_service)

with tab_summary:
    render_summary(data_service)


# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="
    text-align: center; 
    color: #7F8C8D; 
    font-size: 0.75em; 
    padding: 20px 0 10px 0;
    border-top: 1px solid rgba(255,255,255,0.05);
    margin-top: 30px;
">
    Chemicthon 2026
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# AUTO-REFRESH
# ═══════════════════════════════════════════════════════════════════════════════

import streamlit.components.v1 as components

def trigger_browser_refresh():
    """Инжектирует JavaScript для перезагрузки страницы через iframe"""
    components.html(
        """
        <script>
            window.parent.location.reload();
        </script>
        """,
        height=0
    )

# Фрагмент проверяет изменения каждые N секунд
@st.fragment(run_every=data_service.config['data'].get('watch_interval', 5))
def check_for_updates():
    """Периодически проверяет обновления данных"""
    if data_service.check_and_clear_changed_flag():
        st.toast("🔄 Данные обновлены!", icon="✅")
        print('REreloading')
        trigger_browser_refresh()

# Запускаем проверку
check_for_updates()

### # ═══════════════════════════════════════════════════════════════════════════════
### # AUTO-REFRESH (опционально)
### # ═══════════════════════════════════════════════════════════════════════════════
### 
### # Автообновление каждые N секунд для проверки изменений файлов
### # Используем фрагмент с автообновлением (Streamlit 1.33+)
### try:
###     @st.fragment(run_every=data_service.config['data'].get('watch_interval', 5))
###     def auto_refresh_checker():
###         """Фрагмент для автоматической проверки обновлений"""
###         if data_service.check_and_clear_changed_flag():
###             st.toast("🔄 Данные обновлены!", icon="✅")
###             st.rerun(scope='app')
###     
###     auto_refresh_checker()
### except AttributeError:
###     # Fallback для старых версий Streamlit - используем кнопку auto-refresh
###     pass

## # ═══════════════════════════════════════════════════════════════════════════════
## # AUTO-REFRESH (опционально)
## # ═══════════════════════════════════════════════════════════════════════════════
## 
## # Раскомментировать для автоматического обновления каждые N секунд
## import time
## refresh_interval = data_service.config['ui']['refresh_interval']
## time.sleep(refresh_interval)
## st.rerun()

"""
Модуль обобщённых функций для графиков
======================================
Унифицированные функции для создания различных типов визуализаций
"""

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# ЦВЕТОВЫЕ СХЕМЫ
# ═══════════════════════════════════════════════════════════════════════════════

SEVERITY_COLORS = {
    "ok": "#27AE60",
    "warning": "#F39C12", 
    "critical": "#E74C3C",
    "neutral": "#7F8C8D"
}

CHART_TEMPLATE = "plotly_dark"
CHART_BG = "rgba(22, 33, 62, 0.8)"
PAPER_BG = "rgba(0,0,0,0)"
GRID_COLOR = "rgba(255,255,255,0.1)"
FONT_COLOR = "#EAECEE"


def get_chart_layout(
    title: str = "",
    height: int = 400,
    showlegend: bool = True,
    margin: Dict = None
) -> Dict:
    """Базовый layout для всех графиков"""
    return {
        "template": CHART_TEMPLATE,
        "paper_bgcolor": PAPER_BG,
        "plot_bgcolor": CHART_BG,
        "font": {"color": FONT_COLOR, "family": "Inter, sans-serif"},
        "title": {"text": title, "font": {"size": 16}},
        "height": height,
        "showlegend": showlegend,
        "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02},
        "margin": margin or {"l": 50, "r": 30, "t": 50, "b": 50},
        "xaxis": {"gridcolor": GRID_COLOR, "zerolinecolor": GRID_COLOR},
        "yaxis": {"gridcolor": GRID_COLOR, "zerolinecolor": GRID_COLOR},
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ЛИНЕЙНЫЕ ГРАФИКИ
# ═══════════════════════════════════════════════════════════════════════════════

def create_time_series(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str = "",
    color: str = "#3498DB",
    height: int = 350,
    show_anomalies: bool = False,
    anomaly_col: str = "severity",
    threshold_lines: List[Dict] = None,
    y_label: str = ""
) -> go.Figure:
    """
    Универсальный линейный график временного ряда.
    
    Args:
        df: DataFrame с данными
        x: Колонка для оси X (время)
        y: Колонка для оси Y (значения)
        title: Заголовок
        color: Основной цвет линии
        show_anomalies: Показывать аномалии точками
        anomaly_col: Колонка с severity для аномалий
        threshold_lines: Список порогов [{value: float, color: str, label: str}]
        y_label: Подпись оси Y
    """
    fig = go.Figure()
    
    # Основная линия
    fig.add_trace(go.Scatter(
        x=df[x],
        y=df[y],
        mode='lines',
        name=y_label or y,
        line={"color": color, "width": 2},
        hovertemplate=f"<b>%{{x}}</b><br>{y_label or y}: %{{y:.2f}}<extra></extra>"
    ))
    
    # Аномалии
    if show_anomalies and anomaly_col in df.columns:
        for severity, sev_color in [("warning", SEVERITY_COLORS["warning"]), 
                                     ("critical", SEVERITY_COLORS["critical"])]:
            anomalies = df[df[anomaly_col] == severity]
            if not anomalies.empty:
                fig.add_trace(go.Scatter(
                    x=anomalies[x],
                    y=anomalies[y],
                    mode='markers',
                    name=f"{'⚠️ Предупреждение' if severity == 'warning' else '🔴 Критично'}",
                    marker={"color": sev_color, "size": 10, "symbol": "circle"},
                    hovertemplate=(
                        f"<b>%{{x}}</b><br>"
                        f"Значение: %{{y:.2f}}<br>"
                        f"Статус: {severity}<extra></extra>"
                    )
                ))
    
    # Пороговые линии
    if threshold_lines:
        for th in threshold_lines:
            fig.add_hline(
                y=th["value"],
                line_dash="dash",
                line_color=th.get("color", "#E74C3C"),
                annotation_text=th.get("label", ""),
                annotation_position="right"
            )
    
    fig.update_layout(**get_chart_layout(title=title, height=height))
    if y_label:
        fig.update_yaxes(title_text=y_label)
    
    return fig


def create_multi_line(
    df: pd.DataFrame,
    x: str,
    y_columns: List[str],
    title: str = "",
    colors: List[str] = None,
    height: int = 400,
    y_label: str = ""
) -> go.Figure:
    """
    Линейный график с несколькими линиями (для сравнения агрегатов).
    """
    fig = go.Figure()
    
    default_colors = px.colors.qualitative.Set2
    colors = colors or default_colors
    
    for i, col in enumerate(y_columns):
        if col in df.columns:
            fig.add_trace(go.Scatter(
                x=df[x],
                y=df[col],
                mode='lines',
                name=col,
                line={"color": colors[i % len(colors)], "width": 2},
            ))
    
    fig.update_layout(**get_chart_layout(title=title, height=height))
    if y_label:
        fig.update_yaxes(title_text=y_label)
    
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# ГИСТОГРАММЫ И BAR CHARTS
# ═══════════════════════════════════════════════════════════════════════════════

def create_bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str = "",
    color: str = None,
    color_column: str = None,
    color_map: Dict = None,
    height: int = 350,
    orientation: str = "v",
    show_values: bool = True
) -> go.Figure:
    """
    Универсальная гистограмма / bar chart.
    
    Args:
        color_column: Колонка для цветового кодирования
        color_map: Маппинг значений на цвета
    """
    if color_column and color_map:
        colors = df[color_column].map(color_map).fillna(SEVERITY_COLORS["neutral"])
    else:
        colors = color or "#3498DB"
    
    if orientation == "v":
        fig = go.Figure(go.Bar(
            x=df[x],
            y=df[y],
            marker_color=colors,
            text=df[y].round(1) if show_values else None,
            textposition='outside',
            hovertemplate=f"<b>%{{x}}</b><br>{y}: %{{y:.1f}}<extra></extra>"
        ))
    else:
        fig = go.Figure(go.Bar(
            y=df[x],
            x=df[y],
            orientation='h',
            marker_color=colors,
            text=df[y].round(1) if show_values else None,
            textposition='outside',
            hovertemplate=f"<b>%{{y}}</b><br>{y}: %{{x:.1f}}<extra></extra>"
        ))
    
    fig.update_layout(**get_chart_layout(title=title, height=height, showlegend=False))
    return fig


def create_grouped_bar(
    df: pd.DataFrame,
    x: str,
    y_columns: List[str],
    title: str = "",
    colors: List[str] = None,
    height: int = 400
) -> go.Figure:
    """Grouped bar chart для сравнения нескольких метрик"""
    fig = go.Figure()
    
    default_colors = ["#3498DB", "#E74C3C", "#27AE60", "#F39C12"]
    colors = colors or default_colors
    
    for i, col in enumerate(y_columns):
        fig.add_trace(go.Bar(
            name=col,
            x=df[x],
            y=df[col],
            marker_color=colors[i % len(colors)]
        ))
    
    fig.update_layout(**get_chart_layout(title=title, height=height))
    fig.update_layout(barmode='group')
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# КРУГОВЫЕ ДИАГРАММЫ
# ═══════════════════════════════════════════════════════════════════════════════

def create_pie_chart(
    df: pd.DataFrame,
    values: str,
    names: str,
    title: str = "",
    colors: List[str] = None,
    color_map: Dict = None,
    height: int = 300,
    hole: float = 0.4
) -> go.Figure:
    """
    Круговая/кольцевая диаграмма.
    """
    if color_map:
        colors = [color_map.get(name, SEVERITY_COLORS["neutral"]) for name in df[names]]
    
    fig = go.Figure(go.Pie(
        values=df[values],
        labels=df[names],
        hole=hole,
        marker_colors=colors,
        textinfo='percent+label',
        hovertemplate="<b>%{label}</b><br>Время: %{value:.0f} мин<br>Доля: %{percent}<extra></extra>"
    ))
    
    fig.update_layout(**get_chart_layout(title=title, height=height, showlegend=True))
    return fig


def create_sunburst(
    df: pd.DataFrame,
    path: List[str],
    values: str,
    title: str = "",
    color_map: Dict = None,
    height: int = 400
) -> go.Figure:
    """
    Sunburst диаграмма для иерархических данных (категория -> подкатегория).
    """
    fig = px.sunburst(
        df,
        path=path,
        values=values,
        color=path[0] if color_map else None,
        color_discrete_map=color_map
    )
    
    fig.update_layout(**get_chart_layout(title=title, height=height, showlegend=False))
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# GAUGE / ИНДИКАТОРЫ
# ═══════════════════════════════════════════════════════════════════════════════

def create_gauge(
    value: float,
    title: str = "",
    min_val: float = 0,
    max_val: float = 100,
    thresholds: Dict = None,
    suffix: str = "",
    height: int = 200
) -> go.Figure:
    """
    Gauge индикатор для KPI.
    
    Args:
        thresholds: {"green": [min, max], "yellow": [min, max], "red": [min, max]}
    """
    # Дефолтные пороги
    if thresholds is None:
        thresholds = {
            "green": [max_val * 0.7, max_val],
            "yellow": [max_val * 0.4, max_val * 0.7],
            "red": [min_val, max_val * 0.4]
        }
    
    steps = []
    if "red" in thresholds:
        steps.append({"range": thresholds["red"], "color": "rgba(231, 76, 60, 0.3)"})
    if "yellow" in thresholds:
        steps.append({"range": thresholds["yellow"], "color": "rgba(243, 156, 18, 0.3)"})
    if "green" in thresholds:
        steps.append({"range": thresholds["green"], "color": "rgba(39, 174, 96, 0.3)"})
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": title, "font": {"size": 14, "color": FONT_COLOR}},
        number={"suffix": suffix, "font": {"color": FONT_COLOR}},
        gauge={
            "axis": {"range": [min_val, max_val], "tickcolor": FONT_COLOR},
            "bar": {"color": "#3498DB"},
            "bgcolor": "rgba(0,0,0,0)",
            "bordercolor": GRID_COLOR,
            "steps": steps,
            "threshold": {
                "line": {"color": "#E74C3C", "width": 2},
                "thickness": 0.75,
                "value": value
            }
        }
    ))
    
    fig.update_layout(
        paper_bgcolor=PAPER_BG,
        font={"color": FONT_COLOR},
        height=height,
        margin={"l": 30, "r": 30, "t": 50, "b": 30}
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# КОМБИНИРОВАННЫЕ ГРАФИКИ
# ═══════════════════════════════════════════════════════════════════════════════

def create_dual_axis(
    df: pd.DataFrame,
    x: str,
    y1: str,
    y2: str,
    title: str = "",
    y1_label: str = "",
    y2_label: str = "",
    y1_color: str = "#3498DB",
    y2_color: str = "#E74C3C",
    height: int = 400
) -> go.Figure:
    """График с двумя осями Y"""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(
        go.Scatter(x=df[x], y=df[y1], name=y1_label or y1, 
                   line={"color": y1_color, "width": 2}),
        secondary_y=False
    )
    
    fig.add_trace(
        go.Scatter(x=df[x], y=df[y2], name=y2_label or y2,
                   line={"color": y2_color, "width": 2}),
        secondary_y=True
    )
    
    layout = get_chart_layout(title=title, height=height)
    fig.update_layout(**layout)
    fig.update_yaxes(title_text=y1_label or y1, secondary_y=False, gridcolor=GRID_COLOR)
    fig.update_yaxes(title_text=y2_label or y2, secondary_y=True, gridcolor=GRID_COLOR)
    
    return fig


def create_area_with_threshold(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str = "",
    threshold_min: float = None,
    threshold_max: float = None,
    height: int = 350
) -> go.Figure:
    """Area chart с зоной допустимых значений"""
    fig = go.Figure()
    
    # Зона допуска
    if threshold_min is not None and threshold_max is not None:
        fig.add_hrect(
            y0=threshold_min, y1=threshold_max,
            fillcolor="rgba(39, 174, 96, 0.2)",
            line_width=0,
            annotation_text="Норма",
            annotation_position="right"
        )
    
    # Основной график
    fig.add_trace(go.Scatter(
        x=df[x],
        y=df[y],
        fill='tozeroy',
        fillcolor='rgba(52, 152, 219, 0.3)',
        line={"color": "#3498DB", "width": 2},
        hovertemplate="<b>%{x}</b><br>Значение: %{y:.2f}<extra></extra>"
    ))
    
    fig.update_layout(**get_chart_layout(title=title, height=height, showlegend=False))
    return fig

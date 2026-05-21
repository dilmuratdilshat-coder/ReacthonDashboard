"""
Модуль детекции аномалий
========================
Поддерживает два метода:
- Скользящая средняя (Moving Average)
- Z-score
"""

import pandas as pd
import numpy as np
from typing import Tuple, Literal
from dataclasses import dataclass


@dataclass
class AnomalyResult:
    """Результат детекции аномалий"""
    value: float
    is_anomaly: bool
    severity: Literal["ok", "warning", "critical"]
    reference_value: float  # MA или mean
    deviation: float  # отклонение в % или sigma
    message: str


def detect_anomalies_ma(
    series: pd.Series,
    window: int = 24,
    warning_dev: float = 0.15,
    critical_dev: float = 0.25
) -> pd.DataFrame:
    """
    Детекция аномалий методом скользящей средней.
    
    Args:
        series: Временной ряд значений
        window: Размер окна (в записях)
        warning_dev: Порог предупреждения (0.15 = 15%)
        critical_dev: Порог критического отклонения
    
    Returns:
        DataFrame с колонками: value, ma, deviation, severity, is_anomaly
    """
    df = pd.DataFrame({'value': series})
    df['ma'] = series.rolling(window=window, min_periods=1).mean()
    
    # Отклонение от MA в процентах
    df['deviation'] = np.where(
        df['ma'] != 0,
        (df['value'] - df['ma']).abs() / df['ma'],
        0
    )
    
    # Определяем severity
    conditions = [
        df['deviation'] >= critical_dev,
        df['deviation'] >= warning_dev,
    ]
    choices = ['critical', 'warning']
    df['severity'] = np.select(conditions, choices, default='ok')
    df['is_anomaly'] = df['severity'] != 'ok'
    
    return df


def detect_anomalies_zscore(
    series: pd.Series,
    window: int = 72,
    warning_threshold: float = 2.0,
    critical_threshold: float = 3.0
) -> pd.DataFrame:
    """
    Детекция аномалий методом Z-score.
    
    Args:
        series: Временной ряд значений
        window: Размер окна для расчёта статистик
        warning_threshold: Порог Z-score для предупреждения
        critical_threshold: Порог Z-score для критического
    
    Returns:
        DataFrame с колонками: value, mean, std, zscore, severity, is_anomaly
    """
    df = pd.DataFrame({'value': series})
    df['mean'] = series.rolling(window=window, min_periods=1).mean()
    df['std'] = series.rolling(window=window, min_periods=1).std().fillna(1)
    
    # Z-score
    df['zscore'] = np.where(
        df['std'] != 0,
        (df['value'] - df['mean']).abs() / df['std'],
        0
    )
    
    # Определяем severity
    conditions = [
        df['zscore'] >= critical_threshold,
        df['zscore'] >= warning_threshold,
    ]
    choices = ['critical', 'warning']
    df['severity'] = np.select(conditions, choices, default='ok')
    df['is_anomaly'] = df['severity'] != 'ok'
    
    return df


def check_threshold(
    value: float,
    min_val: float = None,
    max_val: float = None,
    yellow_min: float = None,
    critical_below: float = None
) -> Tuple[str, str]:
    """
    Проверка значения относительно порогов.
    
    Returns:
        (severity, message)
    """
    if pd.isna(value):
        return "neutral", "Нет данных"
    
    # Для производительности (с жёлтой зоной)
    if critical_below is not None:
        if value < critical_below:
            return "critical", f"Критически низко: {value:.1f}"
        elif yellow_min is not None and value < yellow_min:
            return "warning", f"Ниже нормы: {value:.1f}"
        elif min_val is not None and value >= min_val:
            return "ok", f"Норма: {value:.1f}"
        return "ok", f"{value:.1f}"
    
    # Для плотности/pH (только границы)
    if min_val is not None and max_val is not None:
        if value < min_val or value > max_val:
            return "critical", f"Вне допуска: {value:.1f}"
        return "ok", f"Норма: {value:.1f}"
    
    return "neutral", f"{value:.1f}"


def calculate_kpi_delta(current: float, previous: float) -> Tuple[float, str]:
    """
    Расчёт изменения KPI.
    
    Returns:
        (процент изменения, строка для отображения)
    """
    if previous == 0 or pd.isna(previous) or pd.isna(current):
        return 0, "—"
    
    delta = ((current - previous) / previous) * 100
    sign = "+" if delta > 0 else ""
    return delta, f"{sign}{delta:.1f}%"


def get_anomaly_label(row: pd.Series, method: str = "ma") -> str:
    """Генерация лейбла для аномалии на графике"""
    if not row.get('is_anomaly', False):
        return ""
    
    severity_icons = {"warning": "⚠️", "critical": "🔴"}
    icon = severity_icons.get(row['severity'], "")
    
    if method == "ma":
        return f"{icon} {row['value']:.1f} (откл. {row['deviation']*100:.0f}%)"
    else:
        return f"{icon} {row['value']:.1f} (z={row['zscore']:.1f}σ)"

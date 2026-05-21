"""
Data Service
============
Сервис загрузки, кэширования и обработки данных.
Поддерживает watchdog для автоматического обновления при изменении файлов.
"""

import pandas as pd
import numpy as np
import yaml
import os
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass, field
import hashlib
#from streamlit.runtime import get_instance
#from streamlit.runtime.session_manager import SessionManager
from streamlit.commands.execution_control import rerun

from utils.anomaly import detect_anomalies_ma, detect_anomalies_zscore, check_threshold

DEBUG = True
DEBUG_DATE = datetime(2026, 1, 16)

@dataclass
class DataCache:
    """Кэш данных с метаданными"""
    tech_journal: pd.DataFrame = None
    downtime: pd.DataFrame = None
    water: pd.DataFrame = None
    last_updated: datetime = None
    file_hashes: Dict[str, str] = field(default_factory=dict)
    data_changed: bool = False  # Флаг для сигнализации об изменениях


class DataService:
    """
    Синглтон-сервис для работы с данными.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, config_path: str = "config.yaml"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_path: str = "config.yaml"):
        if self._initialized:
            return
        
        self.config_path = config_path
        self.config = self._load_config()
        self.cache = DataCache()
        self._watch_thread = None
        self._stop_watching = threading.Event()
        #self.streamlit_inst = streamlit_inst
        
        # Загружаем данные при инициализации
        self.reload_all()
        self._initialized = True
    
    def _load_config(self) -> Dict:
        """Загрузка конфигурации из YAML"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def reload_config(self):
        """Перезагрузка конфигурации"""
        self.config = self._load_config()
    
    def _get_file_hash(self, filepath: str) -> str:
        """Получение хэша файла для отслеживания изменений"""
        if not os.path.exists(filepath):
            return ""
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def _check_files_changed(self) -> bool:
        """Проверка изменились ли файлы"""
        data_config = self.config['data']
        files = [
            data_config['tech_journal'],
            data_config['downtime'],
            data_config['water']
        ]
        
        for filepath in files:
            if os.path.exists(filepath):
                current_hash = self._get_file_hash(filepath)
                #print(current_hash, self.cache.file_hashes.get(filepath), self.cache.file_hashes.get(filepath) != current_hash)
                # NOTE!!!
                if self.cache.file_hashes.get(filepath) != current_hash:
                    return True
        return False
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ЗАГРУЗКА ДАННЫХ
    # ═══════════════════════════════════════════════════════════════════════════
    
    def reload_all(self):
        """Перезагрузка всех данных"""
        data_config = self.config['data']
        
        self.cache.tech_journal = self._load_tech_journal(data_config['tech_journal'])
        self.cache.downtime = self._load_downtime(data_config['downtime'])
        self.cache.water = self._load_water(data_config['water'])
        self.cache.last_updated = datetime.now()
        
        # Обновляем хэши
        for key in ['tech_journal', 'downtime', 'water']:
            filepath = data_config[key]
            if os.path.exists(filepath):
                self.cache.file_hashes[filepath] = self._get_file_hash(filepath)
    
    def _load_tech_journal(self, filepath: str) -> pd.DataFrame:
        """Загрузка и обработка технического журнала"""
        if not os.path.exists(filepath):
            return pd.DataFrame()
        
        df = pd.read_csv(filepath, encoding='utf-8-sig', dtype={'значение':float})
        
        # Нормализация колонок
        df.columns = df.columns.str.strip().str.lower()
        
        # Парсинг даты и времени
        if 'дата' in df.columns:
            df['дата'] = pd.to_datetime(df['дата'], errors='coerce')
        
        # Нормализация часа (может быть "21:00" или просто "21")
        if 'час' in df.columns:
            df['час'] = df['час'].astype(str).str.extract(r'(\d+)')[0].astype(float)
        
        # Создаём полный timestamp
        if 'дата' in df.columns and 'час' in df.columns:
            df['timestamp'] = df.apply(
                lambda r: r['дата'] + timedelta(hours=r['час']) if pd.notna(r['час']) else r['дата'],
                axis=1
            )
        
        # Нормализация названий агрегатов
        if 'агрегат' in df.columns:
            df['агрегат'] = df['агрегат'].str.strip().str.lower()
        
        return df
    
    def _load_downtime(self, filepath: str) -> pd.DataFrame:
        """Загрузка и обработка журнала простоев"""
        if not os.path.exists(filepath):
            return pd.DataFrame()
        
        df = pd.read_csv(filepath, encoding='utf-8-sig')
        df.columns = df.columns.str.strip().str.lower()
        
        # Парсинг timestamp
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        # Нормализация названий агрегатов
        name_mapping = self.config['aggregates']['name_mapping']
        if 'aggregate' in df.columns:
            df['aggregate_normalized'] = df['aggregate'].map(
                lambda x: name_mapping.get(x, name_mapping.get(x.lower() if isinstance(x, str) else x, x))
            )
        
        # Нормализация категорий
        if 'category' in df.columns:
            df['category'] = df['category'].str.strip()
        
        return df
    
    def _load_water(self, filepath: str) -> pd.DataFrame:
        """Загрузка и обработка данных по воде"""
        if not os.path.exists(filepath):
            return pd.DataFrame()
        
        # Файл с табуляцией как разделителем
        df = pd.read_csv(filepath, encoding='utf-8-sig', sep='\t')
        df.columns = df.columns.str.strip().str.lower()
        
        # Нормализация названий колонок
        column_mapping = {
            'дата': 'date',
            'номинальный ежедневный расход': 'nominal',
            'показание счетчика': 'meter',
            'фактический расход за сутки': 'actual',
            'расход в час': 'hourly'
        }
        df = df.rename(columns=column_mapping)
        
        # Парсинг даты
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # Заполнение NaN в nominal
        if 'nominal' in df.columns:
            df['nominal'] = pd.to_numeric(df['nominal'], errors='coerce')
        
        return df
    
    # ═══════════════════════════════════════════════════════════════════════════
    # WATCHDOG
    # ═══════════════════════════════════════════════════════════════════════════
    
    def start_watching(self):
        """Запуск фонового потока для отслеживания изменений файлов"""
        if self._watch_thread is not None and self._watch_thread.is_alive():
            return
        
        self._stop_watching.clear()
        self._watch_thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._watch_thread.start()
    
    def stop_watching(self):
        """Остановка отслеживания"""
        self._stop_watching.set()
        if self._watch_thread:
            self._watch_thread.join(timeout=5)
    
    def _watch_loop(self):
        """Цикл проверки изменений файлов"""
        interval = self.config['data'].get('watch_interval', 5)
        while not self._stop_watching.is_set():
            if self._check_files_changed():
                print('reloading')
                self.reload_all()
                self.cache.data_changed = True  # Устанавливаем флаг
                #rerun() ###############################################################################################
            time.sleep(interval)
    
    def check_and_clear_changed_flag(self) -> bool:
        """
        Проверяет флаг изменений и сбрасывает его.
        Вызывать из основного потока Streamlit.
        
        Returns:
            True если данные изменились с последней проверки
        """
        if self.cache.data_changed:
            self.cache.data_changed = False
            return True
        return False
    
    # ═══════════════════════════════════════════════════════════════════════════
    # GETTERS С ФИЛЬТРАЦИЕЙ
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_tech_data(
        self,
        data_type: str = None,
        aggregate: str = None,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> pd.DataFrame:
        """
        Получение данных тех.журнала с фильтрацией.
        
        Args:
            data_type: Тип данных (производительность, плотность, ph, и т.д.)
            aggregate: Фильтр по агрегату
            start_date: Начало периода
            end_date: Конец периода
        """
        df = self.cache.tech_journal.copy()
        if df.empty:
            return df
        
        if data_type and 'тип_данных' in df.columns:
            df = df[df['тип_данных'] == data_type]
        
        if aggregate and 'агрегат' in df.columns:
            df = df[df['агрегат'] == aggregate.lower()]
        
        if start_date and 'timestamp' in df.columns:
            df = df[df['timestamp'] >= start_date]
        
        if end_date and 'timestamp' in df.columns:
            df = df[df['timestamp'] <= end_date]
        
        return df.sort_values('timestamp') if 'timestamp' in df.columns else df
    
    def get_downtime_data(
        self,
        aggregate: str = None,
        category: str = None,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> pd.DataFrame:
        """Получение данных о простоях с фильтрацией"""
        df = self.cache.downtime.copy()
        if df.empty:
            return df
        
        if aggregate and 'aggregate_normalized' in df.columns:
            df = df[df['aggregate_normalized'] == aggregate.lower()]
        
        if category and 'category' in df.columns:
            df = df[df['category'] == category]
        
        if start_date and 'timestamp' in df.columns:
            df = df[df['timestamp'] >= start_date]
        
        if end_date and 'timestamp' in df.columns:
            df = df[df['timestamp'] <= end_date]
        
        return df
    
    def get_water_data(
        self,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> pd.DataFrame:
        """Получение данных по воде с фильтрацией"""
        df = self.cache.water.copy()
        if df.empty:
            return df
        
        if start_date and 'date' in df.columns:
            df = df[df['date'] >= start_date]
        
        if end_date and 'date' in df.columns:
            df = df[df['date'] <= end_date]
        
        return df.sort_values('date') if 'date' in df.columns else df
    
    # ═══════════════════════════════════════════════════════════════════════════
    # РАСЧЁТЫ KPI
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_current_shift(self) -> Tuple[int, datetime, datetime]:
        """Получение текущей смены и её временных границ"""
        now = datetime.now() if not DEBUG else datetime(2026, 1, 16)
        shift_config = self.config['shifts']
        shift1_start = shift_config['shift_1_start']
        shift2_start = shift_config['shift_2_start']
        
        current_hour = now.hour
        
        if shift1_start <= current_hour < shift2_start:
            # Смена 1 (дневная)
            shift_start = now.replace(hour=shift1_start, minute=0, second=0, microsecond=0)
            shift_end = now.replace(hour=shift2_start, minute=0, second=0, microsecond=0)
            return 1, shift_start, shift_end
        else:
            # Смена 2 (ночная)
            if current_hour >= shift2_start:
                shift_start = now.replace(hour=shift2_start, minute=0, second=0, microsecond=0)
                shift_end = (now + timedelta(days=1)).replace(hour=shift1_start, minute=0, second=0, microsecond=0)
            else:
                shift_start = (now - timedelta(days=1)).replace(hour=shift2_start, minute=0, second=0, microsecond=0)
                shift_end = now.replace(hour=shift1_start, minute=0, second=0, microsecond=0)
            return 2, shift_start, shift_end
    
    def get_productivity_kpi(self, period: str = "shift") -> Dict:
        """
        Расчёт KPI производительности.
        
        Args:
            period: "hour", "shift", "day"
        """
        now = datetime.now() if not DEBUG else datetime(2026, 1, 16)
        
        if period == "hour":
            start = now - timedelta(hours=1)
            prev_start = now - timedelta(hours=2)
            prev_end = start
        elif period == "shift":
            _, shift_start, shift_end = self.get_current_shift()
            start = shift_start
            prev_start = shift_start - timedelta(hours=12)
            prev_end = shift_start
        else:  # day
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            prev_start = start - timedelta(days=1)
            prev_end = start
        
        # Текущий период
        df_current = self.get_tech_data(
            data_type='производительность',
            aggregate='всего',
            start_date=start,
            end_date=now
        )
        
        # Предыдущий период
        df_prev = self.get_tech_data(
            data_type='производительность',
            aggregate='всего',
            start_date=prev_start,
            end_date=prev_end
        )
        # print(df_current)
        
        current_avg = df_current['значение'].mean() if not df_current.empty else 0
        prev_avg = df_prev['значение'].mean() if not df_prev.empty else 0
        
        planned = self.config['thresholds']['productivity']['planned_total']
        
        return {
            'current': current_avg,
            'previous': prev_avg,
            'planned': planned,
            'delta': ((current_avg - prev_avg) / prev_avg * 100) if prev_avg > 0 else 0,
            'plan_percent': (current_avg / planned * 100) if planned > 0 else 0
        }
    
    def get_downtime_kpi(self, period: str = "shift") -> Dict:
        """Расчёт KPI простоев"""
        now = datetime.now() if not DEBUG else datetime(2026, 1, 16)
        
        if period == "hour":
            start = now - timedelta(hours=1)
        elif period == "shift":
            _, start, _ = self.get_current_shift()
        else:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        df = self.get_downtime_data(start_date=start, end_date=now)
        
        total_minutes = df['time_span'].sum() if not df.empty and 'time_span' in df.columns else 0
        
        # По категориям
        by_category = {}
        if not df.empty and 'category' in df.columns:
            by_category = df.groupby('category')['time_span'].sum().to_dict()
        
        return {
            'total_minutes': total_minutes,
            'total_hours': total_minutes / 60,
            'by_category': by_category,
            'count': len(df)
        }
    
    def get_mill_status(self, mill: str) -> Dict:
        """Получение текущего статуса мельницы"""
        # Последние данные по производительности
        df_prod = self.get_tech_data(data_type='производительность', aggregate=mill)
        df_dens = self.get_tech_data(data_type='плотность', aggregate=mill)
        
        prod_value = float(df_prod['значение'].iloc[-1] if not df_prod.empty else None)
        dens_value = float(df_dens['значение'].iloc[-1] if not df_dens.empty else None)
        
        # Получаем пороги
        thresholds = self.config['thresholds']
        prod_th = thresholds['productivity'].get(mill, thresholds['productivity'].get('мельница_1'))
        dens_th = thresholds['density'].get(mill, thresholds['density']['default'])
        
        # print(prod_th)
        # print()
        # print(dens_th)

        # Определяем статусы
        prod_status, prod_msg = check_threshold(
            prod_value,
            min_val=float(prod_th.get('green_min')),
            yellow_min=float(prod_th.get('yellow_min')),
            critical_below=float(prod_th.get('critical_below'))
        )
        
        dens_status, dens_msg = check_threshold(
            dens_value,
            min_val=float(dens_th['min']),
            max_val=float(dens_th['max'])
        )
        
        # Общий статус - худший из двух
        status_priority = {'critical': 3, 'warning': 2, 'ok': 1, 'neutral': 0}
        overall_status = max([prod_status, dens_status], key=lambda x: status_priority.get(x, 0))
        
        return {
            'mill': mill,
            'productivity': prod_value,
            'productivity_status': prod_status,
            'productivity_message': prod_msg,
            'density': dens_value,
            'density_status': dens_status,
            'density_message': dens_msg,
            'overall_status': overall_status,
            'last_update': df_prod['timestamp'].iloc[-1] if not df_prod.empty and 'timestamp' in df_prod.columns else None
        }
    
    def get_alerts(self) -> List[Dict]:
        """Получение списка текущих алертов"""
        alerts = []
        mills = self.config['aggregates']['active_mills']
        
        for mill in mills:
            status = self.get_mill_status(mill)
            
            if status['productivity_status'] == 'critical':
                alerts.append({
                    'severity': 'critical',
                    'type': 'productivity',
                    'aggregate': mill,
                    'message': f"Критическая производительность {mill}: {status['productivity']:.1f} т/ч",
                    'value': status['productivity']
                })
            elif status['productivity_status'] == 'warning':
                alerts.append({
                    'severity': 'warning',
                    'type': 'productivity',
                    'aggregate': mill,
                    'message': f"Низкая производительность {mill}: {status['productivity']:.1f} т/ч",
                    'value': status['productivity']
                })
            
            if status['density_status'] == 'critical':
                alerts.append({
                    'severity': 'critical',
                    'type': 'density',
                    'aggregate': mill,
                    'message': f"Плотность вне допуска {mill}: {status['density']:.1f}%",
                    'value': status['density']
                })
        
        # pH алерты
        df_ph = self.get_tech_data(data_type='ph')
        if not df_ph.empty:
            last_ph = df_ph.iloc[-1]
            ph_th = self.config['thresholds']['ph']
            ph_value = float(last_ph['значение'])
            
            if ph_value < float(ph_th['critical_min']) or ph_value > float(ph_th['critical_max']):
                alerts.append({
                    'severity': 'critical',
                    'type': 'ph',
                    'aggregate': last_ph.get('агрегат', 'unknown'),
                    'message': f"Критический pH: {ph_value:.2f}",
                    'value': ph_value
                })
            elif ph_value < float(ph_th['min']) or ph_value > float(ph_th['max']):
                alerts.append({
                    'severity': 'warning',
                    'type': 'ph',
                    'aggregate': last_ph.get('агрегат', 'unknown'),
                    'message': f"pH вне нормы: {ph_value:.2f}",
                    'value': ph_value
                })
        
        # Сортируем по severity
        alerts.sort(key=lambda x: {'critical': 0, 'warning': 1}.get(x['severity'], 2))
        return alerts
    
    def get_data_with_anomalies(
        self,
        data_type: str,
        aggregate: str = None,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> pd.DataFrame:
        """Получение данных с рассчитанными аномалиями"""
        df = self.get_tech_data(data_type, aggregate, start_date, end_date)
        if df.empty or 'значение' not in df.columns:
            return df
        
        anomaly_config = self.config['anomaly_detection']
        method = anomaly_config['method']
        
        if method == 'zscore':
            params = anomaly_config['zscore']
            anomaly_df = detect_anomalies_zscore(
                df['значение'],
                window=params['window_hours'],
                warning_threshold=params['warning_threshold'],
                critical_threshold=params['critical_threshold']
            )
        else:
            params = anomaly_config['moving_average']
            anomaly_df = detect_anomalies_ma(
                df['значение'],
                window=params['window_hours'],
                warning_dev=params['warning_deviation'],
                critical_dev=params['critical_deviation']
            )
        
        # Объединяем с исходными данными
        for col in ['ma', 'mean', 'deviation', 'zscore', 'severity', 'is_anomaly']:
            if col in anomaly_df.columns:
                df[col] = anomaly_df[col].values
        
        return df


# Глобальный экземпляр (singleton)
_data_service: Optional[DataService] = None


def get_data_service(config_path: str = "config.yaml") -> DataService:
    """Получение глобального экземпляра DataService"""
    global _data_service
    if _data_service is None:
        _data_service = DataService(config_path)
    return _data_service

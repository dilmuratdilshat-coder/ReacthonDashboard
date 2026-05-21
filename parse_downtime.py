"""
Парсер данных о простоях из Excel файла.
Выводит: Data Timestamp, Shift, Category, Subcategory, Time span
"""

import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

# Настройка логирования для нераспознанных данных
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Категории
CATEGORIES = {
    'мех': 'Мех',
    'механ': 'Мех',
    'м': 'Мех',
    'элек': 'Электрик',
    'электр': 'Электрик',
    'э': 'Электрик',
    'тех': 'Тех',
    'технолог': 'Тех',
    'т': 'Тех',
    'другие': 'Другие',
    'друг': 'Другие',
    'п': 'Другие',  # погодные условия
}


def normalize_category(cat: str) -> str:
    """Нормализует категорию к стандартному виду."""
    if pd.isna(cat):
        return 'Неизвестно'
    cat_lower = str(cat).lower().strip()
    for key, value in CATEGORIES.items():
        if cat_lower.startswith(key):
            return value
    return 'Другие'


def parse_new_format(df: pd.DataFrame, sheet_name: str) -> List[Dict[str, Any]]:
    """
    Парсит новый формат (2024+) с разбивкой по сменам и агрегатам.
    Структура: Дата, Смена, [Мех, Элек, Тех, Другие, ПояснениеМех, ПояснениеЭлек, ПояснениеТех, ПояснениеДругие] * N агрегатов
    """
    results = []
    unrecognized = []

    # Определяем структуру колонок из заголовков
    header_row0 = df.iloc[0]  # Названия агрегатов
    header_row1 = df.iloc[1]  # Названия колонок (Дата, Смена, Мех, Элек, ...)

    # Находим блоки агрегатов (где начинается каждый агрегат)
    aggregates = []
    current_agg = None

    for col_idx, val in enumerate(header_row0):
        if pd.notna(val) and 'МШ' in str(val):
            current_agg = {'name': str(val).strip(), 'start_col': col_idx}
            aggregates.append(current_agg)

    if not aggregates:
        logger.warning(f"[{sheet_name}] Не найдены агрегаты МШР/МШЦ")
        return results

    # Для каждого агрегата определяем колонки данных и пояснений
    # Структура: Мех(0), Элек(1), Тех(2), Другие(3), ПояснМех(4), ПояснЭлек(5), ПояснТех(6), ПояснДругие(7)
    category_offsets = [
        (0, 'Мех', 4),      # (offset времени, категория, offset пояснения)
        (1, 'Электрик', 5),
        (2, 'Тех', 6),
        (3, 'Другие', 7),
    ]

    # Парсим данные начиная со строки 2 (индекс 2)
    current_date = None

    for row_idx in range(2, len(df)):
        row = df.iloc[row_idx]

        # Получаем дату и смену
        date_val = row.iloc[0]
        shift_val = row.iloc[1]

        # Обновляем текущую дату если она указана
        if pd.notna(date_val):
            if isinstance(date_val, datetime):
                current_date = date_val
            else:
                try:
                    current_date = pd.to_datetime(date_val)
                except:
                    logger.warning(f"[{sheet_name}] Строка {row_idx + 1}: не удалось распознать дату '{date_val}'")
                    continue

        if current_date is None:
            continue

        # Получаем смену
        shift = None
        if pd.notna(shift_val):
            try:
                shift = int(float(shift_val))
            except:
                logger.warning(f"[{sheet_name}] Строка {row_idx + 1}: не удалось распознать смену '{shift_val}'")

        # Проходим по каждому агрегату
        for agg_idx, agg in enumerate(aggregates):
            agg_start = agg['start_col']
            agg_name = agg['name']

            # Проходим по каждой категории
            for time_offset, category, desc_offset in category_offsets:
                time_col = agg_start + time_offset
                desc_col = agg_start + desc_offset

                # Проверяем границы
                if time_col >= len(row) or desc_col >= len(row):
                    continue

                time_val = row.iloc[time_col]
                desc_val = row.iloc[desc_col] if desc_col < len(row) else None

                # Если есть время простоя
                if pd.notna(time_val):
                    try:
                        time_span = float(time_val)
                        if time_span > 0:
                            subcategory = str(desc_val).strip() if pd.notna(desc_val) else ''

                            results.append({
                                'timestamp': current_date,
                                'shift': shift,
                                'category': category,
                                'subcategory': subcategory,
                                'time_span': time_span,
                                'aggregate': agg_name,
                                'source_sheet': sheet_name
                            })
                    except (ValueError, TypeError):
                        unrecognized.append({
                            'sheet': sheet_name,
                            'row': row_idx + 1,
                            'column': time_col,
                            'value': time_val,
                            'reason': 'не число'
                        })

    # Выводим нераспознанные данные
    for item in unrecognized:
        logger.warning(f"[{item['sheet']}] Строка {item['row']}, колонка {item['column']}: "
                      f"значение '{item['value']}' - {item['reason']}")

    return results


def parse_old_format(df: pd.DataFrame, sheet_name: str) -> List[Dict[str, Any]]:
    """
    Парсит старый формат (2021) без смен.
    Структура:
    - Колонки 1-6: Причины простоя (текст) по агрегатам
    - Колонки 7-12: Время простоя (минуты) по агрегатам
    - Колонки 13-18: Классификация (М/Э/Т) по агрегатам
    """
    results = []

    # Получаем заголовки
    header_row0 = df.iloc[0]
    header_row1 = df.iloc[1]  # Дата, МШР №1, МШЦ №2, ...

    # Находим границы секций
    reason_start_col = None  # Причины простоя
    time_start_col = None    # Время простоя
    class_start_col = None   # Классификация

    for col_idx, val in enumerate(header_row0):
        if pd.notna(val):
            val_str = str(val)
            if 'Причин' in val_str and reason_start_col is None:
                reason_start_col = col_idx
            elif 'Время' in val_str and time_start_col is None:
                time_start_col = col_idx
            elif 'Классиф' in val_str and class_start_col is None:
                class_start_col = col_idx

    if time_start_col is None:
        logger.warning(f"[{sheet_name}] Не найдена колонка 'Время простоя'")
        return results

    # Строим маппинг агрегатов: имя -> {reason_col, time_col, class_col}
    aggregates = {}

    # Собираем агрегаты из секции времени (7-12)
    for col_idx in range(time_start_col, len(header_row1)):
        val = header_row1.iloc[col_idx]
        if pd.notna(val) and 'МШ' in str(val):
            agg_name = str(val).strip()
            if agg_name not in aggregates:
                aggregates[agg_name] = {'name': agg_name, 'time_col': col_idx}

    # Находим соответствующие колонки причин (1-6) - порядок агрегатов такой же
    if reason_start_col is not None:
        reason_aggs = []
        for col_idx in range(reason_start_col, time_start_col if time_start_col else len(header_row1)):
            val = header_row1.iloc[col_idx]
            if pd.notna(val) and 'МШ' in str(val):
                reason_aggs.append((str(val).strip(), col_idx))

        for agg_name, col_idx in reason_aggs:
            if agg_name in aggregates:
                aggregates[agg_name]['reason_col'] = col_idx

    # Находим соответствующие колонки классификации (13-18)
    if class_start_col is not None:
        class_aggs = []
        for col_idx in range(class_start_col, len(header_row1)):
            val = header_row1.iloc[col_idx]
            if pd.notna(val) and 'МШ' in str(val):
                class_aggs.append((str(val).strip(), col_idx))

        for agg_name, col_idx in class_aggs:
            if agg_name in aggregates:
                aggregates[agg_name]['class_col'] = col_idx

    # Парсим данные
    current_date = None

    for row_idx in range(2, len(df)):
        row = df.iloc[row_idx]

        date_val = row.iloc[0]

        # Обновляем дату если указана
        if pd.notna(date_val):
            try:
                if isinstance(date_val, datetime):
                    current_date = date_val
                else:
                    current_date = pd.to_datetime(date_val)
            except:
                logger.warning(f"[{sheet_name}] Строка {row_idx + 1}: не удалось распознать дату '{date_val}'")
                continue

        if current_date is None:
            continue

        # Парсим данные по каждому агрегату
        for agg_name, agg_info in aggregates.items():
            time_col = agg_info.get('time_col')
            reason_col = agg_info.get('reason_col')
            class_col = agg_info.get('class_col')

            if time_col is None or time_col >= len(row):
                continue

            time_val = row.iloc[time_col]

            if pd.notna(time_val):
                try:
                    time_span = float(time_val)
                    if time_span > 0:
                        # Получаем категорию для этого агрегата
                        category = 'Неизвестно'
                        if class_col is not None and class_col < len(row):
                            cat_val = row.iloc[class_col]
                            category = normalize_category(cat_val)

                        # Получаем причину (subcategory) для этого агрегата
                        subcategory = ''
                        if reason_col is not None and reason_col < len(row):
                            reason_val = row.iloc[reason_col]
                            subcategory = str(reason_val).strip() if pd.notna(reason_val) else ''

                        results.append({
                            'timestamp': current_date,
                            'shift': None,  # В старом формате нет смен
                            'category': category,
                            'subcategory': subcategory,
                            'time_span': time_span,
                            'aggregate': agg_name,
                            'source_sheet': sheet_name
                        })
                except (ValueError, TypeError):
                    logger.warning(f"[{sheet_name}] Строка {row_idx + 1}: "
                                  f"время простоя '{time_val}' не является числом")

    return results


def detect_format(df: pd.DataFrame) -> str:
    """Определяет формат листа (new или old)."""
    header_row0 = df.iloc[0] if len(df) > 0 else pd.Series()
    header_row1 = df.iloc[1] if len(df) > 1 else pd.Series()

    # Новый формат имеет "Смена" во второй строке заголовка
    for val in header_row1:
        if pd.notna(val) and 'Смена' in str(val):
            return 'new'

    # Старый формат имеет "Причины простоя" в первой строке
    for val in header_row0:
        if pd.notna(val) and 'Причин' in str(val):
            return 'old'

    return 'unknown'


def parse_excel_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Парсит весь Excel файл и возвращает массив записей о простоях.
    """
    all_results = []
    xl = pd.ExcelFile(file_path)

    print(f"Найдено листов: {len(xl.sheet_names)}")
    print("-" * 60)

    for sheet_idx, sheet_name in enumerate(xl.sheet_names):
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_idx, header=None)

            if len(df) < 3:
                logger.warning(f"[{sheet_name}] Пропущен: мало строк ({len(df)})")
                continue

            format_type = detect_format(df)

            if format_type == 'new':
                results = parse_new_format(df, sheet_name)
            elif format_type == 'old':
                results = parse_old_format(df, sheet_name)
            else:
                logger.warning(f"[{sheet_name}] Неизвестный формат данных")
                # Попробуем как новый формат
                results = parse_new_format(df, sheet_name)

            if results:
                print(f"[OK] {sheet_name}: {len(results)} записей ({format_type} формат)")
                all_results.extend(results)
            else:
                print(f"[-]  {sheet_name}: 0 записей ({format_type} формат)")

        except Exception as e:
            logger.error(f"[{sheet_name}] Ошибка парсинга: {e}")

    print("-" * 60)
    print(f"Всего записей: {len(all_results)}")

    return all_results


def get_downtime_data(file_path: str = 'простои_с_начала_года_2022,2023,2024,2025г.xlsx',
                       verbose: bool = True) -> List[Dict[str, Any]]:
    """
    Основная функция для получения данных о простоях.

    Возвращает массив словарей с полями:
    - timestamp: datetime - дата простоя
    - shift: int или None - номер смены (1 или 2, None для старого формата)
    - category: str - категория (Мех, Электрик, Тех, Другие, Неизвестно)
    - subcategory: str - пояснение/причина простоя
    - time_span: float - длительность простоя в минутах
    - aggregate: str - название агрегата (МШР №1, МШЦ №2 и т.д.)
    - source_sheet: str - имя исходного листа Excel
    """
    if verbose:
        print("=" * 60)
        print("ПАРСИНГ ДАННЫХ О ПРОСТОЯХ")
        print("=" * 60)

    results = parse_excel_file(file_path)

    if verbose and results:
        # Статистика
        from collections import Counter
        category_counts = Counter(r['category'] for r in results)
        category_times = {}
        for r in results:
            cat = r['category']
            category_times[cat] = category_times.get(cat, 0) + r['time_span']

        print("\n" + "=" * 60)
        print("СТАТИСТИКА ПО КАТЕГОРИЯМ:")
        print("=" * 60)
        for cat, count in category_counts.most_common():
            total_time = category_times.get(cat, 0)
            print(f"{cat:<15}: {count:>6} записей, {total_time:>10.0f} мин ({total_time/60:.1f} часов)")

    return results


def to_dataframe(data: List[Dict[str, Any]]) -> pd.DataFrame:
    """Конвертирует результаты в pandas DataFrame."""
    df = pd.DataFrame(data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df


def save_to_csv(data: List[Dict[str, Any]],
                output_path: str = 'downtime_data.csv',
                encoding: str = 'utf-8-sig') -> str:
    """
    Сохраняет данные в CSV файл.

    Args:
        data: Список записей о простоях
        output_path: Путь к выходному файлу
        encoding: Кодировка (utf-8-sig для корректного открытия в Excel)

    Returns:
        Путь к сохранённому файлу
    """
    df = pd.DataFrame(data)
    print(df)
    df = df.dropna()
    print(df)
    # Форматируем timestamp для CSV
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
    df.to_csv(output_path, index=False, encoding=encoding)
    print(f"\nДанные сохранены в: {output_path}")
    print(f"Записей: {len(df)}")
    return output_path


def main():
    file_path = 'data/простои_с_начала_года_2022,2023,2024,2025г.xlsx'

    results = get_downtime_data(file_path, verbose=True)

    if results:
        # Показываем примеры данных
        print("\n" + "=" * 60)
        print("ПРИМЕРЫ ДАННЫХ (первые 20 записей):")
        print("=" * 60)
        print(f"{'Дата':<12} {'Смена':<6} {'Категория':<10} {'Время':<8} {'Агрегат':<10} {'Пояснение'}")
        print("-" * 80)

        for record in results[:20]:
            date_str = record['timestamp'].strftime('%Y-%m-%d') if record['timestamp'] else 'N/A'
            shift_str = str(record['shift']) if record['shift'] else '-'
            subcat = record['subcategory'][:30] + '...' if len(record['subcategory']) > 30 else record['subcategory']

            print(f"{date_str:<12} {shift_str:<6} {record['category']:<10} {record['time_span']:<8.0f} "
                  f"{record['aggregate']:<10} {subcat}")

        # Показываем записи с неизвестной категорией
        unknown = [r for r in results if r['category'] == 'Неизвестно']
        if unknown:
            print("\n" + "=" * 60)
            print(f"НЕРАСПОЗНАННЫЕ ЗАПИСИ (категория 'Неизвестно'): {len(unknown)}")
            print("=" * 60)
            for record in unknown[:15]:
                date_str = record['timestamp'].strftime('%Y-%m-%d') if record['timestamp'] else 'N/A'
                print(f"  {date_str} | {record['aggregate']:<10} | "
                      f"{record['time_span']:.0f} мин | {record['subcategory'][:40]}")
            if len(unknown) > 15:
                print(f"  ... и ещё {len(unknown) - 15} записей")

        # Сохраняем в CSV
        save_to_csv(results)

    return results


if __name__ == '__main__':
    data = main()

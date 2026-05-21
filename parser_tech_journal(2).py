"""
Парсер технического журнала мельничного производства
Извлекает данные из Excel и сохраняет в плоский CSV (long format)
Формат: дата, смена, тип_данных, значение, агрегат
"""

import pandas as pd
import numpy as np
import re
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional

# Настройка кодировки для Windows консоли
sys.stdout.reconfigure(encoding='utf-8')

# Логирование нераспознанных данных
unrecognized_log = []

def log_unrecognized(sheet_name: str, row: int, col: int, value: Any, reason: str):
    """Логирование нераспознанных данных"""
    if pd.notna(value) and str(value).strip():
        unrecognized_log.append({
            'лист': sheet_name,
            'строка': row + 1,
            'столбец': col + 1,
            'значение': str(value)[:100],
            'причина': reason
        })

def parse_sheet_name(sheet_name: str) -> Optional[Dict]:
    """Парсинг имени листа для извлечения даты и смены"""
    match = re.match(r'(\d{2})\.(\d{2})\.(\d{2})см(\d+)', sheet_name)
    if match:
        day, month, year, shift = match.groups()
        return {
            'дата': f"20{year}-{month}-{day}",
            'смена': int(shift)
        }
    return None

def safe_float(value) -> Optional[float]:
    """Безопасное преобразование в число"""
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        if np.isnan(value) if isinstance(value, float) else False:
            return None
        return float(value)
    try:
        cleaned = str(value).strip().replace(',', '.').replace(' ', '')
        if cleaned == '' or cleaned == '-':
            return None
        return float(cleaned)
    except (ValueError, TypeError):
        return None

def safe_time(value) -> Optional[str]:
    """Безопасное преобразование времени"""
    if pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.strftime('%H:%M:%S')
    s = str(value).strip()
    if s == '' or s == '-':
        return None
    return s

def add_record(records: List, дата: str, смена: int, час: Any, тип_данных: str, значение: Any, агрегат: str):
    """Добавление записи в плоский формат"""
    val = safe_float(значение)
    if val is not None:
        records.append({
            'дата': дата,
            'смена': смена,
            'час': час,
            'тип_данных': тип_данных,
            'значение': val,
            'агрегат': агрегат
        })

def add_text_record(records: List, дата: str, смена: int, час: Any, тип_данных: str, значение: str, агрегат: str):
    """Добавление текстовой записи"""
    if значение and str(значение).strip():
        records.append({
            'дата': дата,
            'смена': смена,
            'час': час,
            'тип_данных': тип_данных,
            'значение': str(значение).strip(),
            'агрегат': агрегат
        })

def parse_hourly_data(df: pd.DataFrame, sheet_info: Dict, sheet_name: str) -> List[Dict]:
    """Парсинг почасовых данных"""
    records = []
    дата = sheet_info['дата']
    смена = sheet_info['смена']

    for row_idx in range(4, 17):
        if row_idx >= len(df):
            break

        row = df.iloc[row_idx]
        hour_val = row.iloc[0] if len(row) > 0 else None

        if pd.isna(hour_val):
            continue

        hour_str = str(hour_val).strip().lower()
        if hour_str == 'среднее':
            continue

        hour = safe_float(hour_val)
        if hour is None or hour < 0 or hour > 24:
            log_unrecognized(sheet_name, row_idx, 0, hour_val, "Некорректный час")
            continue

        час = int(hour)

        # Плотность слива мельниц (колонки B-F, индексы 1-5)
        add_record(records, дата, смена, час, 'плотность', row.iloc[1] if len(row) > 1 else None, 'мельница_1')
        add_record(records, дата, смена, час, 'плотность', row.iloc[2] if len(row) > 2 else None, 'мельница_2')
        add_record(records, дата, смена, час, 'плотность', row.iloc[3] if len(row) > 3 else None, 'мельница_3')
        add_record(records, дата, смена, час, 'плотность', row.iloc[4] if len(row) > 4 else None, 'мельница_4')
        add_record(records, дата, смена, час, 'плотность', row.iloc[5] if len(row) > 5 else None, 'мельница_5')

        # Слив гидроциклона (колонки G-H, индексы 6-7)
        add_record(records, дата, смена, час, 'слив_гидроциклон', row.iloc[6] if len(row) > 6 else None, 'ГЦ_1ст')
        add_record(records, дата, смена, час, 'слив_гидроциклон', row.iloc[7] if len(row) > 7 else None, 'ГЦ_2ст')

        # Сгуститель (колонки I-J, индексы 8-9)
        add_record(records, дата, смена, час, 'сгуститель', row.iloc[8] if len(row) > 8 else None, 'сгуститель_1')
        add_record(records, дата, смена, час, 'сгуститель', row.iloc[9] if len(row) > 9 else None, 'сгуститель_2')

        # Классификатор (колонки K, L, M, индексы 10-12)
        add_record(records, дата, смена, час, 'классификатор', row.iloc[10] if len(row) > 10 else None, 'классификатор_1')
        add_record(records, дата, смена, час, 'классификатор', row.iloc[11] if len(row) > 11 else None, 'классификатор_3')
        add_record(records, дата, смена, час, 'классификатор', row.iloc[12] if len(row) > 12 else None, 'классификатор_5')

        # Ситовой анализ гидроциклона (колонки N-O, индексы 13-14)
        add_record(records, дата, смена, час, 'ситовой_анализ', row.iloc[13] if len(row) > 13 else None, 'ГЦ_1ст')
        add_record(records, дата, смена, час, 'ситовой_анализ', row.iloc[14] if len(row) > 14 else None, 'ГЦ_2ст')

        # Производительность мельниц (колонки P-T, индексы 15-19)
        add_record(records, дата, смена, час, 'производительность', row.iloc[15] if len(row) > 15 else None, 'мельница_1')
        add_record(records, дата, смена, час, 'производительность', row.iloc[16] if len(row) > 16 else None, 'мельница_2')
        add_record(records, дата, смена, час, 'производительность', row.iloc[17] if len(row) > 17 else None, 'мельница_3')
        add_record(records, дата, смена, час, 'производительность', row.iloc[18] if len(row) > 18 else None, 'мельница_4')
        add_record(records, дата, смена, час, 'производительность', row.iloc[19] if len(row) > 19 else None, 'мельница_5')

        # Суммарная производительность (колонка U, индекс 20)
        add_record(records, дата, смена, час, 'производительность', row.iloc[20] if len(row) > 20 else None, 'всего')

        # Выпуск МКР (колонка V, индекс 21)
        add_record(records, дата, смена, час, 'выпуск_мкр', row.iloc[21] if len(row) > 21 else None, 'МКР')

    return records

def parse_summary_data(df: pd.DataFrame, sheet_info: Dict, sheet_name: str) -> List[Dict]:
    """Парсинг итоговых данных за смену (средние значения)"""
    records = []
    дата = sheet_info['дата']
    смена = sheet_info['смена']

    for row_idx in range(4, 20):
        if row_idx >= len(df):
            break
        row = df.iloc[row_idx]
        if len(row) > 0 and str(row.iloc[0]).strip().lower() == 'среднее':
            add_record(records, дата, смена, 'среднее', 'плотность_ср', row.iloc[1] if len(row) > 1 else None, 'мельница_1')
            add_record(records, дата, смена, 'среднее', 'плотность_ср', row.iloc[2] if len(row) > 2 else None, 'мельница_2')
            add_record(records, дата, смена, 'среднее', 'плотность_ср', row.iloc[3] if len(row) > 3 else None, 'мельница_3')
            add_record(records, дата, смена, 'среднее', 'плотность_ср', row.iloc[4] if len(row) > 4 else None, 'мельница_4')
            add_record(records, дата, смена, 'среднее', 'плотность_ср', row.iloc[5] if len(row) > 5 else None, 'мельница_5')
            add_record(records, дата, смена, 'среднее', 'слив_гидроциклон_ср', row.iloc[6] if len(row) > 6 else None, 'ГЦ_1ст')
            add_record(records, дата, смена, 'среднее', 'слив_гидроциклон_ср', row.iloc[7] if len(row) > 7 else None, 'ГЦ_2ст')
            add_record(records, дата, смена, 'среднее', 'производительность_итого', row.iloc[20] if len(row) > 20 else None, 'всего')
            break

    return records

def parse_counters_data(df: pd.DataFrame, sheet_info: Dict, sheet_name: str) -> List[Dict]:
    """Парсинг данных счетчиков мельниц"""
    records = []
    дата = sheet_info['дата']
    смена = sheet_info['смена']

    for row_idx in range(4, 10):
        if row_idx >= len(df):
            break
        row = df.iloc[row_idx]
        mill_num = row_idx - 3
        агрегат = f'мельница_{mill_num}'

        if len(row) > 25:
            add_record(records, дата, смена, None, 'счетчик_начало', row.iloc[22], агрегат)
            add_record(records, дата, смена, None, 'счетчик_конец', row.iloc[23], агрегат)
            add_record(records, дата, смена, None, 'переработка', row.iloc[24], агрегат)

    return records

def parse_balls_loading(df: pd.DataFrame, sheet_info: Dict, sheet_name: str) -> List[Dict]:
    """Парсинг данных о загрузке шаров"""
    records = []
    дата = sheet_info['дата']
    смена = sheet_info['смена']

    for row_idx in range(19, 25):
        if row_idx >= len(df):
            break
        row = df.iloc[row_idx]

        if len(row) < 5:
            continue

        mill_cell = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
        mill_match = re.match(r'№(\d+)', mill_cell)

        if mill_match:
            mill_num = int(mill_match.group(1))
            агрегат = f'мельница_{mill_num}'

            add_record(records, дата, смена, None, 'загрузка_шаров_диаметр', row.iloc[2] if len(row) > 2 else None, агрегат)
            add_record(records, дата, смена, None, 'загрузка_шаров_вес', row.iloc[3] if len(row) > 3 else None, агрегат)

            note = str(row.iloc[5]).strip() if len(row) > 5 and pd.notna(row.iloc[5]) else None
            if note:
                add_text_record(records, дата, смена, None, 'загрузка_шаров_примечание', note, агрегат)

    return records

def parse_downtime(df: pd.DataFrame, sheet_info: Dict, sheet_name: str) -> List[Dict]:
    """Парсинг данных о простоях"""
    records = []
    дата = sheet_info['дата']
    смена = sheet_info['смена']

    for row_idx in range(25, 35):
        if row_idx >= len(df):
            break
        row = df.iloc[row_idx]

        if len(row) < 1:
            continue

        first_cell = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
        mill_match = re.match(r'№(\d+)', first_cell)

        if mill_match:
            mill_num = int(mill_match.group(1))
            агрегат = f'мельница_{mill_num}'

            start_time = safe_time(row.iloc[2]) if len(row) > 2 else None
            end_time = safe_time(row.iloc[3]) if len(row) > 3 else None
            duration = str(row.iloc[5]).strip() if len(row) > 5 and pd.notna(row.iloc[5]) else None
            reason = str(row.iloc[7]).strip() if len(row) > 7 and pd.notna(row.iloc[7]) else None

            if start_time:
                add_text_record(records, дата, смена, None, 'простой_начало', start_time, агрегат)
            if end_time:
                add_text_record(records, дата, смена, None, 'простой_конец', end_time, агрегат)
            if duration:
                add_text_record(records, дата, смена, None, 'простой_длительность', duration, агрегат)
            if reason:
                add_text_record(records, дата, смена, None, 'простой_причина', reason, агрегат)

    return records

def parse_moisture_data(df: pd.DataFrame, sheet_info: Dict, sheet_name: str) -> List[Dict]:
    """Парсинг данных о влаге руды"""
    records = []
    дата = sheet_info['дата']
    смена = sheet_info['смена']

    # Влага руды находится в строке 19 (индекс 18)
    # Колонка 12: заголовок "Влага руды, %"
    # Колонки 15-19: значения для мельниц 1-5
    # Колонка 20: среднее значение

    row_idx = 18
    if row_idx >= len(df):
        return records

    row = df.iloc[row_idx]

    # Проверяем, что это строка с влагой руды
    if len(row) > 12:
        header = str(row.iloc[12]).strip().lower() if pd.notna(row.iloc[12]) else ''
        if 'влага' in header:
            # Влага для мельниц 1-5
            add_record(records, дата, смена, None, 'влага_руды', row.iloc[15] if len(row) > 15 else None, 'мельница_1')
            add_record(records, дата, смена, None, 'влага_руды', row.iloc[16] if len(row) > 16 else None, 'мельница_2')
            add_record(records, дата, смена, None, 'влага_руды', row.iloc[17] if len(row) > 17 else None, 'мельница_3')
            add_record(records, дата, смена, None, 'влага_руды', row.iloc[18] if len(row) > 18 else None, 'мельница_4')
            add_record(records, дата, смена, None, 'влага_руды', row.iloc[19] if len(row) > 19 else None, 'мельница_5')
            # Среднее значение
            add_record(records, дата, смена, None, 'влага_руды_ср', row.iloc[20] if len(row) > 20 else None, 'всего')

    return records

def parse_mkr_data(df: pd.DataFrame, sheet_info: Dict, sheet_name: str) -> List[Dict]:
    """Парсинг данных по МКР"""
    records = []
    дата = sheet_info['дата']
    смена = sheet_info['смена']

    for row_idx in range(38, 46):
        if row_idx >= len(df):
            break
        row = df.iloc[row_idx]

        if len(row) < 4:
            continue

        first_cell = str(row.iloc[0]).strip().lower() if pd.notna(row.iloc[0]) else ''

        if 'остаток мкр на начало' in first_cell:
            add_record(records, дата, смена, None, 'мкр_остаток_начало', row.iloc[3], 'МКР')
        elif 'выпуск мкр за смену' in first_cell:
            add_record(records, дата, смена, None, 'мкр_выпуск', row.iloc[3], 'МКР')
        elif 'отгружено мкр' in first_cell:
            add_record(records, дата, смена, None, 'мкр_отгружено', row.iloc[3], 'МКР')
        elif 'остаток мкр на конец' in first_cell:
            add_record(records, дата, смена, None, 'мкр_остаток_конец', row.iloc[3], 'МКР')

    return records

def parse_ph_data(df: pd.DataFrame, sheet_info: Dict, sheet_name: str) -> List[Dict]:
    """Парсинг данных pH"""
    records = []
    дата = sheet_info['дата']
    смена = sheet_info['смена']

    for row_idx in range(40, 45):
        if row_idx >= len(df):
            break
        row = df.iloc[row_idx]

        if len(row) < 10:
            continue

        first_cell = str(row.iloc[7]).strip().lower() if len(row) > 7 and pd.notna(row.iloc[7]) else ''

        if 'рн слива' in first_cell or 'ph слива' in first_cell:
            times = ['21:00', '23:00', '01:00', '03:00', '05:00', '07:00']
            for i, time in enumerate(times):
                ph_val = safe_float(row.iloc[9 + i]) if len(row) > 9 + i else None
                if ph_val is not None:
                    records.append({
                        'дата': дата,
                        'смена': смена,
                        'час': time,
                        'тип_данных': 'ph',
                        'значение': ph_val,
                        'агрегат': 'ГЦ_1'
                    })

            avg_ph = safe_float(row.iloc[16]) if len(row) > 16 else None
            if avg_ph is not None:
                records.append({
                    'дата': дата,
                    'смена': смена,
                    'час': 'среднее',
                    'тип_данных': 'ph_ср',
                    'значение': avg_ph,
                    'агрегат': 'ГЦ_1'
                })
            break

    return records

def parse_excel_file(file_path: str) -> pd.DataFrame:
    """Основная функция парсинга Excel файла"""
    print(f"Открываю файл: {file_path}")

    xlsx = pd.ExcelFile(file_path)
    print(f"Найдено листов: {len(xlsx.sheet_names)}")

    all_records = []
    processed_sheets = 0
    skipped_sheets = []

    for sheet_name in xlsx.sheet_names:
        sheet_info = parse_sheet_name(sheet_name)

        if sheet_info is None:
            skipped_sheets.append(sheet_name)
            log_unrecognized(sheet_name, 0, 0, sheet_name, "Не удалось распознать формат имени листа")
            continue

        print(f"  Обрабатываю: {sheet_name} ({sheet_info['дата']}, смена {sheet_info['смена']})")

        df = pd.read_excel(xlsx, sheet_name=sheet_name, header=None)

        # Собираем все данные
        all_records.extend(parse_hourly_data(df, sheet_info, sheet_name))
        all_records.extend(parse_summary_data(df, sheet_info, sheet_name))
        all_records.extend(parse_counters_data(df, sheet_info, sheet_name))
        all_records.extend(parse_balls_loading(df, sheet_info, sheet_name))
        all_records.extend(parse_downtime(df, sheet_info, sheet_name))
        all_records.extend(parse_moisture_data(df, sheet_info, sheet_name))
        all_records.extend(parse_mkr_data(df, sheet_info, sheet_name))
        all_records.extend(parse_ph_data(df, sheet_info, sheet_name))

        processed_sheets += 1

    print(f"\nОбработано листов: {processed_sheets}")
    if skipped_sheets:
        print(f"Пропущено листов: {len(skipped_sheets)} ({', '.join(skipped_sheets)})")

    print(f"Извлечено записей: {len(all_records)}")

    return pd.DataFrame(all_records)

def print_unrecognized_log():
    """Вывод лога нераспознанных данных"""
    if unrecognized_log:
        print("\n" + "="*60)
        print("НЕРАСПОЗНАННЫЕ ДАННЫЕ:")
        print("="*60)
        for entry in unrecognized_log[:50]:
            print(f"  Лист: {entry['лист']}, Строка: {entry['строка']}, Столбец: {entry['столбец']}")
            print(f"    Значение: {entry['значение']}")
            print(f"    Причина: {entry['причина']}")
        if len(unrecognized_log) > 50:
            print(f"\n  ... и ещё {len(unrecognized_log) - 50} записей")
        print(f"\nВсего нераспознанных записей: {len(unrecognized_log)}")
    else:
        print("\nВсе данные успешно распознаны!")

def main():
    input_file = r'data\Тех журнал 2026г.xlsx'
    output_file = r'output\tech_journal2.csv'

    print("="*60)
    print("ПАРСЕР ТЕХНИЧЕСКОГО ЖУРНАЛА")
    print("="*60)

    # Парсим данные
    df = parse_excel_file(input_file)

    df = df.dropna(subset='час')

    # Сохраняем в CSV
    if not df.empty:
        # Упорядочиваем колонки
        df = df[['дата', 'смена', 'час', 'тип_данных', 'значение', 'агрегат']]
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\nДанные сохранены: {output_file}")
        print(f"  Записей: {len(df)}")
        print(f"  Колонки: {', '.join(df.columns)}")

        # Статистика по типам данных
        print(f"\nСтатистика по типам данных:")
        for тип, count in df['тип_данных'].value_counts().items():
            print(f"  {тип}: {count}")

    # Выводим лог нераспознанных данных
    print_unrecognized_log()

    print("\n" + "="*60)
    print("ГОТОВО!")
    print("="*60)

if __name__ == '__main__':
    main()

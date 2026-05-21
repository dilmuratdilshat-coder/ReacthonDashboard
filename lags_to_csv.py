import pandas as pd
import openpyxl
from datetime import datetime
import logging
import os
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Classification mapping
CLASSIFICATION_MAP = {
    'Мех': 'М',
    'Элек': 'Э',
    'Тех': 'Т',
    'Другие': 'П'
}

def clean_text(text):
    """Clean and strip whitespace from text fields"""
    if pd.isna(text) or text is None:
        return ""
    return str(text).strip()

def parse_date(date_val):
    """Parse date values from Excel"""
    if pd.isna(date_val):
        return None
    
    if isinstance(date_val, datetime):
        return date_val.strftime('%Y-%m-%d')
    
    if isinstance(date_val, str):
        # Try to parse string dates
        try:
            parsed = pd.to_datetime(date_val)
            return parsed.strftime('%Y-%m-%d')
        except:
            return None
    
    return None

def parse_minutes(minutes_val):
    """Parse minutes, handling formulas and errors"""
    if pd.isna(minutes_val):
        return 0.0
    
    if isinstance(minutes_val, str):
        if '#REF!' in minutes_val or '#' in minutes_val:
            return 0.0
        try:
            return float(minutes_val)
        except:
            return 0.0
    
    try:
        return float(minutes_val)
    except:
        return 0.0

def map_classification(original):
    """Map original classification to abbreviated form"""
    if pd.isna(original):
        return ""
    
    original_clean = clean_text(original)
    return CLASSIFICATION_MAP.get(original_clean, original_clean)

def process_sheet(df, sheet_name):
    """Process a single Excel sheet and extract downtime events"""
    events = []
    
    # Expected column patterns (adjust based on your actual Excel structure)
    # This is a flexible approach - modify column names as needed
    
    for idx, row in df.iterrows():
        try:
            # Skip header rows or empty rows
            if pd.isna(row.get('Дата')) and pd.isna(row.get(0)):
                continue
            
            # Extract data from row
            # Adjust column indices/names based on your Excel structure
            date = parse_date(row.get('Дата', row.get(0)))
            if not date:
                continue
            
            # Try to find shift column
            shift = None
            for col in ['Смена', 'См', 1]:
                if col in row.index:
                    shift_val = row[col]
                    if not pd.isna(shift_val):
                        try:
                            shift = float(shift_val)
                            break
                        except:
                            pass
            
            # Try to find equipment column
            equipment = ""
            for col in ['Оборудование', 'Обор', 2]:
                if col in row.index:
                    equipment = clean_text(row[col])
                    if equipment:
                        break
            
            # Try to find cause column
            cause = ""
            for col in ['Причины простоя', 'Причина', 'Причины', 3]:
                if col in row.index:
                    cause = clean_text(row[col])
                    if cause:
                        break
            
            # Try to find minutes column
            minutes = 0.0
            for col in ['Минуты', 'Мин', 'Время', 4]:
                if col in row.index:
                    minutes = parse_minutes(row[col])
                    if minutes > 0:
                        break
            
            # Try to find classification column
            classification = ""
            for col in ['Классификация', 'Тип', 5]:
                if col in row.index:
                    classification = map_classification(row[col])
                    if classification:
                        break
            
            # Try to find notes column
            notes = ""
            for col in ['Примечание', 'Пояснение', 'Заметки', 6, 7]:
                if col in row.index:
                    notes = clean_text(row[col])
                    if notes:
                        break
            
            # Only add event if we have minimum required data
            if date and equipment:
                event = {
                    'date': date,
                    'shift': shift if shift else 0.0,
                    'equipment': equipment,
                    'cause': cause if cause else notes,
                    'downtime_minutes': minutes,
                    'classification': classification,
                    'sheet_name': sheet_name,
                    'notes': notes
                }
                events.append(event)
        
        except Exception as e:
            logger.warning(f"Error processing row {idx} in sheet '{sheet_name}': {e}")
            continue
    
    return events

def convert_excel_to_csv(excel_file, output_csv='downtime_events.csv'):
    """Main function to convert Excel to CSV"""
    
    if not os.path.exists(excel_file):
        logger.error(f"File not found: {excel_file}")
        return
    
    logger.info(f"Reading Excel file: {excel_file}")
    
    try:
        # Load Excel file
        xl_file = pd.ExcelFile(excel_file, engine='openpyxl')
        sheet_names = xl_file.sheet_names
        
        logger.info(f"Found {len(sheet_names)} sheets")
        
        all_events = []
        
        # Process each sheet
        for sheet_name in sheet_names:
            logger.info(f"Processing sheet: {sheet_name}")
            
            try:
                df = pd.read_excel(xl_file, sheet_name=sheet_name)
                events = process_sheet(df, sheet_name)
                
                logger.info(f"  Found {len(events)} events in '{sheet_name}'")
                all_events.extend(events)
                
            except Exception as e:
                logger.error(f"Error processing sheet '{sheet_name}': {e}")
                continue
        
        # Create DataFrame from all events
        if all_events:
            result_df = pd.DataFrame(all_events)
            
            # Reorder columns
            column_order = [
                'date', 'shift', 'equipment', 'cause', 
                'downtime_minutes', 'classification', 'sheet_name', 'notes'
            ]
            result_df = result_df[column_order]
            
            # Save to CSV
            result_df.to_csv(output_csv, index=False, encoding='utf-8')
            logger.info(f"Successfully saved {len(all_events)} events to '{output_csv}'")
            
            # Display sample
            logger.info("\nSample output (first 5 rows):")
            print(result_df.head().to_string())
            
        else:
            logger.warning("No events found in the Excel file")
    
    except Exception as e:
        logger.error(f"Error processing Excel file: {e}")
        raise

if __name__ == "main":
    # File configuration
    excel_filename = 'data/простои_с_начала_года_2022,2023,2024,2025г.xlsx'
    output_filename = 'output/downtime_events.csv'
    
    # Run conversion
    convert_excel_to_csv(excel_filename, output_filename)
    
    logger.info("\nConversion complete!")
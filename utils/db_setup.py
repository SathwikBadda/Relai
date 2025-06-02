# Fixed utils/db_setup.py
import os
import sqlite3
import pandas as pd
from typing import Optional

def create_db_schema(db_path: str = 'data/properties.db'):
    """
    Create the SQLite database schema for properties
    
    Args:
        db_path: Path to the SQLite database file
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Connect to the database (will create it if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create properties table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS properties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_name TEXT NOT NULL,
        property_type TEXT NOT NULL,
        area TEXT NOT NULL,
        possession_date TEXT NOT NULL,
        total_units INTEGER,
        area_size_acres REAL,
        min_size_sqft INTEGER NOT NULL,
        max_size_sqft INTEGER NOT NULL,
        price_per_sqft INTEGER NOT NULL
    )
    ''')
    
    # Create configurations table (many-to-many relationship)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS configurations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    ''')
    
    # Create property-configuration relationship table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS property_configurations (
        property_id INTEGER,
        configuration_id INTEGER,
        PRIMARY KEY (property_id, configuration_id),
        FOREIGN KEY (property_id) REFERENCES properties (id),
        FOREIGN KEY (configuration_id) REFERENCES configurations (id)
    )
    ''')
    
    # Create user_preferences table to store user preferences
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_preferences (
        session_id TEXT PRIMARY KEY,
        area TEXT,
        property_type TEXT,
        min_budget REAL,
        max_budget REAL,
        configuration TEXT,
        possession_date TEXT,
        min_size REAL,
        max_size REAL,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Commit and close
    conn.commit()
    conn.close()
    
    print(f"Database schema created at {db_path}")

def import_csv_to_db(csv_path: str, db_path: str = 'data/properties.db'):
    """
    Import property data from CSV to SQLite database with encoding detection
    
    Args:
        csv_path: Path to the CSV file
        db_path: Path to the SQLite database file
    """
    # Check if CSV exists
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    # Create schema if needed
    create_db_schema(db_path)
    
    # Load CSV data with encoding detection
    try:
        # First try with UTF-8
        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
            print(f"Successfully loaded CSV with UTF-8 encoding")
        except UnicodeDecodeError:
            # If UTF-8 fails, try other common encodings
            encodings = ['latin-1', 'iso-8859-1', 'cp1252', 'utf-8-sig']
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(csv_path, encoding=encoding)
                    print(f"Successfully loaded CSV with {encoding} encoding")
                    break
                except UnicodeDecodeError:
                    continue
            else:
                # If all encodings fail, try with error handling
                df = pd.read_csv(csv_path, encoding='utf-8', errors='ignore')
                print(f"Successfully loaded CSV with UTF-8 encoding (ignoring errors)")
    except Exception as e:
        raise Exception(f"Error loading CSV file: {str(e)}")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute('DELETE FROM property_configurations')
    cursor.execute('DELETE FROM configurations')
    cursor.execute('DELETE FROM properties')
    
    # Process each row in the dataframe
    for _, row in df.iterrows():
        try:
            # Extract configurations and split into list, handle missing data
            configurations_str = row.get('Configurations', '')
            if pd.isna(configurations_str) or configurations_str == '':
                configurations = []
            else:
                configurations = [config.strip() for config in str(configurations_str).split(', ') if config.strip()]
            
            # Handle missing or invalid data
            def safe_get(key, default=None):
                value = row.get(key, default)
                if pd.isna(value):
                    return default
                return value
            
            # Insert property with safe data extraction
            cursor.execute('''
            INSERT INTO properties (
                project_name, property_type, area, possession_date, 
                total_units, area_size_acres, min_size_sqft, 
                max_size_sqft, price_per_sqft
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                safe_get('ProjectName', 'Unknown Project'),
                safe_get('PropertyType', 'Unknown Type'),
                safe_get('Area', 'Unknown Area'),
                safe_get('PossessionDate', 'Unknown Date'),
                safe_get('TotalUnits', 0),
                safe_get('AreaSizeAcres', 0.0),
                safe_get('MinSizeSqft', 0),
                safe_get('MaxSizeSqft', 0),
                safe_get('PricePerSqft', 0)
            ))
            
            # Get the property ID
            property_id = cursor.lastrowid
            
            # Process configurations
            for config in configurations:
                if config:  # Only process non-empty configurations
                    # Insert configuration if it doesn't exist
                    cursor.execute('INSERT OR IGNORE INTO configurations (name) VALUES (?)', (config,))
                    
                    # Get configuration ID
                    cursor.execute('SELECT id FROM configurations WHERE name = ?', (config,))
                    config_row = cursor.fetchone()
                    if config_row:
                        config_id = config_row[0]
                        
                        # Create relationship
                        cursor.execute('''
                        INSERT INTO property_configurations (property_id, configuration_id)
                        VALUES (?, ?)
                        ''', (property_id, config_id))
        
        except Exception as e:
            print(f"Error processing row {_}: {e}")
            # Continue with next row instead of failing completely
            continue
    
    # Commit and close
    conn.commit()
    conn.close()
    
    print(f"Successfully imported {len(df)} properties from {csv_path} to {db_path}")

def get_connection(db_path: str = 'data/properties.db') -> sqlite3.Connection:
    """
    Get a connection to the SQLite database
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        sqlite3.Connection: A connection to the database
    """
    # Ensure the database exists
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}. Please run import_csv_to_db first.")
    
    # Connect with row factory to get dictionary-like results
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    return conn

def store_user_preferences(
    session_id: str,
    area: Optional[str] = None,
    property_type: Optional[str] = None,
    min_budget: Optional[float] = None,
    max_budget: Optional[float] = None,
    configuration: Optional[str] = None,
    possession_date: Optional[str] = None,
    min_size: Optional[float] = None,
    max_size: Optional[float] = None,
    db_path: str = 'data/properties.db'
):
    """
    Store or update user preferences in the database
    
    Args:
        session_id: Unique identifier for the user session
        area: Preferred area/location
        property_type: Type of property (e.g., Apartment, Villa)
        min_budget: Minimum budget in rupees
        max_budget: Maximum budget in rupees
        configuration: BHK configuration
        possession_date: Possession date preference
        min_size: Minimum property size in sqft
        max_size: Maximum property size in sqft
        db_path: Path to the SQLite database file
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # Check if preferences already exist for this session
    cursor.execute('SELECT * FROM user_preferences WHERE session_id = ?', (session_id,))
    existing = cursor.fetchone()
    
    if existing:
        # Update existing preferences
        cursor.execute('''
        UPDATE user_preferences
        SET area = COALESCE(?, area),
            property_type = COALESCE(?, property_type),
            min_budget = COALESCE(?, min_budget),
            max_budget = COALESCE(?, max_budget),
            configuration = COALESCE(?, configuration),
            possession_date = COALESCE(?, possession_date),
            min_size = COALESCE(?, min_size),
            max_size = COALESCE(?, max_size),
            last_updated = CURRENT_TIMESTAMP
        WHERE session_id = ?
        ''', (
            area, property_type, min_budget, max_budget,
            configuration, possession_date, min_size, max_size,
            session_id
        ))
    else:
        # Insert new preferences
        cursor.execute('''
        INSERT INTO user_preferences (
            session_id, area, property_type, min_budget, max_budget,
            configuration, possession_date, min_size, max_size
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id, area, property_type, min_budget, max_budget,
            configuration, possession_date, min_size, max_size
        ))
    
    conn.commit()
    conn.close()

def get_user_preferences(session_id: str, db_path: str = 'data/properties.db'):
    """
    Get user preferences from the database
    
    Args:
        session_id: Unique identifier for the user session
        db_path: Path to the SQLite database file
        
    Returns:
        dict: Dictionary containing user preferences
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM user_preferences WHERE session_id = ?', (session_id,))
    row = cursor.fetchone()
    
    conn.close()
    
    if row:
        return dict(row)
    else:
        return None

# Run this script directly to create the database schema
if __name__ == "__main__":
    # Path to your existing CSV file
    csv_path = "data/properties.csv"
    
    # Path to new SQLite database
    db_path = "data/properties.db"
    
    # Import data if CSV exists
    if os.path.exists(csv_path):
        import_csv_to_db(csv_path, db_path)
    else:
        # Just create the schema
        create_db_schema(db_path)
        print(f"Warning: CSV file not found at {csv_path}. Created empty database schema.")
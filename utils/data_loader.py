# Update utils/data_loader.py - Fixed to handle encoding issues
import pandas as pd
import os
import sqlite3
import numpy as np
from typing import Union, Optional

def load_property_data(data_path: str) -> pd.DataFrame:
    """
    Load property data from CSV file with encoding detection
    
    Args:
        data_path: Path to the CSV file
        
    Returns:
        pd.DataFrame: DataFrame containing property data
    """
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Property data file not found: {data_path}")
    
    try:
        # First try with UTF-8
        try:
            df = pd.read_csv(data_path, encoding='utf-8')
            print(f"Successfully loaded {len(df)} properties from CSV with UTF-8 encoding")
            return df
        except UnicodeDecodeError:
            # If UTF-8 fails, try other common encodings
            encodings = ['latin-1', 'iso-8859-1', 'cp1252', 'utf-8-sig']
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(data_path, encoding=encoding)
                    print(f"Successfully loaded {len(df)} properties from CSV with {encoding} encoding")
                    return df
                except UnicodeDecodeError:
                    continue
            
            # If all encodings fail, try with error handling
            df = pd.read_csv(data_path, encoding='utf-8', errors='ignore')
            print(f"Successfully loaded {len(df)} properties from CSV with UTF-8 encoding (ignoring errors)")
            return df
            
    except Exception as e:
        raise Exception(f"Error loading property data: {str(e)}")

def get_db_connection(db_path: str = 'data/properties.db') -> sqlite3.Connection:
    """
    Get a connection to the SQLite database
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        sqlite3.Connection: A connection to the database
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")
    
    try:
        # Connect with row factory to get dictionary-like results
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        raise Exception(f"Error connecting to database: {str(e)}")

def load_properties_from_db(db_path: str = 'data/properties.db') -> pd.DataFrame:
    """
    Load property data from SQLite database into a pandas DataFrame
    (This is for compatibility with existing code that expects a DataFrame)
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        pd.DataFrame: DataFrame containing property data
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Fetch properties with their configurations
        query = """
        SELECT 
            p.id, p.project_name as ProjectName, p.property_type as PropertyType, 
            p.area as Area, p.possession_date as PossessionDate, 
            p.total_units as TotalUnits, p.area_size_acres as AreaSizeAcres,
            p.min_size_sqft as MinSizeSqft, p.max_size_sqft as MaxSizeSqft, 
            p.price_per_sqft as PricePerSqft,
            GROUP_CONCAT(c.name, ', ') as Configurations
        FROM properties p
        LEFT JOIN property_configurations pc ON p.id = pc.property_id
        LEFT JOIN configurations c ON pc.configuration_id = c.id
        GROUP BY p.id
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        print(f"Successfully loaded {len(df)} properties from SQLite database")
        return df
    except Exception as e:
        raise Exception(f"Error loading property data from database: {str(e)}")

def detect_data_source(data_path: str) -> str:
    """
    Detect the type of data source based on the file extension
    
    Args:
        data_path: Path to the data file
        
    Returns:
        str: 'csv' or 'sqlite'
    """
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Data file not found: {data_path}")
    
    _, ext = os.path.splitext(data_path)
    
    if ext.lower() == '.csv':
        return 'csv'
    elif ext.lower() in ['.db', '.sqlite', '.sqlite3']:
        return 'sqlite'
    else:
        raise ValueError(f"Unsupported data file format: {ext}")

def load_data(data_path: str) -> Union[pd.DataFrame, str]:
    """
    Smart data loader that can handle both CSV and SQLite
    
    Args:
        data_path: Path to the data file
        
    Returns:
        Union[pd.DataFrame, str]: DataFrame or path to SQLite database
    """
    try:
        data_type = detect_data_source(data_path)
        
        if data_type == 'csv':
            return load_property_data(data_path)
        elif data_type == 'sqlite':
            # For SQLite, we'll return the path so we can use the SQL-based tools
            print(f"Using SQLite database: {data_path}")
            return data_path
        else:
            raise ValueError(f"Unsupported data type: {data_type}")
    except Exception as e:
        raise Exception(f"Error loading data: {str(e)}")

def sample_dataset(n_samples=5):
    """
    Generate a sample property dataset for testing purposes
    
    Args:
        n_samples: Number of samples to generate
        
    Returns:
        pd.DataFrame: DataFrame containing sample property data
    """
    areas = ['Gachibowli', 'Hitech City', 'Kondapur', 'Miyapur', 'Bachupally', 'Kukatpally', 'Manikonda']
    property_types = ['Apartment', 'Villa', 'Duplex', 'Independent House', 'Plot']
    configurations = ['1BHK', '2BHK', '3BHK', '4BHK', '5BHK']
    
    # Generate random data
    data = {
        'ProjectName': [f"Project {i+1}" for i in range(n_samples)],
        'PropertyType': np.random.choice(property_types, n_samples),
        'Area': np.random.choice(areas, n_samples),
        'PossessionDate': [f"{np.random.randint(1, 13)}/1/{np.random.randint(2023, 2027)}" for _ in range(n_samples)],
        'TotalUnits': np.random.randint(50, 500, n_samples),
        'AreaSizeAcres': np.random.uniform(5, 25, n_samples).round(1),
        'Configurations': [', '.join(np.random.choice(configurations, np.random.randint(1, 4), replace=False)) for _ in range(n_samples)],
        'MinSizeSqft': np.random.randint(800, 1500, n_samples),
        'MaxSizeSqft': np.random.randint(1500, 3000, n_samples),
        'PricePerSqft': np.random.randint(4000, 8000, n_samples)
    }
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Ensure min_size < max_size
    for i in range(n_samples):
        if df.at[i, 'MinSizeSqft'] >= df.at[i, 'MaxSizeSqft']:
            df.at[i, 'MaxSizeSqft'] = df.at[i, 'MinSizeSqft'] + np.random.randint(300, 1000)
    
    return df
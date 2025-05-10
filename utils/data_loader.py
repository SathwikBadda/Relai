# utils/data_loader.py - Data loading and preprocessing functions

import pandas as pd
import os

def load_property_data(csv_path: str) -> pd.DataFrame:
    """
    Load the property dataset from CSV file and perform necessary preprocessing
    
    Args:
        csv_path: Path to the CSV file containing property data
        
    Returns:
        DataFrame: Processed property data
    """
    # Check if file exists
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Property data file not found at: {csv_path}")
    
    # Load the CSV file
    df = pd.read_csv(csv_path)
    
    # Clean column names (in case they have spaces)
    df.columns = df.columns.str.strip()
    
    # Ensure required columns exist
    required_columns = [
        'ProjectName', 'PropertyType', 'Area', 'PossessionDate', 
        'TotalUnits', 'AreaSizeAcres', 'Configurations', 
        'MinSizeSqft', 'MaxSizeSqft', 'PricePerSqft'
    ]
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns in the dataset: {missing_columns}")
    
    # Convert columns to appropriate data types
    # Numeric columns
    numeric_columns = ['TotalUnits', 'AreaSizeAcres', 'MinSizeSqft', 'MaxSizeSqft', 'PricePersqft']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Fill missing values
    # For numeric columns, fill with mean or 0
    for col in numeric_columns:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].mean() if df[col].count() > 0 else 0)
    
    # For string columns, fill with 'N/A'
    string_columns = ['ProjectName', 'PropertyType', 'Area', 'PossessionDate', 'Configurations']
    for col in string_columns:
        if col in df.columns:
            df[col] = df[col].fillna('N/A')
    
    # Additional preprocessing steps if needed
    # Convert possession date to proper format if needed
    # df['PossessionDate'] = pd.to_datetime(df['PossessionDate'], errors='coerce')
    
    # Handle any other preprocessing steps specific to your data
    
    print(f"Successfully loaded property data with {len(df)} records")
    return df

def sample_dataset(df: pd.DataFrame, n: int = 5) -> None:
    """
    Print a sample of the dataset for inspection
    
    Args:
        df: DataFrame to sample
        n: Number of records to sample
    """
    print(f"\nSample of {n} records from the dataset:")
    print("-" * 80)
    print(df.sample(n))
    print("-" * 80)
    
    # Print column statistics
    print("\nDataset Statistics:")
    print(f"Number of properties: {len(df)}")
    print(f"Number of unique areas: {df['Area'].nunique()}")
    print(f"Property types: {', '.join(df['PropertyType'].unique())}")
    print(f"Price range: ₹{df['PricePersqft'].min():,} - ₹{df['PricePersqft'].max():,} per sq.ft")

# Test the loader
if __name__ == "__main__":
    from config import DATA_PATH
    
    try:
        df = load_property_data(DATA_PATH)
        sample_dataset(df)
    except Exception as e:
        print(f"Error loading data: {e}")
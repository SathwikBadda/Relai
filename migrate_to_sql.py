# Create migrate_to_sql.py
import os
import sys
import argparse

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from utils.db_setup import create_db_schema, import_csv_to_db
from config import DATA_PATH

def main():
    """
    Main function to migrate property data from CSV to SQLite database
    """
    parser = argparse.ArgumentParser(description='Migrate property data from CSV to SQLite database')
    parser.add_argument('--csv', type=str, default=DATA_PATH, 
                        help='Path to the CSV file (default: from config.py)')
    parser.add_argument('--db', type=str, default='data/properties.db', 
                        help='Path to the SQLite database (default: data/properties.db)')
    parser.add_argument('--schema-only', action='store_true',
                        help='Create only the database schema without importing data')
    
    args = parser.parse_args()
    
    # Create directory for database if it doesn't exist
    os.makedirs(os.path.dirname(args.db), exist_ok=True)
    
    if args.schema_only:
        # Create only the schema
        print(f"Creating database schema at {args.db}...")
        create_db_schema(args.db)
        print("Schema created successfully!")
    else:
        # Create schema and import data
        if not os.path.exists(args.csv):
            print(f"Error: CSV file not found at {args.csv}")
            return 1
        
        print(f"Migrating data from {args.csv} to {args.db}...")
        import_csv_to_db(args.csv, args.db)
        print("Migration completed successfully!")
    
    print("\nNext steps:")
    print("1. Update the DATA_PATH in config.py to point to your new database:")
    print(f"   DATA_PATH = \"{args.db}\"")
    print("2. Run the app.py to use the SQL-based database")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
# Fixed utils/property_tools_sql.py - Complete merged version
import sqlite3
from typing import List, Dict, Any, Tuple, Optional
import os
import re
from datetime import datetime

class PropertyRecommendationToolsSQL:
    """Tools for recommending properties using a SQL database instead of pandas"""
    
    def __init__(self, db_path: str = 'data/properties.db'):
        """
        Initialize with the path to the SQLite database
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        
        # Verify database exists
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database not found: {db_path}")

    def get_connection(self):
        """
        Get a connection to the SQLite database
        
        Returns:
            sqlite3.Connection: A connection to the database
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            raise Exception(f"Error connecting to database: {str(e)}")

    def search_properties(
        self,
        area: Optional[str] = None,
        property_type: Optional[str] = None,
        min_budget: Optional[float] = None,
        max_budget: Optional[float] = None,
        configurations: Optional[str] = None,
        possession_date: Optional[str] = None,
        min_size: Optional[float] = None,
        max_size: Optional[float] = None,
        session_id: Optional[str] = None,
        limit: int = 10
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], bool]:
        """
        Search for properties based on user preferences
        
        Args:
            area: Location/area in Hyderabad
            property_type: Type of property (e.g., Apartment, Villa)
            min_budget: Minimum budget in rupees
            max_budget: Maximum budget in rupees
            configurations: BHK configuration (e.g., '2BHK', '3BHK')
            possession_date: When the property will be available
            min_size: Minimum property size in sqft
            max_size: Maximum property size in sqft
            session_id: Session ID to store preferences
            limit: Maximum number of properties to return
            
        Returns:
            Tuple containing:
            - List of matching properties
            - Feedback dictionary
            - Boolean indicating if exact match
        """
        # Store user preferences if session_id is provided
        if session_id:
            try:
                from utils.db_setup import store_user_preferences
                store_user_preferences(
                    session_id=session_id,
                    area=area,
                    property_type=property_type,
                    min_budget=min_budget,
                    max_budget=max_budget,
                    configuration=configurations,
                    possession_date=possession_date,
                    min_size=min_size,
                    max_size=max_size,
                    db_path=self.db_path
                )
            except Exception as e:
                print(f"Error storing preferences: {e}")
        
        # Handle single budget value - if only max_budget is provided, set min_budget to 0
        if max_budget and not min_budget:
            min_budget = 0
            print(f"Only max budget provided: filtering properties below ₹{max_budget:,.0f}")
        
        # If only area is specified, increase the limit to show more properties
        if area and not (property_type or min_budget or max_budget or configurations or 
                         possession_date or min_size or max_size):
            limit = max(limit, 15)  # Show at least 15 properties for area-only queries
        
        try:
            # Connect to database
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Build query
            query = """
            SELECT DISTINCT 
                p.id, p.project_name, p.property_type, p.area, p.possession_date,
                p.min_size_sqft, p.max_size_sqft, p.price_per_sqft,
                (p.min_size_sqft * p.price_per_sqft) as min_total_price,
                (p.max_size_sqft * p.price_per_sqft) as max_total_price,
                GROUP_CONCAT(c.name, ', ') as configurations
            FROM properties p
            LEFT JOIN property_configurations pc ON p.id = pc.property_id
            LEFT JOIN configurations c ON pc.configuration_id = c.id
            WHERE 1=1
            """
            
            params = []
            exact_match_conditions = []
            
            # Add conditions based on preferences
            if area:
                query += " AND p.area = ?"
                params.append(area)
                exact_match_conditions.append("area")
            
            if property_type:
                query += " AND p.property_type = ?"
                params.append(property_type)
                exact_match_conditions.append("property_type")
            
            if min_budget:
                query += " AND (p.max_size_sqft * p.price_per_sqft) >= ?"
                params.append(min_budget)
                exact_match_conditions.append("min_budget")
            
            if max_budget:
                query += " AND (p.min_size_sqft * p.price_per_sqft) <= ?"
                params.append(max_budget)
                exact_match_conditions.append("max_budget")
            
            if configurations:
                # Extract and expand configurations for more intelligent matching
                config_list = [c.strip() for c in configurations.split(',')]
                expanded_configs = []
        
                for config in config_list:
                    expanded_configs.append(config)
                    # If it's a BHK configuration, add similar formats and alternative options
                    if 'BHK' in config:
                        # Extract the number of bedrooms
                        bhk_number = config.replace('BHK', '').strip()
                        if bhk_number.isdigit():
                            # Add alternative formats of the same configuration
                            expanded_configs.append(f"{bhk_number} BHK")
                            expanded_configs.append(f"{bhk_number} Bedroom")
                            
                            # If 3BHK is requested, also include 2BHK options
                            if bhk_number == '3':
                                expanded_configs.append('2BHK')
                                expanded_configs.append('2 BHK')
                                expanded_configs.append('2 Bedroom')
        
                # Add configuration filter with expanded options
                query += f"""
                AND EXISTS (
                    SELECT 1 FROM property_configurations pc2 
                    JOIN configurations c2 ON pc2.configuration_id = c2.id 
                    WHERE pc2.property_id = p.id AND c2.name IN ({','.join(['?'] * len(expanded_configs))})
                )
                """
                params.extend(expanded_configs)
                exact_match_conditions.append("configurations")
            
            # Improved possession date handling
            if possession_date:
                if possession_date.lower() in ['ready', 'ready to move', 'ready to move in']:
                    # Get current date for "ready to move" properties
                    current_date = datetime.now()
                    
                    # Include properties that are ready or will be ready this year
                    query += " AND (p.possession_date LIKE ? OR p.possession_date LIKE ? OR p.possession_date LIKE ?)"
                    params.extend(['%ready%', '%Ready%', f"%{current_date.year}%"])
                    print(f"Filtering for ready to move properties or available in {current_date.year}")
                    
                    exact_match_conditions.append("possession_date")
                elif re.match(r'^\d{4}$', possession_date):
                    # If just a year is provided
                    query += " AND p.possession_date LIKE ?"
                    params.append(f"%{possession_date}%")
                    exact_match_conditions.append("possession_date")
                else:
                    # Try to parse as a date
                    try:
                        date_obj = datetime.strptime(possession_date, "%m/%d/%Y")
                        query += " AND p.possession_date = ?"
                        params.append(date_obj.strftime("%m/%d/%Y"))
                        exact_match_conditions.append("possession_date")
                    except ValueError:
                        # If parsing fails, use simple text matching
                        query += " AND p.possession_date LIKE ?"
                        params.append(f"%{possession_date}%")
                        exact_match_conditions.append("possession_date")
            
            if min_size:
                query += " AND p.max_size_sqft >= ?"
                params.append(min_size)
                exact_match_conditions.append("min_size")
            
            if max_size:
                query += " AND p.min_size_sqft <= ?"
                params.append(max_size)
                exact_match_conditions.append("max_size")
            
            # Group by property
            query += " GROUP BY p.id"
            
            # Order by closest match to preferences
            order_clause = []
            
            if area:
                order_clause.append("p.area = ? DESC")
                params.append(area)
            
            if property_type:
                order_clause.append("p.property_type = ? DESC")
                params.append(property_type)
            
            if configurations:
                # Order by the number of matching configurations
                order_clause.append(f"""
                (SELECT COUNT(*) FROM property_configurations pc3
                 JOIN configurations c3 ON pc3.configuration_id = c3.id
                 WHERE pc3.property_id = p.id AND c3.name IN ({','.join(['?'] * len(expanded_configs))})) DESC
                """)
                params.extend(expanded_configs)
            
            # Add a tie-breaker sort by total price if budget specified
            if min_budget or max_budget:
                if min_budget and max_budget:
                    target_budget = (min_budget + max_budget) / 2
                    order_clause.append("ABS((p.min_size_sqft * p.price_per_sqft + p.max_size_sqft * p.price_per_sqft) / 2 - ?) ASC")
                    params.append(target_budget)
                elif min_budget:
                    order_clause.append("(p.min_size_sqft * p.price_per_sqft) ASC")
                else:
                    order_clause.append("(p.max_size_sqft * p.price_per_sqft) DESC")
            
            # Append order clause if any
            if order_clause:
                query += " ORDER BY " + ", ".join(order_clause)
            
            # Add limit
            query += f" LIMIT {limit}"
            
            # Execute the query
            cursor.execute(query, params)
            result_rows = cursor.fetchall()
            
            # Check if we have an exact match
            exact_match = len(result_rows) > 0 and len(exact_match_conditions) > 0
            
            # Format results
            properties = []
            for row in result_rows:
                # Convert row to dict
                row_dict = dict(row)
                
                # Calculate total prices properly
                min_total = row_dict['min_size_sqft'] * row_dict['price_per_sqft']
                max_total = row_dict['max_size_sqft'] * row_dict['price_per_sqft']
                
                # Format in lakhs if under 1 crore, otherwise in crores
                if min_total < 10000000 and max_total < 10000000:
                    # Both values less than 1 crore, format in lakhs
                    min_lakhs = min_total / 100000
                    max_lakhs = max_total / 100000
                    price_str = f"₹{min_lakhs:.2f} - ₹{max_lakhs:.2f} Lakhs"
                elif min_total < 10000000:
                    # Min in lakhs, max in crores
                    min_lakhs = min_total / 100000
                    max_crores = max_total / 10000000
                    price_str = f"₹{min_lakhs:.2f} Lakhs - ₹{max_crores:.2f} Cr"
                else:
                    # Both in crores
                    min_crores = min_total / 10000000
                    max_crores = max_total / 10000000
                    price_str = f"₹{min_crores:.2f} - ₹{max_crores:.2f} Cr"
                
                # Format property data
                prop = {
                    "name": row_dict["project_name"],
                    "area": row_dict["area"],
                    "type": row_dict["property_type"],
                    "configuration": row_dict["configurations"] or "Not specified",
                    "size": f"{row_dict['min_size_sqft']} - {row_dict['max_size_sqft']} sqft",
                    "price_per_sqft": f"₹{row_dict['price_per_sqft']:,}",
                    "approx_total_price": price_str,
                    "possession_date": row_dict["possession_date"]
                }
                properties.append(prop)
            
            # If no results or very few, try a relaxed search
            if len(properties) < 2 and len(exact_match_conditions) > 0:
                relaxed_results, relaxed_feedback = self.relaxed_search(
                    area=area,
                    property_type=property_type,
                    min_budget=min_budget,
                    max_budget=max_budget,
                    configurations=configurations,
                    possession_date=possession_date,
                    min_size=min_size,
                    max_size=max_size,
                    limit=limit
                )
                
                # If original search returned at least one result, merge with relaxed results
                if properties:
                    # Add any relaxed results not already in the list (by name)
                    existing_names = set(p["name"] for p in properties)
                    for relaxed_prop in relaxed_results:
                        if relaxed_prop["name"] not in existing_names:
                            properties.append(relaxed_prop)
                            if len(properties) >= limit:
                                break
                    
                    feedback = {
                        "exact_match_conditions": exact_match_conditions,
                        "relaxed_search_added": len(properties) - len(result_rows),
                        "strategy": "partial_match_with_relaxed"
                    }
                else:
                    # Use relaxed results completely
                    properties = relaxed_results
                    feedback = relaxed_feedback
                    exact_match = False
            else:
                # Regular search feedback
                feedback = {
                    "exact_match_conditions": exact_match_conditions,
                    "strategy": "exact_match" if exact_match else "area_only" if area else "diverse_sample"
                }
                
                # Add adjustment suggestions
                if not exact_match:
                    if area and len(properties) > 0:
                        # If we found properties in the area but had to relax other conditions
                        conditions_without_area = [c for c in exact_match_conditions if c != "area"]
                        if conditions_without_area:
                            feedback["relaxed_conditions"] = conditions_without_area
                            
                            # Suggest what might need adjustment
                            if "min_budget" in conditions_without_area or "max_budget" in conditions_without_area:
                                feedback["adjustment_needed"] = "budget"
                            elif "configurations" in conditions_without_area:
                                feedback["adjustment_needed"] = "configurations"
            
            conn.close()
            return properties, feedback, exact_match
        
        except Exception as e:
            print(f"Error in search_properties: {e}")
            return [], {"error": str(e)}, False
    
    def relaxed_search(
        self,
        area: Optional[str] = None,
        property_type: Optional[str] = None,
        min_budget: Optional[float] = None,
        max_budget: Optional[float] = None,
        configurations: Optional[str] = None,
        possession_date: Optional[str] = None,
        min_size: Optional[float] = None,
        max_size: Optional[float] = None,
        limit: int = 5
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Perform a relaxed search when exact match doesn't yield results
        Uses a strategy of progressively relaxing constraints
        """
        try:
            # Connect to database
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Strategy 1: Keep area but relax other constraints
            if area:
                query = """
                SELECT DISTINCT 
                    p.id, p.project_name, p.property_type, p.area, p.possession_date,
                    p.min_size_sqft, p.max_size_sqft, p.price_per_sqft,
                    (p.min_size_sqft * p.price_per_sqft) as min_total_price,
                    (p.max_size_sqft * p.price_per_sqft) as max_total_price,
                    GROUP_CONCAT(c.name, ', ') as configurations
                FROM properties p
                LEFT JOIN property_configurations pc ON p.id = pc.property_id
                LEFT JOIN configurations c ON pc.configuration_id = c.id
                WHERE p.area = ?
                GROUP BY p.id
                LIMIT ?
                """
                
                cursor.execute(query, [area, limit])
                area_rows = cursor.fetchall()
                
                if area_rows:
                    properties = []
                    for row in area_rows:
                        row_dict = dict(row)
                        
                        # Calculate total prices properly
                        min_total = row_dict['min_size_sqft'] * row_dict['price_per_sqft']
                        max_total = row_dict['max_size_sqft'] * row_dict['price_per_sqft']
                        
                        # Format in lakhs if under 1 crore, otherwise in crores
                        if min_total < 10000000 and max_total < 10000000:
                            min_lakhs = min_total / 100000
                            max_lakhs = max_total / 100000
                            price_str = f"₹{min_lakhs:.2f} - ₹{max_lakhs:.2f} Lakhs"
                        elif min_total < 10000000:
                            min_lakhs = min_total / 100000
                            max_crores = max_total / 10000000
                            price_str = f"₹{min_lakhs:.2f} Lakhs - ₹{max_crores:.2f} Cr"
                        else:
                            min_crores = min_total / 10000000
                            max_crores = max_total / 10000000
                            price_str = f"₹{min_crores:.2f} - ₹{max_crores:.2f} Cr"
                        
                        prop = {
                            "name": row_dict["project_name"],
                            "area": row_dict["area"],
                            "type": row_dict["property_type"],
                            "configuration": row_dict["configurations"] or "Not specified",
                            "size": f"{row_dict['min_size_sqft']} - {row_dict['max_size_sqft']} sqft",
                            "price_per_sqft": f"₹{row_dict['price_per_sqft']:,}",
                            "approx_total_price": price_str,
                            "possession_date": row_dict["possession_date"]
                        }
                        properties.append(prop)
                    
                    feedback = {
                        "strategy": "area_only",
                        "relaxed_all_except_area": True
                    }
                    
                    conn.close()
                    return properties, feedback
            
            # Strategy 2: Get a diverse sample
            query = """
            SELECT DISTINCT 
                p.id, p.project_name, p.property_type, p.area, p.possession_date,
                p.min_size_sqft, p.max_size_sqft, p.price_per_sqft,
                (p.min_size_sqft * p.price_per_sqft) as min_total_price,
                (p.max_size_sqft * p.price_per_sqft) as max_total_price,
                GROUP_CONCAT(c.name, ', ') as configurations
            FROM properties p
            LEFT JOIN property_configurations pc ON p.id = pc.property_id
            LEFT JOIN configurations c ON pc.configuration_id = c.id
            GROUP BY p.id
            ORDER BY RANDOM()
            LIMIT ?
            """
            
            cursor.execute(query, [limit])
            sample_rows = cursor.fetchall()
            
            properties = []
            for row in sample_rows:
                row_dict = dict(row)
                
                # Calculate total prices properly
                min_total = row_dict['min_size_sqft'] * row_dict['price_per_sqft']
                max_total = row_dict['max_size_sqft'] * row_dict['price_per_sqft']
                    
                # Format in lakhs if under 1 crore, otherwise in crores
                if min_total < 10000000 and max_total < 10000000:
                    min_lakhs = min_total / 100000
                    max_lakhs = max_total / 100000
                    price_str = f"₹{min_lakhs:.2f} - ₹{max_lakhs:.2f} Lakhs"
                elif min_total < 10000000:
                    min_lakhs = min_total / 100000
                    max_crores = max_total / 10000000
                    price_str = f"₹{min_lakhs:.2f} Lakhs - ₹{max_crores:.2f} Cr"
                else:
                    min_crores = min_total / 10000000
                    max_crores = max_total / 10000000
                    price_str = f"₹{min_crores:.2f} - ₹{max_crores:.2f} Cr"
                    
                prop = {
                    "name": row_dict["project_name"],
                    "area": row_dict["area"],
                    "type": row_dict["property_type"],
                    "configuration": row_dict["configurations"] or "Not specified",
                    "size": f"{row_dict['min_size_sqft']} - {row_dict['max_size_sqft']} sqft",
                    "price_per_sqft": f"₹{row_dict['price_per_sqft']:,}",
                    "approx_total_price": price_str,
                    "possession_date": row_dict["possession_date"]
                }
                properties.append(prop)
            
            feedback = {
                "strategy": "diverse_sample",
                "relaxed_all": True,
                "message": "Showing a diverse sample of properties. Please refine your criteria for more specific matches."
            }
            
            conn.close()
            return properties, feedback
        
        except Exception as e:
            print(f"Error in relaxed_search: {e}")
            return [], {"error": str(e)}
    
    def get_unique_areas(self) -> List[str]:
        """Get a list of all available areas"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT DISTINCT area FROM properties ORDER BY area")
            areas = [row['area'] for row in cursor.fetchall()]
            
            conn.close()
            return areas
        except Exception as e:
            print(f"Error in get_unique_areas: {e}")
            return []
    
    def get_property_types(self) -> List[str]:
        """Get a list of all available property types"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT DISTINCT property_type FROM properties ORDER BY property_type")
            types = [row['property_type'] for row in cursor.fetchall()]
            
            conn.close()
            return types
        except Exception as e:
            print(f"Error in get_property_types: {e}")
            return []
    
    def get_configurations(self) -> List[str]:
        """Get a list of all available configurations"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT DISTINCT name FROM configurations ORDER BY name")
            configs = [row['name'] for row in cursor.fetchall()]
            
            conn.close()
            return configs
        except Exception as e:
            print(f"Error in get_configurations: {e}")
            return []
    
    def get_price_range(self) -> Dict[str, float]:
        """Get the minimum and maximum property prices"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT 
                MIN(min_size_sqft * price_per_sqft) as min_price, 
                MAX(max_size_sqft * price_per_sqft) as max_price
            FROM properties
            """)
            
            result = cursor.fetchone()
            
            conn.close()
            
            return {
                "min": result['min_price'],
                "max": result['max_price']
            }
        except Exception as e:
            print(f"Error in get_price_range: {e}")
            return {"min": 0, "max": 0}
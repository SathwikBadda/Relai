# fix_agent.py - Improved version with better area matching
import os
import streamlit as st
import sqlite3
import sys
import json
import re
import traceback
from typing import Optional, Dict, List, Any, Union
from difflib import SequenceMatcher

# Function to get a database connection
def get_db_connection(db_path='data/properties.db'):
    """Get a database connection with row factory"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# Function to verify database is ready
def verify_database(db_path='data/properties.db'):
    """Check if database exists and has properties table"""
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if properties table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='properties'")
        if not cursor.fetchone():
            conn.close()
            print("Database does not have a properties table")
            return False
        
        # Check if there are properties
        cursor.execute("SELECT COUNT(*) FROM properties")
        count = cursor.fetchone()[0]
        
        if count == 0:
            conn.close()
            print("Database has no properties")
            return False
        
        print(f"Database verified: {count} properties found")
        conn.close()
        return True
    except Exception as e:
        print(f"Database verification failed: {e}")
        return False

# Calculate similarity between two strings
def string_similarity(str1, str2):
    """Calculate similarity between two strings using SequenceMatcher"""
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

# Find potential area matches from the database
def find_area_matches(area_input, db_path='data/properties.db'):
    """Find potential area matches from the database with similarity scores"""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # Get all distinct areas from the database
    cursor.execute("SELECT DISTINCT area FROM properties")
    all_areas = [row['area'] for row in cursor.fetchall()]
    conn.close()
    
    # Calculate similarity scores
    similarity_scores = []
    for db_area in all_areas:
        # Calculate similarity score
        similarity = string_similarity(area_input, db_area)
        
        # Check for word-level matches (e.g., "lb nagar" vs "L B Nagar")
        # Split both strings and check for word matches
        input_words = set(area_input.lower().split())
        db_words = set(db_area.lower().split())
        word_match_ratio = len(input_words.intersection(db_words)) / max(len(input_words), len(db_words)) if max(len(input_words), len(db_words)) > 0 else 0
        
        # Combine the scores, giving more weight to word matches
        combined_score = (similarity * 0.4) + (word_match_ratio * 0.6)
        
        similarity_scores.append((db_area, combined_score))
    
    # Sort by similarity score
    similarity_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Return top matches with scores above threshold
    return [match for match in similarity_scores if match[1] > 0.5]

# Parse compact preferences like "5cr;ready;gachibowli;3bhk;appartment"
def parse_compact_preferences(input_text):
    """
    Parse compact preference inputs like "5cr;ready;gachibowli;3bhk;appartment"
    Returns a dictionary of preferences
    """
    preferences = {}
    
    # If input contains semicolons, it's likely a compact format
    if ';' in input_text:
        parts = input_text.split(';')
        for part in parts:
            part = part.strip().lower()
            
            # Budget handling
            if 'cr' in part or 'crore' in part:
                try:
                    amount = float(part.replace('cr', '').replace('crore', ''))
                    preferences['max_budget'] = amount * 10000000  # Convert to rupees
                except ValueError:
                    pass
            elif 'lakh' in part or 'lac' in part:
                try:
                    amount = float(part.replace('lakh', '').replace('lac', ''))
                    preferences['max_budget'] = amount * 100000  # Convert to rupees
                except ValueError:
                    pass
            elif part.isdigit():  # Just a number could be budget in rupees
                try:
                    amount = float(part)
                    if amount > 10000:  # Likely rupees
                        preferences['max_budget'] = amount
                except ValueError:
                    pass
            
            # Possession status
            elif part in ['ready', 'readytomove', 'ready to move']:
                preferences['possession_date'] = 'Ready to Move'
            elif part in ['underconstruction', 'under construction', 'upcoming']:
                preferences['possession_date'] = 'Under Construction'
            
            # BHK configuration
            elif 'bhk' in part:
                bhk = part.replace('bhk', '')
                try:
                    if bhk.isdigit():
                        preferences['configurations'] = f"{bhk}BHK"
                except:
                    pass
            
            # Property type
            elif part in ['apartment', 'appartment', 'flat']:
                preferences['property_type'] = 'Apartment'
            elif part in ['villa', 'independent house']:
                preferences['property_type'] = 'Villa'
            elif part in ['plot', 'land']:
                preferences['property_type'] = 'Plot'
            
            # For any other part that didn't match the above patterns,
            # assume it might be an area and store it
            else:
                # Store the part as a potential area
                preferences['area'] = part

    return preferences

# Helper function to extract preferences from text inputs
def extract_preferences_from_text(text):
    """Extract property preferences from text input"""
    preferences = {}
    
    # Generic area extraction patterns - more flexible to match any area name
    area_patterns = [
        # Find areas mentioned with prepositions like "in", "at", "near"
        r'(?:in|at|near|around|from)\s+([A-Za-z0-9\s]+?)(?:\s+(?:with|for|under|below|above|having|that|which|and|,|\.|$))',
        
        # Areas with common Indian suffixes (more general matching)
        r'(?:in|at|near|around)\s+([A-Za-z0-9\s]+?(?:Hills|City|Nagar|Puram|Pally|Colony|Gardens|Heights|guda|bad|poor|pet|puram|pally|halli))(?:\s+|$|\.)',
        
        # Direct area mentions without prepositions
        r'\b([A-Za-z0-9\s]+?(?:Hills|City|Nagar|Puram|Pally|Colony|Gardens|Heights|guda|bad|poor|pet|puram|pally|halli))\b',
        
        # Fallback for any capitalized words that might be area names
        r'(?:in|at|near|around)\s+([A-Za-z][A-Za-z0-9\s]+?)(?:\s+|$|\.)'
    ]
    
    for pattern in area_patterns:
        area_match = re.search(pattern, text, re.IGNORECASE)
        if area_match:
            area = area_match.group(1).strip()
            # Remove common words that might be part of the match but not the area
            area = re.sub(r'\b(?:in|at|near|around|from|the|a|an)\b', '', area, flags=re.IGNORECASE).strip()
            
            # Check if area is not empty after cleaning
            if area and len(area) > 1:  # At least 2 chars to avoid single letters
                preferences['area'] = area
                break
    
    # Extract property type
    if re.search(r'\b(?:apartment|flat)\b', text, re.IGNORECASE):
        preferences['property_type'] = 'Apartment'
    elif re.search(r'\bvilla\b', text, re.IGNORECASE):
        preferences['property_type'] = 'Villa'
    elif re.search(r'\b(?:plot|open plot|land)\b', text, re.IGNORECASE):
        preferences['property_type'] = 'Plot'
    
    # Extract BHK configuration
    bhk_match = re.search(r'(\d+)\s*(?:bhk|bedroom)', text, re.IGNORECASE)
    if bhk_match:
        preferences['configurations'] = f"{bhk_match.group(1)}BHK"
    
    # Extract budget
    budget_match = re.search(r'(\d+\.?\d*)\s*(?:lakh|lac|cr|crore)', text, re.IGNORECASE)
    if budget_match:
        amount = float(budget_match.group(1))
        if 'crore' in text.lower() or 'cr' in text.lower():
            amount = amount * 10000000  # Convert crore to rupees
        elif 'lakh' in text.lower() or 'lac' in text.lower():
            amount = amount * 100000  # Convert lakhs to rupees
        
        # Determine if it's min or max budget based on context
        if re.search(r'\b(?:under|less than|below|max|maximum|not more than)\b', text, re.IGNORECASE):
            preferences['max_budget'] = amount
        elif re.search(r'\b(?:above|more than|at least|min|minimum)\b', text, re.IGNORECASE):
            preferences['min_budget'] = amount
        else:
            # If unclear, set as max budget by default
            preferences['max_budget'] = amount
    
    # Extract possession status
    if re.search(r'\b(?:ready|ready to move|immediate|ready for possession)\b', text, re.IGNORECASE):
        preferences['possession_date'] = 'Ready to Move'
    elif re.search(r'\b(?:under construction|upcoming|future|not ready)\b', text, re.IGNORECASE):
        preferences['possession_date'] = 'Under Construction'
    
    return preferences

# Main function to handle property search - this key function needs to handle all input formats
def search_properties(query=None):
    """
    Single-argument property search function that accepts any input format.
    This is the function we'll expose to the LLM to prevent the "too many arguments" error.
    """
    try:
        print(f"Search properties called with: {query}")
        
        # Initialize preferences dictionary
        preferences = {}
        
        # Convert all positional args to a single string if they're a list
        if isinstance(query, list):
            query = " ".join(str(item) for item in query)
            print(f"Converted list to string: {query}")
        
        # Process the query based on its type
        if query:
            if isinstance(query, str):
                # Check if it's a compact format with semicolons
                if ';' in query:
                    compact_prefs = parse_compact_preferences(query)
                    preferences.update(compact_prefs)
                    print(f"Parsed semicolon format: {preferences}")
                # Otherwise treat it as regular text
                else:
                    text_prefs = extract_preferences_from_text(query)
                    preferences.update(text_prefs)
                    print(f"Extracted preferences from text: {preferences}")
            elif isinstance(query, dict):
                # If it's already a dictionary, use it directly
                preferences.update(query)
                print(f"Using provided dictionary: {preferences}")
        
        # Now call the actual implementation with the parsed preferences
        return improved_property_search(**preferences)
    
    except Exception as e:
        print(f"Error in search_properties wrapper: {e}")
        traceback.print_exc()
        # Return a graceful error response
        return {
            "properties": [],
            "exact_match": False,
            "count": 0,
            "advice": f"An error occurred while searching for properties. Please try again."
        }

# Improved property search implementation
def improved_property_search(**kwargs):
    """
    Improved property search implementation with flexible area matching
    and better SQL queries.
    """
    try:
        print(f"Debug - improved_property_search called with kwargs: {kwargs}")
        
        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Extract search parameters
        area = kwargs.get('area')
        property_type = kwargs.get('property_type')
        min_budget = kwargs.get('min_budget')
        max_budget = kwargs.get('max_budget')
        configurations = kwargs.get('configurations')
        possession_date = kwargs.get('possession_date')
        min_size = kwargs.get('min_size')
        max_size = kwargs.get('max_size')
        
        # Debug output
        print(f"Search parameters: area={area}, property_type={property_type}, "
              f"budget={min_budget}-{max_budget}, config={configurations}, "
              f"possession={possession_date}, size={min_size}-{max_size}")
        
        # Try to store preferences if this is a Streamlit app session
        try:
            if hasattr(st, 'session_state') and 'session_id' in st.session_state and any([area, property_type, min_budget, max_budget, configurations, possession_date, min_size, max_size]):
                try:
                    from utils.db_setup import store_user_preferences
                    store_user_preferences(
                        session_id=st.session_state.session_id,
                        area=area,
                        property_type=property_type,
                        min_budget=min_budget,
                        max_budget=max_budget,
                        configuration=configurations,
                        possession_date=possession_date,
                        min_size=min_size,
                        max_size=max_size,
                        db_path='data/properties.db'
                    )
                except ImportError:
                    print("Non-critical: Could not import store_user_preferences")
        except Exception as e:
            print(f"Non-critical error storing preferences: {e}")
        
        # IMPROVED AREA SEARCH: First, check if we need to do area matching
        area_candidates = []
        potential_matches = []
        
        if area:
            print(f"Starting enhanced location search for area: {area}")
            
            # Use the improved area matching algorithm
            potential_matches = find_area_matches(area)
            print(f"Potential area matches: {potential_matches}")
            
            # If we have matches with good scores, use them
            if potential_matches:
                area_candidates = [match[0] for match in potential_matches]
                print(f"Using the following area matches: {area_candidates}")
            else:
                print(f"No good area matches found for '{area}' in database")
                
                # Get a list of all areas for suggestions
                cursor.execute("SELECT DISTINCT area FROM properties")
                all_areas = [row['area'] for row in cursor.fetchall()]
                
                return {
                    "properties": [],
                    "exact_match": False,
                    "count": 0,
                    "area_not_found": True,  # Flag that area wasn't found
                    "user_input_area": area,  # Store what user entered
                    "all_areas": all_areas[:10],  # Send sample of areas for LLM to suggest
                    "advice": f"No properties found in '{area}'. The area name might be misspelled or not in our database."
                }
        
        # Build query based on whether we have area matches or not
        if area and area_candidates:
            # Base query to get properties from matched areas
            query = """
            SELECT 
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
            
            # Add area filter with placeholders
            area_placeholders = ', '.join(['?'] * len(area_candidates))
            query += f" AND p.area IN ({area_placeholders})"
            params = area_candidates.copy()
        else:
            # Base query without area filter
            query = """
            SELECT 
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
        
        # Add additional filters if provided
        if property_type:
            query += " AND LOWER(p.property_type) = LOWER(?)"
            params.append(property_type)
        
        if min_budget:
            query += " AND (p.min_size_sqft * p.price_per_sqft) >= ?"
            params.append(min_budget)
        
        if max_budget:
            query += " AND (p.max_size_sqft * p.price_per_sqft) <= ?"
            params.append(max_budget)
        
        if configurations:
            # Handle different configuration formats
            config_list = []
            if isinstance(configurations, str):
                config_list = [c.strip() for c in configurations.split(',')]
            elif isinstance(configurations, list):
                config_list = configurations
            else:
                config_list = [str(configurations)]
            
            # Add configuration filter with improved matching
            config_conditions = []
            for config in config_list:
                config_conditions.append("LOWER(c.name) LIKE LOWER(?)")
                params.append(f"%{config}%")
            
            if config_conditions:
                query += f" AND EXISTS (SELECT 1 FROM property_configurations pc2 JOIN configurations c2 ON pc2.configuration_id = c2.id WHERE pc2.property_id = p.id AND ({' OR '.join(config_conditions)}))"
        
        if possession_date:
            query += " AND LOWER(p.possession_date) LIKE LOWER(?)"
            params.append(f'%{possession_date}%')
        
        if min_size:
            query += " AND p.max_size_sqft >= ?"
            params.append(min_size)
        
        if max_size:
            query += " AND p.min_size_sqft <= ?"
            params.append(max_size)
        
        # Group by to ensure unique properties
        query += " GROUP BY p.id"
        
        # Debug the query
        print(f"Executing query: {query}")
        print(f"With parameters: {params}")
        
        # Execute query
        cursor.execute(query, params)
        results = cursor.fetchall()
        print(f"Query returned {len(results)} results")
        
        # If we have an area but no results with filters, try just the area without other filters
        if area and area_candidates and len(results) == 0 and (property_type or min_budget or max_budget or configurations or possession_date or min_size or max_size):
            print(f"No results with filters, fetching ALL properties in {area_candidates}")
            
            # Simple query to get all properties in the matched areas
            area_placeholders = ', '.join(['?'] * len(area_candidates))
            area_query = f"""
            SELECT 
                p.id, p.project_name, p.property_type, p.area, p.possession_date,
                p.min_size_sqft, p.max_size_sqft, p.price_per_sqft,
                (p.min_size_sqft * p.price_per_sqft) as min_total_price,
                (p.max_size_sqft * p.price_per_sqft) as max_total_price,
                GROUP_CONCAT(c.name, ', ') as configurations
            FROM properties p
            LEFT JOIN property_configurations pc ON p.id = pc.property_id
            LEFT JOIN configurations c ON pc.configuration_id = c.id
            WHERE p.area IN ({area_placeholders})
            GROUP BY p.id
            """
            
            cursor.execute(area_query, area_candidates)
            results = cursor.fetchall()
            print(f"Retrieved ALL {len(results)} properties in {area_candidates}")
        
        # Format results into property objects
        properties = []
        for row in results:
            row_dict = dict(row)
            
            prop = {
                "name": row_dict["project_name"],
                "area": row_dict["area"],
                "type": row_dict["property_type"],
                "configuration": row_dict["configurations"] or "Not specified",
                "size": f"{row_dict['min_size_sqft']} - {row_dict['max_size_sqft']} sqft",
                "price_per_sqft": f"₹{row_dict['price_per_sqft']:,}",
                "approx_total_price": f"₹{row_dict['min_total_price']:,.0f} - ₹{row_dict['max_total_price']:,.0f}",
                "possession_date": row_dict["possession_date"]
            }
            properties.append(prop)
        
        # Analyze results for feedback
        areas = {}
        property_types = {}
        configurations_dict = {}
        
        for prop in properties:
            # Count areas
            property_area = prop["area"]
            areas[property_area] = areas.get(property_area, 0) + 1
            
            # Count property types
            p_type = prop["type"]
            property_types[p_type] = property_types.get(p_type, 0) + 1
            
            # Count configurations
            for config in prop["configuration"].split(", "):
                if config != "Not specified":
                    configurations_dict[config] = configurations_dict.get(config, 0) + 1
        
        # Create response
        response = {
            "properties": properties,
            "exact_match": True if area and area_candidates and len(area_candidates) > 0 and string_similarity(area, area_candidates[0]) > 0.9 else False,
            "fuzzy_match": True if area and area_candidates and len(area_candidates) > 0 else False,
            "count": len(properties),
            "feedback": {
                "areas": areas,
                "property_types": property_types,
                "configurations": configurations_dict
            }
        }
        
        # Add matched area information if available
        if area and area_candidates:
            response["user_input_area"] = area
            response["matched_areas"] = area_candidates
            
            # Add match confidence information
            if potential_matches:
                response["area_match_scores"] = [
                    {"area": match[0], "similarity": match[1]} 
                    for match in potential_matches
                ]
        
        # Create advice based on results
        if len(properties) > 0:
            if area and len(area_candidates) > 0:
                # Mention how the area was matched if it wasn't an exact match
                if not response["exact_match"]:
                    advice = f"Showing {len(properties)} properties in {', '.join(area_candidates)} (matched from your search for '{area}')."
                else:
                    advice = f"Showing {len(properties)} properties in {', '.join(area_candidates)}."
            else:
                advice = f"Found {len(properties)} properties matching your criteria."
            
            # Add area distribution if multiple areas
            if len(areas) > 1:
                top_areas = sorted(areas.items(), key=lambda x: x[1], reverse=True)[:3]
                advice += f" Top areas: {', '.join([f'{a} ({c})' for a, c in top_areas])}."
            
            # Add property type info if multiple types
            if len(property_types) > 1:
                advice += f" Property types include: {', '.join([f'{t} ({c})' for t, c in property_types.items()])}."
            
            # Add configuration info if available
            if configurations_dict:
                advice += f" Configurations: {', '.join([f'{c} ({count})' for c, count in configurations_dict.items()])}."
            
            response["advice"] = advice
        else:
            if area:
                advice = f"No properties found in {area}"
                if property_type or min_budget or max_budget or configurations or possession_date:
                    advice += " with your specified filters. Try broadening your search criteria."
                else:
                    advice += ". "
                    
                    # Get some alternative area suggestions
                    cursor.execute("SELECT DISTINCT area FROM properties LIMIT 5")
                    alt_areas = [row['area'] for row in cursor.fetchall()]
                    if alt_areas:
                        advice += f"Try searching in other popular areas like {', '.join(alt_areas)}."
            else:
                advice = "No properties found matching your criteria. Try adjusting your search parameters."
            
            response["advice"] = advice
        
        # Close connection
        conn.close()
        return response
            
    except Exception as e:
        print(f"Error in property search: {e}")
        traceback.print_exc()
        # Return a graceful error response
        return {
            "properties": [],
            "exact_match": False,
            "count": 0,
            "advice": f"An error occurred while searching for properties. Please try again with different criteria."
        }

# Helper functions for the agent
def get_user_preferences():
    """Get user preferences from the database."""
    try:
        db_path = 'data/properties.db'
        
        # Get the session ID from Streamlit
        if hasattr(st, 'session_state') and 'session_id' in st.session_state:
            session_id = st.session_state.session_id
        else:
            return {
                "has_preferences": False,
                "message": "Session not initialized. Your preferences will be saved once you search for properties."
            }
        
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Get preferences
        cursor.execute('SELECT * FROM user_preferences WHERE session_id = ?', (session_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            # Convert to dictionary
            preferences = dict(row)
            
            # Format preferences for display
            formatted_prefs = {}
            
            if preferences.get('area'):
                formatted_prefs['area'] = preferences['area']
            
            if preferences.get('property_type'):
                formatted_prefs['property_type'] = preferences['property_type']
            
            if preferences.get('min_budget') and preferences.get('max_budget'):
                formatted_prefs['budget'] = f"₹{preferences['min_budget']:,.0f} - ₹{preferences['max_budget']:,.0f}"
            elif preferences.get('min_budget'):
                formatted_prefs['budget'] = f"Above ₹{preferences['min_budget']:,.0f}"
            elif preferences.get('max_budget'):
                formatted_prefs['budget'] = f"Up to ₹{preferences['max_budget']:,.0f}"
            
            if preferences.get('configuration'):
                formatted_prefs['configuration'] = preferences['configuration']
            
            if preferences.get('min_size') and preferences.get('max_size'):
                formatted_prefs['size'] = f"{preferences['min_size']} - {preferences['max_size']} sqft"
            elif preferences.get('min_size'):
                formatted_prefs['size'] = f"Above {preferences['min_size']} sqft"
            elif preferences.get('max_size'):
                formatted_prefs['size'] = f"Up to {preferences['max_size']} sqft"
            
            if preferences.get('possession_date'):
                formatted_prefs['possession_date'] = preferences['possession_date']
            
            return {
                "has_preferences": True,
                "preferences": formatted_prefs,
                "last_updated": preferences.get('last_updated'),
                "message": "Here are your current preferences. You can update these at any time to refine your property search."
            }
        else:
            return {
                "has_preferences": False,
                "message": "No preferences stored yet. Share your preferences for location, budget, or property type to get personalized recommendations."
            }
    except Exception as e:
        print(f"Error getting user preferences: {e}")
        traceback.print_exc()
        return {
            "has_preferences": False,
            "message": "An error occurred while retrieving your preferences. Please try again."
        }

# Helper function to get unique areas
def get_unique_areas():
    """Get all unique areas from the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT area FROM properties ORDER BY area')
        areas = [row['area'] for row in cursor.fetchall()]
        conn.close()
        return areas
    except Exception as e:
        print(f"Error getting areas: {e}")
        return ["Error retrieving areas"]

# Helper function to get property types
def get_property_types():
    """Get all property types from the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT property_type FROM properties ORDER BY property_type')
        types = [row['property_type'] for row in cursor.fetchall()]
        conn.close()
        return types
    except Exception as e:
        print(f"Error getting property types: {e}")
        return ["Error retrieving property types"]

# Helper function to get configurations
def get_configurations():
    """Get all configurations from the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM configurations ORDER BY name')
        configs = [row['name'] for row in cursor.fetchall()]
        conn.close()
        return configs
    except Exception as e:
        print(f"Error getting configurations: {e}")
        return ["Error retrieving configurations"]

# Helper function to get price range
def get_price_range():
    """Get price range from the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Calculate min and max prices
        cursor.execute('''
        SELECT 
            MIN(min_size_sqft * price_per_sqft) as min_price,
            MAX(max_size_sqft * price_per_sqft) as max_price
        FROM properties
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        min_price = row['min_price']
        max_price = row['max_price']
        
        return {
            "min_price": f"₹{min_price:,.0f}",
            "max_price": f"₹{max_price:,.0f}",
            "min_price_lakhs": f"₹{min_price/100000:.2f} Lakhs",
            "max_price_lakhs": f"₹{max_price/100000:.2f} Lakhs",
            "min_price_crores": f"₹{min_price/10000000:.2f} Crores",
            "max_price_crores": f"₹{max_price/10000000:.2f} Crores"
        }
    except Exception as e:
        print(f"Error getting price range: {e}")
        return {"error": "Error retrieving price range"}

# Function to create a fixed agent with standard tools
def create_fixed_agent(db_path='data/properties.db'):
    """Create an agent with direct SQL functions"""
    try:
        # Verify database is ready
        verify_database(db_path)
        
        # Import required tools and agent components
        print("Importing modules for agent creation...")
        try:
            # Import the necessary libraries
            from langchain.tools import Tool
            from langchain.agents import AgentExecutor, create_openai_functions_agent
            from langchain_openai import ChatOpenAI
            from langchain.memory import ConversationBufferMemory
            from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
            
            # Get system prompt from config
            from prompts.system_prompts import SYSTEM_PROMPT
            from config import MODEL_NAME, TEMPERATURE, MAX_TOKENS
            
            print("Successfully imported required modules")
        except ImportError as e:
            print(f"Error importing required modules: {e}")
            raise Exception(f"Failed to import necessary libraries: {e}")
        
        # Create tools using the simplified single-argument search function
        print("Creating tools with single-argument interface...")
        tools = [
            Tool(
                name="search_properties",
                func=search_properties,  # Use the single-argument wrapper function
                description="""
                Search for properties based on criteria. Just provide a description of what you're looking for.
                Examples:
                - search_properties("3BHK apartment in Banjara Hills")
                - search_properties("Properties in Gachibowli under 2 crore")
                - search_properties("Ready to move villas in Hitech City")
                """
            ),
            Tool(
                name="get_user_preferences",
                func=get_user_preferences,
                description="Get the user's stored preferences from previous interactions."
            ),
            Tool(
                name="get_areas",
                func=get_unique_areas,
                description="Get a list of all available areas/locations in Hyderabad."
            ),
            Tool(
                name="get_property_types",
                func=get_property_types,
                description="Get a list of all available property types."
            ),
            Tool(
                name="get_configurations",
                func=get_configurations,
                description="Get a list of all available BHK configurations."
            ),
            Tool(
                name="get_price_range",
                func=get_price_range,
                description="Get the minimum and maximum property prices available in the database."
            )
        ]
        
        # Enhanced system prompt with better guidance
        enhanced_prompt = SYSTEM_PROMPT + """

IMPORTANT GUIDELINES FOR PROPERTY RECOMMENDATIONS:

1. When exact property matches aren't found:
   - Always explain why certain preferences might be difficult to match
   - Suggest which preferences the user might consider adjusting
   - Present alternative properties that match SOME of their criteria
   - Focus on properties from the same area if location was specified

2. When showing properties:
   - Highlight which aspects match the user's preferences
   - Point out where properties differ from their ideal preferences
   - Suggest realistic alternatives if their budget doesn't match the area

3. For better recommendations:
   - Suggest nearby areas if their preferred location has limited options
   - Explain trade-offs between different areas (e.g., price vs. connectivity)
   - Offer helpful context about property trends in Hyderabad

4. CRITICAL AREA MATCHING GUIDELINES:
   - When the user mentions an area that doesn't match exactly with the database:
     a. Detect when search_properties returns area_not_found flag
     b. Check the list of similar areas in the database
     c. Ask "Did you mean [suggested area]?" based on closest matching areas
     d. Suggest up to 3 possible area matches that sound similar
     e. If no similar matches, explain that the area might not be in our database and list some popular areas
   - For misspelled areas (like "hitehcity" vs "HI Tech City" or "lb nagar" vs "L B Nagar"), 
     directly suggest the proper spelling from our database
   - Handle areas with formatting differences intelligently (spaces, capitalization, etc.)

5. When using tools:
   - Use the search_properties tool to search for properties based on user preferences
   - ALWAYS USE ONLY ONE ARGUMENT with search_properties - a single string describing what to search for
   - CORRECT: search_properties("3BHK in Kukatpally under 40000000")
   - INCORRECT: search_properties("Kukatpally", "Apartment", "3BHK", 40000000)
   - DO NOT pass multiple arguments to search_properties - only pass a single string
   - For semicolon-separated inputs, just pass them directly as one string:
     search_properties("5cr;ready;gachibowli;3bhk;apartment")
   - Use get_user_preferences to retrieve information from previous interactions
   - Display ALL available properties in a given area

6. Understanding user preferences:
   - When a user provides preferences, incorporate them into your search query
   - Use conversational memory to refer to previous preferences
   - If new preferences contradict old ones, prioritize the newer information

7. Property search priorities:
   - Area/location is the MOST IMPORTANT search criterion
   - When a user mentions an area, immediately search for properties in that area
   - Show the user a comprehensive list of properties in their desired area
   - If there are too many results, suggest additional filters

8. Results display and explanation:
   - When showing property search results, display ALL available properties
   - Provide area-specific insights when showing properties in a particular area
   - Break down results by property types, configurations, and price ranges
   - Explain the characteristics of the area that make it desirable

Keep these guidelines in mind when helping users find their ideal property in Hyderabad!
"""
        
        # Create prompt
        print("Creating prompt template...")
        prompt = ChatPromptTemplate.from_messages([
            ("system", enhanced_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # Initialize LLM
        print("Creating LLM...")
        try:
            llm = ChatOpenAI(
                model=MODEL_NAME,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS
            )
            print(f"Successfully created LLM with model: {MODEL_NAME}")
        except Exception as e:
            print(f"Error creating LLM: {e}")
            raise Exception(f"Failed to initialize ChatOpenAI model: {e}")
        
        # Create memory
        print("Creating conversation memory...")
        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        
        # Create agent
        print("Creating agent...")
        try:
            agent = create_openai_functions_agent(llm, tools, prompt)
            if agent is None:
                raise Exception("Agent creation returned None")
            print("Successfully created agent")
        except Exception as e:
            print(f"Error in create_openai_functions_agent: {e}")
            traceback.print_exc()
            
            # Fallback to direct agent executor creation without the agent factory
            print("Using fallback agent creation method...")
            from langchain.agents.openai_functions_agent.base import OpenAIFunctionsAgent
            agent = OpenAIFunctionsAgent(llm=llm, tools=tools, prompt=prompt)
        
        # Create agent executor
        print("Creating agent executor...")
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            memory=memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=10
        )
        
        print("Agent created successfully!")
        return agent_executor
    except Exception as e:
        
        # Create an emergency fallback function
        def emergency_fallback(input_query):
            """Emergency fallback for when agent creation fails"""
            try:
                print("Using emergency fallback search function")
                # Try to extract area from input
                preferences = extract_preferences_from_text(input_query)
                area = preferences.get('area')
                
                if area:
                    # Try to search for properties in the area
                    try:
                        results = improved_property_search(**preferences)
                        count = results.get("count", 0)
                        return {
                            "output": f"I found {count} properties in {area}. Here are some details about them.",
                            "intermediate_steps": [],
                            "tool_results": results
                        }
                    except:
                        pass
                
                if ';' in input_query:
                    # Try parsing as compact format
                    compact_prefs = parse_compact_preferences(input_query)
                    if compact_prefs:
                        try:
                            results = improved_property_search(**compact_prefs)
                            count = results.get("count", 0)
                            return {
                                "output": f"I found {count} properties matching your criteria. Here are the details.",
                                "intermediate_steps": [],
                                "tool_results": results
                            }
                        except:
                            pass
                
                # Default response
                return {
                    "output": "I can help you find properties in Hyderabad. Please let me know which area you're interested in, such as Gachibowli, Banjara Hills, or Hitech City.",
                    "intermediate_steps": [],
                    "tool_results": None
                }
            except Exception as fallback_error:
                print(f"Error in emergency fallback: {fallback_error}")
                return {
                    "output": "I'm here to help you find real estate properties in Hyderabad. Please tell me which area you're interested in exploring.",
                    "intermediate_steps": [],
                    "tool_results": None
                }
        
        print("Returning emergency fallback function")
        return emergency_fallback
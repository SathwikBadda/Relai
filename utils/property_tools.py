# utils/property_tools.py - Enhanced property search and filter functionality

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

class PropertyRecommendationTools:
    """
    Tools for searching and filtering property data with enhanced recommendation capabilities
    """
    def __init__(self, df: pd.DataFrame):
        """
        Initialize with property dataset
        
        Args:
            df: DataFrame containing property data
        """
        self.df = df
        # Ensure required columns exist or add fallbacks
        self._ensure_columns()
        
    def _ensure_columns(self):
        """Ensure all required columns exist, creating fallbacks if necessary"""
        required_columns = [
            'ProjectName', 'PropertyType', 'Area', 'PossessionDate', 
            'TotalUnits', 'AreaSizeAcres', 'Configurations', 
            'MinSizeSqft', 'MaxSizeSqft', 'PricePerSqft'
        ]
        
        for col in required_columns:
            if col not in self.df.columns:
                print(f"Warning: Column '{col}' not found in dataset. Creating fallback.")
                
                # Create fallback columns with default values
                if col == 'PricePerSqft' and 'PricePerSqft' in self.df.columns:
                    self.df[col] = self.df['PricePerSqft']
                elif col in ['MinSizeSqft', 'MaxSizeSqft', 'TotalUnits', 'AreaSizeAcres', 'PricePersqft']:
                    self.df[col] = 0
                else:
                    self.df[col] = 'N/A'
        
    def search_properties(self, 
                         area: Optional[str] = None,
                         property_type: Optional[str] = None, 
                         min_budget: Optional[float] = None,
                         max_budget: Optional[float] = None,
                         configurations: Optional[str] = None,
                         possession_date: Optional[str] = None,
                         min_size: Optional[float] = None,
                         max_size: Optional[float] = None) -> Tuple[List[Dict], Dict, bool]:
        """
        Search for properties based on given criteria.
        
        Args:
            area: Preferred location/area
            property_type: Type of property (Apartment, Villa, etc.)
            min_budget: Minimum budget
            max_budget: Maximum budget
            configurations: BHK configuration (e.g., 2BHK, 3BHK)
            possession_date: Preferred possession date
            min_size: Minimum property size in sqft
            max_size: Maximum property size in sqft
            
        Returns:
            Tuple containing:
            - List of matching properties
            - Dictionary of feedback on which criteria were problematic
            - Boolean indicating if these are exact matches (True) or relaxed matches (False)
        """
        try:
            # Store the original criteria for feedback
            original_criteria = {
                'area': area,
                'property_type': property_type,
                'min_budget': min_budget,
                'max_budget': max_budget,
                'configurations': configurations,
                'possession_date': possession_date,
                'min_size': min_size,
                'max_size': max_size
            }
            
            # Make a copy of the DataFrame for filtering
            filtered_df = self.df.copy()
            
            # Apply each filter separately and track the count after each filter
            # This helps identify which criteria are too restrictive
            filter_counts = {'initial': len(filtered_df)}
            
            # Area filter
            if area:
                filtered_df = filtered_df[filtered_df['Area'].str.contains(area, case=False, na=False)]
                filter_counts['area'] = len(filtered_df)
            
            # Property type filter
            if property_type:
                filtered_df = filtered_df[filtered_df['PropertyType'].str.contains(property_type, case=False, na=False)]
                filter_counts['property_type'] = len(filtered_df)
            
            # Budget filters
            if min_budget and 'PricePersqft' in filtered_df.columns and 'MinSizeSqft' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['PricePerSqft'] * filtered_df['MinSizeSqft'] >= min_budget]
                filter_counts['min_budget'] = len(filtered_df)
            
            if max_budget and 'PricePersqft' in filtered_df.columns and 'MinSizeSqft' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['PricePerSqft'] * filtered_df['MinSizeSqft'] <= max_budget]
                filter_counts['max_budget'] = len(filtered_df)
            
            # Configuration filter
            if configurations:
                filtered_df = filtered_df[filtered_df['Configurations'].str.contains(configurations, case=False, na=False)]
                filter_counts['configurations'] = len(filtered_df)
            
            # Possession date filter
            if possession_date:
                filtered_df = filtered_df[filtered_df['PossessionDate'].str.contains(possession_date, case=False, na=False)]
                filter_counts['possession_date'] = len(filtered_df)
            
            # Size filters
            if min_size and 'MinSizeSqft' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['MinSizeSqft'] >= min_size]
                filter_counts['min_size'] = len(filtered_df)
            
            if max_size and 'MaxSizeSqft' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['MaxSizeSqft'] <= max_size]
                filter_counts['max_size'] = len(filtered_df)
            
            # Get top results (limit to 5 for readability)
            results = filtered_df.head(5).to_dict('records')
            
            # Analyze which criteria might be too restrictive
            feedback = self._analyze_filter_results(filter_counts, original_criteria)
            
            if not results:
                # If no exact matches, use alternative search strategies
                return self._alternative_search(area, property_type, min_budget, max_budget, configurations, 
                                              possession_date, min_size, max_size, filter_counts)
            
            # Format results for better readability
            formatted_results = self._format_property_results(results)
                
            return formatted_results, feedback, True
        except Exception as e:
            print(f"Error in search_properties: {e}")
            # Return an empty list if there's an error
            return [], {"error": str(e)}, False
    
    def _analyze_filter_results(self, filter_counts: Dict[str, int], 
                               original_criteria: Dict[str, Any]) -> Dict[str, str]:
        """
        Analyze the filter results to identify which criteria might be too restrictive.
        
        Args:
            filter_counts: Dictionary with counts after each filter
            original_criteria: The original search criteria
            
        Returns:
            Dictionary with feedback on each criterion
        """
        feedback = {}
        initial_count = filter_counts.get('initial', 0)
        
        # Skip 'initial' when looking for the most restrictive filter
        most_restrictive = None
        smallest_count = initial_count
        
        for criterion, count in filter_counts.items():
            if criterion != 'initial' and count < smallest_count:
                smallest_count = count
                most_restrictive = criterion
        
        # Generate specific feedback for each criterion
        for criterion, count in filter_counts.items():
            if criterion == 'initial':
                continue
                
            prev_count = initial_count
            # Find the previous filter to calculate drop percentage
            prev_keys = list(filter_counts.keys())
            current_index = prev_keys.index(criterion)
            if current_index > 0:
                prev_key = prev_keys[current_index - 1]
                prev_count = filter_counts[prev_key]
            
            # Calculate the percentage drop
            if prev_count > 0:
                drop_percentage = ((prev_count - count) / prev_count) * 100
            else:
                drop_percentage = 0
                
            # Generate specific feedback based on the drop
            if drop_percentage > 80:
                feedback[criterion] = f"highly restrictive (eliminated {drop_percentage:.1f}% of options)"
            elif drop_percentage > 50:
                feedback[criterion] = f"somewhat restrictive (eliminated {drop_percentage:.1f}% of options)"
            elif drop_percentage > 20:
                feedback[criterion] = f"slightly restrictive (eliminated {drop_percentage:.1f}% of options)"
        
        # Add a note about the most restrictive criterion
        if most_restrictive and smallest_count == 0:
            feedback['most_restrictive'] = most_restrictive
            
        return feedback
    
    def _alternative_search(self, area, property_type, min_budget, max_budget, 
                           configurations, possession_date, min_size, max_size,
                           filter_counts) -> Tuple[List[Dict], Dict, bool]:
        """
        Perform alternative searches when no exact matches are found.
        Tries different relaxation strategies based on the filter results.
        
        Returns:
            Tuple containing:
            - List of alternative properties
            - Dictionary of feedback
            - Boolean indicating these are relaxed matches (False)
        """
        feedback = {}
        
        # Strategy 1: If area filter exists and has matches, show properties just from that area
        if area and filter_counts.get('area', 0) > 0:
            area_df = self.df[self.df['Area'].str.contains(area, case=False, na=False)]
            if len(area_df) > 0:
                # Get a diverse sample of properties from this area
                area_results = self._get_diverse_sample(area_df, 5)
                formatted_results = self._format_property_results(area_results)
                
                feedback = {
                    "strategy": "area_only",
                    "message": f"Showing diverse properties in {area} as your other preferences couldn't be matched exactly."
                }
                
                # Determine which criteria need adjustment
                most_restrictive = filter_counts.get('most_restrictive', None)
                if most_restrictive:
                    feedback["adjustment_needed"] = most_restrictive
                    
                return formatted_results, feedback, False
                
        # Strategy 2: Relax budget constraints by 20%
        relaxed_min_budget = min_budget * 0.8 if min_budget else None
        relaxed_max_budget = max_budget * 1.2 if max_budget else None
        
        relaxed_results, relaxed_feedback, _ = self.search_properties(
            area=area,
            property_type=property_type,
            min_budget=relaxed_min_budget,
            max_budget=relaxed_max_budget,
            configurations=configurations,
            possession_date=possession_date,
            min_size=min_size,
            max_size=max_size
        )
        
        if relaxed_results:
            feedback = {
                "strategy": "relaxed_budget",
                "message": "Found properties by relaxing your budget constraints by 20%."
            }
            return relaxed_results, feedback, False
            
        # Strategy 3: If we have configuration but no matches, relax that
        if configurations and not relaxed_results:
            # For example, if they asked for 4BHK, we might also show 3BHK
            config_relaxed_results, _, _ = self.search_properties(
                area=area,
                property_type=property_type,
                min_budget=min_budget,
                max_budget=max_budget,
                configurations=None,  # Remove configuration constraint
                possession_date=possession_date,
                min_size=min_size,
                max_size=max_size
            )
            
            if config_relaxed_results:
                feedback = {
                    "strategy": "relaxed_configuration",
                    "message": f"Found properties by relaxing your {configurations} requirement."
                }
                return config_relaxed_results, feedback, False
        
        # Strategy 4: Last resort - show a random sample of properties
        sample_results = self._get_diverse_sample(self.df, 5)
        formatted_results = self._format_property_results(sample_results)
        
        feedback = {
            "strategy": "diverse_sample",
            "message": "Your preferences were very specific. Here's a diverse selection of properties to consider."
        }
        
        return formatted_results, feedback, False
    
    def _get_diverse_sample(self, df: pd.DataFrame, n: int = 5) -> List[Dict]:
        """
        Get a diverse sample of properties from the DataFrame.
        This tries to include properties with different characteristics.
        
        Args:
            df: DataFrame to sample from
            n: Number of properties to return
            
        Returns:
            List of diverse property records
        """
        if len(df) <= n:
            return df.to_dict('records')
        
        diverse_sample = []
        
        # Try to get properties from different areas
        if 'Area' in df.columns:
            areas = df['Area'].unique()
            for area in areas[:min(n, len(areas))]:
                area_props = df[df['Area'] == area].head(1).to_dict('records')
                if area_props:
                    diverse_sample.extend(area_props)
        
        # If we need more, try different property types
        if len(diverse_sample) < n and 'PropertyType' in df.columns:
            prop_types = df['PropertyType'].unique()
            for ptype in prop_types[:min(n-len(diverse_sample), len(prop_types))]:
                type_props = df[df['PropertyType'] == ptype].head(1).to_dict('records')
                if type_props:
                    diverse_sample.extend(type_props)
        
        # If we need more, try different configurations
        if len(diverse_sample) < n and 'Configurations' in df.columns:
            configs = df['Configurations'].unique()
            for config in configs[:min(n-len(diverse_sample), len(configs))]:
                config_props = df[df['Configurations'] == config].head(1).to_dict('records')
                if config_props:
                    diverse_sample.extend(config_props)
        
        # If we still need more, just get a random sample
        if len(diverse_sample) < n:
            remaining = n - len(diverse_sample)
            sample_props = df.sample(min(remaining, len(df))).to_dict('records')
            diverse_sample.extend(sample_props)
        
        # Ensure we don't return more than n properties
        return diverse_sample[:n]
    
    def _format_property_results(self, properties: List[Dict]) -> List[Dict]:
        """
        Format property results for display
        
        Args:
            properties: List of property dictionaries
            
        Returns:
            List of formatted property dictionaries
        """
        formatted_results = []
        for idx, prop in enumerate(properties, 1):
            # Calculate approximate total price
            min_size = prop.get('MinSizeSqft', 0)
            price_per_sqft = prop.get('PricePersqft', 0)
            if pd.isna(min_size) or pd.isna(price_per_sqft):
                approx_price = 0
            else:
                approx_price = price_per_sqft * min_size
            
            formatted_prop = {
                "id": idx,
                "name": prop.get('ProjectName', 'N/A'),
                "area": prop.get('Area', 'N/A'),
                "type": prop.get('PropertyType', 'N/A'),
                "configuration": prop.get('Configurations', 'N/A'),
                "size": f"{prop.get('MinSizeSqft', 0)} - {prop.get('MaxSizeSqft', 0)} sq.ft",
                "price_per_sqft": f"₹{prop.get('PricePerSqft', 0):,}",
                "approx_total_price": f"₹{approx_price:,.0f}",
                "possession_date": prop.get('PossessionDate', 'N/A')
            }
            formatted_results.append(formatted_prop)
        
        return formatted_results
    
    def relaxed_search(self, area=None, property_type=None, min_budget=None, 
                      max_budget=None, configurations=None) -> List[Dict]:
        """
        Perform a more relaxed search when no exact matches are found.
        (Legacy method, kept for backward compatibility)
        
        Args:
            area: Optional area/location
            property_type: Optional property type
            min_budget: Optional minimum budget
            max_budget: Optional maximum budget
            configurations: Optional BHK configuration
            
        Returns:
            List of properties that match relaxed criteria
        """
        results, _, _ = self._alternative_search(
            area, property_type, min_budget, max_budget, 
            configurations, None, None, None, {}
        )
        return results
    
    def get_unique_areas(self) -> List[str]:
        """Get list of all unique areas in the dataset"""
        try:
            return self.df['Area'].unique().tolist()
        except Exception as e:
            print(f"Error in get_unique_areas: {e}")
            return []
    
    def get_property_types(self) -> List[str]:
        """Get list of all property types"""
        try:
            return self.df['PropertyType'].unique().tolist()
        except Exception as e:
            print(f"Error in get_property_types: {e}")
            return []
    
    def get_configurations(self) -> List[str]:
        """Get list of all BHK configurations"""
        try:
            return self.df['Configurations'].unique().tolist()
        except Exception as e:
            print(f"Error in get_configurations: {e}")
            return []
    
    def get_price_range(self) -> Dict[str, float]:
        """Get min and max property prices"""
        try:
            if 'PricePersqft' in self.df.columns and 'MinSizeSqft' in self.df.columns and 'MaxSizeSqft' in self.df.columns:
                min_price = (self.df['PricePerSqft'] * self.df['MinSizeSqft']).min()
                max_price = (self.df['PricePerSqft'] * self.df['MaxSizeSqft']).max()
                
                # Handle NaN values
                if pd.isna(min_price):
                    min_price = 0
                if pd.isna(max_price):
                    max_price = 0
                    
                return {"min": min_price, "max": max_price}
            else:
                return {"min": 0, "max": 0}
        except Exception as e:
            print(f"Error in get_price_range: {e}")
            return {"min": 0, "max": 0}
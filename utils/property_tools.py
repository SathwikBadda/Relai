# utils/property_tools.py - Property search and filter functionality

import pandas as pd
from typing import List, Dict, Any, Optional

class PropertyRecommendationTools:
    """
    Tools for searching and filtering property data
    """
    def __init__(self, df: pd.DataFrame):
        """
        Initialize with property dataset
        
        Args:
            df: DataFrame containing property data
        """
        self.df = df
        
    def search_properties(self, 
                         area: Optional[str] = None,
                         property_type: Optional[str] = None, 
                         min_budget: Optional[float] = None,
                         max_budget: Optional[float] = None,
                         configurations: Optional[str] = None,
                         possession_date: Optional[str] = None,
                         min_size: Optional[float] = None,
                         max_size: Optional[float] = None) -> List[Dict]:
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
            List of matching properties
        """
        filtered_df = self.df.copy()
        
        # Apply filters if they are not None
        if area:
            filtered_df = filtered_df[filtered_df['Area'].str.contains(area, case=False, na=False)]
        
        if property_type:
            filtered_df = filtered_df[filtered_df['PropertyType'].str.contains(property_type, case=False, na=False)]
        
        # Use PricePersqft and MinSizeSqft to calculate total price
        if min_budget:
            # This is an approximation - adjust based on your actual pricing model
            filtered_df = filtered_df[filtered_df['PricePersqft'] * filtered_df['MinSizeSqft'] >= min_budget]
        
        if max_budget:
            filtered_df = filtered_df[filtered_df['PricePersqft'] * filtered_df['MinSizeSqft'] <= max_budget]
        
        if configurations:
            filtered_df = filtered_df[filtered_df['Configurations'].str.contains(configurations, case=False, na=False)]
        
        if possession_date:
            # This would need more sophisticated date handling based on your data
            filtered_df = filtered_df[filtered_df['PossessionDate'].str.contains(possession_date, case=False, na=False)]
        
        if min_size:
            filtered_df = filtered_df[filtered_df['MinSizeSqft'] >= min_size]
        
        if max_size:
            filtered_df = filtered_df[filtered_df['MaxSizeSqft'] <= max_size]
        
        # Get top results (limit to 5 for readability)
        results = filtered_df.head(5).to_dict('records')
        
        if not results:
            # If no exact matches, relax criteria
            return self.relaxed_search(area, property_type, min_budget, max_budget, configurations)
        
        # Format results for better readability
        formatted_results = []
        for idx, prop in enumerate(results, 1):
            # Calculate approximate total price
            approx_price = prop.get('PricePersqft', 0) * prop.get('MinSizeSqft', 0)
            
            formatted_prop = {
                "id": idx,
                "name": prop.get('ProjectName', 'N/A'),
                "area": prop.get('Area', 'N/A'),
                "type": prop.get('PropertyType', 'N/A'),
                "configuration": prop.get('Configurations', 'N/A'),
                "size": f"{prop.get('MinSizeSqft', 0)} - {prop.get('MaxSizeSqft', 0)} sq.ft",
                "price_per_sqft": f"₹{prop.get('PricePersqft', 0):,}",
                "approx_total_price": f"₹{approx_price:,.0f}",
                "possession_date": prop.get('PossessionDate', 'N/A')
            }
            formatted_results.append(formatted_prop)
            
        return formatted_results
    
    def relaxed_search(self, area=None, property_type=None, min_budget=None, 
                      max_budget=None, configurations=None) -> List[Dict]:
        """
        Perform a more relaxed search when no exact matches are found.
        
        Args:
            area: Optional area/location
            property_type: Optional property type
            min_budget: Optional minimum budget
            max_budget: Optional maximum budget
            configurations: Optional BHK configuration
            
        Returns:
            List of properties that match relaxed criteria
        """
        # Relax budget constraints by 15%
        if min_budget:
            min_budget = min_budget * 0.85
        if max_budget:
            max_budget = max_budget * 1.15
            
        # Try without area constraint if it was provided
        relaxed_df = self.df.copy()
        
        if property_type:
            relaxed_df = relaxed_df[relaxed_df['PropertyType'].str.contains(property_type, case=False, na=False)]
        
        if min_budget:
            relaxed_df = relaxed_df[relaxed_df['PricePersqft'] * relaxed_df['MinSizeSqft'] >= min_budget]
        
        if max_budget:
            relaxed_df = relaxed_df[relaxed_df['PricePersqft'] * relaxed_df['MinSizeSqft'] <= max_budget]
        
        if configurations:
            relaxed_df = relaxed_df[relaxed_df['Configurations'].str.contains(configurations, case=False, na=False)]
        
        results = relaxed_df.head(3).to_dict('records')
        
        # Format results
        formatted_results = []
        for idx, prop in enumerate(results, 1):
            approx_price = prop.get('PricePersqft', 0) * prop.get('MinSizeSqft', 0)
            
            formatted_prop = {
                "id": idx,
                "name": prop.get('ProjectName', 'N/A'),
                "area": prop.get('Area', 'N/A'),
                "type": prop.get('PropertyType', 'N/A'),
                "configuration": prop.get('Configurations', 'N/A'),
                "size": f"{prop.get('MinSizeSqft', 0)} - {prop.get('MaxSizeSqft', 0)} sq.ft",
                "price_per_sqft": f"₹{prop.get('PricePersqft', 0):,}",
                "approx_total_price": f"₹{approx_price:,.0f}",
                "possession_date": prop.get('PossessionDate', 'N/A')
            }
            formatted_results.append(formatted_prop)
            
        return formatted_results
    
    def get_unique_areas(self) -> List[str]:
        """Get list of all unique areas in the dataset"""
        return self.df['Area'].unique().tolist()
    
    def get_property_types(self) -> List[str]:
        """Get list of all property types"""
        return self.df['PropertyType'].unique().tolist()
    
    def get_configurations(self) -> List[str]:
        """Get list of all BHK configurations"""
        return self.df['Configurations'].unique().tolist()
    
    def get_price_range(self) -> Dict[str, float]:
        """Get min and max property prices"""
        min_price = (self.df['PricePersqft'] * self.df['MinSizeSqft']).min()
        max_price = (self.df['PricePersqft'] * self.df['MaxSizeSqft']).max()
        return {"min": min_price, "max": max_price}
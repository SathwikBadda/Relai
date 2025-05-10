# tests/test_property_tools.py - Tests for the property tools

import unittest
import os
import sys
import pandas as pd
import numpy as np

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.property_tools import PropertyRecommendationTools

class TestPropertyTools(unittest.TestCase):
    """Test cases for the PropertyRecommendationTools class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a sample DataFrame for testing
        self.test_data = pd.DataFrame({
            'ProjectName': ['Luxury Towers', 'Budget Homes', 'Mid-Range Villas', 'Premium Apartments', 'Economy Flats'],
            'PropertyType': ['Apartment', 'Apartment', 'Villa', 'Apartment', 'Apartment'],
            'Area': ['Gachibowli', 'Bachupally', 'Kondapur', 'Hitech City', 'Miyapur'],
            'PossessionDate': ['1/1/2025', '6/1/2025', '12/1/2024', '3/1/2026', '9/1/2025'],
            'TotalUnits': [100, 500, 50, 200, 300],
            'AreaSizeAcres': [5.0, 20.0, 10.0, 7.5, 15.0],
            'Configurations': ['3BHK, 4BHK', '1BHK, 2BHK', '3BHK, 4BHK, 5BHK', '2BHK, 3BHK, 4BHK', '1BHK, 2BHK'],
            'MinSizeSqft': [1500, 600, 2000, 1200, 500],
            'MaxSizeSqft': [2500, 1000, 3500, 2000, 900],
            'PricePersqft': [8000, 4000, 7000, 6000, 3500]
        })
        
        # Create PropertyRecommendationTools instance
        self.property_tools = PropertyRecommendationTools(self.test_data)
    
    def test_search_properties_area(self):
        """Test search by area"""
        results = self.property_tools.search_properties(area='Gachibowli')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], 'Luxury Towers')
        self.assertEqual(results[0]['area'], 'Gachibowli')
    
    def test_search_properties_type(self):
        """Test search by property type"""
        results = self.property_tools.search_properties(property_type='Villa')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], 'Mid-Range Villas')
        self.assertEqual(results[0]['type'], 'Villa')
    
    def test_search_properties_configuration(self):
        """Test search by configuration"""
        results = self.property_tools.search_properties(configurations='1BHK')
        self.assertEqual(len(results), 2)
        areas = [result['area'] for result in results]
        self.assertIn('Bachupally', areas)
        self.assertIn('Miyapur', areas)
    
    def test_search_properties_budget(self):
        """Test search by budget range"""
        # Search for properties between 3M and 5M (using PricePersqft * MinSizeSqft)
        min_budget = 3000000  # 3 million
        max_budget = 5000000  # 5 million
        
        results = self.property_tools.search_properties(
            min_budget=min_budget,
            max_budget=max_budget
        )
        
        # Verify results
        for result in results:
            # Extract numeric price from the formatted string
            price_str = result['approx_total_price']
            price_value = float(price_str.replace('₹', '').replace(',', ''))
            
            # Check if price is within range
            self.assertGreaterEqual(price_value, min_budget)
            self.assertLessEqual(price_value, max_budget)
    
    def test_search_properties_size(self):
        """Test search by property size"""
        results = self.property_tools.search_properties(
            min_size=1000,
            max_size=2000
        )
        
        # Check that all results are within size range
        for result in results:
            size_str = result['size']
            min_size = int(size_str.split(' - ')[0])
            max_size = int(size_str.split(' - ')[1].split(' ')[0])
            
            self.assertGreaterEqual(min_size, 1000)
            self.assertLessEqual(max_size, 2000)
    
    def test_search_properties_possession(self):
        """Test search by possession date"""
        results = self.property_tools.search_properties(possession_date='2025')
        
        # All results should have 2025 in possession date
        for result in results:
            self.assertIn('2025', result['possession_date'])
    
    def test_search_properties_combined(self):
        """Test search with multiple criteria"""
        results = self.property_tools.search_properties(
            area='Hitech City',
            configurations='3BHK',
            min_budget=7000000
        )
        
        # Should match Premium Apartments
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], 'Premium Apartments')
    
    def test_search_properties_no_match(self):
        """Test search with no matching results"""
        # Search for an impossible combination
        results = self.property_tools.search_properties(
            area='Gachibowli',
            property_type='Villa'
        )
        
        # Should return relaxed results
        self.assertTrue(len(results) > 0)
        
        # Check if results are from relaxed search (should include properties 
        # that match property_type='Villa' but not area='Gachibowli')
        villa_found = False
        for result in results:
            if result['type'] == 'Villa':
                villa_found = True
                break
        
        self.assertTrue(villa_found)
    
    def test_relaxed_search(self):
        """Test relaxed search functionality"""
        # Direct call to relaxed_search
        results = self.property_tools.relaxed_search(
            area='Unknown Area',  # Non-existent area
            property_type='Apartment',
            min_budget=5000000,
            max_budget=10000000
        )
        
        # Should still return some results by relaxing the area constraint
        self.assertTrue(len(results) > 0)
        
        # All results should be Apartments
        for result in results:
            self.assertEqual(result['type'], 'Apartment')
    
    def test_get_unique_areas(self):
        """Test getting unique areas"""
        areas = self.property_tools.get_unique_areas()
        
        # Check that all areas are in the result
        expected_areas = ['Gachibowli', 'Bachupally', 'Kondapur', 'Hitech City', 'Miyapur']
        for area in expected_areas:
            self.assertIn(area, areas)
        
        # Check that the count matches
        self.assertEqual(len(areas), len(expected_areas))
    
    def test_get_property_types(self):
        """Test getting property types"""
        property_types = self.property_tools.get_property_types()
        
        # Check that both property types are included
        self.assertIn('Apartment', property_types)
        self.assertIn('Villa', property_types)
        
        # Check count
        self.assertEqual(len(property_types), 2)
    
    def test_get_configurations(self):
        """Test getting configurations"""
        configurations = self.property_tools.get_configurations()
        
        # Check that the unique configurations are returned
        expected_configs = ['3BHK, 4BHK', '1BHK, 2BHK', '3BHK, 4BHK, 5BHK', '2BHK, 3BHK, 4BHK']
        for config in expected_configs:
            self.assertIn(config, configurations)
    
    def test_get_price_range(self):
        """Test getting price range"""
        price_range = self.property_tools.get_price_range()
        
        # Check min price (Economy Flats: 500 * 3500 = 1,750,000)
        expected_min = 500 * 3500
        self.assertEqual(price_range['min'], expected_min)
        
        # Check max price (Mid-Range Villas: 3500 * 7000 = 24,500,000)
        expected_max = 3500 * 7000
        self.assertEqual(price_range['max'], expected_max)
    
    def test_empty_dataframe(self):
        """Test with empty DataFrame"""
        empty_df = pd.DataFrame(columns=self.test_data.columns)
        empty_tools = PropertyRecommendationTools(empty_df)
        
        # Search should return empty list
        results = empty_tools.search_properties(area='Gachibowli')
        self.assertEqual(len(results), 0)
        
        # Price range should handle empty DataFrame gracefully
        price_range = empty_tools.get_price_range()
        self.assertTrue(np.isnan(price_range['min']) or price_range['min'] == 0)
        self.assertTrue(np.isnan(price_range['max']) or price_range['max'] == 0)

if __name__ == '__main__':
    unittest.main()
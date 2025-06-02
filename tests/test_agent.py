# tests/test_agent.py - Tests for the agent functionality

import unittest
import os
import sys
import pandas as pd
from unittest.mock import MagicMock, patch

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from realestate_agent import create_real_estate_agent
from utils.property_tools import PropertyRecommendationTools

class TestRealEstateAgent(unittest.TestCase):
    """Test cases for the real estate agent"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a sample DataFrame for testing
        self.test_data = pd.DataFrame({
            'ProjectName': ['Test Project 1', 'Test Project 2', 'Test Project 3'],
            'PropertyType': ['Apartment', 'Villa', 'Apartment'],
            'Area': ['Gachibowli', 'Kondapur', 'Hitech City'],
            'PossessionDate': ['1/1/2025', '6/1/2025', '12/1/2024'],
            'TotalUnits': [100, 50, 200],
            'AreaSizeAcres': [5.0, 10.0, 7.5],
            'Configurations': ['2BHK, 3BHK', '3BHK, 4BHK', '2BHK, 3BHK, 4BHK'],
            'MinSizeSqft': [1000, 1500, 1200],
            'MaxSizeSqft': [1500, 2500, 2000],
            'PricePerSqft': [5000, 7000, 6000]
        })
        
        # Create property tools
        self.property_tools = PropertyRecommendationTools(self.test_data)
    
    @patch('langchain_openai.ChatOpenAI')
    def test_agent_creation(self, mock_chat_openai):
        """Test that agent can be created without errors"""
        # Mock the ChatOpenAI class
        mock_chat_instance = MagicMock()
        mock_chat_openai.return_value = mock_chat_instance
        
        # Create the agent
        agent = create_real_estate_agent(self.property_tools)
        
        # Assert that agent is created successfully
        self.assertIsNotNone(agent)
    
    def test_property_search(self):
        """Test property search functionality"""
        # Test search with area filter
        results = self.property_tools.search_properties(area="Gachibowli")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["area"], "Gachibowli")
        
        # Test search with property type filter
        results = self.property_tools.search_properties(property_type="Villa")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["type"], "Villa")
        
        # Test search with configuration filter
        results = self.property_tools.search_properties(configurations="4BHK")
        self.assertEqual(len(results), 2)  # Both Villa and one Apartment have 4BHK
        
        # Test search with min budget filter
        results = self.property_tools.search_properties(min_budget=6000000)  # 6000 * 1000
        self.assertEqual(len(results), 2)  # Two properties above this budget
        
        # Test search with no results
        results = self.property_tools.search_properties(area="Unknown Area")
        # Should return relaxed search results instead
        self.assertTrue(len(results) > 0)
    
    def test_get_unique_areas(self):
        """Test getting unique areas"""
        areas = self.property_tools.get_unique_areas()
        self.assertEqual(len(areas), 3)
        self.assertIn("Gachibowli", areas)
        self.assertIn("Kondapur", areas)
        self.assertIn("Hitech City", areas)
    
    def test_get_property_types(self):
        """Test getting property types"""
        property_types = self.property_tools.get_property_types()
        self.assertEqual(len(property_types), 2)
        self.assertIn("Apartment", property_types)
        self.assertIn("Villa", property_types)
    
    def test_get_configurations(self):
        """Test getting configurations"""
        configs = self.property_tools.get_configurations()
        self.assertEqual(len(configs), 3)
        
    def test_get_price_range(self):
        """Test getting price range"""
        price_range = self.property_tools.get_price_range()
        self.assertIn("min", price_range)
        self.assertIn("max", price_range)
        # Min price should be MinSizeSqft * PricePersqft for the cheapest property
        expected_min = 1000 * 5000  # From Test Project 1
        self.assertEqual(price_range["min"], expected_min)

if __name__ == '__main__':
    unittest.main()
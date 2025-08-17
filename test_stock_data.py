#!/usr/bin/env python3
"""
Unit tests for StockData class using real JSON test data.

Run with: python test_stock_data.py
"""

import unittest
import json
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from stock_data import StockData, StockDataCollection


class TestStockData(unittest.TestCase):
    """Unit tests for StockData class"""
    
    @classmethod
    def setUpClass(cls):
        """Load test data from JSON files"""
        cls.test_data_dir = project_root / "test_data"
        cls.test_stocks = {}
        
        # Load test data for Japanese stocks
        symbols = ["8194.T", "9699.T", "9715.T"]
        
        for symbol in symbols:
            info_files = list(cls.test_data_dir.glob(f"{symbol}_*_info.json"))
            if info_files:
                with open(info_files[0], 'r', encoding='utf-8') as f:
                    info_data = json.load(f)
                    cls.test_stocks[symbol] = info_data
    
    def create_stock_from_test_data(self, symbol: str) -> StockData:
        """Create StockData object from test JSON data"""
        test_data = self.test_stocks[symbol]
        info = test_data['info']
        
        return StockData(
            symbol=symbol,
            price=info.get('currentPrice') or info.get('regularMarketPrice'),
            eps=info.get('trailingEps'),
            bps=info.get('bookValue'),
            name=info.get('shortName') or info.get('longName'),
            dividend_yield=info.get('dividendYield'),
            info=info
        )
    
    def test_basic_properties(self):
        """Test basic property access methods"""
        stock = self.create_stock_from_test_data("8194.T")
        
        # Test basic properties
        self.assertEqual(stock.symbol(), "8194.T")
        self.assertIsNotNone(stock.price())
        self.assertIsNotNone(stock.eps())
        self.assertIsNotNone(stock.bps())
        self.assertIsNotNone(stock.company_name())
        
        # Test specific values from known test data (LIFE CORPORATION)
        self.assertIn("LIFE", stock.company_name())
        self.assertGreater(stock.price(), 2000)  # Should be around 2458
        self.assertGreater(stock.eps(), 200)     # Should be around 207.7
        self.assertGreater(stock.bps(), 1600)    # Should be around 1633.747
    
    def test_financial_metrics(self):
        """Test calculated financial metrics"""
        stock = self.create_stock_from_test_data("8194.T")
        
        # Test earnings yield calculation
        earnings_yield = stock.earnings_yield()
        self.assertIsNotNone(earnings_yield)
        self.assertGreater(earnings_yield, 0)
        
        # Manual calculation check
        expected_earnings_yield = (stock.eps() / stock.price()) * 100
        self.assertAlmostEqual(earnings_yield, expected_earnings_yield, places=2)
        
        # Test BPR calculation
        bpr = stock.bpr()
        self.assertIsNotNone(bpr)
        self.assertGreater(bpr, 0)
        
        # Manual calculation check
        expected_bpr = (stock.bps() / stock.price()) * 100
        self.assertAlmostEqual(bpr, expected_bpr, places=2)
    
    def test_formatting_methods(self):
        """Test formatting methods"""
        stock = self.create_stock_from_test_data("8194.T")
        
        # Test price formatting
        formatted_price = stock.format_price()
        self.assertTrue(formatted_price.startswith("¥"))
        self.assertIn(",", formatted_price)  # Should have thousands separator
        
        # Test percentage formatting
        earnings_yield_str = stock.format_earnings_yield()
        self.assertTrue(earnings_yield_str.endswith("%"))
        
        bpr_str = stock.format_bpr()
        self.assertTrue(bpr_str.endswith("%"))
    
    def test_company_information(self):
        """Test company information methods"""
        stock = self.create_stock_from_test_data("8194.T")
        
        # Test business information
        self.assertIsNotNone(stock.sector())
        self.assertIsNotNone(stock.industry())
        self.assertEqual(stock.country(), "Japan")
        self.assertIsNotNone(stock.currency())
        
        # Test specific values from test data
        self.assertIn("Consumer", stock.sector())  # Consumer Defensive
        self.assertIn("Grocery", stock.industry()) # Grocery Stores
    
    def test_data_quality_methods(self):
        """Test data quality assessment methods"""
        stock = self.create_stock_from_test_data("8194.T")
        
        # Test validity
        self.assertTrue(stock.is_valid())
        self.assertTrue(stock.has_financial_data())
        
        # Test completeness score
        completeness = stock.completeness_score()
        self.assertGreater(completeness, 0.5)  # Should have most data
        self.assertLessEqual(completeness, 1.0)
    
    def test_multiple_stocks(self):
        """Test with multiple stock symbols"""
        symbols = ["8194.T", "9699.T", "9715.T"]
        stocks = []
        
        for symbol in symbols:
            if symbol in self.test_stocks:
                stock = self.create_stock_from_test_data(symbol)
                stocks.append(stock)
        
        # Test that we have multiple stocks
        self.assertGreater(len(stocks), 1)
        
        # Test that all stocks have different symbols
        stock_symbols = [stock.symbol() for stock in stocks]
        self.assertEqual(len(stock_symbols), len(set(stock_symbols)))
        
        # Test that all stocks have valid data
        for stock in stocks:
            self.assertTrue(stock.is_valid())
            self.assertIsNotNone(stock.price())
    
    def test_to_dict_conversion(self):
        """Test dictionary conversion for display"""
        stock = self.create_stock_from_test_data("8194.T")
        
        stock_dict = stock.to_dict()
        
        # Test required keys
        required_keys = ["銘柄コード", "銘柄名", "株価", "EPS", "BPS", 
                        "株式益利回り (%)", "株式純資産利回り (%)", "配当利回り (%)"]
        
        for key in required_keys:
            self.assertIn(key, stock_dict)
        
        # Test values
        self.assertEqual(stock_dict["銘柄コード"], "8194.T")
        self.assertNotEqual(stock_dict["銘柄名"], "N/A")
        self.assertTrue(stock_dict["株価"].startswith("¥"))


class TestStockDataCollection(unittest.TestCase):
    """Unit tests for StockDataCollection class"""
    
    @classmethod
    def setUpClass(cls):
        """Load test data"""
        cls.test_data_dir = Path(__file__).parent / "test_data"
        cls.test_stocks = {}
        
        symbols = ["8194.T", "9699.T", "9715.T"]
        for symbol in symbols:
            info_files = list(cls.test_data_dir.glob(f"{symbol}_*_info.json"))
            if info_files:
                with open(info_files[0], 'r', encoding='utf-8') as f:
                    info_data = json.load(f)
                    cls.test_stocks[symbol] = info_data
    
    def create_test_collection(self) -> StockDataCollection:
        """Create collection with test data"""
        collection = StockDataCollection()
        
        for symbol, test_data in self.test_stocks.items():
            info = test_data['info']
            stock = StockData(
                symbol=symbol,
                price=info.get('currentPrice') or info.get('regularMarketPrice'),
                eps=info.get('trailingEps'),
                bps=info.get('bookValue'),
                name=info.get('shortName') or info.get('longName'),
                dividend_yield=info.get('dividendYield'),
                info=info
            )
            collection.add(stock)
        
        return collection
    
    def test_collection_operations(self):
        """Test collection operations"""
        collection = self.create_test_collection()
        
        # Test length
        self.assertGreater(len(collection), 0)
        
        # Test symbols
        symbols = collection.symbols()
        self.assertIn("8194.T", symbols)
        
        # Test get by symbol
        stock = collection.get_by_symbol("8194.T")
        self.assertIsNotNone(stock)
        self.assertEqual(stock.symbol(), "8194.T")
        
        # Test valid stocks
        valid_stocks = collection.valid_stocks()
        self.assertEqual(len(valid_stocks), len(collection))
    
    def test_collection_analytics(self):
        """Test collection analytics"""
        collection = self.create_test_collection()
        
        # Test average earnings yield
        avg_earnings_yield = collection.average_earnings_yield()
        self.assertIsNotNone(avg_earnings_yield)
        self.assertGreater(avg_earnings_yield, 0)
    
    def test_dataframe_conversion(self):
        """Test DataFrame conversion"""
        collection = self.create_test_collection()
        
        df = collection.to_dataframe()
        self.assertGreater(len(df), 0)
        self.assertIn("銘柄コード", df.columns)
        self.assertIn("銘柄名", df.columns)


class TestRealWorldScenarios(unittest.TestCase):
    """Test real-world usage scenarios"""
    
    @classmethod
    def setUpClass(cls):
        """Load test data"""
        cls.test_data_dir = Path(__file__).parent / "test_data"
        cls.test_stocks = {}
        
        symbols = ["8194.T", "9699.T", "9715.T"]
        for symbol in symbols:
            info_files = list(cls.test_data_dir.glob(f"{symbol}_*_info.json"))
            if info_files:
                with open(info_files[0], 'r', encoding='utf-8') as f:
                    info_data = json.load(f)
                    cls.test_stocks[symbol] = info_data
    
    def test_stock_comparison(self):
        """Test comparing multiple stocks"""
        stocks = []
        
        for symbol, test_data in self.test_stocks.items():
            info = test_data['info']
            stock = StockData(
                symbol=symbol,
                price=info.get('currentPrice') or info.get('regularMarketPrice'),
                eps=info.get('trailingEps'),
                bps=info.get('bookValue'),
                name=info.get('shortName') or info.get('longName'),
                dividend_yield=info.get('dividendYield'),
                info=info
            )
            stocks.append(stock)
        
        # Compare earnings yields
        earnings_yields = [stock.earnings_yield() for stock in stocks if stock.earnings_yield()]
        self.assertGreater(len(earnings_yields), 1)
        
        # Find best earnings yield
        best_stock = max(stocks, key=lambda s: s.earnings_yield() or 0)
        self.assertIsNotNone(best_stock)
    
    def test_portfolio_analysis(self):
        """Test portfolio-style analysis"""
        collection = StockDataCollection()
        
        for symbol, test_data in self.test_stocks.items():
            info = test_data['info']
            stock = StockData(
                symbol=symbol,
                price=info.get('currentPrice') or info.get('regularMarketPrice'),
                eps=info.get('trailingEps'), 
                bps=info.get('bookValue'),
                name=info.get('shortName') or info.get('longName'),
                dividend_yield=info.get('dividendYield'),
                info=info
            )
            collection.add(stock)
        
        # Portfolio metrics
        total_stocks = len(collection)
        valid_stocks = len(collection.valid_stocks())
        avg_earnings_yield = collection.average_earnings_yield()
        
        self.assertGreater(total_stocks, 0)
        self.assertEqual(valid_stocks, total_stocks)
        self.assertIsNotNone(avg_earnings_yield)


def run_tests():
    """Run all tests with detailed output"""
    print("🧪 Running StockData Unit Tests...")
    print("=" * 50)
    
    # Check if test data exists
    test_data_dir = Path(__file__).parent / "test_data"
    if not test_data_dir.exists():
        print("❌ Error: test_data directory not found!")
        print("Please run: python fetch_test_data.py --symbols 8194.T,9699.T,9715.T")
        return False
    
    # Check for required test files
    symbols = ["8194.T", "9699.T", "9715.T"]
    missing_files = []
    
    for symbol in symbols:
        info_files = list(test_data_dir.glob(f"{symbol}_*_info.json"))
        if not info_files:
            missing_files.append(f"{symbol}_*_info.json")
    
    if missing_files:
        print(f"❌ Missing test data files: {missing_files}")
        print("Please run: python fetch_test_data.py --symbols 8194.T,9699.T,9715.T")
        return False
    
    # Run tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestStockData))
    suite.addTests(loader.loadTestsFromTestCase(TestStockDataCollection))
    suite.addTests(loader.loadTestsFromTestCase(TestRealWorldScenarios))
    
    # Run with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print(f"✅ All tests passed! ({result.testsRun} tests)")
        return True
    else:
        print(f"❌ {len(result.failures + result.errors)} test(s) failed out of {result.testsRun}")
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
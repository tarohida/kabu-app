"""
Stock Data Classes

Provides object-oriented interface for stock data with method-based parameter access.
"""

import pandas as pd
from typing import Optional, Dict, Any


class StockData:
    """
    Stock data class with method-based parameter access.
    
    Encapsulates all stock information and provides clean interface for accessing
    financial metrics through methods.
    """
    
    def __init__(self, 
                 symbol: str,
                 price: Optional[float] = None,
                 eps: Optional[float] = None, 
                 bps: Optional[float] = None,
                 name: Optional[str] = None,
                 dividend_yield: Optional[float] = None,
                 info: Optional[Dict[str, Any]] = None,
                 history: Optional[pd.DataFrame] = None,
                 debug_info: Optional[Dict[str, Any]] = None):
        """
        Initialize StockData object.
        
        Args:
            symbol: Stock symbol (e.g., "8194.T", "AAPL")
            price: Current stock price
            eps: Earnings per share (trailing)
            bps: Book value per share
            name: Company name
            dividend_yield: Dividend yield (as decimal, e.g., 0.025 for 2.5%)
            info: Raw info data from yfinance
            history: Historical price data
            debug_info: Debug information from data fetching
        """
        self._symbol = symbol
        self._price = price
        self._eps = eps
        self._bps = bps
        self._name = name
        self._dividend_yield = dividend_yield
        self._info = info or {}
        self._history = history
        self._debug_info = debug_info or {}
        
        # Calculated fields cache
        self._earnings_yield = None
        self._bpr = None
        self._dividend_yield_percent = None
        self._dividend_per_year = None
    
    # Basic Properties
    def symbol(self) -> str:
        """Get stock symbol"""
        return self._symbol
    
    def price(self) -> Optional[float]:
        """Get current stock price"""
        return self._price
    
    def eps(self) -> Optional[float]:
        """Get earnings per share (trailing)"""
        return self._eps
    
    def forward_eps(self) -> Optional[float]:
        """Get forward earnings per share"""
        return self._info.get('forwardEps')
    
    def bps(self) -> Optional[float]:
        """Get book value per share"""
        return self._bps
    
    def company_name(self) -> Optional[str]:
        """Get company name"""
        return self._name
    
    # Calculated Financial Metrics
    def earnings_yield(self) -> Optional[float]:
        """Calculate earnings yield as percentage (1/PER * 100)"""
        if self._earnings_yield is None:
            per = self.pe_ratio()
            if per is not None and per != 0:
                self._earnings_yield = (1 / per) * 100
            elif self._price and self._eps and self._price != 0:
                # Fallback to direct calculation if PER not available
                self._earnings_yield = (self._eps / self._price) * 100
        return self._earnings_yield
    
    def forward_earnings_yield(self) -> Optional[float]:
        """Calculate forward earnings yield as percentage (1/Forward PER * 100)"""
        forward_per = self.forward_pe_ratio()
        if forward_per is not None and forward_per != 0:
            return (1 / forward_per) * 100
        else:
            # Fallback to direct calculation if Forward PER not available
            forward_eps = self.forward_eps()
            if self._price and forward_eps and self._price != 0:
                return (forward_eps / self._price) * 100
        return None
    
    def current_year_earnings_yield(self) -> Optional[float]:
        """Calculate current year earnings yield (今期決算時)"""
        # Use trailing EPS as current year (most recent full year)
        return self.earnings_yield()
    
    def next_year_earnings_yield(self) -> Optional[float]:
        """Calculate next year earnings yield (次期決算時) - 予想PERベース"""
        # Use forward EPS as next year estimate
        return self.forward_earnings_yield()
    
    def next_year_earnings_yield_market_cap_based(self) -> Optional[float]:
        """Calculate next year earnings yield based on market cap (時価総額ベース)"""
        market_cap = self.market_cap()
        predicted_net_income = self._get_predicted_net_income()
        
        if market_cap and predicted_net_income and market_cap != 0:
            return (predicted_net_income / market_cap) * 100
        return None
    
    def _get_predicted_net_income(self) -> Optional[float]:
        """Get predicted net income from forward EPS and shares outstanding"""
        forward_eps = self.forward_eps()
        shares_outstanding = self.shares_outstanding()
        
        if forward_eps and shares_outstanding:
            return forward_eps * shares_outstanding
        return None
    
    def net_income_actual(self) -> Optional[float]:
        """Get actual net income (trailing EPS × shares outstanding)"""
        trailing_eps = self.eps()
        shares_outstanding = self.shares_outstanding()
        
        if trailing_eps and shares_outstanding:
            return trailing_eps * shares_outstanding
        return None
    
    def net_income_predicted(self) -> Optional[float]:
        """Get predicted net income (forward EPS × shares outstanding)"""
        return self._get_predicted_net_income()
    
    def bpr(self) -> Optional[float]:
        """Calculate book-to-price ratio as percentage (BPS/Price * 100)"""
        if self._bpr is None:
            if self._price and self._bps and self._price != 0:
                self._bpr = (self._bps / self._price) * 100
        return self._bpr
    
    def dividend_yield_percent(self) -> Optional[float]:
        """
        Get dividend yield as percentage
        
        Yahoo Finance API Data Format:
        - dividendYield: Already in percentage format (e.g., 2.6 for 2.6%)
        - NOT in decimal format (i.e., not 0.026 for 2.6%)
        - Confirmed by observing actual API responses showing values like 2.60 instead of 0.026
        """
        if self._dividend_yield_percent is None:
            if self._dividend_yield is not None:
                # Yahoo Finance returns dividend yield already as percentage (e.g., 2.6 for 2.6%)
                # So we use the value directly without multiplication
                self._dividend_yield_percent = self._dividend_yield
        return self._dividend_yield_percent
    
    def dividend_per_year(self) -> Optional[float]:
        """
        Get annual dividend per share
        
        Yahoo Finance API Data Format:
        - dividendRate: Annual dividend amount in currency units (e.g., 1.20 for $1.20)
        - dividendYield: Already in percentage format (e.g., 2.6 for 2.6%)
        
        Fallback calculation: dividendYield(%) × price = annual dividend
        Note: dividendYield is already percentage, so direct multiplication with price
        """
        if self._dividend_per_year is None:
            # Try to get from info data
            dividend_rate = self._info.get('dividendRate')
            if dividend_rate is not None:
                self._dividend_per_year = dividend_rate
            elif self._dividend_yield and self._price:
                # Calculate from dividend yield (dividendYield is already in percentage format)
                # Formula: (dividendYield% ÷ 100) × price = annual dividend
                self._dividend_per_year = (self._dividend_yield / 100) * self._price
        return self._dividend_per_year
    
    # Market Cap and Valuation Metrics
    def market_cap(self) -> Optional[int]:
        """Get market capitalization"""
        return self._info.get('marketCap')
    
    def shares_outstanding(self) -> Optional[int]:
        """Get shares outstanding"""
        return self._info.get('sharesOutstanding')
    
    def pe_ratio(self) -> Optional[float]:
        """Get P/E ratio (trailing)"""
        return self._info.get('trailingPE')
    
    def forward_pe_ratio(self) -> Optional[float]:
        """Get forward P/E ratio"""
        return self._info.get('forwardPE')
    
    def price_to_book(self) -> Optional[float]:
        """Get price-to-book ratio"""
        return self._info.get('priceToBook')
    
    # Business Information
    def sector(self) -> Optional[str]:
        """Get business sector"""
        return self._info.get('sector')
    
    def industry(self) -> Optional[str]:
        """Get industry"""
        return self._info.get('industry')
    
    def country(self) -> Optional[str]:
        """Get country"""
        return self._info.get('country')
    
    def currency(self) -> Optional[str]:
        """Get trading currency"""
        return self._info.get('currency')
    
    def website(self) -> Optional[str]:
        """Get company website"""
        return self._info.get('website')
    
    def business_summary(self) -> Optional[str]:
        """Get business summary"""
        return self._info.get('longBusinessSummary')
    
    def employees(self) -> Optional[int]:
        """Get number of full-time employees"""
        return self._info.get('fullTimeEmployees')
    
    # Price History Methods
    def price_history(self, days: int = 5) -> Optional[pd.DataFrame]:
        """Get price history for specified days"""
        if self._history is not None and not self._history.empty:
            return self._history.tail(days) if days > 0 else self._history
        return None
    
    def price_change_1d(self) -> Optional[float]:
        """Get 1-day price change percentage"""
        hist = self.price_history(2)
        if hist is not None and len(hist) >= 2:
            prev_price = hist['Close'].iloc[-2]
            curr_price = hist['Close'].iloc[-1]
            if prev_price != 0:
                return ((curr_price - prev_price) / prev_price) * 100
        return None
    
    def high_52w(self) -> Optional[float]:
        """Get 52-week high"""
        return self._info.get('fiftyTwoWeekHigh')
    
    def low_52w(self) -> Optional[float]:
        """Get 52-week low"""
        return self._info.get('fiftyTwoWeekLow')
    
    # Data Quality Methods
    def is_valid(self) -> bool:
        """Check if stock data contains minimum required information"""
        return self._price is not None and self._symbol is not None
    
    def has_financial_data(self) -> bool:
        """Check if financial data (EPS, BPS) is available"""
        return self._eps is not None and self._bps is not None
    
    def completeness_score(self) -> float:
        """Get data completeness score (0.0 to 1.0)"""
        fields = [
            self._price, self._eps, self._bps, self._name,
            self._dividend_yield, self.market_cap(), self.sector()
        ]
        available = sum(1 for field in fields if field is not None)
        return available / len(fields)
    
    # Debug and Raw Data Access
    def debug_info(self) -> Dict[str, Any]:
        """Get debug information from data fetching"""
        return self._debug_info
    
    def raw_info(self) -> Dict[str, Any]:
        """Get raw info data"""
        return self._info
    
    def data_source(self) -> str:
        """Get data source information"""
        if self._debug_info.get('attempts'):
            for attempt in self._debug_info['attempts']:
                if attempt.get('history_result', {}).get('source') == 'test_data':
                    return 'test_data'
        return 'yahoo_finance'
    
    # Formatting Methods
    def format_price(self, currency_symbol: str = "¥") -> str:
        """Format price with currency symbol"""
        if self._price is not None:
            return f"{currency_symbol}{self._price:,.0f}"
        return "N/A"
    
    def format_percentage(self, value: Optional[float], precision: int = 2) -> str:
        """Format percentage value"""
        if value is not None:
            return f"{value:.{precision}f}%"
        return "N/A"
    
    def format_earnings_yield(self, precision: int = 2) -> str:
        """Format earnings yield as percentage"""
        return self.format_percentage(self.earnings_yield(), precision)
    
    def format_current_year_earnings_yield(self, precision: int = 2) -> str:
        """Format current year earnings yield as percentage"""
        return self.format_percentage(self.current_year_earnings_yield(), precision)
    
    def format_next_year_earnings_yield(self, precision: int = 2) -> str:
        """Format next year earnings yield as percentage (予想PERベース)"""
        return self.format_percentage(self.next_year_earnings_yield(), precision)
    
    def format_next_year_earnings_yield_market_cap_based(self, precision: int = 2) -> str:
        """Format next year earnings yield as percentage (時価総額ベース)"""
        return self.format_percentage(self.next_year_earnings_yield_market_cap_based(), precision)
    
    def format_bpr(self, precision: int = 2) -> str:
        """Format BPR as percentage"""
        return self.format_percentage(self.bpr(), precision)
    
    def format_dividend_yield(self, precision: int = 2) -> str:
        """Format dividend yield as percentage"""
        return self.format_percentage(self.dividend_yield_percent(), precision)
    
    # String Representation
    def __str__(self) -> str:
        return f"StockData({self._symbol}: {self.format_price()})"
    
    def __repr__(self) -> str:
        return (f"StockData(symbol='{self._symbol}', price={self._price}, "
                f"eps={self._eps}, bps={self._bps}, name='{self._name}')")
    
    # Dictionary Conversion (for backward compatibility)
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for display"""
        return {
            "銘柄コード": self.symbol(),
            "銘柄名": self.company_name() or "N/A",
            "株価": self.format_price(),
            "今期決算時益利回り (%)": self.format_current_year_earnings_yield(),
            "次期益利回り(予想PER) (%)": self.format_next_year_earnings_yield(),
            "次期益利回り(時価総額) (%)": self.format_next_year_earnings_yield_market_cap_based(),
            "PER": self.pe_ratio(),
            "予想PER": self.forward_pe_ratio(),
            "時価総額": self.market_cap(),
            "発行済み株式数": self.shares_outstanding(),
            "純利益実績": self.net_income_actual(),
            "純利益見込み": self.net_income_predicted(),
            "EPS": self._eps,
            "Forward EPS": self.forward_eps(),
            "配当利回り (%)": self.format_dividend_yield(),
            "年あたり配当 (円)": self.dividend_per_year(),
            "株式純資産利回り (%)": self.format_bpr(),
            "BPS": self._bps,
            "セクター": self.sector(),
            "業界": self.industry(),
            "国": self.country(),
            "データソース": self.data_source()
        }


class StockDataCollection:
    """
    Collection of StockData objects with batch operations.
    """
    
    def __init__(self, stocks: list[StockData] = None):
        self._stocks = stocks or []
    
    def add(self, stock: StockData) -> None:
        """Add stock to collection"""
        self._stocks.append(stock)
    
    def get_by_symbol(self, symbol: str) -> Optional[StockData]:
        """Get stock by symbol"""
        for stock in self._stocks:
            if stock.symbol() == symbol:
                return stock
        return None
    
    def symbols(self) -> list[str]:
        """Get all symbols in collection"""
        return [stock.symbol() for stock in self._stocks]
    
    def valid_stocks(self) -> list[StockData]:
        """Get only stocks with valid data"""
        return [stock for stock in self._stocks if stock.is_valid()]
    
    def stocks_with_financials(self) -> list[StockData]:
        """Get stocks with complete financial data"""
        return [stock for stock in self._stocks if stock.has_financial_data()]
    
    def average_earnings_yield(self) -> Optional[float]:
        """Calculate average earnings yield of collection"""
        valid_yields = [stock.earnings_yield() for stock in self._stocks 
                       if stock.earnings_yield() is not None]
        return sum(valid_yields) / len(valid_yields) if valid_yields else None
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert collection to pandas DataFrame for display"""
        data = [stock.to_dict() for stock in self._stocks]
        return pd.DataFrame(data)
    
    def __len__(self) -> int:
        return len(self._stocks)
    
    def __iter__(self):
        return iter(self._stocks)
    
    def __getitem__(self, index):
        return self._stocks[index]
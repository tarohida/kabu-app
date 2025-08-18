# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Japanese stock analysis Streamlit application that displays earnings yield and book-to-price ratio (BPR) for Japanese stocks using the yfinance library. The application uses dependency injection architecture for data providers and object-oriented design for stock data representation.

## Development Commands

**Run the application:**
```bash
streamlit run app.py
```

**Run unit tests:**
```bash
python test_stock_data.py
```

**Install dependencies (manual):**
Dependencies are managed via virtual environment. Key requirements:
- streamlit
- yfinance 
- pandas
- numpy

**Activate virtual environment:**
```bash
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

## Architecture Overview

### Core Components

1. **app.py** - Main Streamlit application with dependency injection pattern
   - `YahooFinanceProvider` - Live Yahoo Finance API data fetching with retry logic
   - `TestDataProvider` - JSON file-based test data provider
   - `StockDataProvider` - Abstract interface for data providers

2. **stock_data.py** - Object-oriented data models
   - `StockData` - Individual stock with method-based parameter access
   - `StockDataCollection` - Batch operations on multiple stocks

3. **fetch_test_data.py** - CLI tool for test data management
4. **test_stock_data.py** - Comprehensive unit tests using real JSON test data

### Data Provider Pattern

The application uses dependency injection to switch between live API and test data:
- Runtime provider selection via Streamlit sidebar
- Cached data providers in session state
- Unified `StockData` object returned by all providers
- Test data automatically loaded from `test_data/` directory

### StockData Class Design

All stock information accessed through methods, not direct attributes:
- Basic properties: `symbol()`, `price()`, `eps()`, `bps()`, `company_name()`
- Calculated metrics: `earnings_yield()`, `bpr()`, `dividend_yield_percent()`
- Formatting methods: `format_price()`, `format_earnings_yield()`, `format_bpr()`
- Data quality: `is_valid()`, `has_financial_data()`, `completeness_score()`

## Key Dependencies

- **streamlit:** Web application framework
- **yfinance:** Yahoo Finance API client with rate limiting issues
- **pandas:** Data manipulation and JSON timestamp handling
- **numpy:** Numeric computations

## Stock Symbol Format

- Japanese stocks: Use `.T` suffix (e.g., `8194.T`, `9699.T`, `7203.T`)
- US stocks: Use standard symbols (e.g., `AAPL`, `MSFT`)
- Default symbols are pre-configured Japanese stocks

## Test Data Management

**Fetch test data (recommended before development):**
```bash
# Default Japanese stocks (8194.T, 9699.T, 9715.T)
python fetch_test_data.py

# Custom symbols
python fetch_test_data.py --symbols AAPL,MSFT,GOOGL

# Custom period and delay
python fetch_test_data.py --period 1mo --delay 10

# Clean old files only
python fetch_test_data.py --clean-only

# See all options
python fetch_test_data.py --help
```

**Generated test files:**
- `test_data/{symbol}_YYYYMMDD_HHMMSS_history.json` - Price history data
- `test_data/{symbol}_YYYYMMDD_HHMMSS_info.json` - Company information

**File deduplication:**
The app automatically prevents duplicate test files by checking for existing files before saving new ones.

**Using test data:**
In the Streamlit app, select "テストデータ" from the sidebar to use saved data instead of live API calls.

## Yahoo Finance API Challenges

- **Rate limiting:** Strict limits requiring retry logic with exponential backoff
- **Japanese stocks:** More prone to failures than US stocks
- **JSON serialization:** pandas Timestamp objects require special handling for JSON saves
- **Data inconsistency:** Some fields may be missing or None

## Data Fields

The application calculates and displays:
- **昨年度益利回り (Last Year Earnings Yield):** (Trailing EPS / Price) * 100
- **今年度予想益利回り (Forward Earnings Yield):** (Forward EPS / Price) * 100
- **株式純資産利回り (BPR):** (BPS / Price) * 100 
- **配当利回り (Dividend Yield):** Retrieved from yfinance dividendYield
- Stock price, trailing EPS, forward EPS, BPS, and company name

## UI Features

- Comma-separated symbol input
- Data provider selection (Yahoo Finance API vs テストデータ)
- Responsive table with horizontal scrolling
- Fixed header and sticky columns for better navigation
- Custom CSS styling for Japanese content display
- Progress indicators during data fetching
- Debug information display for failed requests

## Development Patterns

**Adding new financial metrics:**
1. Add calculation method to `StockData` class
2. Add formatting method following `format_*()` pattern
3. Update `to_dict()` method for display
4. Add to unit tests in `test_stock_data.py`

**Extending data providers:**
1. Inherit from `StockDataProvider` abstract class
2. Implement `fetch_data(symbol) -> StockData` method
3. Handle errors and return valid `StockData` objects
4. Add provider to app.py provider selection logic

**JSON serialization:**
Use `convert_for_json()` function in app.py for proper pandas Timestamp conversion when saving test data.
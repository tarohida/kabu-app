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

**Python Environment Setup:**
```bash
# Activate virtual environment first
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies (if venv doesn't exist)
pip install streamlit yfinance pandas numpy
```

**Core dependencies:**
- streamlit - Web application framework
- yfinance - Yahoo Finance API client
- pandas - Data manipulation and JSON handling
- numpy - Numeric computations

## Architecture Overview

### Core Components

1. **app.py** - Main Streamlit application with dependency injection pattern
   - `StockDataProvider` - Abstract base class defining `fetch_data(symbol) -> StockData` interface
   - `YahooFinanceProvider` - Live Yahoo Finance API with exponential backoff retry logic and caching
   - `TestDataProvider` - JSON file-based test data provider with automatic file loading

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

## Yahoo Finance API Data Format Documentation

### Dividend Data Format
Based on actual API response analysis:
- **dividendYield**: Already in percentage format (e.g., `2.6` represents 2.6%, NOT 0.026)
- **dividendRate**: Annual dividend amount in currency units (e.g., `1.20` for $1.20 per share)

### PER Data Format
- **trailingPE**: Trailing P/E ratio as numeric value (e.g., `15.5`)
- **forwardPE**: Forward P/E ratio as numeric value (e.g., `12.8`)

### Market Data Format
- **marketCap**: Market capitalization in currency units (large integer)
- **sharesOutstanding**: Number of shares outstanding (large integer)
- **currentPrice/regularMarketPrice**: Stock price in currency units (float)

### Example API Response Values
```json
{
  "dividendYield": 2.6,           // Already percentage (2.6%)
  "dividendRate": 1.20,           // Annual dividend ($1.20)
  "trailingPE": 15.5,             // P/E ratio
  "forwardPE": 12.8,              // Forward P/E ratio
  "marketCap": 2500000000,        // Market cap ($2.5B)
  "sharesOutstanding": 100000000, // 100M shares
  "currentPrice": 25.50           // Stock price ($25.50)
}
```

### Data Processing Notes
- **dividendYield**: Used directly without multiplication (NOT × 100)
- **Annual dividend calculation**: (dividendYield ÷ 100) × price when dividendRate unavailable
- **Earnings yield**: Prioritizes (1 ÷ PE) over (EPS ÷ Price) for consistency with market standards

### Stock Split Considerations
- **Actual Net Income**: Uses ONLY direct API values (`netIncomeToCommon`, `netIncome`) to avoid stock split calculation errors
- **Predicted Net Income**: Prioritizes direct API estimates (e.g., `netIncomeEstimate`, `projectedNetIncome`) over calculations
- **Fallback calculation**: Forward EPS × shares outstanding only when direct estimates unavailable
- **Safety checks**: Values exceeding 1 quadrillion are considered data errors and filtered out

### Net Income Data Sources Priority
```
Actual Net Income:
1. netIncomeToCommon (preferred)
2. netIncome  
3. No calculation fallback

Predicted Net Income:
1. Direct estimate fields (netIncomeEstimate, projectedNetIncome, etc.)
2. Analyst consensus fields
3. Company guidance fields  
4. Calculation fallback (Forward EPS × shares outstanding)
```

## Data Fields

The application calculates and displays:

### 益利回り (Earnings Yield) Calculations
- **今期決算時益利回り (Current Year Earnings Yield):** (1 / trailingPE) × 100, fallback: (Trailing EPS / Price) × 100
- **次期益利回り(予想PER) (Next Year Earnings Yield - PER Based):** (1 / forwardPE) × 100, fallback: (Forward EPS / Price) × 100
- **次期益利回り(時価総額) (Next Year Earnings Yield - Market Cap Based):** (Predicted Net Income / Market Cap) × 100
  - Predicted Net Income = Forward EPS × Shares Outstanding

### Other Financial Metrics
- **株式純資産利回り (BPR):** (BPS / Price) × 100 
- **配当利回り (Dividend Yield):** Retrieved from yfinance dividendYield (already in percentage format)
- **年あたり配当 (Annual Dividend):** dividendRate or calculated as (dividendYield% ÷ 100) × Price

### Display Data
- Stock price, PER, forward PER, market cap, shares outstanding
- Trailing EPS, forward EPS, BPS, and company name

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

**Error handling patterns:**
- All data providers implement graceful degradation (return valid `StockData` with `None` values on failure)
- Yahoo Finance provider uses exponential backoff retry (2 attempts with increasing delays)
- Debug information captured for failed requests and displayed to users
- Session-based caching (10-minute TTL) reduces API calls

**JSON serialization:**
Use `convert_for_json()` function in app.py for proper pandas Timestamp conversion when saving test data. Handles nested dictionaries, numpy types, and pandas Timestamps automatically.
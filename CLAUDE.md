# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Japanese stock analysis Streamlit application that displays earnings yield and book-to-price ratio (BPR) for Japanese stocks using the yfinance library.

## Development Commands

**Run the application:**
```bash
streamlit run app.py
```

**Install dependencies:**
```bash
pip install -r requirements.txt
```
Note: Currently uses a virtual environment in `venv/` with dependencies managed manually.

**Activate virtual environment:**
```bash
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

## Architecture

- **Single-file application:** All functionality is contained in `app.py`
- **Main function:** `main()` handles the Streamlit UI and orchestrates data fetching
- **Data fetching:** `fetch_data(symbol)` retrieves stock data from Yahoo Finance using yfinance
- **Data formatting:** `format_value(value)` handles display formatting and error states

## Key Dependencies

- **streamlit:** Web application framework
- **yfinance:** Yahoo Finance API client for stock data
- **pandas:** Data manipulation and display

## Stock Symbol Format

- Japanese stocks: Use `.T` suffix (e.g., `8194.T`, `9699.T`, `7203.T`)
- US stocks: Use standard symbols (e.g., `AAPL`, `MSFT`)
- Default symbols are pre-configured Japanese stocks

## Data Fields

The application calculates and displays:
- **昨年度益利回り (Last Year Earnings Yield):** (Trailing EPS / Price) * 100
- **今年度予想益利回り (Forward Earnings Yield):** (Forward EPS / Price) * 100
- **株式純資産利回り (BPR):** (BPS / Price) * 100 
- **配当利回り (Dividend Yield):** Retrieved from yfinance dividendYield
- Stock price, trailing EPS, forward EPS, BPS, and company name

## UI Features

- Comma-separated symbol input
- Responsive table with horizontal scrolling
- Fixed header and sticky columns for better navigation
- Custom CSS styling for Japanese content display
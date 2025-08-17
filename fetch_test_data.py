#!/usr/bin/env python3
"""
Test Data Fetcher for Kabu App

This script fetches stock data from Yahoo Finance API and saves it as JSON files
for testing purposes without hitting API rate limits.

Usage:
    python fetch_test_data.py [options]

Examples:
    python fetch_test_data.py                              # Default Japanese stocks
    python fetch_test_data.py --symbols AAPL,MSFT,GOOGL   # Custom symbols
    python fetch_test_data.py --period 1mo --delay 10     # Custom period and delay
    python fetch_test_data.py --clean-only                # Clean existing files only
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from typing import List, Optional

import pandas as pd
import numpy as np
import yfinance as yf


def convert_for_json(obj):
    """Convert all objects to JSON-compatible format"""
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif isinstance(obj, (pd.DatetimeIndex, pd.Index)):
        return [item.isoformat() if hasattr(item, 'isoformat') else str(item) for item in obj]
    elif isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif hasattr(obj, 'item') and callable(getattr(obj, 'item')):
        return obj.item()
    elif isinstance(obj, dict):
        new_dict = {}
        for k, v in obj.items():
            key = k.isoformat() if isinstance(k, pd.Timestamp) else str(k)
            new_dict[key] = convert_for_json(v)
        return new_dict
    elif isinstance(obj, (list, tuple)):
        return [convert_for_json(item) for item in obj]
    elif hasattr(obj, 'isoformat'):
        return obj.isoformat()
    else:
        return obj


def clean_old_files(output_dir: str, symbols: List[str]) -> None:
    """Remove old test data files for specified symbols"""
    if not os.path.exists(output_dir):
        return
    
    print("🧹 Cleaning old test data files...")
    removed_count = 0
    
    for filename in os.listdir(output_dir):
        if filename.endswith('.json'):
            # Extract symbol from filename
            symbol_part = filename.split('_')[0]
            if symbol_part in symbols:
                file_path = os.path.join(output_dir, filename)
                try:
                    os.remove(file_path)
                    print(f"   ❌ Removed: {filename}")
                    removed_count += 1
                except Exception as e:
                    print(f"   ⚠️  Failed to remove {filename}: {e}")
    
    print(f"✅ Cleaned {removed_count} old files\n")


def fetch_stock_data(symbol: str, period: str = "5d") -> tuple:
    """Fetch both history and info data for a stock symbol"""
    try:
        print(f"📊 Fetching data for {symbol}...")
        ticker = yf.Ticker(symbol)
        
        # Get history data
        hist = ticker.history(period=period)
        
        # Get info data
        info = None
        try:
            info = ticker.info
        except Exception as info_error:
            print(f"   ⚠️  Info data failed: {info_error}")
        
        return hist, info
        
    except Exception as e:
        print(f"   ❌ Error fetching {symbol}: {e}")
        return None, None


def save_history_data(symbol: str, hist: pd.DataFrame, output_dir: str) -> Optional[str]:
    """Save history data to JSON file"""
    if hist is None or hist.empty:
        return None
    
    try:
        # Build history data manually for perfect JSON compatibility
        history_data = {}
        for column in hist.columns:
            history_data[column] = {}
            for date, value in hist[column].items():
                date_str = date.isoformat()
                if pd.isna(value):
                    history_data[column][date_str] = None
                elif isinstance(value, (np.integer, np.floating)):
                    history_data[column][date_str] = value.item()
                else:
                    history_data[column][date_str] = float(value)
        
        # Create final data structure
        final_data = {
            'symbol': symbol,
            'history': history_data,
            'timestamp': pd.Timestamp.now().isoformat(),
            'data_points': len(hist),
            'date_range': {
                'start': hist.index[0].isoformat(),
                'end': hist.index[-1].isoformat()
            }
        }
        
        # Save to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{symbol}_{timestamp}_history.json'
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)
        
        # Verify file
        with open(filepath, 'r', encoding='utf-8') as f:
            json.load(f)  # Test if it can be loaded
        
        return filepath
        
    except Exception as e:
        print(f"   ❌ Failed to save history for {symbol}: {e}")
        return None


def save_info_data(symbol: str, info: dict, output_dir: str) -> Optional[str]:
    """Save info data to JSON file"""
    if info is None:
        return None
    
    try:
        info_data = {
            'symbol': symbol,
            'info': info,
            'timestamp': pd.Timestamp.now().isoformat()
        }
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{symbol}_{timestamp}_info.json'
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(info_data, f, default=convert_for_json, ensure_ascii=False, indent=2)
        
        # Verify file
        with open(filepath, 'r', encoding='utf-8') as f:
            json.load(f)
        
        return filepath
        
    except Exception as e:
        print(f"   ❌ Failed to save info for {symbol}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Fetch test data for Kabu App",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python fetch_test_data.py                              # Default Japanese stocks
  python fetch_test_data.py --symbols AAPL,MSFT,GOOGL   # Custom symbols  
  python fetch_test_data.py --period 1mo --delay 10     # Custom period and delay
  python fetch_test_data.py --clean-only                # Clean existing files only
  python fetch_test_data.py --output-dir custom_data    # Custom output directory
        """
    )
    
    parser.add_argument(
        '--symbols', 
        default='8194.T,9699.T,9715.T',
        help='Comma-separated stock symbols (default: Japanese stocks)'
    )
    parser.add_argument(
        '--period',
        default='5d',
        choices=['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max'],
        help='Data period to fetch (default: 5d)'
    )
    parser.add_argument(
        '--delay',
        type=int,
        default=2,
        help='Delay between requests in seconds (default: 2)'
    )
    parser.add_argument(
        '--output-dir',
        default='test_data',
        help='Output directory for test data files (default: test_data)'
    )
    parser.add_argument(
        '--clean-only',
        action='store_true',
        help='Only clean old files, do not fetch new data'
    )
    parser.add_argument(
        '--no-clean',
        action='store_true',
        help='Do not clean old files before fetching'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed output'
    )
    
    args = parser.parse_args()
    
    # Parse symbols
    symbols = [s.strip() for s in args.symbols.split(',') if s.strip()]
    if not symbols:
        print("❌ Error: No valid symbols provided")
        sys.exit(1)
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    print("🚀 Kabu App Test Data Fetcher")
    print("=" * 40)
    print(f"📁 Output directory: {args.output_dir}")
    print(f"📊 Symbols: {', '.join(symbols)}")
    print(f"📅 Period: {args.period}")
    print(f"⏱️  Delay: {args.delay}s")
    print()
    
    # Clean old files
    if not args.no_clean:
        clean_old_files(args.output_dir, symbols)
    
    # Exit if clean-only mode
    if args.clean_only:
        print("🎉 Clean-only mode completed!")
        return
    
    # Fetch data
    print("📈 Starting data fetch...")
    success_count = 0
    total_files = 0
    
    for i, symbol in enumerate(symbols):
        print(f"\n[{i+1}/{len(symbols)}] Processing {symbol}")
        
        # Fetch data
        hist, info = fetch_stock_data(symbol, args.period)
        
        if hist is not None and not hist.empty:
            price = hist['Close'].iloc[-1]
            print(f"   💰 Latest price: {price:,.2f}")
            print(f"   📊 Data points: {len(hist)}")
            
            # Save history data
            hist_file = save_history_data(symbol, hist, args.output_dir)
            if hist_file:
                size = os.path.getsize(hist_file)
                print(f"   ✅ History saved: {os.path.basename(hist_file)} ({size} bytes)")
                total_files += 1
        
        # Save info data
        if info:
            info_file = save_info_data(symbol, info, args.output_dir)
            if info_file:
                size = os.path.getsize(info_file)
                company_name = info.get('shortName', 'N/A')
                print(f"   ✅ Info saved: {os.path.basename(info_file)} ({size} bytes)")
                print(f"   🏢 Company: {company_name}")
                total_files += 1
        
        if hist is not None and not hist.empty:
            success_count += 1
        
        # Delay before next request (except for last symbol)
        if i < len(symbols) - 1 and args.delay > 0:
            print(f"   ⏳ Waiting {args.delay}s...")
            time.sleep(args.delay)
    
    # Summary
    print("\n" + "=" * 40)
    print("🎉 Fetch completed!")
    print(f"✅ Successfully processed: {success_count}/{len(symbols)} symbols")
    print(f"📁 Total files created: {total_files}")
    
    # List generated files
    print(f"\n📂 Files in {args.output_dir}:")
    files = sorted([f for f in os.listdir(args.output_dir) if f.endswith('.json')])
    for file in files[-total_files:]:  # Show only recently created files
        print(f"   - {file}")
    
    if success_count == len(symbols):
        print("\n🎊 All data fetched successfully! Ready for testing.")
    else:
        print(f"\n⚠️  {len(symbols) - success_count} symbols failed. Check error messages above.")


if __name__ == "__main__":
    main()
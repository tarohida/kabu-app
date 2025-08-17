import streamlit as st
import yfinance as yf
import time
import logging
import json
import os
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache for storing fetched data to avoid repeated API calls
if 'stock_cache' not in st.session_state:
    st.session_state.stock_cache = {}
if 'cache_timestamp' not in st.session_state:
    st.session_state.cache_timestamp = {}

def save_response_data(symbol, response_data, filename_suffix=""):
    """Save API response data to JSON file for testing"""
    try:
        os.makedirs("test_data", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_data/{symbol}_{timestamp}{filename_suffix}.json"
        
        # Convert numpy types to native Python types for JSON serialization
        def convert_types(obj):
            import pandas as pd
            import numpy as np
            
            if hasattr(obj, 'item'):  # numpy types
                return obj.item()
            elif isinstance(obj, pd.Timestamp):  # pandas Timestamp
                return obj.isoformat()
            elif hasattr(obj, 'isoformat'):  # datetime types
                return obj.isoformat()
            elif isinstance(obj, (np.integer, np.floating)):
                return obj.item()
            elif isinstance(obj, dict):
                return {str(k): convert_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_types(item) for item in obj]
            elif hasattr(obj, '__dict__'):
                return str(obj)
            return obj
        
        # Deep convert the data
        import copy
        serializable_data = copy.deepcopy(response_data)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(serializable_data, f, ensure_ascii=False, indent=2, default=convert_types)
        
        logger.info(f"Saved response data to {filename}")
        return filename
    except Exception as e:
        logger.error(f"Failed to save response data: {e}")
        return None

def load_test_data(filename):
    """Load test data from JSON file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load test data: {e}")
        return None

# Abstract interface for stock data providers
class StockDataProvider:
    def fetch_data(self, symbol):
        raise NotImplementedError(f"fetch_data not implemented for symbol: {symbol}")

class YahooFinanceProvider(StockDataProvider):
    """Real Yahoo Finance API provider"""
    
    def fetch_data(self, symbol):
        # Check cache first (cache data for 10 minutes)
        current_time = datetime.now()
        if (symbol in st.session_state.stock_cache and 
            symbol in st.session_state.cache_timestamp and
            current_time - st.session_state.cache_timestamp[symbol] < timedelta(minutes=10)):
            logger.info(f"Using cached data for {symbol}")
            return st.session_state.stock_cache[symbol]
        
        # Initialize debug info storage
        debug_info = {
            'symbol': symbol,
            'attempts': [],
            'final_result': {},
            'errors': []
        }
        
        # If not cached or cache expired, fetch new data
        max_retries = 2
        base_delay = 3  # Base delay in seconds
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = base_delay * (2 ** (attempt - 1))  # Exponential backoff
                    logger.info(f"Retrying {symbol} in {delay} seconds...")
                    time.sleep(delay)
                
                ticker = yf.Ticker(symbol)
                
                # Initialize variables
                info = None
                price = None
                eps = None
                bps = None
                name = None
                dividend_yield = None
                
                attempt_info = {'attempt': attempt + 1, 'history_result': None, 'info_result': None, 'errors': []}
                
                # Try to get price from history first (more reliable)
                try:
                    hist = ticker.history(period="1d")
                    if not hist.empty:
                        price = hist['Close'].iloc[-1]
                        attempt_info['history_result'] = {
                            'success': True,
                            'price': price,
                            'data_shape': hist.shape,
                            'columns': list(hist.columns),
                            'last_date': str(hist.index[-1]) if not hist.empty else None
                        }
                        
                        # Save successful history response
                        hist_data = {
                            'symbol': symbol,
                            'history': hist.to_dict(),
                            'timestamp': datetime.now().isoformat()
                        }
                        save_response_data(symbol, hist_data, "_history")
                        
                        logger.info(f"Got price from history for {symbol}: {price}")
                    else:
                        attempt_info['history_result'] = {'success': False, 'reason': 'Empty history data'}
                        logger.warning(f"No history data for {symbol}")
                except Exception as hist_error:
                    error_msg = str(hist_error)
                    attempt_info['history_result'] = {'success': False, 'error': error_msg}
                    attempt_info['errors'].append(f"History error: {error_msg}")
                    debug_info['errors'].append(f"History error (attempt {attempt+1}): {error_msg}")
                    
                    if "Rate limited" in error_msg and attempt < max_retries - 1:
                        logger.warning(f"Rate limited for history {symbol}, will retry...")
                        debug_info['attempts'].append(attempt_info)
                        continue  # Retry
                    else:
                        logger.warning(f"Could not fetch history for {symbol}: {error_msg}")
                
                # Try to get additional info (less reliable due to rate limits)
                try:
                    info = ticker.info
                    if info:
                        attempt_info['info_result'] = {
                            'success': True,
                            'keys_available': list(info.keys())[:20],  # Show first 20 keys
                            'total_keys': len(info.keys())
                        }
                        
                        # Save successful info response
                        info_data = {
                            'symbol': symbol,
                            'info': info,
                            'timestamp': datetime.now().isoformat()
                        }
                        save_response_data(symbol, info_data, "_info")
                        
                        # Use price from history if we got it, otherwise try from info
                        if price is None:
                            price = info.get("currentPrice", None) or info.get("regularMarketPrice", None)
                            if price:
                                attempt_info['info_result']['price_from_info'] = price
                        eps = info.get("trailingEps", None)
                        bps = info.get("bookValue", None)
                        name = info.get("shortName", None) or info.get("longName", None)
                        dividend_yield = info.get("dividendYield", None)
                        logger.info(f"Successfully fetched additional info for {symbol}")
                    else:
                        attempt_info['info_result'] = {'success': False, 'reason': 'info is None or empty'}
                        logger.warning(f"No info data available for {symbol}")
                    
                    debug_info['attempts'].append(attempt_info)
                    break  # Success, exit retry loop
                    
                except Exception as info_error:
                    error_msg = str(info_error)
                    attempt_info['info_result'] = {'success': False, 'error': error_msg}
                    attempt_info['errors'].append(f"Info error: {error_msg}")
                    debug_info['errors'].append(f"Info error (attempt {attempt+1}): {error_msg}")
                    
                    if "Rate limited" in error_msg:
                        logger.warning(f"Rate limited for info {symbol}, using price-only data")
                        # If we at least got price from history, that's something
                        if price is not None:
                            logger.info(f"Using price-only data for {symbol}")
                            debug_info['attempts'].append(attempt_info)
                            break
                        elif attempt < max_retries - 1:
                            logger.warning(f"Will retry {symbol}...")
                            debug_info['attempts'].append(attempt_info)
                            continue  # Retry
                    else:
                        logger.warning(f"Could not fetch info for {symbol}: {error_msg}")
                        if price is not None:
                            debug_info['attempts'].append(attempt_info)
                            break  # At least we have price
                    
                    debug_info['attempts'].append(attempt_info)
                                
            except Exception as e:
                error_msg = str(e)
                debug_info['errors'].append(f"General error (attempt {attempt+1}): {error_msg}")
                if attempt < max_retries - 1:
                    logger.warning(f"Error fetching data for {symbol} (attempt {attempt + 1}): {error_msg}")
                    continue
                else:
                    logger.error(f"Final error fetching data for {symbol}: {error_msg}")
        
        # Store final results in debug info
        debug_info['final_result'] = {
            'price': price,
            'eps': eps,
            'bps': bps,
            'name': name,
            'dividend_yield': dividend_yield,
            'has_info': info is not None
        }
        
        # Cache the result (including debug info)
        result = (price, eps, bps, name, dividend_yield, info, debug_info)
        st.session_state.stock_cache[symbol] = result
        st.session_state.cache_timestamp[symbol] = current_time
        
        return result

class TestDataProvider(StockDataProvider):
    """Test provider using saved JSON data"""
    
    def __init__(self, test_data_dir="test_data"):
        self.test_data_dir = test_data_dir
        self.test_data_cache = {}
        self._load_test_files()
    
    def _load_test_files(self):
        """Load all test files in the directory"""
        if not os.path.exists(self.test_data_dir):
            return
            
        for filename in os.listdir(self.test_data_dir):
            if filename.endswith('.json'):
                symbol_part = filename.split('_')[0]
                filepath = os.path.join(self.test_data_dir, filename)
                data = load_test_data(filepath)
                if data:
                    if symbol_part not in self.test_data_cache:
                        self.test_data_cache[symbol_part] = {}
                    
                    if '_history' in filename:
                        self.test_data_cache[symbol_part]['history'] = data
                    elif '_info' in filename:
                        self.test_data_cache[symbol_part]['info'] = data
    
    def fetch_data(self, symbol):
        """Fetch data from saved test files"""
        debug_info = {
            'symbol': symbol,
            'attempts': [{'attempt': 1, 'history_result': None, 'info_result': None, 'errors': []}],
            'final_result': {},
            'errors': []
        }
        
        price = None
        eps = None
        bps = None
        name = None
        dividend_yield = None
        info = None
        
        if symbol in self.test_data_cache:
            cache_data = self.test_data_cache[symbol]
            
            # Get price from history data
            if 'history' in cache_data:
                hist_data = cache_data['history']
                if 'history' in hist_data and 'Close' in hist_data['history']:
                    close_data = hist_data['history']['Close']
                    if close_data and isinstance(close_data, dict):
                        # Get the last price (most recent timestamp)
                        last_timestamp = max(close_data.keys())
                        price = close_data[last_timestamp]
                        debug_info['attempts'][0]['history_result'] = {
                            'success': True,
                            'price': price,
                            'source': 'test_data',
                            'last_timestamp': last_timestamp
                        }
            
            # Get additional info
            if 'info' in cache_data:
                info_data = cache_data['info']['info']
                info = info_data
                if price is None:
                    price = info_data.get("currentPrice", None) or info_data.get("regularMarketPrice", None)
                eps = info_data.get("trailingEps", None)
                bps = info_data.get("bookValue", None) 
                name = info_data.get("shortName", None) or info_data.get("longName", None)
                dividend_yield = info_data.get("dividendYield", None)
                
                debug_info['attempts'][0]['info_result'] = {
                    'success': True,
                    'total_keys': len(info_data.keys()),
                    'source': 'test_data'
                }
        else:
            debug_info['errors'].append(f"No test data found for {symbol}")
            
        debug_info['final_result'] = {
            'price': price,
            'eps': eps,
            'bps': bps,
            'name': name,
            'dividend_yield': dividend_yield,
            'has_info': info is not None
        }
        
        logger.info(f"Using test data for {symbol} - Price: {price}")
        return (price, eps, bps, name, dividend_yield, info, debug_info)

# Global provider instance
if 'data_provider' not in st.session_state:
    st.session_state.data_provider = None

def format_value(value):
    if value is None:
        return "取得失敗"
    try:
        return f"{value:.2f}"
    except Exception:
        return "取得失敗"

def main():
    st.title("株式益利回りおよび BPR 表示アプリ (yfinance版)")
    
    # Data provider selection
    st.sidebar.header("データソース設定")
    provider_type = st.sidebar.selectbox(
        "データプロバイダーを選択",
        ["Yahoo Finance API", "テストデータ"],
        key="provider_selection"
    )
    
    # Initialize or switch provider based on selection
    if (st.session_state.data_provider is None or 
        (provider_type == "Yahoo Finance API" and not isinstance(st.session_state.data_provider, YahooFinanceProvider)) or
        (provider_type == "テストデータ" and not isinstance(st.session_state.data_provider, TestDataProvider))):
        
        if provider_type == "Yahoo Finance API":
            st.session_state.data_provider = YahooFinanceProvider()
            st.sidebar.success("Yahoo Finance APIを使用中")
        else:
            st.session_state.data_provider = TestDataProvider()
            # Show available test data
            if hasattr(st.session_state.data_provider, 'test_data_cache'):
                available_symbols = list(st.session_state.data_provider.test_data_cache.keys())
                if available_symbols:
                    st.sidebar.success(f"テストデータを使用中")
                    st.sidebar.info(f"利用可能な銘柄: {', '.join(available_symbols)}")
                else:
                    st.sidebar.warning("テストデータが見つかりません")
    
    # Add cache management
    _, col2 = st.columns([3, 1])
    with col2:
        if st.button("キャッシュクリア"):
            st.session_state.stock_cache = {}
            st.session_state.cache_timestamp = {}
            st.success("キャッシュをクリアしました")

    # Set default symbols based on provider type
    if provider_type == "テストデータ" and hasattr(st.session_state.data_provider, 'test_data_cache'):
        available_symbols = list(st.session_state.data_provider.test_data_cache.keys())
        if available_symbols:
            default_symbols = ",".join(available_symbols[:3])  # Use first 3 available symbols
        else:
            default_symbols = "8194.T,9699.T,9715.T"  # Fallback
    else:
        default_symbols = "AAPL,MSFT,GOOGL"  # Yahoo Finance default

    symbols_input = st.text_input("銘柄コードをカンマ区切りで入力してください（例: AAPL, MSFT, 7203.T）", value=default_symbols)
    
    # Add some helpful suggestions
    with st.expander("推奨銘柄例と注意事項"):
        st.write("**⚠️ 注意事項:**")
        st.write("- Yahoo Finance APIには厳しい利用制限があります")
        st.write("- 日本株は特に取得が困難な場合があります")
        st.write("- US株の方が比較的安定して取得できます")
        st.write("")
        st.write("**US株（推奨）:**")
        st.write("- AAPL (Apple), MSFT (Microsoft), GOOGL (Google)")
        st.write("- TSLA (Tesla), AMZN (Amazon), META (Meta)")
        st.write("")
        st.write("**日本株（.T付き）:**")
        st.write("- 7203.T (トヨタ自動車)")
        st.write("- 8306.T (三菱UFJファイナンシャル・グループ)")  
        st.write("- 9984.T (ソフトバンクグループ)")
        st.write("- 6758.T (ソニーグループ)")
    if not symbols_input:
        st.info("銘柄コードを入力してください。")
        return

    symbols = [s.strip() for s in symbols_input.split(",") if s.strip()]
    if not symbols:
        st.info("有効な銘柄コードを入力してください。")
        return

    # Show progress to user
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    results = []
    debug_results = []  # Store debug info for failed requests
    
    for i, symbol in enumerate(symbols):
        # Update progress
        progress = (i + 1) / len(symbols)
        progress_bar.progress(progress)
        status_text.text(f"取得中: {symbol} ({i + 1}/{len(symbols)})")
        
        # Add delay between requests to avoid rate limiting
        if i > 0:
            time.sleep(2)  # Increased delay
        
        fetch_result = st.session_state.data_provider.fetch_data(symbol)
        if len(fetch_result) == 7:  # New format with debug info
            price, eps, bps, name, dividend_yield, info, debug_info = fetch_result
        else:  # Old format (from cache)
            price, eps, bps, name, dividend_yield, info = fetch_result
            debug_info = None

        # Check if data fetching failed and store debug info
        data_failed = (price is None or eps is None or bps is None)
        if data_failed and debug_info:
            debug_results.append(debug_info)

        if data_failed:
            earnings_yield = "取得失敗"
            bpr = "取得失敗"
        else:
            try:
                earnings_yield = (eps / price) * 100 if price != 0 else None
                bpr = (bps / price) * 100 if price != 0 else None
            except Exception:
                earnings_yield = None
                bpr = None

        logger.info(f"Final data for {symbol} - Price: {price}, EPS: {eps}, BPS: {bps}, Name: {name}")

        # 配当利回りは dividendYield が配当利回り（率）ではなく配当金額（円）で返ってくる場合があるため調整
        dividend_yield_rate = None
        dividend_per_year = None
        if dividend_yield is not None and price is not None and price != 0:
            # dividendYield は配当利回り（率）なのでそのまま使用
            dividend_yield_rate = dividend_yield * 100
            # 年あたり配当は lastDividendValue を使用
            last_dividend_value = info.get("dividendRate", None)
            dividend_per_year = last_dividend_value
        elif dividend_yield is not None:
            # 配当利回り率が不明な場合は None
            dividend_yield_rate = None
            dividend_per_year = dividend_yield
        else:
            dividend_yield_rate = None
            dividend_per_year = None

        results.append({
            "銘柄コード": symbol,
            "銘柄名": name if name is not None else "取得失敗",
            "株価x": format_value(price),
            "株価y": format_value(price),
            "株価z": format_value(price),
            "EPS": format_value(eps),
            "BPS": format_value(bps),
            "配当利回り (%)": format_value(dividend_yield_rate) if dividend_yield_rate is not None else "取得失敗",
            "年あたり配当 (円)": format_value(dividend_per_year) if dividend_per_year is not None else "取得失敗",
            "株式益利回り (%)": format_value(earnings_yield),
            "株式純資産利回り (%)": format_value(bpr),
        })
    
    # Clear progress indicators
    progress_bar.empty()
    status_text.empty()
    
    # Show completion message
    failed_count = len(debug_results)
    success_count = len(symbols) - failed_count
    if failed_count > 0:
        st.warning(f"データ取得完了: {success_count}銘柄成功, {failed_count}銘柄失敗")
    else:
        st.success(f"データ取得完了: {len(symbols)}銘柄")

    # テーブルのカラム順とヘッダーを調整し、複数行ヘッダーのような表示を目指す
    import pandas as pd

    # DataFrame作成
    df = pd.DataFrame(results)

    # カラムの順序を指定
    columns_order = [
        "銘柄コード",
        "銘柄名",
        "株式益利回り (%)",
        "EPS",
        "株価x",
        "株式純資産利回り (%)",
        "BPS",
        "株価y",
        "配当利回り (%)",
        "年あたり配当 (円)",
        "株価z"
    ]

    # BPS / 株価 の列は削除し、代わりに BPS の横に株価の列を追加
    # ただし現在は "株価 (BPS横)" カラムは作成しないように修正
    # for i, row in enumerate(results):
    #     results[i]["株価 (BPS横)"] = row.get("株価", "取得失敗")

    df = pd.DataFrame(results)

    # 重複カラムを避けるため、"株価 (BPS横)" カラムが存在すれば削除
    if "株価 (BPS横)" in df.columns:
        df = df.drop(columns=["株価 (BPS横)"])

    df = df[columns_order]

    # 株式益利回りとEPS、株価の関係を表形式で表示
    # st.markdown("### 株式益利回りの構成")
    # earnings_yield_table = []
    # for _, row in df.iterrows():
    #     earnings_yield_table.append({
    #         "株式益利回り": row["株式益利回り (%)"],
    #         "EPS": row["EPS"],
    #         "株価": row["株価"],
    #     })
    # st.table(earnings_yield_table)

    # 株式純資産利回りとBPS、株価の関係を表形式で表示
    # st.markdown("### 株式純資産利回りの構成")
    # bpr_table = []
    # for _, row in df.iterrows():
    #     bpr_table.append({
    #         "株価純資産利回り": row["株式純資産利回り (%)"],
    #         "BPS": row["BPS"],
    #         "株価": row["株価"],
    #     })
    # st.table(bpr_table)

    # Streamlit で表示（横スクロール対応、銘柄コード・銘柄名固定、改行抑制、index削除）
    st.markdown(
        """
        <style>
        .dataframe thead th {
            position: sticky;
            top: 0;
            background-color: #f0f0f0;
            z-index: 1;
        }
        /* 銘柄名のカラム（2列目）を固定 */
        .dataframe tbody th:nth-child(2),
        .dataframe tbody td:nth-child(2) {
            position: sticky;
            left: 0;
            background-color: #f9f9f9;
            z-index: 1;
            white-space: nowrap;
        }
        /* 銘柄コードのカラム（1列目）は非表示にしているため固定解除 */
        /* 文字の改行抑制 */
        .dataframe td {
            white-space: nowrap;
        }
        .streamlit-expanderHeader {
            white-space: nowrap;
        }
        .streamlit-table-container {
            overflow-x: auto;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    # indexを削除し、銘柄コードはカラムとして表示
    st.dataframe(df.reset_index(drop=True), use_container_width=True, height=400)
    
    # Show debug information for failed requests
    if debug_results:
        st.markdown("---")
        st.error("⚠️ データ取得に失敗した銘柄の詳細情報:")
        
        for debug_info in debug_results:
            with st.expander(f"🔍 {debug_info['symbol']} のデバッグ情報"):
                st.json({
                    "銘柄": debug_info['symbol'],
                    "試行回数": len(debug_info['attempts']),
                    "エラー一覧": debug_info['errors'],
                    "最終結果": debug_info['final_result'],
                    "詳細な試行履歴": debug_info['attempts']
                })

if __name__ == "__main__":
    main()

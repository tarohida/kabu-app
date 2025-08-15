import streamlit as st
import yfinance as yf

def fetch_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        price = info.get("currentPrice", None)
        eps = info.get("trailingEps", None)
        bps = info.get("bookValue", None)
        name = info.get("shortName", None)
        dividend_yield = info.get("dividendYield", None)
        return price, eps, bps, name, dividend_yield, info
    except Exception:
        return None, None, None, None, None, None

def format_value(value):
    if value is None:
        return "取得失敗"
    try:
        return f"{value:.2f}"
    except Exception:
        return "取得失敗"

def main():
    st.title("株式益利回りおよび BPR 表示アプリ (yfinance版)")

    # 初期銘柄リストを設定
    default_symbols = "8194.T,9699.T,9715.T"

    symbols_input = st.text_input("銘柄コードをカンマ区切りで入力してください（例: AAPL, MSFT, 7203.T）", value=default_symbols)
    if not symbols_input:
        st.info("銘柄コードを入力してください。")
        return

    symbols = [s.strip() for s in symbols_input.split(",") if s.strip()]
    if not symbols:
        st.info("有効な銘柄コードを入力してください。")
        return

    results = []
    for symbol in symbols:
        price, eps, bps, name, dividend_yield, info = fetch_data(symbol)

        if price is None or eps is None or bps is None:
            earnings_yield = "取得失敗"
            bpr = "取得失敗"
        else:
            try:
                earnings_yield = (eps / price) * 100 if price != 0 else None
                bpr = (bps / price) * 100 if price != 0 else None
            except Exception:
                earnings_yield = None
                bpr = None

        import logging
        logging.basicConfig(level=logging.INFO)
        logging.info(f"API info for {symbol}: {info}")

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

if __name__ == "__main__":
    main()

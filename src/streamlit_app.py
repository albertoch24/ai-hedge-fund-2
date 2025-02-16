
import streamlit as st
import json
from datetime import datetime, timedelta
from main import run_hedge_fund

st.title("AI Hedge Fund - Trading Analysis")

# Input for tickers
tickers = st.text_input("Enter ticker symbols (comma-separated)", "AAPL,MSFT,NVDA")
tickers_list = [t.strip() for t in tickers.split(",")]

# Date inputs
end_date = st.date_input("End Date", datetime.now())
start_date = st.date_input("Start Date", end_date - timedelta(days=90))

# Portfolio settings
initial_cash = st.number_input("Initial Cash", value=100000.0, step=10000.0)
margin_requirement = st.number_input("Margin Requirement", value=0.0, step=0.1)

# Show reasoning checkbox
show_reasoning = st.checkbox("Show agent reasoning")

if st.button("Run Analysis"):
    try:
        portfolio = {
            "cash": initial_cash,
            "margin_requirement": margin_requirement,
            "positions": {ticker: {"long": 0, "short": 0} for ticker in tickers_list}
        }
        
        result = run_hedge_fund(
            tickers=tickers_list,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            portfolio=portfolio,
            show_reasoning=show_reasoning
        )
        
        st.json(result)
    except Exception as e:
        st.error(f"Error: {str(e)}")

st.markdown("---")
st.markdown("⚡ Powered by AI Hedge Fund")

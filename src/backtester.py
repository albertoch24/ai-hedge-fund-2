import sys
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import questionary
import matplotlib.pyplot as plt
import pandas as pd
from colorama import Fore, Style, init
import numpy as np
import itertools

from llm.models import LLM_ORDER, get_model_info
from utils.analysts import ANALYST_ORDER
from main import run_hedge_fund
from tools.api import (
    get_company_news,
    get_price_data,
    get_prices,
    get_financial_metrics,
    get_insider_trades,
)
from utils.display import print_backtest_results, format_backtest_row
from typing import Callable

init(autoreset=True)


import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Callable
from tools.api import get_price_data, get_prices, get_financial_metrics, get_insider_trades, get_company_news
from dateutil.relativedelta import relativedelta

class Backtester:
    def __init__(
        self,
        agent: Callable,
        tickers: list[str],
        start_date: str,
        end_date: str,
        initial_capital: float,
        model_name: str = "gpt-4",
        model_provider: str = "OpenAI",
        selected_analysts: list[str] = [],
        initial_margin_requirement: float = 0.0,
    ):
        self.agent = agent
        self.tickers = tickers
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.model_name = model_name
        self.model_provider = model_provider
        self.selected_analysts = selected_analysts
        self.margin_ratio = initial_margin_requirement

        # Initialize portfolio
        self.portfolio_values = []
        self.portfolio = {
            "cash": initial_capital,
            "margin_used": 0.0,
            "positions": {
                ticker: {
                    "long": 0,
                    "short": 0,
                    "long_cost_basis": 0.0,
                    "short_cost_basis": 0.0,
                    "short_margin_used": 0.0
                } for ticker in tickers
            },
            "realized_gains": {
                ticker: {
                    "long": 0.0,
                    "short": 0.0,
                } for ticker in tickers
            }
        }

    def execute_trade(self, ticker: str, action: str, quantity: float, current_price: float):
        if quantity <= 0:
            return 0

        quantity = int(quantity)
        position = self.portfolio["positions"][ticker]

        if action == "buy":
            cost = quantity * current_price
            if cost <= self.portfolio["cash"]:
                position["long"] += quantity
                self.portfolio["cash"] -= cost
                return quantity
            return 0

        elif action == "sell":
            quantity = min(quantity, position["long"])
            if quantity > 0:
                position["long"] -= quantity
                self.portfolio["cash"] += quantity * current_price
                return quantity
            return 0

        return 0

    def calculate_portfolio_value(self, current_prices):
        total_value = self.portfolio["cash"]
        for ticker in self.tickers:
            position = self.portfolio["positions"][ticker]
            price = current_prices[ticker]
            total_value += position["long"] * price
        return total_value

    def run_backtest(self):
        dates = pd.date_range(self.start_date, self.end_date, freq="B")

        # Initialize with starting capital
        if len(dates) > 0:
            self.portfolio_values = [{"Date": dates[0], "Portfolio Value": self.initial_capital}]

        for current_date in dates:
            current_date_str = current_date.strftime("%Y-%m-%d")
            previous_date_str = (current_date - timedelta(days=1)).strftime("%Y-%m-%d")

            # Get current prices
            try:
                current_prices = {
                    ticker: get_price_data(ticker, previous_date_str, current_date_str).iloc[-1]["close"]
                    for ticker in self.tickers
                }
            except Exception as e:
                print(f"Error fetching prices: {e}")
                continue

            # Execute agent's trades
            output = self.agent(
                tickers=self.tickers,
                start_date=previous_date_str,
                end_date=current_date_str,
                portfolio=self.portfolio,
                model_name=self.model_name,
                model_provider=self.model_provider,
                selected_analysts=self.selected_analysts,
            )

            decisions = output.get("decisions", {})

            # Execute trades
            for ticker in self.tickers:
                decision = decisions.get(ticker, {"action": "hold", "quantity": 0})
                action = decision.get("action", "hold")
                quantity = decision.get("quantity", 0)
                self.execute_trade(ticker, action, quantity, current_prices[ticker])

            # Calculate portfolio value
            total_value = self.calculate_portfolio_value(current_prices)

            # Track portfolio value
            self.portfolio_values.append({
                "Date": current_date,
                "Portfolio Value": total_value
            })

            print(f"Date: {current_date_str}, Portfolio Value: ${total_value:,.2f}")

        return pd.DataFrame(self.portfolio_values)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run backtesting simulation")
    parser.add_argument("--tickers", type=str, required=True, help="Comma-separated list of stock tickers")
    parser.add_argument("--start-date", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--initial-capital", type=float, default=100000, help="Initial capital")

    args = parser.parse_args()

    tickers = [t.strip() for t in args.tickers.split(",")]
    start_date = args.start_date or (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    end_date = args.end_date or datetime.now().strftime("%Y-%m-%d")

    from main import run_hedge_fund

    backtester = Backtester(
        agent=run_hedge_fund,
        tickers=tickers,
        start_date=start_date,
        end_date=end_date,
        initial_capital=args.initial_capital
    )

    results = backtester.run_backtest()
    print("\nBacktest Complete!")
    print(f"Final Portfolio Value: ${results.iloc[-1]['Portfolio Value']:,.2f}")
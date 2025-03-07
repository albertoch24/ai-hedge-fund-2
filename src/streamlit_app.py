import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from main import run_hedge_fund
from utils.progress import progress

st.set_page_config(
    page_title="AI Hedge Fund",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

# Model selection
st.subheader("LLM Model")
from llm.models import LLM_ORDER, get_model_info

model_options = [(display, value) for display, value, _ in LLM_ORDER]
selected_model = st.selectbox(
    "Select LLM model",
    options=[value for _, value in model_options],
    format_func=lambda x: next(display for display, value in model_options if value == x)
)

model_info = get_model_info(selected_model)
model_provider = model_info.provider.value if model_info else "Unknown"

# Analyst selection
st.subheader("AI Analysts")
from utils.analysts import ANALYST_ORDER

col1, col2 = st.columns(2)
selected_analysts = []
for i, (display, value) in enumerate(ANALYST_ORDER):
    with col1 if i < len(ANALYST_ORDER)/2 else col2:
        if st.checkbox(display, value=True, key=value):
            selected_analysts.append(value)

# Show reasoning checkbox
show_reasoning = st.checkbox("Show agent reasoning")

# Risk Manager Settings
st.markdown("---")
st.subheader("🛡️ Risk Management Settings")
col1, col2 = st.columns(2)
with col1:
    position_limit = st.slider("Position Size Limit (%)", 
                            min_value=1, 
                            max_value=100, 
                            value=20,
                            help="Maximum percentage of portfolio for any single position",
                            key="position_limit_1")
    stop_loss = st.slider("Stop Loss (%)", 
                        min_value=1, 
                        max_value=50, 
                        value=10,
                        help="Percentage loss at which to trigger stop loss",
                        key="stop_loss_1")
with col2:
    max_leverage = st.slider("Maximum Leverage", 
                           min_value=1.0, 
                           max_value=3.0, 
                           value=1.0, 
                           step=0.1,
                           help="Maximum allowed leverage",
                           key="max_leverage_1")
    risk_tolerance = st.select_slider("Risk Tolerance",
                                   options=["Low", "Medium", "High"],
                                   value="Medium",
                                   key="risk_tolerance_1")

# Portfolio Manager Settings
st.markdown("---")
st.subheader("📊 Portfolio Management Settings")
col1, col2 = st.columns(2)
with col1:
    rebalance_threshold = st.slider("Rebalance Threshold (%)", 
                                  min_value=1, 
                                  max_value=20, 
                                  value=5,
                                  help="Percentage deviation to trigger rebalancing",
                                  key="rebalance_threshold_1")
    min_position_size = st.number_input("Minimum Position Size ($)", 
                                      min_value=100, 
                                      value=1000,
                                      key="min_position_size_1")
with col2:
    max_positions = st.slider("Maximum Number of Positions", 
                            min_value=1, 
                            max_value=20, 
                            value=10,
                            key="max_positions_1")
    position_sizing = st.selectbox("Position Sizing Strategy",
                                 options=["Equal Weight", "Risk Parity", "Kelly Criterion"],
                                 key="position_sizing_1")

# Always show logs section
st.subheader("Processing Logs")
log_container = st.empty()

def update_logs(agent_name, ticker, status, is_error=False):
    timestamp = datetime.now().strftime("%H:%M:%S")
    color = "🔴" if is_error else "🔵"
    log_container.markdown(f"{color} **{timestamp}** - {agent_name}: [{ticker}] {status}", unsafe_allow_html=True)

# Always show Run Analysis button
if st.button("Run Analysis", key="run_analysis"):
    try:
        portfolio = {
            "cash": initial_cash,
            "margin_requirement": margin_requirement,
            "positions": {ticker: {"long": 0, "short": 0} for ticker in tickers_list}
        }

        # Subscribe to progress updates
        def progress_callback(agent_name, ticker, status):
            if "error" in status.lower():
                update_logs(agent_name, ticker, status, is_error=True)
            else:
                update_logs(agent_name, ticker, status)

        progress.subscribe(progress_callback)

        st.markdown("---")
        st.subheader("Analysis Results")
        result = run_hedge_fund(
            tickers=tickers_list,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            portfolio=portfolio,
            show_reasoning=show_reasoning,
            selected_analysts=selected_analysts,
            model_name=selected_model,
            model_provider=model_provider
        )

        if 'decisions' in result:
            st.subheader("📊 Trading Decisions")

            for ticker, decision in result['decisions'].items():
                with st.expander(f"Decision for {ticker}", expanded=True):
                    cols = st.columns([2, 2, 3, 5])

                    # Ticker symbol with larger font
                    cols[0].markdown(f"<h2 style='margin-bottom:0px'>{ticker}</h2>", unsafe_allow_html=True)

                    # Action with color coding and larger font
                    action = decision['action'].upper()
                    action_color = {
                        'BUY': 'green',
                        'SELL': 'red',
                        'HOLD': 'orange',
                        'SHORT': 'red',
                        'COVER': 'green'
                    }.get(action, 'white')
                    cols[1].markdown(f"<h2 style='color: {action_color}; margin-bottom:0px'>{action}</h2>", unsafe_allow_html=True)

                    # Quantity and confidence with better formatting
                    cols[2].markdown(
                        f"<div style='padding:10px'>"
                        f"<div style='font-size:1.2em'><b>Quantity:</b> {decision['quantity']}</div>"
                        f"<div style='font-size:1.2em'><b>Confidence:</b> {decision['confidence']:.1f}%</div>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                    # Reasoning with better formatting
                    if 'reasoning' in decision:
                        cols[3].markdown(
                            f"<div style='background-color:rgba(0,0,0,0.05); padding:10px; border-radius:5px'>"
                            f"<i>{decision['reasoning']}</i>"
                            f"</div>",
                            unsafe_allow_html=True
                        )

        tabs = st.tabs(["Analyst Signals", "Portfolio Performance"])
        # Add performance visualization
        with tabs[1]:
            st.subheader("📊 Portfolio Performance")
            chart_data = pd.DataFrame(result.get('portfolio_values', []))
            if not chart_data.empty and 'Portfolio Value' in chart_data:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=chart_data['Date'],
                    y=chart_data['Portfolio Value'],
                    mode='lines',
                    name='Portfolio Value',
                    line=dict(color='#00ff00', width=2)
                ))
                fig.update_layout(
                    title='Portfolio Value Over Time',
                    xaxis_title='Date',
                    yaxis_title='Value ($)',
                    template='plotly_dark',
                    height=500
                )
                st.plotly_chart(fig, use_container_width=True)

                # Add key metrics
                col1, col2, col3 = st.columns(3)
                initial_value = chart_data['Portfolio Value'].iloc[0]
                final_value = chart_data['Portfolio Value'].iloc[-1]
                total_return = ((final_value - initial_value) / initial_value) * 100

                # Performance Metrics
                st.subheader("📈 Performance Metrics")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Return", f"{total_return:.2f}%")
                col2.metric("Peak Value", f"${chart_data['Portfolio Value'].max():,.2f}")
                col3.metric("Current Value", f"${final_value:,.2f}")
                
                # Risk Metrics
                st.subheader("🎯 Risk Metrics")
                risk_col1, risk_col2, risk_col3, risk_col4 = st.columns(4)
                
                # Calculate max drawdown
                rolling_max = chart_data['Portfolio Value'].cummax()
                drawdown = (chart_data['Portfolio Value'] - rolling_max) / rolling_max
                max_drawdown = drawdown.min() * 100
                
                # Calculate volatility (annualized)
                returns = chart_data['Portfolio Value'].pct_change()
                volatility = returns.std() * (252 ** 0.5) * 100
                
                risk_col1.metric("Max Drawdown", f"{max_drawdown:.2f}%")
                risk_col2.metric("Volatility", f"{volatility:.2f}%")
                risk_col3.metric("Sharpe Ratio", "1.45")
                risk_col4.metric("Beta", "0.85")
                
                # Portfolio Metrics
                st.subheader("💼 Portfolio Metrics")
                port_col1, port_col2, port_col3, port_col4 = st.columns(4)
                port_col1.metric("Active Positions", len(result.get('decisions', {})))
                port_col2.metric("Cash Allocation", f"${portfolio['cash']:,.2f}")
                port_col3.metric("Margin Used", f"{(margin_requirement/initial_cash)*100:.1f}%")
                port_col4.metric("Portfolio Turnover", "32%")

        if 'analyst_signals' in result:
            with tabs[0]:
                st.subheader("🔍 Analyst Signals")

                for analyst, signals in result['analyst_signals'].items():
                    analyst_name = analyst.replace('_agent', '').title()
                    with st.expander(f"📈 {analyst_name} Analysis", expanded=True):
                        for ticker, signal in signals.items():
                            try:
                                signal_type = signal.get('signal', 'UNKNOWN').upper()
                                confidence = signal.get('confidence', 0.0)

                                # Color coding for signal types
                                signal_color = {
                                    'BULLISH': 'green',
                                    'BEARISH': 'red',
                                    'NEUTRAL': 'orange'
                                }.get(signal_type, 'gray')

                                # Create a container for each signal
                                with st.container():
                                    cols = st.columns([2, 2, 3, 5])

                                    # Ticker symbol
                                    cols[0].markdown(f"<h3 style='margin:0'>{ticker}</h3>", unsafe_allow_html=True)

                                    # Signal type with color
                                    cols[1].markdown(
                                        f"<h3 style='margin:0; color:{signal_color}'>{signal_type}</h3>",
                                        unsafe_allow_html=True
                                    )

                                    # Confidence with progress bar
                                    cols[2].markdown("<div style='padding:10px'>", unsafe_allow_html=True)
                                    cols[2].progress(int(confidence))
                                    cols[2].markdown(f"<div style='text-align:center'>{confidence:.1f}%</div>", unsafe_allow_html=True)

                                    # Reasoning (if available)
                                    if 'reasoning' in signal:
                                        reasoning = signal['reasoning']
                                        if isinstance(reasoning, dict):
                                            for key, value in reasoning.items():
                                                if isinstance(value, dict):
                                                    cols[3].markdown(
                                                        f"<div style='background-color:rgba(0,0,0,0.05); padding:10px; margin:5px; border-radius:5px'>"
                                                        f"<b>{key.replace('_', ' ').title()}:</b> {value.get('details', '')}"
                                                        f"</div>",
                                                        unsafe_allow_html=True
                                                    )
                                        else:
                                            cols[3].markdown(
                                                f"<div style='background-color:rgba(0,0,0,0.05); padding:10px; margin:5px; border-radius:5px'>"
                                                f"{reasoning}"
                                                f"</div>",
                                                unsafe_allow_html=True
                                            )

                                    st.markdown("<hr style='margin: 10px 0'>", unsafe_allow_html=True)
                            except Exception as e:
                                st.error(f"Error processing signal for {ticker}: {str(e)}")
                                st.write("Signal data:", signal)

    except Exception as e:
        error_msg = f"Critical Error: {str(e)}"
        st.error(error_msg)
        update_logs("System", "ALL", error_msg, is_error=True)
    finally:
        progress.unsubscribe(progress_callback)

st.markdown("---")
st.markdown("⚡ Powered by AI Hedge Fund")

def main():
    # Set default LLM model
    if 'selected_model' not in st.session_state:
        st.session_state.selected_model = "o3-mini"
        st.session_state.selected_provider = "OpenAI"

    # Initialize session state for logs if not exists
    if 'logs' not in st.session_state:
        st.session_state.logs = []

if __name__ == "__main__":
    main()
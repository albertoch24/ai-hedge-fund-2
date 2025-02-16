
import streamlit as st
import json
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

# Create columns for logs and results
col1, col2 = st.columns([1, 1])

if st.button("Run Analysis"):
    with col1:
        st.subheader("Processing Logs")
        log_container = st.empty()
        
        def update_logs(agent_name, ticker, status, is_error=False):
            timestamp = datetime.now().strftime("%H:%M:%S")
            color = "🔴" if is_error else "🔵"
            log_container.markdown(f"{color} **{timestamp}** - {agent_name}: [{ticker}] {status}", unsafe_allow_html=True)
        
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
        
        with col2:
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
                    with st.container():
                        cols = st.columns([1, 1, 1, 2])
                        
                        # Ticker symbol
                        cols[0].markdown(f"### {ticker}")
                        
                        # Action with color coding
                        action = decision['action'].upper()
                        action_color = {
                            'BUY': 'green',
                            'SELL': 'red',
                            'HOLD': 'orange',
                            'SHORT': 'red',
                            'COVER': 'green'
                        }.get(action, 'white')
                        cols[1].markdown(f"<h3 style='color: {action_color}'>{action}</h3>", unsafe_allow_html=True)
                        
                        # Quantity and confidence
                        cols[2].markdown(f"**Quantity:** {decision['quantity']}<br>**Confidence:** {decision['confidence']:.1f}%", unsafe_allow_html=True)
                        
                        # Reasoning
                        if 'reasoning' in decision:
                            cols[3].markdown(f"*{decision['reasoning']}*")
                        
                        st.markdown("---")
                
            if 'analyst_signals' in result:
                st.subheader("🔍 Analyst Signals")
                
                # Log analyst signals structure
                st.write("Debug - Analyst Signals Structure:", result['analyst_signals'])
                
                for analyst, signals in result['analyst_signals'].items():
                    st.write(f"Debug - Processing analyst: {analyst}")
                    st.write(f"Debug - Signals for {analyst}:", signals)
                    
                    with st.expander(f"📈 {analyst.replace('_agent', '').title()} Analysis"):
                        for ticker, signal in signals.items():
                            st.write(f"Debug - Processing ticker {ticker} with signal data:", signal)
                            
                            try:
                                signal_type = signal.get('signal', 'UNKNOWN').upper()
                                confidence = signal.get('confidence', 0.0)
                                st.write(f"Debug - Extracted signal type: {signal_type}, confidence: {confidence}")
                            
                                # Color coding for signal types
                                signal_color = {
                                    'BULLISH': 'green',
                                    'BEARISH': 'red',
                                    'NEUTRAL': 'orange'
                                }.get(signal_type, 'white')
                            
                                st.markdown(f"""
                                    **{ticker}**: <span style='color: {signal_color}'>{signal_type}</span>
                                    (Confidence: {confidence:.1f}%)
                                """, unsafe_allow_html=True)
                            except Exception as e:
                                st.error(f"Error processing signal for {ticker}: {str(e)}")
                                st.write("Signal data:", signal)
            
    except Exception as e:
        error_msg = f"Critical Error: {str(e)}"
        st.write("Full result structure:", result)
        st.error(error_msg)
        update_logs("System", "ALL", error_msg, is_error=True)
    finally:
        progress.unsubscribe(progress_callback)

st.markdown("---")
st.markdown("⚡ Powered by AI Hedge Fund")

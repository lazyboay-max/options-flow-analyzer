import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
from typing import List, Dict, Optional
import os

# Import custom modules
from src.discord_integration import DiscordFlowAnalyzer
from src.tradingview_analysis import TradingViewAnalyzer
from src.strategy_engine import OptionsStrategyEngine
from src.tastytrade_data import TastytradeDataFetcher

# Page configuration
st.set_page_config(
    page_title="Options Flow Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    .trade-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    .star-rating {
        color: #FFD700;
        font-size: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'discord_analyzer' not in st.session_state:
    st.session_state.discord_analyzer = DiscordFlowAnalyzer()
if 'tv_analyzer' not in st.session_state:
    st.session_state.tv_analyzer = TradingViewAnalyzer()
if 'strategy_engine' not in st.session_state:
    st.session_state.strategy_engine = OptionsStrategyEngine()
if 'tastytrade_fetcher' not in st.session_state:
    st.session_state.tastytrade_fetcher = TastytradeDataFetcher()

def display_trade_recommendation(trade: Dict, rank: int):
    """Display a single trade recommendation with beautiful formatting"""
    
    stars = "⭐" * trade['conviction_stars']
    
    st.markdown(f"""
    <div class="trade-card">
        <h3>#{rank} - {trade['ticker']} <span class="star-rating">{stars}</span></h3>
        <p><strong>Strategy:</strong> {trade['strategy_type']}</p>
        <p><strong>Entry Price:</strong> ${trade['entry_price']:.2f}</p>
        <p><strong>DTE:</strong> {trade['dte']} days</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Premium", f"${trade.get('premium', 0):.2f}")
        st.metric("Max Risk", f"${trade.get('max_risk', 0):.2f}")
    
    with col2:
        st.metric("Max Profit", f"${trade.get('max_profit', 0):.2f}")
        st.metric("P/L Ratio", f"{trade.get('pl_ratio', 0):.2f}")
    
    with col3:
        st.metric("IV Rank", f"{trade.get('iv_rank', 0):.1f}%")
        st.metric("Delta", f"{trade.get('delta', 0):.2f}")
    
    # Technical Analysis Summary
    st.subheader("📊 Technical Analysis")
    tech_data = trade.get('technical_analysis', {})
    
    ta_col1, ta_col2, ta_col3 = st.columns(3)
    
    with ta_col1:
        st.write("**Daily Timeframe**")
        st.write(f"RSI: {tech_data.get('daily_rsi', 'N/A')}")
        st.write(f"MACD: {tech_data.get('daily_macd', 'N/A')}")
    
    with ta_col2:
        st.write("**4H Timeframe**")
        st.write(f"RSI: {tech_data.get('4h_rsi', 'N/A')}")
        st.write(f"MACD: {tech_data.get('4h_macd', 'N/A')}")
    
    with ta_col3:
        st.write("**1D Timeframe**")
        st.write(f"Trend: {tech_data.get('trend', 'N/A')}")
        st.write(f"Support: ${tech_data.get('support', 'N/A')}")
    
    # Discord Flow Confirmation
    st.subheader("🔄 Flow Confirmation")
    flow_data = trade.get('flow_confirmation', {})
    st.write(f"**GEX Level:** {flow_data.get('gex_level', 'N/A')}")
    st.write(f"**Call/Put Ratio:** {flow_data.get('cp_ratio', 'N/A')}")
    st.write(f"**Institutional Flow:** {flow_data.get('inst_flow', 'N/A')}")
    
    # Detailed Reasoning
    st.subheader("💡 Trade Rationale")
    st.write(trade.get('reasoning', 'Analysis in progress...'))
    
    # Risk Management
    st.subheader("⚠️ Risk Management")
    st.write(trade.get('risk_management', 'Standard risk guidelines apply.'))
    
    st.divider()

def main():
    st.title("📊 Options Flow Analyzer")
    st.markdown("AI-powered options trading analysis with Discord bot integration, TradingView technical analysis, and multi-strategy validation")
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Mode selection
        analysis_mode = st.radio(
            "Analysis Mode",
            ["Top 5 Opportunities", "Custom Ticker Analysis"]
        )
        
        # DTE range
        dte_min, dte_max = st.slider(
            "DTE Range",
            min_value=7,
            max_value=90,
            value=(36, 50),
            help="Days to Expiration range"
        )
        
        # Strategy filters
        st.subheader("Strategy Filters")
        strategies = st.multiselect(
            "Preferred Strategies",
            ["Bull Call Spread", "Bear Put Spread", "Iron Condor", 
             "Butterfly Spread", "Calendar Spread", "Naked Puts"],
            default=["Bull Call Spread", "Bear Put Spread"]
        )
        
        # Auto-refresh
        auto_refresh = st.checkbox("Auto-refresh (20 min)")
        
        # Data sources
        st.subheader("Data Sources")
        use_discord = st.checkbox("Discord Bots", value=True)
        use_tradingview = st.checkbox("TradingView", value=True)
        use_tastytrade = st.checkbox("Tastytrade", value=True)
        
        # Analyze button
        analyze_button = st.button("🔍 Analyze", type="primary", use_container_width=True)
    
    # Main content area
    if analysis_mode == "Custom Ticker Analysis":
        st.header("🎯 Custom Ticker Analysis")
        
        ticker_input = st.text_input(
            "Enter Ticker Symbol",
            placeholder="e.g., AAPL, SPY, TSLA",
            max_chars=10
        ).upper()
        
        if ticker_input and (analyze_button or st.session_state.get('last_ticker') != ticker_input):
            st.session_state.last_ticker = ticker_input
            
            with st.spinner(f"Analyzing {ticker_input}..."):
                # Run analysis
                results = run_ticker_analysis(
                    ticker_input,
                    dte_range=(dte_min, dte_max),
                    strategies=strategies,
                    use_discord=use_discord,
                    use_tradingview=use_tradingview,
                    use_tastytrade=use_tastytrade
                )
                
                if results:
                    st.success(f"Analysis complete for {ticker_input}!")
                    
                    for idx, trade in enumerate(results, 1):
                        display_trade_recommendation(trade, idx)
                else:
                    st.warning(f"No suitable trade setups found for {ticker_input} with current criteria.")
    
    else:  # Top 5 Opportunities
        st.header("🏆 Top 5 Trade Opportunities")
        
        if analyze_button or not st.session_state.get('cached_opportunities'):
            with st.spinner("Scanning markets and analyzing opportunities..."):
                # Run comprehensive analysis
                opportunities = run_top_opportunities_analysis(
                    dte_range=(dte_min, dte_max),
                    strategies=strategies,
                    use_discord=use_discord,
                    use_tradingview=use_tradingview,
                    use_tastytrade=use_tastytrade
                )
                
                st.session_state.cached_opportunities = opportunities
                st.session_state.last_update = datetime.now()
        
        # Display opportunities
        if st.session_state.get('cached_opportunities'):
            # Last update time
            if 'last_update' in st.session_state:
                st.caption(f"Last updated: {st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')}")
            
            for idx, trade in enumerate(st.session_state.cached_opportunities, 1):
                display_trade_recommendation(trade, idx)
        else:
            st.info("Click 'Analyze' to generate trade recommendations")
    
    # Auto-refresh logic
    if auto_refresh:
        time.sleep(1200)  # 20 minutes
        st.rerun()

def run_ticker_analysis(ticker: str, dte_range: tuple, strategies: List[str], 
                       use_discord: bool, use_tradingview: bool, use_tastytrade: bool) -> List[Dict]:
    """Run analysis for a specific ticker"""
    results = []
    
    try:
        # Gather data from Discord bots
        discord_data = {}
        if use_discord:
            discord_data = st.session_state.discord_analyzer.get_ticker_flow(ticker)
        
        # Get TradingView technical analysis
        tv_data = {}
        if use_tradingview:
            tv_data = st.session_state.tv_analyzer.analyze_ticker(ticker)
        
        # Get Tastytrade options data
        tastytrade_data = {}
        if use_tastytrade:
            tastytrade_data = st.session_state.tastytrade_fetcher.get_options_data(ticker, dte_range)
        
        # Run strategy engine
        recommendations = st.session_state.strategy_engine.generate_recommendations(
            ticker=ticker,
            discord_data=discord_data,
            tv_data=tv_data,
            tastytrade_data=tastytrade_data,
            dte_range=dte_range,
            preferred_strategies=strategies
        )
        
        results = recommendations
        
    except Exception as e:
        st.error(f"Error analyzing {ticker}: {str(e)}")
    
    return results

def run_top_opportunities_analysis(dte_range: tuple, strategies: List[str],
                                  use_discord: bool, use_tradingview: bool, use_tastytrade: bool) -> List[Dict]:
    """Run analysis to find top 5 trade opportunities"""
    
    # Default watchlist (can be customized)
    watchlist = ['SPY', 'QQQ', 'IWM', 'TSLA', 'AAPL', 'NVDA', 'MSFT', 'AMZN', 'META', 'GOOGL']
    
    all_opportunities = []
    
    for ticker in watchlist:
        try:
            opportunities = run_ticker_analysis(
                ticker=ticker,
                dte_range=dte_range,
                strategies=strategies,
                use_discord=use_discord,
                use_tradingview=use_tradingview,
                use_tastytrade=use_tastytrade
            )
            
            if opportunities:
                all_opportunities.extend(opportunities)
        
        except Exception as e:
            continue
    
    # Sort by conviction and return top 5
    all_opportunities.sort(key=lambda x: x.get('conviction_stars', 0), reverse=True)
    return all_opportunities[:5]

if __name__ == "__main__":
    main()

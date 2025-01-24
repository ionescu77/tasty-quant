import streamlit as st
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import os
from datetime import datetime, timedelta

# Set the title of the Streamlit app
st.title("Equity Options Trading Dashboard")

# Define the path to the data directory
DATA_DIR = 'data'

# Function to load the watchlist
@st.cache_data
def load_watchlist(filepath):
    """Load the positions watchlist CSV."""
    try:
        df = pd.read_csv(filepath)
        return df
    except Exception as e:
        st.error(f"Error loading watchlist: {e}")
        return pd.DataFrame()

# Function to extract all unique symbols from positions-quotes CSV files
@st.cache_data
def get_all_symbols(data_dir):
    """Extract all unique group_names from positions-quotes CSV files."""
    symbols = set()
    for filename in os.listdir(data_dir):
        if filename.startswith('positions-quotes') and filename.endswith('.csv'):
            file_path = os.path.join(data_dir, filename)
            try:
                df = pd.read_csv(file_path, usecols=['group_name'])
                symbols.update(df['group_name'].dropna().unique())
            except ValueError:
                st.warning(f"Required column 'group_name' not found in {filename}. Skipping.")
                continue
            except Exception as e:
                st.warning(f"Error reading {filename}: {e}. Skipping.")
                continue
    return sorted(list(symbols))

# Function to load and aggregate positions-quotes CSV files
@st.cache_data
def load_quotes(symbol, start_date, end_date):
    """
    Load and aggregate positions-quotes CSV files for the selected symbol and date range.
    """
    all_quotes = []
    for filename in os.listdir(DATA_DIR):
        if filename.startswith('positions-quotes') and filename.endswith('.csv'):
            # Extract date from filename
            try:
                file_date_str = filename.replace('positions-quotes-', '').replace('.csv', '')
                file_date = datetime.strptime(file_date_str, '%Y%m%d').date()
            except ValueError:
                st.warning(f"Filename {filename} does not match expected date format. Skipping.")
                continue

            if start_date <= file_date <= end_date:
                file_path = os.path.join(DATA_DIR, filename)
                try:
                    df = pd.read_csv(file_path)
                    # Filter by selected symbol
                    df = df[df['group_name'] == symbol]
                    all_quotes.append(df)
                except Exception as e:
                    st.warning(f"Error loading {filename}: {e}")
                    continue
    if all_quotes:
        combined_quotes = pd.concat(all_quotes, ignore_index=True)
        # Convert relevant columns to numeric, coercing errors to NaN
        numeric_cols = ['quantity', 'market_price', 'bid_price', 'ask_price', 'bid_size', 'ask_size']
        for col in numeric_cols:
            if col in combined_quotes.columns:
                combined_quotes[col] = pd.to_numeric(combined_quotes[col], errors='coerce')
            else:
                st.warning(f"Column '{col}' not found in quotes data.")
        return combined_quotes
    else:
        return pd.DataFrame()

# Function to load and aggregate strategy-mtm CSV files
@st.cache_data
def load_strategy_mtm(symbol, start_date, end_date):
    """
    Load and aggregate strategy-mtm CSV files for the selected symbol and date range.
    """
    all_mtm = []
    for filename in os.listdir(DATA_DIR):
        if filename.startswith('strategy-mtm') and filename.endswith('.csv'):
            # Extract date from filename
            try:
                file_date_str = filename.replace('strategy-mtm-', '').replace('.csv', '')
                file_date = datetime.strptime(file_date_str, '%Y%m%d').date()
            except ValueError:
                st.warning(f"Filename {filename} does not match expected date format. Skipping.")
                continue

            if start_date <= file_date <= end_date:
                file_path = os.path.join(DATA_DIR, filename)
                try:
                    df = pd.read_csv(file_path)
                    # Filter by selected symbol
                    df = df[df['group_name'] == symbol]
                    # Keep only 'timestamp' and 'net_value' columns
                    if 'timestamp' in df.columns and 'net_value' in df.columns:
                        df = df[['timestamp', 'net_value']]
                        all_mtm.append(df)
                    else:
                        st.warning(f"Required columns not found in {filename}. Skipping.")
                except Exception as e:
                    st.warning(f"Error loading {filename}: {e}")
                    continue
    if all_mtm:
        combined_mtm = pd.concat(all_mtm, ignore_index=True)
        # Convert 'net_value' to numeric, coercing errors to NaN
        if 'net_value' in combined_mtm.columns:
            combined_mtm['net_value'] = pd.to_numeric(combined_mtm['net_value'], errors='coerce')
        else:
            st.warning("Column 'net_value' not found in combined MTM data.")
        return combined_mtm
    else:
        return pd.DataFrame()

"""
    Claude sugggested to define function
"""

def filter_data_by_timeframe(df, timeframe):
    """Filter DataFrame based on selected timeframe."""
    if df.empty:
        return df

    current_time = pd.Timestamp.now()

    if timeframe == "Intraday":
        # Show only today's data
        start_time = current_time.normalize()  # Start of today
        return df[df['timestamp'].dt.date == current_time.date()]

    elif timeframe == "Weekly":
        # Show current week's data
        start_time = current_time - pd.Timedelta(days=current_time.dayofweek)
        return df[df['timestamp'] >= start_time]

    elif timeframe == "Monthly":
        # Show current month's data
        start_time = current_time.replace(day=1)
        return df[df['timestamp'] >= start_time]

    elif timeframe == "Year":
        # Show current year's data
        start_time = current_time.replace(month=1, day=1)
        return df[df['timestamp'] >= start_time]

    # Default case ("All"): return all data
    return df

# Load the watchlist
watchlist_path = os.path.join(DATA_DIR, 'positions-watchlist.csv')
watchlist_df = load_watchlist(watchlist_path)

# Extract all symbols from historical data
historical_symbols = get_all_symbols(DATA_DIR)

# Determine current symbols from watchlist
current_symbols = watchlist_df['group_name'].dropna().unique()

# Merge symbols from watchlist and historical data, ensuring uniqueness
all_symbols = sorted(list(set(historical_symbols)))

if not all_symbols:
    st.error("No symbols found in positions-quotes CSV files.")
else:
    # Sidebar - Symbol Selection
    st.sidebar.header("Filters")

    # Checkbox to toggle between active symbols and all symbols
    show_active_only = st.sidebar.checkbox("Show Active Symbols Only", value=False)

    if show_active_only:
        display_symbols = [f"{symbol}*" for symbol in current_symbols]
        symbol_mapping = {f"{symbol}*": symbol for symbol in current_symbols}
    else:
        display_symbols = [f"{symbol}*" if symbol in current_symbols else symbol for symbol in all_symbols]
        symbol_mapping = {f"{symbol}*": symbol for symbol in current_symbols}
        symbol_mapping.update({symbol: symbol for symbol in all_symbols if symbol not in current_symbols})

    # Enhanced Symbol Selection with Search Feature
    selected_symbol_display = st.sidebar.selectbox("Select Symbol", display_symbols)
    selected_symbol = symbol_mapping.get(selected_symbol_display, selected_symbol_display)

    # Sidebar - Time Range Selection
    st.sidebar.markdown("### Time Range Selection")
    time_range_type = st.sidebar.radio("Select Time Range Type", ["All", "Custom"])

    # Function to get available date range for the selected symbol
    @st.cache_data
    def get_symbol_date_range(symbol):
        """Get the minimum and maximum dates available for the selected symbol."""
        dates = []
        for filename in os.listdir(DATA_DIR):
            if filename.startswith('positions-quotes') and filename.endswith('.csv'):
                try:
                    file_date_str = filename.replace('positions-quotes-', '').replace('.csv', '')
                    file_date = datetime.strptime(file_date_str, '%Y%m%d').date()
                except ValueError:
                    continue
                # Check if the symbol exists in this file
                file_path = os.path.join(DATA_DIR, filename)
                try:
                    df = pd.read_csv(file_path, usecols=['group_name'])
                except ValueError:
                    continue
                if symbol not in df['group_name'].values:
                    continue
                dates.append(file_date)
        if dates:
            return min(dates), max(dates)
        else:
            return None, None

    min_available_date, max_available_date = get_symbol_date_range(selected_symbol)

    if time_range_type == "All":
        # Use the full date range available for the selected symbol
        start_date = min_available_date if min_available_date else datetime.now().date()
        end_date = max_available_date if max_available_date else datetime.now().date()
    else:
        # Custom date range selected by the user
        if min_available_date and max_available_date:
            default_start_date = min_available_date
            default_end_date = max_available_date
            start_date = st.sidebar.date_input("Start Date",
                                               min_value=min_available_date,
                                               max_value=max_available_date,
                                               value=min_available_date)
            end_date = st.sidebar.date_input("End Date",
                                             min_value=min_available_date,
                                             max_value=max_available_date,
                                             value=max_available_date)
        else:
            # Fallback to last 7 days if date range is unavailable
            default_end_date = datetime.now().date()
            default_start_date = default_end_date - timedelta(days=7)
            start_date = st.sidebar.date_input("Start Date", default_start_date)
            end_date = st.sidebar.date_input("End Date", default_end_date)

        # Validate date range
        if start_date > end_date:
            st.sidebar.error("Start Date must be before End Date.")

    # Sidebar - Timeframe and Interval Selection
    st.sidebar.markdown("### Timeframe and Interval Selection")
    timeframe = st.sidebar.selectbox(
        "Select Timeframe",
        ["All", "Year", "Monthly", "Weekly", "Intraday"],
        help="All: Show all available data\n"
             "Year: Show current year's data\n"
             "Monthly: Show current month's data\n"
             "Weekly: Show current week's data\n"
             "Intraday: Show today's data"
    )
    interval = st.sidebar.selectbox("Select Interval",
                                    ["1 Minute", "5 Minutes", "15 Minutes", "30 Minutes", "1 Hour",
                                     "Daily", "Weekly", "Monthly"])

    # Define resampling rule based on interval
    resample_mapping = {
        "1 Minute": "min",      # Changed from 'T' to 'min' to fix FutureWarning
        "5 Minutes": "5min",
        "15 Minutes": "15min",
        "30 Minutes": "30min",
        "1 Hour": "1h",
        "Daily": "D",
        "Weekly": "W",
        "Monthly": "M",
    }

    resample_rule = resample_mapping.get(interval, "D")  # Default to Daily if not found

    # Load data based on selections
    quotes_df = load_quotes(selected_symbol, start_date, end_date)
    strategy_mtm_df = load_strategy_mtm(selected_symbol, start_date, end_date)

    # Debugging: Option to show debugging information
    show_debug = st.sidebar.checkbox("Show Debugging Information")

    if show_debug:
        st.subheader("Debugging Information")
        st.write("### Quotes DataFrame:")
        st.write(quotes_df.head())
        st.write("### Quotes DataFrame Data Types:")
        st.write(quotes_df.dtypes)

        st.write("### Strategy MTM DataFrame:")
        st.write(strategy_mtm_df.head())
        st.write("### Strategy MTM DataFrame Data Types:")
        st.write(strategy_mtm_df.dtypes)

    """ Claude suggested: """
    # Filter data based on selected timeframe
    if timeframe != "All":
        # Filter quotes_df
        if not quotes_df.empty:
            quotes_df['timestamp'] = pd.to_datetime(quotes_df['timestamp'])
            quotes_df = filter_data_by_timeframe(quotes_df, timeframe)

        # Filter strategy_mtm_df
        if not strategy_mtm_df.empty:
            if 'timestamp' in strategy_mtm_df.columns:
                strategy_mtm_df['timestamp'] = pd.to_datetime(strategy_mtm_df['timestamp'])
            else:
                strategy_mtm_df = strategy_mtm_df.reset_index()
                strategy_mtm_df['timestamp'] = pd.to_datetime(strategy_mtm_df['timestamp'])
            strategy_mtm_df = filter_data_by_timeframe(strategy_mtm_df, timeframe)

        if quotes_df.empty and strategy_mtm_df.empty:
            st.warning(f"No data available for the selected {timeframe} timeframe.")
    """ End of Claude """

    # Check if quote data is available
    if quotes_df.empty:
        st.warning("No quote data available for the selected symbol and date range.")
    else:
        # Process Quotes DataFrame
        # Convert 'timestamp' to datetime if not already
        if not pd.api.types.is_datetime64_any_dtype(quotes_df['timestamp']):
            try:
                quotes_df['timestamp'] = pd.to_datetime(quotes_df['timestamp'], errors='coerce')
            except Exception as e:
                st.error(f"Error parsing timestamps in quotes data: {e}")
                quotes_df['timestamp'] = pd.to_datetime(quotes_df['timestamp'], errors='coerce')

        # Drop rows with invalid timestamps
        quotes_df = quotes_df.dropna(subset=['timestamp'])

        # Calculate mid_price
        if 'bid_price' in quotes_df.columns and 'ask_price' in quotes_df.columns:
            quotes_df['mid_price'] = (quotes_df['bid_price'] + quotes_df['ask_price']) / 2
        else:
            st.error("Columns 'bid_price' and/or 'ask_price' not found in quotes data.")
            quotes_df['mid_price'] = pd.NA

        # Ensure 'quantity' exists
        if 'quantity' not in quotes_df.columns:
            st.error("Column 'quantity' not found in quotes data.")
            quotes_df['quantity'] = 0  # Default to 0 to avoid NaN issues

        # No filtering for 0.00 and NaN values as per user request

        # Plot Price Evolution Chart with Dynamic Strategy
        st.header(f"Price Evolution for {selected_symbol}")

        # Create a subplot with 2 rows and 1 column
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            vertical_spacing=0.1,
                            subplot_titles=("Long and Short Positions", "Dynamic Strategy"))

        # Organize Sidebar Toggles without Expanders
        st.sidebar.markdown("### Long Position Series")
        show_long_bid = st.sidebar.checkbox("Show Long Bid", value=True, key="long_bid")
        show_long_ask = st.sidebar.checkbox("Show Long Ask", value=True, key="long_ask")
        show_long_mid = st.sidebar.checkbox("Show Long Mid Price", value=True, key="long_mid")

        st.sidebar.markdown("### Short Position Series")
        show_short_bid = st.sidebar.checkbox("Show Short Bid", value=True, key="short_bid")
        show_short_ask = st.sidebar.checkbox("Show Short Ask", value=True, key="short_ask")
        show_short_mid = st.sidebar.checkbox("Show Short Mid Price", value=True, key="short_mid")

        st.sidebar.markdown("### Strategy and Data")
        show_dynamic_strategy = st.sidebar.checkbox("Show Dynamic Strategy", value=True, key="dynamic_strategy")
        show_strategy_mtm = st.sidebar.checkbox("Show Strategy MTM Net Price", value=True, key="strategy_mtm")
        show_data_tables = st.sidebar.checkbox("Show Data Tables for Verification", value=True, key="data_tables")
        show_acquisition_price = st.sidebar.checkbox("Show Acquisition Price Line", value=True, key="acquisition_price")

        # Calculate Net Acquisition Price for the Selected Symbol
        acquisition_prices = watchlist_df[watchlist_df['group_name'] == selected_symbol]
        if not acquisition_prices.empty:
            net_acquisition_price = (acquisition_prices['quantity'] * acquisition_prices['open_price']).sum()
            average_open_price = (acquisition_prices['open_price']).mean()  # Optional: Average open price
        else:
            net_acquisition_price = None
            average_open_price = None
            st.warning("Acquisition price not found for the selected symbol.")

        # Filter Long and Short Positions
        long_positions = quotes_df[quotes_df['quantity'] > 0]
        short_positions = quotes_df[quotes_df['quantity'] < 0]

        # Plot Long Positions
        if not long_positions.empty:
            long_agg = long_positions.resample(resample_rule, on='timestamp').agg({
                'bid_price': 'mean',
                'ask_price': 'mean',
                'mid_price': 'mean'
            }).reset_index()

            if show_long_bid:
                fig.add_trace(go.Scatter(
                    x=long_agg['timestamp'],
                    y=long_agg['bid_price'],
                    mode='lines',
                    name='Long Bid',
                    line=dict(color='green'),
                    showlegend=True
                ), row=1, col=1)

            if show_long_ask:
                fig.add_trace(go.Scatter(
                    x=long_agg['timestamp'],
                    y=long_agg['ask_price'],
                    mode='lines',
                    name='Long Ask',
                    line=dict(color='red'),
                    showlegend=True
                ), row=1, col=1)

            if show_long_mid:
                fig.add_trace(go.Scatter(
                    x=long_agg['timestamp'],
                    y=long_agg['mid_price'],
                    mode='lines',
                    name='Long Mid Price',
                    line=dict(color='blue'),
                    showlegend=True
                ), row=1, col=1)
        else:
            st.info("No Long Positions data available for the selected parameters.")

        # Plot Short Positions
        if not short_positions.empty:
            short_agg = short_positions.resample(resample_rule, on='timestamp').agg({
                'bid_price': 'mean',
                'ask_price': 'mean',
                'mid_price': 'mean'
            }).reset_index()

            if show_short_bid:
                fig.add_trace(go.Scatter(
                    x=short_agg['timestamp'],
                    y=short_agg['bid_price'],
                    mode='lines',
                    name='Short Bid',
                    line=dict(color='orange'),
                    showlegend=True
                ), row=1, col=1)

            if show_short_ask:
                fig.add_trace(go.Scatter(
                    x=short_agg['timestamp'],
                    y=short_agg['ask_price'],
                    mode='lines',
                    name='Short Ask',
                    line=dict(color='purple'),
                    showlegend=True
                ), row=1, col=1)

            if show_short_mid:
                fig.add_trace(go.Scatter(
                    x=short_agg['timestamp'],
                    y=short_agg['mid_price'],
                    mode='lines',
                    name='Short Mid Price',
                    line=dict(color='pink'),
                    showlegend=True
                ), row=1, col=1)
        else:
            st.info("No Short Positions data available for the selected parameters.")

        # Plot Dynamic Strategy
        if show_dynamic_strategy:
            if not strategy_mtm_df.empty:
                # Process Strategy MTM DataFrame
                # Convert 'timestamp' to datetime if not already
                if not pd.api.types.is_datetime64_any_dtype(strategy_mtm_df['timestamp']):
                    try:
                        strategy_mtm_df['timestamp'] = pd.to_datetime(strategy_mtm_df['timestamp'], errors='coerce')
                    except Exception as e:
                        st.error(f"Error parsing timestamps in Strategy MTM data: {e}")
                        strategy_mtm_df['timestamp'] = pd.to_datetime(strategy_mtm_df['timestamp'], errors='coerce')

                # Drop rows with invalid timestamps
                strategy_mtm_df = strategy_mtm_df.dropna(subset=['timestamp'])

                # Sort by timestamp
                strategy_mtm_df = strategy_mtm_df.sort_values('timestamp')

                # Set 'timestamp' as index for resampling
                strategy_mtm_df = strategy_mtm_df.set_index('timestamp')

                # Resample
                if not strategy_mtm_df.empty:
                    try:
                        dynamic_strategy = strategy_mtm_df.resample(resample_rule).mean().reset_index()
                    except Exception as e:
                        st.error(f"Error during resampling Dynamic Strategy data: {e}")
                        dynamic_strategy = pd.DataFrame()
                else:
                    dynamic_strategy = pd.DataFrame()

                # No filtering for 0.00 and NaN values as per user request

                # Plot Dynamic Strategy
                if not dynamic_strategy.empty:
                    fig.add_trace(go.Scatter(
                        x=dynamic_strategy['timestamp'],
                        y=dynamic_strategy['net_value'],
                        mode='lines',
                        name='Dynamic Strategy',
                        line=dict(color='darkgreen'),
                        showlegend=True
                    ), row=2, col=1)

                    # Plot Acquisition Price Line if enabled
                    if show_acquisition_price and net_acquisition_price is not None:
                        # Ensure there are at least two points to plot the line
                        if not dynamic_strategy.empty:
                            acquisition_trace = go.Scatter(
                                x=[dynamic_strategy['timestamp'].min(), dynamic_strategy['timestamp'].max()],
                                y=[net_acquisition_price, net_acquisition_price],
                                mode='lines',
                                name='Acquisition Price',
                                line=dict(color='orange', dash='dash'),
                                hovertemplate=f'Acquisition Price: {net_acquisition_price:.2f}<extra></extra>',  # Correct hovertemplate
                                showlegend=True
                            )
                            fig.add_trace(acquisition_trace, row=2, col=1)
                else:
                    st.warning("No Dynamic Strategy data available after resampling.")
            else:
                st.info("No Strategy MTM data available for Dynamic Strategy.")
        else:
            st.info("Dynamic Strategy is hidden.")

        # Update layout for better aesthetics
        fig.update_layout(
            height=800,  # Adjust height as needed
            hovermode="x unified",  # Unified hover to show all hoverinfos at the same x
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        # Update y-axes titles
        fig.update_yaxes(title_text="Price", row=1, col=1)
        fig.update_yaxes(title_text="Dynamic Strategy Net Value", row=2, col=1)

        # Update x-axis title
        fig.update_xaxes(title_text="Timestamp", row=2, col=1)

        # Display the Plotly figure in Streamlit
        st.plotly_chart(fig, use_container_width=True)

        # Plot Strategy MTM Chart
        st.header(f"Strategy MTM for {selected_symbol}")

        if show_strategy_mtm and not strategy_mtm_df.empty:
            # Ensure 'net_value' is numeric
            strategy_mtm_df['net_value'] = pd.to_numeric(strategy_mtm_df['net_value'], errors='coerce')

            # Drop rows with NaN 'net_value'
            strategy_mtm_df = strategy_mtm_df.dropna(subset=['net_value'])

            # Reset index to have 'timestamp' as a column again
            strategy_mtm_df = strategy_mtm_df.reset_index()

            # Sort by timestamp
            strategy_mtm_df = strategy_mtm_df.sort_values('timestamp')

            # Resample Strategy MTM data
            if not strategy_mtm_df.empty:
                try:
                    strategy_mtm_agg = strategy_mtm_df.resample(resample_rule, on='timestamp').agg({
                        'net_value': 'mean'
                    }).reset_index()
                except Exception as e:
                    st.error(f"Error during resampling Strategy MTM data: {e}")
                    strategy_mtm_agg = pd.DataFrame()
            else:
                strategy_mtm_agg = pd.DataFrame()

            # No filtering for 0.00 and NaN values as per user request

            # Plot Strategy MTM
            if not strategy_mtm_agg.empty:
                fig_mtm = go.Figure()

                min_value = strategy_mtm_agg['net_value'].min()
                max_value = strategy_mtm_agg['net_value'].max()

                # Plot Strategy MTM Net Price
                fig_mtm.add_trace(go.Scatter(
                    x=strategy_mtm_agg['timestamp'],
                    y=strategy_mtm_agg['net_value'],
                    mode='lines',
                    name='Strategy MTM Net Price',
                    line=dict(color='darkgreen'),
                    showlegend=True
                ))

                # Add min value annotation
                fig_mtm.add_annotation(
                    x=strategy_mtm_agg.loc[strategy_mtm_agg['net_value'].idxmin(), 'timestamp'],
                    y=min_value,
                    text=f'Min: {min_value:.2f}',
                    showarrow=True,
                    arrowhead=1,
                    yshift=10
                )

                # Add max value annotation
                fig_mtm.add_annotation(
                    x=strategy_mtm_agg.loc[strategy_mtm_agg['net_value'].idxmax(), 'timestamp'],
                    y=max_value,
                    text=f'Max: {max_value:.2f}',
                    showarrow=True,
                    arrowhead=1,
                    yshift=-10
                )

                # Plot Acquisition Price Line if enabled and available
                if show_acquisition_price and net_acquisition_price is not None:
                    fig_mtm.add_trace(go.Scatter(
                        x=[strategy_mtm_agg['timestamp'].min(), strategy_mtm_agg['timestamp'].max()],
                        y=[net_acquisition_price, net_acquisition_price],
                        mode='lines',
                        name='Acquisition Price',
                        line=dict(color='orange', dash='dash'),
                        showlegend=True
                    ))

                # Update layout for better aesthetics
                fig_mtm.update_layout(
                    height=400,
                    hovermode="x unified",  # Unified hover to show all hoverinfos at the same x
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    ),
                    xaxis_title="Timestamp",
                    yaxis_title="Net Value"
                )

                # Display the Plotly figure in Streamlit
                st.plotly_chart(fig_mtm, use_container_width=True)
            else:
                st.warning("No data available after resampling Strategy MTM.")
        else:
            st.info("Strategy MTM Net Price is hidden or no data available.")

        # Display Aggregated Data for Verification
        if show_data_tables:
            st.header("Data Tables for Verification")

            if not quotes_df.empty:
                st.subheader("Quotes DataFrame")
                # Merge 'open_price' from watchlist into quotes_df
                merged_quotes = quotes_df.merge(acquisition_prices[['streamer_symbol', 'open_price']],
                                               on='streamer_symbol', how='left')
                st.dataframe(merged_quotes)

            if not strategy_mtm_df.empty:
                st.subheader("Strategy MTM DataFrame")
                st.dataframe(strategy_mtm_df)

            if 'long_agg' in locals() and not long_agg.empty:
                st.subheader("Long Positions Aggregated Data")
                st.dataframe(long_agg)

            if 'short_agg' in locals() and not short_agg.empty:
                st.subheader("Short Positions Aggregated Data")
                st.dataframe(short_agg)

            if 'dynamic_strategy' in locals() and not dynamic_strategy.empty:
                st.subheader("Dynamic Strategy Aggregated Data")
                st.dataframe(dynamic_strategy)

            if 'strategy_mtm_agg' in locals() and not strategy_mtm_agg.empty:
                st.subheader("Strategy MTM Aggregated Data")
                st.dataframe(strategy_mtm_agg)

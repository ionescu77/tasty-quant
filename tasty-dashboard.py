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
            start_date = st.sidebar.date_input(
                "Start Date",
                min_value=min_available_date,
                max_value=max_available_date,
                value=min_available_date
            )
            end_date = st.sidebar.date_input(
                "End Date",
                min_value=min_available_date,
                max_value=max_available_date,
                value=max_available_date
            )
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
    timeframe = st.sidebar.selectbox("Select Timeframe", ["All", "Year", "Monthly", "Weekly", "Intraday"])
    interval = st.sidebar.selectbox(
        "Select Interval",
        ["1 Minute", "5 Minutes", "15 Minutes", "30 Minutes", "1 Hour",
         "Daily", "Weekly", "Monthly"]
    )

    # Define resampling rule based on interval
    resample_mapping = {
        "1 Minute": "min",      # Replaced 'T' with 'min'
        "5 Minutes": "5min",    # Replaced '5T' with '5min'
        "15 Minutes": "15min",  # Replaced '15T' with '15min'
        "30 Minutes": "30min",  # Replaced '30T' with '30min'
        "1 Hour": "1h",
        "Daily": "D",
        "Weekly": "W",
        "Monthly": "ME",
    }

    resample_rule = resample_mapping.get(interval, "D")  # Default to Daily if not found

    # Load data based on selections
    quotes_df = load_quotes(selected_symbol, start_date, end_date)
    strategy_mtm_df = load_strategy_mtm(selected_symbol, start_date, end_date)

    # Check if quote data is available
    if quotes_df.empty:
        st.warning("No quote data available for the selected symbol and date range.")
    else:
        # Process Quotes DataFrame
        # Convert 'timestamp' to datetime if not already
        if 'timestamp' in quotes_df.columns:
            if not pd.api.types.is_datetime64_any_dtype(quotes_df['timestamp']):
                try:
                    quotes_df['timestamp'] = pd.to_datetime(quotes_df['timestamp'], errors='coerce')
                except Exception as e:
                    st.error(f"Error parsing timestamps in quotes data: {e}")
                    quotes_df['timestamp'] = pd.to_datetime(quotes_df['timestamp'], errors='coerce')
        else:
            st.error("Column 'timestamp' not found in quotes data.")
            quotes_df['timestamp'] = pd.NaT

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

        # Plot Price and Size Evolution Charts
        st.header(f"Price and Size Evolution for {selected_symbol}")

        # Create a subplot with 4 rows and 1 column
        fig = make_subplots(
            rows=4, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=(
                "Long Positions - Price",
                "Long Positions - Size",
                "Short Positions - Price",
                "Short Positions - Size"
            )
        )

        # Organize Sidebar Toggles without Expanders
        st.sidebar.markdown("### Long Position Series")
        show_long_bid = st.sidebar.checkbox("Show Long Bid Price", value=True, key="long_bid")
        show_long_ask = st.sidebar.checkbox("Show Long Ask Price", value=True, key="long_ask")
        show_long_mid = st.sidebar.checkbox("Show Long Mid Price", value=True, key="long_mid")
        show_long_bid_size = st.sidebar.checkbox("Show Long Bid Size", value=True, key="long_bid_size")
        show_long_ask_size = st.sidebar.checkbox("Show Long Ask Size", value=True, key="long_ask_size")

        st.sidebar.markdown("### Short Position Series")
        show_short_bid = st.sidebar.checkbox("Show Short Bid Price", value=True, key="short_bid")
        show_short_ask = st.sidebar.checkbox("Show Short Ask Price", value=True, key="short_ask")
        show_short_mid = st.sidebar.checkbox("Show Short Mid Price", value=True, key="short_mid")
        show_short_bid_size = st.sidebar.checkbox("Show Short Bid Size", value=True, key="short_bid_size")
        show_short_ask_size = st.sidebar.checkbox("Show Short Ask Size", value=True, key="short_ask_size")

        st.sidebar.markdown("### Strategy and Data")
        show_strategy_mtm = st.sidebar.checkbox("Show Strategy MTM Net Price", value=True, key="strategy_mtm")
        show_data_tables = st.sidebar.checkbox("Show Data Tables for Verification", value=True, key="data_tables")
        show_acquisition_price = st.sidebar.checkbox("Show Acquisition Price Line", value=True, key="acquisition_price")

        # Calculate Net Acquisition Price for the Selected Symbol
        acquisition_prices = watchlist_df[watchlist_df['group_name'] == selected_symbol]
        if not acquisition_prices.empty:
            net_acquisition_price = (acquisition_prices['quantity'] * acquisition_prices['open_price']).sum()
            average_open_price = acquisition_prices['open_price'].mean()  # Optional: Average open price
        else:
            net_acquisition_price = None
            average_open_price = None
            st.warning("Acquisition price not found for the selected symbol.")

        # Filter Long and Short Positions
        long_positions = quotes_df[quotes_df['quantity'] > 0]
        short_positions = quotes_df[quotes_df['quantity'] < 0]

        # Function to plot positions
        def plot_positions(positions, row_num, bid_price, ask_price, mid_price, bid_size, ask_size, position_type):
            """
            Plot price and size for given positions.
            """
            if not positions.empty:
                # Set 'timestamp' as index for resampling
                positions = positions.set_index('timestamp')

                # Aggregation includes bid_size and ask_size
                agg = positions.resample(resample_rule).agg({
                    'bid_price': 'mean',
                    'ask_price': 'mean',
                    'mid_price': 'mean',
                    'bid_size': 'mean',
                    'ask_size': 'mean'
                }).reset_index()

                # Plot Prices
                if bid_price:
                    color = 'green'
                    agg_price = agg['bid_price']
                    fig.add_trace(go.Scatter(
                        x=agg['timestamp'],
                        y=agg_price,
                        mode='lines',
                        name=f'{position_type} Bid Price',
                        line=dict(color=color),
                        showlegend=True
                    ), row=row_num, col=1)

                if ask_price:
                    color = 'red'
                    agg_price = agg['ask_price']
                    fig.add_trace(go.Scatter(
                        x=agg['timestamp'],
                        y=agg_price,
                        mode='lines',
                        name=f'{position_type} Ask Price',
                        line=dict(color=color),
                        showlegend=True
                    ), row=row_num, col=1)

                if mid_price:
                    color = 'blue'
                    agg_price = agg['mid_price']
                    fig.add_trace(go.Scatter(
                        x=agg['timestamp'],
                        y=agg_price,
                        mode='lines',
                        name=f'{position_type} Mid Price',
                        line=dict(color=color),
                        showlegend=True
                    ), row=row_num, col=1)

                # Plot Sizes
                if bid_size:
                    color = 'orange'  # Same color for both Long and Short Bid Size
                    agg_size = agg['bid_size']
                    fig.add_trace(go.Scatter(
                        x=agg['timestamp'],
                        y=agg_size,
                        mode='lines',
                        name=f'{position_type} Bid Size',
                        line=dict(color=color),
                        showlegend=True
                    ), row=row_num + 1, col=1)

                if ask_size:
                    color = 'purple'  # Same color for both Long and Short Ask Size
                    agg_size = agg['ask_size']
                    fig.add_trace(go.Scatter(
                        x=agg['timestamp'],
                        y=agg_size,
                        mode='lines',
                        name=f'{position_type} Ask Size',
                        line=dict(color=color),
                        showlegend=True
                    ), row=row_num + 1, col=1)
            else:
                st.info(f"No {position_type} Positions data available for the selected parameters.")

        # Plot Long Positions
        plot_positions(
            positions=long_positions,
            row_num=1,
            bid_price=show_long_bid,
            ask_price=show_long_ask,
            mid_price=show_long_mid,
            bid_size=show_long_bid_size,
            ask_size=show_long_ask_size,
            position_type='Long'
        )

        # Plot Short Positions
        plot_positions(
            positions=short_positions,
            row_num=3,
            bid_price=show_short_bid,
            ask_price=show_short_ask,
            mid_price=show_short_mid,
            bid_size=show_short_bid_size,
            ask_size=show_short_ask_size,
            position_type='Short'
        )

        # Update layout for better aesthetics
        fig.update_layout(
            height=1200,  # Adjusted height to accommodate 4 subplots
            hovermode="x unified",  # Unified hover to show all hoverinfos at the same x
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.15,
                xanchor="right",
                x=1
            ),
            title_text=f"Price and Size Evolution for {selected_symbol}"
        )

        # Update y-axes titles
        fig.update_yaxes(title_text="Price", row=1, col=1)
        fig.update_yaxes(title_text="Size", row=2, col=1)
        fig.update_yaxes(title_text="Price", row=3, col=1)
        fig.update_yaxes(title_text="Size", row=4, col=1)

        # Update x-axis title
        fig.update_xaxes(title_text="Timestamp", row=4, col=1)

        # Apply rangebreaks to hide weekends
        fig.update_xaxes(
            rangebreaks=[
                dict(bounds=["sat", "mon"])  # Hide weekends
            ]
        )

        # Display the Plotly figure in Streamlit
        st.plotly_chart(fig, use_container_width=True)

        # Plot Strategy MTM Chart
        st.header(f"Strategy MTM for {selected_symbol}")

        if show_strategy_mtm and not strategy_mtm_df.empty:
            # Ensure 'net_value' is numeric
            strategy_mtm_df['net_value'] = pd.to_numeric(strategy_mtm_df['net_value'], errors='coerce')

            # Drop rows with NaN 'net_value'
            strategy_mtm_df = strategy_mtm_df.dropna(subset=['net_value'])

            # Sort by timestamp
            if 'timestamp' in strategy_mtm_df.columns:
                if not pd.api.types.is_datetime64_any_dtype(strategy_mtm_df['timestamp']):
                    strategy_mtm_df['timestamp'] = pd.to_datetime(strategy_mtm_df['timestamp'], errors='coerce')
            else:
                st.error("Column 'timestamp' not found in Strategy MTM data.")
                strategy_mtm_df['timestamp'] = pd.NaT

            # Drop rows with invalid timestamps
            strategy_mtm_df = strategy_mtm_df.dropna(subset=['timestamp'])

            strategy_mtm_df = strategy_mtm_df.sort_values('timestamp')

            # Resample Strategy MTM data
            if 'timestamp' in strategy_mtm_df.columns:
                strategy_mtm_df = strategy_mtm_df.set_index('timestamp')
                try:
                    strategy_mtm_agg = strategy_mtm_df.resample(resample_rule).agg({'net_value': 'mean'}).reset_index()
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
                min_idx = strategy_mtm_agg['net_value'].idxmin()
                if pd.notna(min_idx):
                    fig_mtm.add_annotation(
                        x=strategy_mtm_agg.loc[min_idx, 'timestamp'],
                        y=strategy_mtm_agg.loc[min_idx, 'net_value'],
                        text=f'Min: {strategy_mtm_agg.loc[min_idx, "net_value"]:.2f}',
                        showarrow=True,
                        arrowhead=1,
                        yshift=10
                    )

                # Add max value annotation
                max_idx = strategy_mtm_agg['net_value'].idxmax()
                if pd.notna(max_idx):
                    fig_mtm.add_annotation(
                        x=strategy_mtm_agg.loc[max_idx, 'timestamp'],
                        y=strategy_mtm_agg.loc[max_idx, 'net_value'],
                        text=f'Max: {strategy_mtm_agg.loc[max_idx, "net_value"]:.2f}',
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

                # Apply rangebreaks to hide weekends
                fig_mtm.update_xaxes(
                    rangebreaks=[
                        dict(bounds=["sat", "mon"])  # Hide weekends
                    ]
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
                # Merge 'open_price' from watchlist into quotes_df if applicable
                if 'streamer_symbol' in quotes_df.columns and 'open_price' in acquisition_prices.columns:
                    merged_quotes = quotes_df.merge(acquisition_prices[['streamer_symbol', 'open_price']],
                                                   on='streamer_symbol', how='left')
                    st.dataframe(merged_quotes)
                else:
                    st.warning("Required columns for merging 'open_price' not found.")
                    st.dataframe(quotes_df)

            if not strategy_mtm_df.empty:
                st.subheader("Strategy MTM DataFrame")
                st.dataframe(strategy_mtm_df)

            # Display aggregated data if available
            if 'long_positions' in locals() and not long_positions.empty:
                st.subheader("Long Positions DataFrame")
                st.dataframe(long_positions)

            if 'short_positions' in locals() and not short_positions.empty:
                st.subheader("Short Positions DataFrame")
                st.dataframe(short_positions)

            if 'strategy_mtm_agg' in locals() and not strategy_mtm_agg.empty:
                st.subheader("Strategy MTM Aggregated Data")
                st.dataframe(strategy_mtm_agg)

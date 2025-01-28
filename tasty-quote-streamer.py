import asyncio
import signal
import sys
from decimal import Decimal
from typing import List, Dict
from datetime import datetime, timezone

import pandas as pd
import yaml
from tastytrade import Session, DXLinkStreamer
from tastytrade.dxfeed import Quote

import os
import logging

from utils import RenewableSession

# --------------------- Configuration Loading ---------------------

def load_config(config_file: str) -> Dict:
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        print(f"Configuration file {config_file} not found.")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing the configuration file: {e}")
        sys.exit(1)

config = load_config('tasty-quote-streamer.yaml')

# --------------------- Logging Setup ---------------------

def setup_logging(logging_config: Dict):
    log_level = getattr(logging, logging_config.get('level', 'INFO').upper(), logging.INFO)
    log_file = logging_config.get('file', 'tasty-quote-streamer.log')

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)  # Optionally, also log to console
        ]
    )
    # Override the tastytrade logger to INFO level to suppress DEBUG messages
    tastytrade_logger = logging.getLogger('tastytrade')
    tastytrade_logger.setLevel(logging.INFO)

setup_logging(config.get('logging', {}))

# --------------------- Global Variables ---------------------

# Shared dictionary to store latest quotes
quotes_data: Dict[str, Quote] = {}

# Flag to control shutdown
shutdown_flag = asyncio.Event()

# --------------------- Helper Functions ---------------------

def get_today_date() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%d')

def get_current_iso_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()

def ensure_directory(directory: str):
    try:
        os.makedirs(directory, exist_ok=True)
        logging.debug(f"Ensured directory exists: {directory}")
    except Exception as e:
        logging.exception(f"Failed to create directory {directory}: {e}")
        sys.exit(1)

def get_csv_path(directory: str, template: str) -> str:
    filename = template.format(date=get_today_date())
    return os.path.join(directory, filename)

def initialize_output_files(output_dir: str, strategy_csv: str, positions_csv: str):
    # Ensure output directory exists
    ensure_directory(output_dir)

    # Initialize Strategy CSV
    if not os.path.exists(strategy_csv):
        try:
            pd.DataFrame(columns=['timestamp', 'group_name', 'net_value']).to_csv(strategy_csv, index=False)
            logging.info(f"Created Strategy CSV: {strategy_csv}")
        except Exception as e:
            logging.exception(f"Failed to create Strategy CSV {strategy_csv}: {e}")

    # Initialize Positions Quotes CSV
    if not os.path.exists(positions_csv):
        try:
            pd.DataFrame(columns=[
                'timestamp', 'group_name', 'streamer_symbol', 'quantity','open_price',
                'market_price', 'bid_price', 'ask_price', 'bid_size', 'ask_size'
            ]).to_csv(positions_csv, index=False)
            logging.info(f"Created Positions Quotes CSV: {positions_csv}")
        except Exception as e:
            logging.exception(f"Failed to create Positions Quotes CSV {positions_csv}: {e}")

async def write_strategy_csv(strategy_csv: str, net_credit_debit: pd.DataFrame):
    timestamp = get_current_iso_timestamp()
    net_credit_debit['timestamp'] = timestamp
    # Reorder columns to have timestamp first
    columns = ['timestamp', 'group_name', 'net_value']
    data_to_write = net_credit_debit[columns]
    try:
        data_to_write.to_csv(strategy_csv, mode='a', header=False, index=False)
        logging.debug(f"Appended to Strategy CSV: {strategy_csv}")
    except Exception as e:
        logging.exception(f"Failed to append to Strategy CSV {strategy_csv}: {e}")

async def write_positions_csv(positions_csv: str, df: pd.DataFrame):
    timestamp = get_current_iso_timestamp()
    # Merge the DataFrame with quotes_data to get bid and ask details
    df_quotes = df.merge(
        pd.DataFrame.from_dict({k: {
            'bid_price': v.bid_price,
            'ask_price': v.ask_price,
            'bid_size': v.bid_size,
            'ask_size': v.ask_size
        } for k, v in quotes_data.items()}, orient='index'),
        left_on='streamer_symbol',
        right_index=True,
        how='left'
    )

    # Ensure required columns are present
    required_columns = ['bid_price', 'ask_price', 'bid_size', 'ask_size', 'open_price']
    for col in required_columns:
        if col not in df_quotes.columns:
            df_quotes[col] = Decimal('0')
    df_quotes[required_columns] = df_quotes[required_columns].fillna(Decimal('0'))

    # Prepare the data to write
    df_quotes['timestamp'] = timestamp
    columns = [
        'timestamp', 'group_name', 'streamer_symbol', 'quantity','open_price',
        'market_price', 'bid_price', 'ask_price', 'bid_size', 'ask_size'
    ]
    data_to_write = df_quotes[columns].copy()

    # Convert Decimal to float for CSV
    for column in ['bid_price', 'ask_price', 'bid_size', 'ask_size', 'open_price']:
        data_to_write[column] = data_to_write[column].astype(float)

    try:
        data_to_write.to_csv(positions_csv, mode='a', header=False, index=False)
        logging.debug(f"Appended to Positions Quotes CSV: {positions_csv}")
    except Exception as e:
        logging.exception(f"Failed to append to Positions Quotes CSV {positions_csv}: {e}")

def calculate_strategy_net_credit_debit(df: pd.DataFrame) -> pd.DataFrame:
    df['net_value'] = df['market_price'] * df['quantity']
    grouped = df.groupby('group_name')['net_value'].sum().reset_index()
    return grouped

async def update_market_prices(df: pd.DataFrame):
    """
    Update the market prices in the DataFrame based on the latest quotes_data.
    Utilizes vectorized operations for performance optimization.
    """
    # Create a pandas Series from the prices_data
    prices_series = pd.Series({symbol: (float(quote.bid_price) + float(quote.ask_price)) / 2
                               if quote.bid_price and quote.ask_price else 0.0
                               for symbol, quote in quotes_data.items()})

    # Map the 'streamer_symbol' to their latest market prices, filling missing with 0.0
    df['market_price'] = df['streamer_symbol'].map(prices_series).fillna(0.0)

async def process_quotes(streamer: DXLinkStreamer):
    """
    Coroutine to process incoming quotes and update the quotes_data dictionary.
    """
    try:
        async for quote in streamer.listen(Quote):
            if quote and quote.event_symbol:
                quotes_data[quote.event_symbol] = quote
                logging.debug(f"Received quote for {quote.event_symbol}")
    except asyncio.CancelledError:
        logging.info("Quote processing task has been cancelled.")
    except Exception as e:
        logging.exception(f"Error in process_quotes: {e}")

async def periodic_task(df: pd.DataFrame, output_dir: str, symbols: List[str]):
    """
    Periodically update market prices, calculate net credit/debit, and write to CSVs.
    """
    strategy_template = config['output']['strategy_filename_template']
    positions_template = config['output']['positions_filename_template']
    strategy_csv = get_csv_path(output_dir, strategy_template)
    positions_csv = get_csv_path(output_dir, positions_template)

    # Initialize output CSV files if they don't exist
    initialize_output_files(output_dir, strategy_csv, positions_csv)
    logging.info(f"Initializing output files: {strategy_csv}, {positions_csv}")

    # Wait until all symbols have received bid and ask data
    logging.info("Waiting for all symbols to receive bid & ask data before starting calculations...")
    while True:
        missing_symbols = [symbol for symbol in symbols if symbol not in quotes_data or
                           not quotes_data[symbol].bid_price or
                           not quotes_data[symbol].ask_price]
        if not missing_symbols:
            logging.info("All symbols have received bid & ask data. Starting calculations.")
            break
        logging.info(f"Still waiting for data on symbols: {missing_symbols}")
        await asyncio.sleep(5)  # Wait for 5 seconds before rechecking

    while not shutdown_flag.is_set():
        try:
            logging.info("Updating Market Prices...")
            await update_market_prices(df)
            net_credit_debit = calculate_strategy_net_credit_debit(df)
            logging.info("Net Credit/Debit Per Strategy:")
            logging.info(net_credit_debit.to_string(index=False))

            # Filter symbols with complete bid & ask data
            available_symbols = [symbol for symbol in symbols if symbol in quotes_data and
                                 quotes_data[symbol].bid_price and
                                 quotes_data[symbol].ask_price]
            missing_symbols = [symbol for symbol in symbols if symbol not in available_symbols]

            if missing_symbols:
                logging.warning(f"Missing bid & ask data for symbols: {missing_symbols}. Skipping their net_value calculation.")

            # Proceed only with available symbols
            if available_symbols:
                filtered_df = df[df['streamer_symbol'].isin(available_symbols)].copy()
                # Calculate net_value only for available symbols
                filtered_net_credit_debit = calculate_strategy_net_credit_debit(filtered_df)
                await write_strategy_csv(strategy_csv, filtered_net_credit_debit)
                await write_positions_csv(positions_csv, filtered_df)
                logging.debug(filtered_df[['group_name', 'streamer_symbol', 'quantity', 'market_price']].to_string(index=False))
            else:
                logging.warning("No symbols have complete bid & ask data for this cycle. Skipping CSV write.")

        except Exception as e:
            logging.exception(f"Error in periodic_task: {e}")

        # Sleep for 60 seconds or until shutdown is triggered
        try:
            await asyncio.wait_for(shutdown_flag.wait(), timeout=60.0)
        except asyncio.TimeoutError:
            continue

def handle_shutdown():
    """
    Signal handler to initiate graceful shutdown.
    """
    logging.info("Received stop signal. Initiating graceful shutdown...")
    shutdown_flag.set()

def load_symbols_from_portfolio(portfolio_file: str) -> (List[str], pd.DataFrame):
    try:
        df = pd.read_csv(portfolio_file)
        symbols = df['streamer_symbol'].dropna().unique().tolist()
        logging.info(f"Loaded symbols from portfolio: {symbols}")
        return symbols, df
    except FileNotFoundError:
        logging.error(f"Portfolio file {portfolio_file} not found.")
        sys.exit(1)
    except pd.errors.EmptyDataError:
        logging.error(f"Portfolio file {portfolio_file} is empty.")
        sys.exit(1)
    except Exception as e:
        logging.exception(f"Error loading portfolio CSV: {e}")
        sys.exit(1)

async def main():
    """
    Main coroutine to set up the session, streamer, and manage tasks.
    """
    portfolio_file = config['portfolio']['file']
    output_dir = config['output']['directory']

    symbols, df = load_symbols_from_portfolio(portfolio_file)

    if config['streaming'].get('symbols'):
        # Override symbols if specified in the config file
        symbols = config['streaming']['symbols']
        logging.info(f"Overriding symbols from config: {symbols}")

    if not symbols:
        logging.error("No symbols available to subscribe.")
        sys.exit(1)

    # Initialize market_price column
    df['market_price'] = 0.0

    # Register signal handlers for graceful shutdown within the main coroutine
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_shutdown)

    # Create a TastyTrade session with error handling
    try:
        session = RenewableSession()
    except Exception as e:
        logging.exception(f"Failed to create TastyTrade session: {e}")
        sys.exit(1)

    # Start the streamer and manage tasks
    async with DXLinkStreamer(session) as streamer:
        try:
            await streamer.subscribe(Quote, symbols)
            logging.info(f"Subscribed to quotes for symbols: {symbols}")
        except Exception as e:
            logging.exception(f"Failed to subscribe to quotes: {e}")
            return

        # Start quote processing task
        quote_task = asyncio.create_task(process_quotes(streamer))

        # Start periodic update task
        periodic_update_task = asyncio.create_task(periodic_task(df, output_dir, symbols))

        # Wait until shutdown is triggered
        await shutdown_flag.wait()

        # Cancel tasks gracefully
        tasks = [quote_task, periodic_update_task]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

        logging.info("Shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.exception(f"An error occurred: {e}")
    finally:
        logging.info("Event loop closed.")

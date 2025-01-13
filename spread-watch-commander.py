import asyncio
from decimal import Decimal
import pandas as pd
from typing import Dict  # Added import for typing
from tastytrade import Session, DXLinkStreamer
from tastytrade.dxfeed import Quote
import os
import argparse  # Import argparse for argument parsing
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from datetime import datetime

# Initialize Rich console
console = Console()

# Setup environment variables for Tastytrade credentials
TASTYTRADE_USERNAME = os.environ.get('TASTY_USER', '')
TASTYTRADE_PASSWORD = os.environ.get('TASTY_PASS', '')

DATA_FILE = "data/positions-watchlist.csv"  # Example path to the CSV data file

async def process_quotes(streamer: DXLinkStreamer, prices: dict[str, Decimal], update_event):
    """Listen to live quotes and update current prices."""
    async for quote in streamer.listen(Quote):
        if quote and quote.bid_price is not None and quote.ask_price is not None:
            market_price = (quote.bid_price + quote.ask_price) / 2
            prices[quote.event_symbol] = market_price
        update_event.set()  # Notify an update has occurred

def calculate_strategy_net_credit_debit(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate net value of strategies based on market prices."""
    df['net_value'] = df['market_price'] * df['quantity']
    return df.groupby('group_name')['net_value'].sum().reset_index()

async def async_main(df, prices: Dict[str, Decimal], session, show_strategies: bool, show_details: bool):
    """Main asynchronous loop to update and display market data."""
    previous_prices = {symbol: 0 for symbol in df['streamer_symbol']}
    previous_net_values = {}
    symbol_list = df['streamer_symbol'].tolist()

    update_event = asyncio.Event()
    last_update_time = datetime.now()

    async with DXLinkStreamer(session) as streamer:
        await streamer.subscribe(Quote, symbol_list)
        asyncio.create_task(process_quotes(streamer, prices, update_event))

        while True:
            # Wait for the update event to be set
            await update_event.wait()
            update_event.clear()

            # Record the last update time
            last_update_time = datetime.now()

            # Update market prices
            for symbol in prices:
                current_price = float(prices[symbol])
                df.loc[df['streamer_symbol'] == symbol, 'market_price'] = current_price

            net_credit_debit = calculate_strategy_net_credit_debit(df)

            # Clear screen and build a table
            console.clear()
            header_text = Text("Portfolio Strategy Monitor", style="bold underline")
            console.rule(header_text)

            # Display CSV file information
            file_info = Text(f"Data Source: {DATA_FILE}", style="bold yellow")
            console.print(file_info)

            # Conditionally display Strategy table
            if show_strategies:
                table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
                table.add_column("Group Name", style="dim", width=12)
                table.add_column("Net Credit/Debit", justify="right")

                for idx, row in net_credit_debit.iterrows():
                    previous_net_value = previous_net_values.get(row['group_name'], 0)
                    if row['net_value'] > previous_net_value:
                        color = "green"
                    elif row['net_value'] < previous_net_value:
                        color = "red"
                    else:
                        color = "white"

                    table.add_row(row['group_name'], f"[{color}]{row['net_value']:.2f}[/{color}]")
                    previous_net_values[row['group_name']] = row['net_value']

                console.print(table)

            # Conditionally display Detail table
            if show_details:
                detail_table = Table(show_header=True, header_style="bold cyan", box=box.SIMPLE)
                detail_table.add_column("Group Name", style="dim", width=12)
                detail_table.add_column("Symbol", style="bold")
                detail_table.add_column("Quantity", justify="right")
                detail_table.add_column("Market Price", justify="right")

                for idx, row in df.iterrows():
                    current_price = row['market_price']
                    prev_price = previous_prices[row['streamer_symbol']]
                    color = "green" if current_price > prev_price else "red" if current_price < prev_price else "white"

                    detail_table.add_row(
                        row['group_name'],
                        row['streamer_symbol'],
                        str(row['quantity']),
                        f"[{color}]{current_price:.2f}[/{color}]"
                    )

                    # Update previous prices
                    previous_prices[row['streamer_symbol']] = current_price

                console.print(detail_table)

            # Display current time without seconds and seconds since last update
            current_time = datetime.now().strftime("%H:%M")
            seconds_since_last_update = (datetime.now() - last_update_time).seconds
            update_message = f"Current time: {current_time} | Last update: {seconds_since_last_update}s ago"

            console.print(update_message)

            # Press Ctrl+C message
            quit_message = Panel(Text("Press Ctrl+C to quit", justify="center", style="bold white on blue"), title="Instruction")
            console.print(quit_message)

            await asyncio.sleep(1)  # Keep refreshing every second for real-time updates

def main():
    parser = argparse.ArgumentParser(description="Real-time Option Tickers Display")
    parser.add_argument(
        '--strategies',
        action='store_true',
        help='Display the strategy table'
    )
    parser.add_argument(
        '--details',
        action='store_true',
        help='Display the details table'
    )
    args = parser.parse_args()

    # Determine which tables to display
    if not args.strategies and not args.details:
        # Default behavior: display strategies only
        show_strategies = True
        show_details = False
    else:
        show_strategies = args.strategies
        show_details = args.details

    session = Session(TASTYTRADE_USERNAME, TASTYTRADE_PASSWORD)
    df = pd.read_csv(DATA_FILE)
    df['market_price'] = 0.0
    prices: Dict[str, Decimal] = {}

    try:
        asyncio.run(async_main(df, prices, session, show_strategies, show_details))
    except KeyboardInterrupt:
        console.print("\n[bold red]Exiting...[/bold red]")

if __name__ == "__main__":
    main()

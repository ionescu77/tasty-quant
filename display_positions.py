# display_positions.py

import asyncio
from decimal import Decimal
import pandas as pd
from typing import Dict
from tastytrade import Session, DXLinkStreamer
from tastytrade.dxfeed import Quote
import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from datetime import datetime
import argparse
import cProfile
import pstats

from utils import RenewableSession

# Initialize Rich console
console = Console()

# Path to the CSV positions data file
DATA_FILE = "data/positions-watchlist.csv"

async def process_quotes(streamer: DXLinkStreamer, prices: dict[str, Decimal], update_event):
    """Listen to live quotes and update current prices."""
    async for quote in streamer.listen(Quote):
        if quote and quote.bid_price is not None and quote.ask_price is not None:
            market_price = (quote.bid_price + quote.ask_price) / 2
            prices[quote.event_symbol] = market_price
        update_event.set()  # Notify an update has occurred

async def async_main(df, prices: Dict[str, Decimal], session, show_details: bool):
    """Main asynchronous loop to update and display position details."""
    previous_prices = {symbol: 0 for symbol in df['streamer_symbol']}
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

            # Clear screen and build a table
            console.clear()
            header_text = Text("Portfolio Positions Monitor", style="bold underline")
            console.rule(header_text)

            # Display CSV file information
            file_info = Text(f"Data Source: {DATA_FILE}", style="bold yellow")
            console.print(file_info)

            # Display Detail table
            if show_details:
                detail_table = Table(show_header=True, header_style="bold cyan", box=box.SIMPLE)
                detail_table.add_column("Group Name", style="dim", width=12)
                detail_table.add_column("Symbol", style="bold")
                detail_table.add_column("Quantity", justify="right")
                detail_table.add_column("Market Price", justify="right")

                for idx, row in df.iterrows():
                    current_price = row['market_price']
                    prev_price = previous_prices[row['streamer_symbol']]

                    # Determine color based on price change
                    if current_price > prev_price:
                        color = "green"
                    elif current_price < prev_price:
                        color = "red"
                    else:
                        color = "white"

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
    parser = argparse.ArgumentParser(description="Real-time Positions Display")
    parser.add_argument(
        '--profile',
        action='store_true',
        help='Enable profiling with cProfile'
    )
    args = parser.parse_args()

    session = RenewableSession()
    df = pd.read_csv(DATA_FILE)
    df['market_price'] = 0.0
    prices: Dict[str, Decimal] = {}

    if args.profile:
        # Profile the async_main function
        profiler = cProfile.Profile()
        profiler.enable()

    try:
        asyncio.run(async_main(df, prices, session, show_details=True))
    except KeyboardInterrupt:
        console.print("\n[bold red]Exiting...[/bold red]")
    finally:
        if args.profile:
            profiler.disable()
            # Save profiling results to a file
            profiler.dump_stats('positions_profile.prof')
            console.print("[yellow]Profiling complete. Check 'positions_profile.prof' for details.[/yellow]")

if __name__ == "__main__":
    main()

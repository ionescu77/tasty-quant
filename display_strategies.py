# display_strategies.py

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

def calculate_strategy_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate net value, initial net, P&L amount, P&L percentage, and net open price per contract for each strategy group.

    Args:
        df (pd.DataFrame): DataFrame containing position data with 'group_name',
                           'quantity', 'market_price', and 'open_price'.

    Returns:
        pd.DataFrame: DataFrame with calculated metrics per 'group_name'.
    """
    # Calculate current net value: sum of (market_price * quantity) per group
    df['net_value'] = df['market_price'] * df['quantity']
    current_net = df.groupby('group_name')['net_value'].sum().reset_index(name='current_net')

    # Calculate initial net value: sum of (open_price * quantity) per group
    df['initial_net'] = df['open_price'] * df['quantity']
    initial_net = df.groupby('group_name')['initial_net'].sum().reset_index(name='initial_net')

    # Merge current net and initial net into a single DataFrame
    metrics = pd.merge(current_net, initial_net, on='group_name')

    # Calculate P&L Amount: current_net - initial_net
    metrics['pl_amount'] = metrics['current_net'] - metrics['initial_net']

    # Calculate P&L Percentage: (pl_amount / |initial_net|) * 100
    metrics['pl_percentage'] = (metrics['pl_amount'] / metrics['initial_net'].abs()) * 100
    metrics['pl_percentage'] = metrics['pl_percentage'].fillna(0)  # Handle division by zero

    # Calculate total quantity per group for long positions (quantity > 0)
    long_positions = df[df['quantity'] > 0]
    total_quantity = long_positions.groupby('group_name')['quantity'].sum().reset_index(name='total_quantity')

    # Merge total quantity into metrics
    metrics = pd.merge(metrics, total_quantity, on='group_name', how='left')

    # Calculate Net Open Price per Contract
    metrics['net_open_price'] = metrics.apply(
        lambda row: row['initial_net'] / row['total_quantity'] if row['total_quantity'] != 0 else 0,
        axis=1
    )

    return metrics

async def process_quotes(streamer: DXLinkStreamer, prices: dict[str, Decimal], update_event):
    """Listen to live quotes and update current prices."""
    async for quote in streamer.listen(Quote):
        if quote and quote.bid_price is not None and quote.ask_price is not None:
            market_price = (quote.bid_price + quote.ask_price) / 2
            prices[quote.event_symbol] = market_price
        update_event.set()  # Notify an update has occurred

async def async_main(df, prices: Dict[str, Decimal], session, show_strategies: bool):
    """Main asynchronous loop to update and display strategy metrics."""
    previous_metrics = {}
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

            # Calculate strategy metrics including P&L
            strategy_metrics = calculate_strategy_metrics(df)

            # Clear screen and build a table
            console.clear()
            header_text = Text("Portfolio Strategy Monitor", style="bold underline")
            console.rule(header_text)

            # Display CSV file information
            file_info = Text(f"Data Source: {DATA_FILE}", style="bold yellow")
            console.print(file_info)

            # Display Strategy table with P&L
            if show_strategies:
                table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
                table.add_column("Group Name", style="dim", width=12)
                table.add_column("Net Credit/Debit", justify="right")
                table.add_column("Net Open Price", justify="right")
                table.add_column("P&L Amount", justify="right")
                table.add_column("P&L %", justify="right")

                for idx, row in strategy_metrics.iterrows():
                    # Determine color based on P&L Amount
                    if row['pl_amount'] > 0:
                        color = "green"
                    elif row['pl_amount'] < 0:
                        color = "red"
                    else:
                        color = "white"

                    # Format P&L Amount and Percentage
                    pl_amount_str = f"[{color}]{row['pl_amount']:.2f}[/{color}]"
                    pl_percentage_str = f"[{color}]{row['pl_percentage']:.2f}%[/{color}]"

                    table.add_row(
                        row['group_name'],
                        f"{row['current_net']:.2f}",
                        f"{row['net_open_price']:.2f}",
                        pl_amount_str,
                        pl_percentage_str
                    )

                    # Update previous metrics
                    previous_metrics[row['group_name']] = row['current_net']

                console.print(table)

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
    parser = argparse.ArgumentParser(description="Real-time Strategy Monitor Display")
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
        asyncio.run(async_main(df, prices, session, show_strategies=True))
    except KeyboardInterrupt:
        console.print("\n[bold red]Exiting...[/bold red]")
    finally:
        if args.profile:
            profiler.disable()
            # Save profiling results to a file
            profiler.dump_stats('strategies_profile.prof')
            console.print("[yellow]Profiling complete. Check 'strategies_profile.prof' for details.[/yellow]")

if __name__ == "__main__":
    main()
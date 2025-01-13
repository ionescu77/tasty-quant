import asyncio
from decimal import Decimal
import pandas as pd
from tastytrade import Session, DXLinkStreamer
from tastytrade.dxfeed import Quote
import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.columns import Columns  # Import Columns
from datetime import datetime
from typing import Dict  # Ensure Dict is imported

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

def chunk_dataframe(df: pd.DataFrame, chunk_size: int) -> list[pd.DataFrame]:
    """Split the dataframe into chunks of specified size."""
    return [df.iloc[i:i + chunk_size] for i in range(0, len(df), chunk_size)]

async def async_main(df, prices, session):
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

            # Clear screen and build a layout
            console.clear()
            header_text = Text("Portfolio Strategy Monitor", style="bold underline")
            console.rule(header_text)

            # Display CSV file information
            file_info = Text(f"Data Source: {DATA_FILE}", style="bold yellow")
            console.print(file_info)

            # Strategy table
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

            # Detail tables split into multiple columns
            chunk_size = 10  # Number of positions per column
            detail_chunks = chunk_dataframe(df, chunk_size)
            detail_tables = []

            for chunk in detail_chunks:
                detail_table = Table(show_header=True, header_style="bold cyan", box=box.SIMPLE, show_lines=True)
                detail_table.add_column("Group Name", style="dim", width=12)
                detail_table.add_column("Symbol", style="bold")
                detail_table.add_column("Quantity", justify="right")
                detail_table.add_column("Market Price", justify="right")

                for idx, row in chunk.iterrows():
                    current_price = row['market_price']
                    prev_price = previous_prices[row['streamer_symbol']]
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

                detail_tables.append(detail_table)

            # Arrange detail tables in columns
            columns = Columns(detail_tables, equal=True)
            console.print(columns)

            # Display current time without seconds and seconds since last update
            current_time = datetime.now().strftime("%H:%M")
            seconds_since_last_update = (datetime.now() - last_update_time).seconds
            update_message = f"Current time: {current_time} | Last update: {seconds_since_last_update}s ago"

            console.print(update_message)

            # Press Ctrl+C message
            quit_message = Panel(
                Text("Press Ctrl+C to quit", justify="center", style="bold white on blue"),
                title="Instruction",
                expand=False
            )
            console.print(quit_message)

            await asyncio.sleep(1)  # Keep refreshing every second for real-time updates

def main():
    session = Session(TASTYTRADE_USERNAME, TASTYTRADE_PASSWORD)
    df = pd.read_csv(DATA_FILE)
    df['market_price'] = 0.0
    prices: Dict[str, Decimal] = {}

    try:
        asyncio.run(async_main(df, prices, session))
    except KeyboardInterrupt:
        console.print("\n[bold red]Exiting...[/bold red]")

if __name__ == "__main__":
    main()

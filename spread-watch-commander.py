import asyncio
from decimal import Decimal
import pandas as pd
from tastytrade import Session, DXLinkStreamer
from tastytrade.dxfeed import Quote
import os
from rich.console import Console
from rich.table import Table
from rich import box

# Initialize Rich console
console = Console()

# Setup environment variables for Tastytrade credentials
TASTYTRADE_USERNAME = os.environ.get('TASTY_USER', '')
TASTYTRADE_PASSWORD = os.environ.get('TASTY_PASS', '')

async def process_quotes(streamer: DXLinkStreamer, prices: dict[str, Decimal]):
    """Listen to live quotes and update current prices."""
    async for quote in streamer.listen(Quote):
        if quote and quote.bid_price is not None and quote.ask_price is not None:
            market_price = (quote.bid_price + quote.ask_price) / 2
            prices[quote.event_symbol] = market_price

def calculate_strategy_net_credit_debit(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate net value of strategies based on market prices."""
    df['net_value'] = df['market_price'] * df['quantity']
    return df.groupby('group_name')['net_value'].sum().reset_index()

async def async_main(df, prices, session):
    """Main asynchronous loop to update and display market data."""
    previous_prices = {symbol: 0 for symbol in df['streamer_symbol']}
    symbol_list = df['streamer_symbol'].tolist()

    async with DXLinkStreamer(session) as streamer:
        await streamer.subscribe(Quote, symbol_list)
        asyncio.create_task(process_quotes(streamer, prices))

        while True:
            # Update market prices
            for symbol in prices:
                current_price = float(prices[symbol])
                df.loc[df['streamer_symbol'] == symbol, 'market_price'] = current_price

            net_credit_debit = calculate_strategy_net_credit_debit(df)

            # Clear screen and build a table
            console.clear()
            table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)

            table.add_column("Group Name", style="dim", width=12)
            table.add_column("Net Credit/Debit", justify="right")
            for idx, row in net_credit_debit.iterrows():
                color = "green" if row['net_value'] > 0 else "red"
                table.add_row(row['group_name'], f"[{color}]{row['net_value']:.2f}[/{color}]")

            console.print(table)

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

            await asyncio.sleep(1)

def main():
    session = Session(TASTYTRADE_USERNAME, TASTYTRADE_PASSWORD)
    df = pd.read_csv("data/sample-watchlist.csv")
    df['market_price'] = 0.0
    prices: Dict[str, Decimal] = {}

    try:
        asyncio.run(async_main(df, prices, session))
    except KeyboardInterrupt:
        console.print("\n[bold red]Exiting...[/bold red]")

if __name__ == "__main__":
    main()

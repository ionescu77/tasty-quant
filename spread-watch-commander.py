import asyncio
import curses
from decimal import Decimal
from typing import Dict
import pandas as pd
from tastytrade import Session, DXLinkStreamer
from tastytrade.dxfeed import Quote
import os
import contextlib

# Setup environment variables for Tastytrade credentials
TASTYTRADE_USERNAME = os.environ.get('TASTY_USER', '')
TASTYTRADE_PASSWORD = os.environ.get('TASTY_PASS', '')

# Flag to enable or disable debug messages
DEBUG_ENABLED = False

async def process_quotes(streamer: DXLinkStreamer, prices: Dict[str, Decimal]):
    """Listen to live quotes and update current prices."""
    try:
        async for quote in streamer.listen(Quote):
            if quote:
                if DEBUG_ENABLED:
                    print(f"Received quote: {quote}")
                if quote.bid_price is not None and quote.ask_price is not None:
                    market_price = (quote.bid_price + quote.ask_price) / 2
                    prices[quote.event_symbol] = market_price
                else:
                    prices[quote.event_symbol] = Decimal('0')
    except asyncio.CancelledError:
        # Handle cancellation and cleanup
        print("Quote processing canceled.")
    finally:
        await streamer.close()

def calculate_strategy_net_credit_debit(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate net value of strategies based on market prices."""
    df['net_value'] = df['market_price'] * df['quantity']
    return df.groupby('group_name')['net_value'].sum().reset_index()

async def async_main(df, prices, stdscr, session):
    """Main asynchronous loop to update and display market data."""
    quote_task = None
    try:
        symbol_list = df['streamer_symbol'].tolist()

        # Streamer setup and subscription
        async with DXLinkStreamer(session) as streamer:
            await streamer.subscribe(Quote, symbol_list)
            quote_task = asyncio.create_task(process_quotes(streamer, prices))

            while True:
                # Capture key events
                key = stdscr.getch()
                if key in [ord('q'), ord('Q')]:
                    break

                # Update market prices
                for symbol in prices:
                    df.loc[df['streamer_symbol'] == symbol, 'market_price'] = float(prices[symbol])

                net_credit_debit = calculate_strategy_net_credit_debit(df)

                # Clear and refresh the screen
                stdscr.clear()
                stdscr.addstr(0, 0, "Net Credit/Debit Per Strategy:")
                stdscr.addstr(1, 0, "-" * 50)

                # Format displayed data
                for idx, row in net_credit_debit.iterrows():
                    stdscr.addstr(2 + idx, 0, f"{row['group_name']:<10} {row['net_value']:>10.2f}")

                stdscr.addstr(4 + len(net_credit_debit), 0, "-" * 50)
                for idx, row in df.iterrows():
                    stdscr.addstr(5 + len(net_credit_debit) + idx, 0,
                                  f"{row['group_name']:<10} {row['streamer_symbol']:<15} "
                                  f"{row['quantity']:>5} {row['market_price']:>10.2f}")

                stdscr.refresh()

                # Sleep briefly to avoid flicker
                await asyncio.sleep(1)

    except asyncio.CancelledError:
        print("Main async task canceled.")
    finally:
        if quote_task:
            quote_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await quote_task

def main(stdscr):
    """Initialize curses and run the main async loop."""
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(100)

    session = Session(TASTYTRADE_USERNAME, TASTYTRADE_PASSWORD)
    df = pd.read_csv("data/sample-watchlist.csv")
    df['market_price'] = 0.0
    prices: Dict[str, Decimal] = {}

    try:
        asyncio.run(async_main(df, prices, stdscr, session))
    except KeyboardInterrupt:
        print("Keyboard interrupt received, exiting.")

if __name__ == "__main__":
    curses.wrapper(main)

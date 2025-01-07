import asyncio
from rich.console import Console
from rich.table import Table
from tastytrade.instruments import InstrumentType, Option

from tastytrade.utils import TastytradeError, today_in_new_york

from utils import (
    ZERO,
    RenewableSession,
    conditional_color,
    get_confirmation,
    print_error,
    print_warning,
)

async def main():
    sesh = RenewableSession()
    console = Console()
    table = Table(header_style="bold", title_style="bold", title="Positions with Streamer Symbols")
    table.add_column("#", justify="left")
    table.add_column("Symbol", justify="left")
    table.add_column("Streamer Symbol", justify="left")
    table.add_column("Qty", justify="right")
    table.add_column("Position Type", justify="center")

    # For simplicity, assuming you're only dealing with one account
    account = sesh.get_account()
    positions = account.get_positions(sesh, include_marks=True)

    positions.sort(key=lambda pos: pos.symbol)

    options_symbols = [
        p.symbol for p in positions if p.instrument_type == InstrumentType.EQUITY_OPTION
    ]
    options = Option.get_options(sesh, options_symbols) if options_symbols else []
    options_dict = {o.symbol: o for o in options}

    for i, pos in enumerate(positions):
        row = [f"{i+1}"]

        # Retrieve the streamer symbol if it's an equity option
        streamer_symbol = "N/A"
        if pos.instrument_type == InstrumentType.EQUITY_OPTION:
            option = options_dict.get(pos.symbol)
            if option:
                streamer_symbol = option.streamer_symbol

        # Determine position type based on quantity direction
        position_type = "Long" if pos.quantity_direction == "Long" else "Short"

        # Adjust quantity to be negative if the position is short
        adjusted_quantity = pos.quantity if pos.quantity_direction == "Long" else -pos.quantity

        row.extend([
            pos.symbol,
            streamer_symbol,
            f"{adjusted_quantity:g}",
            position_type
        ])
        table.add_row(*row)

    console.print(table)

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import argparse
import csv
import os
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

"""
    - connect to TastyTrade
    - Query portfolio current positions
    - Retrieve data with Streamer Symbols
    - Write positions to csv file

"""
async def main(export_csv: bool):
    sesh = RenewableSession()
    console = Console()
    table = Table(header_style="bold", title_style="bold", title="Positions with Streamer Symbols")
    table.add_column("#", justify="left")
    table.add_column("Symbol", justify="left")
    table.add_column("Streamer Symbol", justify="left")
    table.add_column("Qty", justify="right")
    table.add_column("Position Type", justify="center")
    table.add_column("Cost", justify="center")

    # For simplicity, assuming you're only dealing with one account
    account = sesh.get_account()
    positions = account.get_positions(sesh, include_marks=True)

    positions.sort(key=lambda pos: pos.symbol)

    options_symbols = [
        p.symbol for p in positions if p.instrument_type == InstrumentType.EQUITY_OPTION
    ]
    options = Option.get_options(sesh, options_symbols) if options_symbols else []
    options_dict = {o.symbol: o for o in options}

    csv_data = [] if export_csv else None  # Prepare data for CSV export

    for i, pos in enumerate(positions):
        row = [f"{i+1}"]

        # Retrieve the streamer symbol if it's an equity option
        streamer_symbol = "N/A"
        if pos.instrument_type == InstrumentType.EQUITY_OPTION:
            option = options_dict.get(pos.symbol)
            if option:
                streamer_symbol = option.streamer_symbol

        open_price = pos.average_open_price

        # Determine position type based on quantity direction
        position_type = "Long" if pos.quantity_direction == "Long" else "Short"

        # Adjust quantity to be negative if the position is short
        adjusted_quantity = pos.quantity if pos.quantity_direction == "Long" else -pos.quantity

        # Split the Symbol to get group_name
        group_name = pos.symbol.split()[0]

        # Append row to table
        table.add_row(
            str(i + 1),
            pos.symbol,
            streamer_symbol,
            f"{adjusted_quantity:g}",
            position_type,
            f"{open_price:.2f}"
        )

        # Prepare CSV row if export is enabled
        if export_csv and streamer_symbol != "N/A":
            csv_data.append([group_name, streamer_symbol, adjusted_quantity, open_price])

    # Export to CSV if requested
    if export_csv:
        csv_path = os.path.join("data", "positions-watchlist.csv")
        os.makedirs("data", exist_ok=True)  # Ensure data directory exists

        with open(csv_path, mode="w", newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["group_name", "streamer_symbol", "quantity", "open_price"])
            writer.writerows(csv_data)

    # Display the table
    console.print(table)

    # Print CSV export message if applicable
    if export_csv:
        console.print(f"Portfolio Position with Symbols saved to {csv_path}", style="green")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Display portfolio positions with streamer symbols.")
    parser.add_argument(
        "--export-csv",
        action="store_true",
        help="Export the positions data to data/positions-watchlist.csv"
    )
    args = parser.parse_args()
    asyncio.run(main(export_csv=args.export_csv))

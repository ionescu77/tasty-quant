# tasty-quant
Some tools and helpers for tastytrade

## spread-watch-commander.py
Inspired by Midnight Commander

It will display and update the prices for your option-stragies.

You should add your positions to the file
`./data/sample-watchlist.csv`

```
Data Source: data/sample-watchlist.csv

  Group Name     Net Credit/Debit
 ─────────────────────────────────
  AAPL                       1.42
  MU                         4.42
  bhp                        0.03


  Group Name     Symbol            Quantity   Market Price
 ──────────────────────────────────────────────────────────
  AAPL           .AAPL250117C250         -1           0.76
  AAPL           .AAPL250117C245          1           2.17
  MU             .MU250321C105            1           7.97
  MU             .MU250321C120           -1           3.55
  bhp            .BHP250117C55           -1           0.03
  bhp            .BHP250117C52.5          1           0.05

Current time: 22:59 | Last update: 0s ago
╭───────────────────────────────────────────── Instruction ──────────────────────────────────────────────╮
│                                          Press Ctrl+C to quit                                          │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────╯

```

## positions_with_streamer_symbols.py

We needed a way to find out the DX Feed streamer symbols for your portfolio, so run this:

```bash
python positions_with_streamer_symbols.py
                    Positions with Streamer Symbols
┏━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━┳━━━━━━━━━━━━━━━┓
┃ #  ┃ Symbol                ┃ Streamer Symbol  ┃ Qty ┃ Position Type ┃
┡━━━━╇━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━╇━━━━━━━━━━━━━━━┩
│ 1  │ AAPL  250117C00245000 │ .AAPL250117C245  │   1 │     Long      │
│ 2  │ AAPL  250117C00250000 │ .AAPL250117C250  │  -1 │     Short     │
│ 3  │ BHP   250117C00052500 │ .BHP250117C52.5  │   1 │     Long      │
│ 4  │ BHP   250117C00055000 │ .BHP250117C55    │  -1 │     Short     │
│ 5  │ MU    250321C00105000 │ .MU250321C105    │   1 │     Long      │
│ 6  │ MU    250321C00120000 │ .MU250321C120    │  -1 │     Short     │
└────┴───────────────────────┴──────────────────┴─────┴───────────────┘
```

# Install
- git clone repo
```
git clone git@github.com:ionescu77/tasty-quant.git
```
- change direcory
```
cd tasty-quant
```
- setup venv
```
python3 -m venv .
```
- source venv
```bash
source bin/activate
```
- install requirements
```
pip install -r requirements.txt
```
- edit the positions in the portfolio file
```
./data/sample-watchlist.csv
```
- run app
```
python spread-watch-commander.py
```

# Optional
- set user environment variables (better not to write in a file)
- I prefer to enter manually

> Note:
> 
> For `positions_with_streamer_symbols.py` I have used the RenewableSession() implementation from tastytrade utils.py
> I need to implement this also for the `spread-watch-commander.py`

```bash
export TASTY_USER="your-tasty-username"
export TASTY_PASS="your-tasty-password"
```


# tasty-quant
Some tools and helpers for tastytrade.

Thanks to
| * | URL |
| --- | --- |
| sdk and cli | https://github.com/tastyware/tastytrade-cli |
| from tstytrade Reddit | https://gist.github.com/dboonstra/f081e3d439bf3559af6e2ede22b3481f |

## spread-watch-commander.py
```bash
spread-watch-commander.py
```
Inspired by Midnight Commander

It will display and update the prices for your option-stragies.

You should add your positions to the file
`./data/portfolio-watchlist.csv`
or use `positions_with_streamer_symbols.py --export-csv` to generate the file based on your current TastyTrade portfolio positions.

A sample `data/sample-watch.csv` is provided as an example.

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
```bash
positions_with_streamer_symbols.py
```
We needed a way to find out the DX Feed streamer symbols for your portfolio, so run this to display your positions:

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

Using the `--export-csv` parameter will generate a csv file based on your TastyTrade portfolio.

```bash
python positions_with_streamer_symbols.py --export-csv
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

Portfolio Position with Symbols saved to data/positions-watchlist.csv
```

# spread-watch.py

```bash
spread-watch.py
```
This sample script was found on reddit, it will generate following output:

```bash
python spread-watch.py
Updating Market Prices...
Net Credit/Debit Per Strategy:
  group_name  net_value
0       AAPL      0.325
1         MU      3.770
2        bhp      0.000
  group_name  streamer_symbol  quantity  market_price
0       AAPL  .AAPL250117C250        -1         0.115
1       AAPL  .AAPL250117C245         1         0.440
2         MU    .MU250321C105         1         6.300
3         MU    .MU250321C120        -1         2.530
4        bhp    .BHP250117C55        -1         0.025
5        bhp  .BHP250117C52.5         1         0.025
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
./data/portfolio-watchlist.csv
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

# To-Do
- [ ] generate the `watchlist.csv` from the user portfolio (take into account multiple `Account`s sic)
- [ ] add the tickers to a DB (sqlite or TimeSeriesDB?)
- [ ] Create a GUI (Streamlit?) for ticker history & portfolio heatmap
- [ ] etc.

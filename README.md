# tasty-quant
Some tools and helpers for tastytrade


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

# Environment
- set user environment variables (better not to write in a file)
```bash
export TASTY_USER="your-tasty-username"
export TASTY_PASS="your-tasty-password"
```

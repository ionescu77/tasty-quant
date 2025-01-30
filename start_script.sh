#!/bin/bash
cd /Users/razvansky/myProjects/tasty-quant
source bin/activate
python positions_with_streamer_symbols.py --export-csv
python tasty-quote-streamer.py

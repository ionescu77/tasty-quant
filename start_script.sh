#!/bin/bash
cd /Users/razvansky/myProjects/tasty-quant
source bin/activate
sleep 5
python positions_with_streamer_symbols.py --export-csv
sleep 10
python tasty-quote-streamer.py

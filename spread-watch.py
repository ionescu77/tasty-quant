import asyncio
from decimal import Decimal
from typing import List, Dict

import pandas as pd
from tastytrade import Session, DXLinkStreamer
from tastytrade.dxfeed import Quote

import os

TASTYTRADE_USERNAME = os.environ['TASTY_USER']
TASTYTRADE_PASSWORD = os.environ['TASTY_PASS']


async def process_quotes(streamer: DXLinkStreamer, prices: Dict[str, Decimal]):
    async for quote in streamer.listen(Quote):
        if quote:
             if quote.bid_price is not None and quote.ask_price is not None:
                market_price = (quote.bid_price + quote.ask_price) / 2
                prices[quote.event_symbol] = market_price
             else:
                prices[quote.event_symbol] = Decimal('0')
        
def calculate_strategy_net_credit_debit(df: pd.DataFrame) -> pd.DataFrame:
    df['net_value'] = df['market_price'] * df['quantity']
    grouped = df.groupby('group_name')['net_value'].sum().reset_index()
    
    return grouped


async def main():
    session = Session(TASTYTRADE_USERNAME, TASTYTRADE_PASSWORD)
    df = pd.read_csv("data/positions-watchlist.csv")
    df['market_price'] = 0.0
    symbol_list = df['streamer_symbol'].tolist()
    prices: Dict[str, Decimal] = {}
    async with DXLinkStreamer(session) as streamer:
        await streamer.subscribe(Quote, symbol_list)
        
        quote_task = asyncio.create_task(process_quotes(streamer, prices))
        await asyncio.sleep(1)


        while True:
            print("Updating Market Prices...")
            
            for index, row in df.iterrows():
                symbol = row['streamer_symbol']
                if symbol in prices:
                    df.loc[index, 'market_price'] = float(prices[symbol])
                else:
                    df.loc[index, 'market_price'] = 0.0

            net_credit_debit = calculate_strategy_net_credit_debit(df)
            print("Net Credit/Debit Per Strategy:")
            print(net_credit_debit)
            
            print(df[['group_name','streamer_symbol','quantity','market_price']])
            
            await asyncio.sleep(60)



if __name__ == "__main__":
    asyncio.run(main())

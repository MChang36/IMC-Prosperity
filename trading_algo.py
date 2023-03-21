from typing import Any, Dict, List
from datamodel import OrderDepth, TradingState, Order, Symbol
#import math
#import pandas as pd
#import numpy as np
import statistics

class Trader:
    
    def __init__(self):
        self.history = {"PEARLS": [], "BANANAS": []}
        self.limits = {"PEARLS": 20, "BANANAS": 20}

    def get_limit(self, product):
        return self.limits[product]

    def calc_expected(self, state: TradingState):
        expectations = {}

        for product in state.listings.keys():
            #for each product, look at order depths, then calc expected value using that
            #last 30 timestamps
            ask_hist = []
            bid_hist = []
            # Update histories
            order_depth = state.order_depths[product]
            for price in order_depth.sell_orders:
                ask_hist.append([price]*abs(order_depth.sell_orders[price]))
            ask_hist = [item for sublist in ask_hist for item in sublist]
            for price in order_depth.buy_orders:
                bid_hist.append([price]*order_depth.buy_orders[price])
            bid_hist = [item for sublist in bid_hist for item in sublist]
            
            print(statistics.median(bid_hist+ask_hist))
            
            self.history[product].append(statistics.median(bid_hist+ask_hist))
            
            # Calc average of up to last 10 timestamps
            lookback = 100
            sample = self.history[product][-lookback:]
            expectations[product] = statistics.mean(sample)
            
        return expectations

    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        result = {}
        expectations: Dict[str, List[int]] = self.calc_expected(state)
        print(expectations)

        for product in state.listings.keys():
            order_depth: OrderDepth = state.order_depths[product]
            orders: list[Order] = []
            if product in state.position.keys():
                print("Position:", product, state.position[product])

            # buy
            ask = sorted([price for price in order_depth.sell_orders.keys() if price < expectations[product]])
            ask_volumes = [order_depth.sell_orders[price] for price in ask]
            if product in state.position.keys():
                limit = self.limits[product] - state.position[product]
            else:
                limit = self.limits[product]
            while len(ask) > 0:
                if limit + ask_volumes[0] > 0:
                    print("BUY", str(-ask_volumes[0])+"x", product, ask[0])
                    orders.append(Order(product, ask[0], -ask_volumes[0]))
                elif limit > 0:
                    # put in order with remaining limit
                    print("BUY", str(limit)+"x", product, ask[0])
                    orders.append(Order(product, ask[0], limit))
                best_ask = ask.pop(0)
                best_vol = ask_volumes.pop(0)
                limit += best_vol
            if limit > 0:
                print("BUY", str(limit)+"x", product, 0.9*expectations[product])
                orders.append(Order(product, 0.9*expectations[product], limit))

            #sell
            bid = sorted([price for price in order_depth.buy_orders.keys() if price > expectations[product]])
            bid_volumes = [order_depth.buy_orders[price] for price in bid]
            if product in state.position.keys():
                limit = self.limits[product] + state.position[product]
            else:
                limit = self.limits[product]
            while len(bid) > 0:
                if limit - bid_volumes[0] > 0:
                    print("SELL", str(bid_volumes[0])+"x", product, bid[0])
                    orders.append(Order(product, bid[0], -bid_volumes[0]))
                elif limit > 0:
                    # put in order with remaining limit
                    print("SELL", str(limit)+"x", product, bid[0])
                    orders.append(Order(product, bid[0], -limit))
                best_bid = bid.pop(0)
                best_vol = bid_volumes.pop(0)
                limit -= best_vol
            if limit > 0:
                print("SELL", str(limit)+"x", product, 1.1*expectations[product])
                orders.append(Order(product, 1.1*expectations[product], -limit))

            result[product] = orders
        return result
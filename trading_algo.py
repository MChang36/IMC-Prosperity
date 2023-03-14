from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order

import pandas as pd
import numpy as np

class Trader:

    def calc_expected(self, state: TradingState) -> Dict[str, tuple[int]]:
        expectations = {}

        for product in state.listings.keys():
            # for each product, look at order depths, then calc expected value using that
            print(product)

        return expectations

    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        result = {}
        
        expectations: Dict[str, List[int]] = calc_expected(state)

        for product in state.listings.keys():
            order_depth: OrderDepth = state.order_depths[product]
            orders: list[Order] = []
            
            # buy
            if len(order_depth.sell_orders) > 0:
                best_ask = min(order_depth.sell_orders.keys())
                best_ask_volume = order_depth.sell_orders[best_ask]
                
                if best_ask < expectations[1]:
                    print("BUY", str(-best_ask_volume)+"x", best_ask)
                    orders.append(Order(product, best_ask, -best_ask_volume))

            # sell
            if len(order_depth.buy_orders) > 0:
                best_bid = max(order_depth.buy_orders.keys())
                best_bid_volume = order_depth.buy_orders[best_bid]
                
                if best_bid > expectations[0]:
                    print("SELL", str(best_bid_volume)+"x", best_bid)
                    orders.append(Order(product, best_bid, -best_bid_volume))

            result[product] = orders
        return result
from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order
import math
import pandas as pd
import numpy as np

class Trader:

    # def calc_expected(self, state: TradingState) -> Dict[str, tuple[int]]:
    #     expectations = {}

    #     for product in state.listings.keys():
    #         # for each product, look at order depths, then calc expected value using that
    #         print(product)

    #     return expectations

    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        result = {}
        limits = {"BANANAS": 20, "PEARLS": 20}
        expectations: Dict[str, List[int]] = {"BANANAS": (4935.64, 4940.94),
                                              "PEARLS": (9996.58, 10003.40)} #calc_expected(state)

        for product in state.listings.keys():
            order_depth: OrderDepth = state.order_depths[product]
            orders: list[Order] = []

            # buy
            ask = sorted([price for price in order_depth.sell_orders.keys() if price < expectations[product][1]])
            ask_volumes = [order_depth.sell_orders[price] for price in ask]
            if product in state.position.keys():
                limit = limits[product] - state.position[product]
            else:
                limit = limits[product]

            while len(ask) > 0:
                if limit + ask_volumes[0] > 0:
                    print("BUY", str(-ask_volumes[0])+"x", ask[0])
                    orders.append(Order(product, ask[0], -ask_volumes[0]))
                else:
                    # put in order with remaining limit
                    print("BUY", str(limit)+"x", ask[0])
                    orders.append(Order(product, ask[0], limit))
                best_ask = ask.pop(0)
                best_vol = ask_volumes.pop(0)
                limit += best_vol
            if limit > 0:
                print("BUY", str(limit)+"x", math.ceil(expectations[product][1]-1))
                orders.append(Order(product, math.ceil(expectations[product][1]-1), limit))

            #sell
            bid = sorted([price for price in order_depth.buy_orders.keys() if price > expectations[product][0]])
            bid_volumes = [order_depth.buy_orders[price] for price in bid]
            if product in state.position.keys():
                limit = limits[product] + state.position[product]
            else:
                limit = limits[product]
            while len(bid) > 0:
                if limit - bid_volumes[0] > 0:
                    print("SELL", str(bid_volumes[0])+"x", bid[0])
                    orders.append(Order(product, bid[0], -bid_volumes[0]))
                else:
                    # put in order with remaining limit
                    print("SELL", str(limit)+"x", bid[0])
                    orders.append(Order(product, bid[0], -limit))
                best_bid = bid.pop(0)
                best_vol = bid_volumes.pop(0)
                limit += best_vol
            if limit > 0:
                print("SELL", str(limit)+"x", math.floor(expectations[product][1]+1))
                orders.append(Order(product, math.floor(expectations[product][1]+1), -limit))

            result[product] = orders
        return result
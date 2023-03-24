from typing import Any, Dict, List
from datamodel import OrderDepth, TradingState, Order, Symbol
import math
import pandas as pd
import numpy as np
import statistics

class Trader:
    
    def __init__(self):
        self.products = ["PEARLS", "BANANAS", "COCONUTS:PINA_COLADAS"]
        self.history = {"PEARLS": [], "BANANAS": [], "COCONUTS": [], "PINA_COLADAS": []}
        self.spread_history = {"COCONUTS:PINA_COLADAS": []}
        self.limits = {"PEARLS": 20, "BANANAS": 20, "COCONUTS": 600, "PINA_COLADAS": 300}
        self.types = {"stationary": ["PEARLS"], 
                      "trend": ["BANANAS"], 
                      "pair": ["COCONUTS:PINA_COLADAS"]}
    
    def update_hist(self, state: TradingState):
        for product in state.listings.keys():
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
            
            self.history[product].append(statistics.median(bid_hist+ask_hist))

    def calc_expected(self):
        expectations = {}
        for product in self.products:
            # Calc average of up to last 30 timestamps
            lookback = 30
            # if pair trading
            if ":" in product:
                product1 = product.split(":")[0]
                product2 = product.split(":")[1]
                prod1 = np.array(self.history[product1])[-lookback:]
                prod2 = np.array(self.history[product2])[-lookback:]
                hedge_ratio = 1 if len(prod1) < 2 else np.corrcoef(prod1, prod2)[1, 0] * np.std(prod2) / np.std(prod1)
                print("HEDGE:", hedge_ratio)
                spread = prod2[-1] - prod1[-1] * hedge_ratio
                self.spread_history[product].append(spread)
                sample = self.spread_history[product][-lookback:]
                spread_sma = statistics.mean(sample)
                spread_std = statistics.stdev(sample) if len(sample) > 1 else 0
                expectations[product] = (spread_sma-2*spread_std, spread_sma+2*spread_std, hedge_ratio)
            else:
                sample = self.history[product][-lookback:]
                sma = statistics.mean(sample)
                std = statistics.stdev(sample) if len(sample) > 1 else 0
                expectations[product] = (sma-2*std,sma+2*std)
        return expectations

    def stationary_good(self, state, product, order_depth, lb, ub):
        orders = []
        #buy
        orders += self.buy(state, product, order_depth, lb)[0]
        #sell
        orders += self.sell(state, product, order_depth, ub)[0]
        return orders
    
    def sell(self, state, product, depth, ub, market_making=True):
        orders = []
        bid = sorted([price for price in depth.buy_orders.keys() if price > ub])
        bid_volumes = [depth.buy_orders[price] for price in bid]
        vol = 0
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
            vol += abs(best_vol)
        if limit > 0:
            print("SELL", str(limit)+"x", product, ub)
            orders.append(Order(product, ub, -limit))
            vol = limit
        return orders, vol
    
    def buy(self, state, product, depth, lb, market_making=True):
        orders = []
        ask = sorted([price for price in depth.sell_orders.keys() if price < lb])
        ask_volumes = [depth.sell_orders[price] for price in ask]
        vol = 0
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
            vol += abs(best_vol)
            limit += best_vol
        if limit > 0:
            print("BUY", str(limit)+"x", product, lb)
            orders.append(Order(product, lb, limit))
            vol = limit
        return orders, vol
    
    def paired_goods(self, state, product, product1, product2, depth_1, depth_2, lb, ub, hedge):
        # price taking in account order depth
        orders_1 = []
        orders_2 = []
        first_pos = 0
        if math.isnan(lb) or math.isnan(ub):
            return orders_1, orders_2
        if self.spread_history[product][-1] > ub:
            (order, first_pos) = self.sell(state, product2, depth_2, self.history[product2][-1], False)
            orders_2 += order
        elif self.spread_history[product][-1] < lb:
            (order, first_pos) = self.buy(state, product2, depth_2, self.history[product2][-1], False)
            orders_2 += order
        elif self.spread_history[product][-1] >= lb and self.spread_history[product][-1] <= ub and product2 in state.position.keys():
            if state.position[product2] > 0:
                first_pos = -state.position[product2]
                print("SELL", str(state.position[product2])+"x", product2, self.history[product2][-1])
                orders_2.append(Order(product2, self.history[product2][-1], first_pos))
            elif state.position[product2] < 0:
                first_pos = state.position[product2]
                print("BUY", str(state.position[product2])+"x", product2, self.history[product2][-1])
                orders_2.append(Order(product2, self.history[product2][-1], first_pos))
        
        sec_pos = round(-hedge*first_pos)
        if sec_pos > 0:
            print("BUY", str(sec_pos)+"x", product1, self.history[product1][-1])
            orders_1.append(Order(product1, self.history[product1][-1], sec_pos))
        elif sec_pos < 0:
            print("SELL", str(sec_pos)+"x", product1, self.history[product1][-1])
            orders_1.append(Order(product1, self.history[product1][-1], sec_pos))

        return orders_1, orders_2

    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        result = {}
        self.update_hist(state)
        expectations = self.calc_expected()
        print(expectations)

        for product in self.products:
            if ":" in product:
                product1 = product.split(":")[0]
                product2 = product.split(":")[1]
                depth_1 = state.order_depths[product1]
                depth_2 = state.order_depths[product2]
            else:
                order_depth: OrderDepth = state.order_depths[product]
            orders: list[Order] = []
            if product in state.position.keys():
                print("Position:", product, state.position[product])

            if product in self.types["stationary"] or product in self.types["trend"]:
                orders = self.stationary_good(state, product, order_depth, expectations[product][0], expectations[product][1])
                result[product] = orders
            elif product in self.types["pair"]:
                product1 = product.split(":")[0]
                product2 = product.split(":")[1]
                orders_1, orders_2 = self.paired_goods(state, product, product1, product2, depth_1, depth_2, expectations[product][0], expectations[product][1], expectations[product][2])
                result[product1] = orders_1
                result[product2] = orders_2
            
        return result
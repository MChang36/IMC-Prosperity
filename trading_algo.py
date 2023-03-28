from typing import Any, Dict, List
from datamodel import OrderDepth, TradingState, Order, Symbol
import math
import pandas as pd
import numpy as np
import statistics

class Trader:
    
    def __init__(self):
        self.products = ["PEARLS", "BANANAS", 
                         "COCONUTS:PINA_COLADAS", 
                         "BERRIES", "DIVING_GEAR", "DIP", 
                         "BAGUETTE", "PICNIC_BASKET", "UKULELE"] #
        self.history = {"PEARLS": [], "BANANAS": [],
                        "COCONUTS": [], "PINA_COLADAS": [],
                        "BERRIES": [], "DIVING_GEAR": [], "DOLPHIN_SIGHTINGS": [], "DIP": [], 
                         "BAGUETTE": [], "PICNIC_BASKET": [], "UKULELE": []}
        self.true_range = {"PEARLS": [], "BANANAS": [],
                        "COCONUTS": [], "PINA_COLADAS": [],
                        "BERRIES": [], "DIVING_GEAR": [], "DOLPHIN_SIGHTINGS": [], "DIP": [], 
                         "BAGUETTE": [], "PICNIC_BASKET": [], "UKULELE": []}
        self.time_period = 0
        self.ema_history = {"PEARLS": [], "BANANAS": [],
                    "COCONUTS": [], "PINA_COLADAS": [],
                    "BERRIES": [], "DIVING_GEAR": [], "DOLPHIN_SIGHTINGS": [], "DIP": [], 
                         "BAGUETTE": [], "PICNIC_BASKET": [], "UKULELE": []}
        self.spread_history = {"COCONUTS:PINA_COLADAS": []}
        self.limits = {"PEARLS": 20, "BANANAS": 20,
                        "COCONUTS": 600, "PINA_COLADAS": 300,
                        "BERRIES": 250, "DIVING_GEAR": 50, "DIP": 300, 
                         "BAGUETTE": 150, "PICNIC_BASKET": 70, "UKULELE": 70}
        self.types = {"stationary": ["PEARLS", "COCONUTS", "PINA_COLADAS", "DIVING_GEAR", "DIP", 
                         "BAGUETTE", "PICNIC_BASKET", "UKULELE"], 
                      "trend": ["BANANAS", "BERRIES"], 
                      "pair": ["COCONUTS:PINA_COLADAS"],
                      "observation": ["DOLPHIN_SIGHTINGS"]} #
    
    def update_hist(self, state: TradingState):
        for product in self.history:
            if product in self.types["observation"]:
                self.history[product].append(state.observations[product])
            else:
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

                # Update true range
                order_depth = state.order_depths[product]
                today_prices = list(order_depth.sell_orders) + list(order_depth.buy_orders)
                high = max(today_prices)
                low = min(today_prices)
                close_prev = self.history[product][-1] if len(self.history[product]) > 0 else 0

                self.true_range[product].append(max([(high - low), abs(high - close_prev), abs(low - close_prev)]))

                #Update time period
                lengths = []
                for lst in self.history.values():
                    lengths.append(len(lst))
                self.time_period = min(lengths)

    def calc_expected(self, state):
        expectations = {}
        for product in self.products:
            # Calc average of up to last 30 timestamps
            # if pair trading
            if ":" in product:
                product1 = product.split(":")[0]
                product2 = product.split(":")[1]
                lookback = 60
                prod1 = np.array(self.history[product1])[-lookback:]
                prod2 = np.array(self.history[product2])[-lookback:]
                minsize = min(len(prod1), len(prod2))
                if minsize < 2:
                    break
                prod1 =  prod1[-minsize:]
                prod2 = prod2[-minsize:]
                hedge_ratio = np.corrcoef(prod1, prod2)[1, 0] * np.std(prod1) / np.std(prod2)
                print("HEDGE:", hedge_ratio)
                spread = prod1[-1] - prod2[-1] * hedge_ratio
                self.spread_history[product].append(spread)
                sample = self.spread_history[product][-lookback:]
                spread_sma = statistics.mean(sample)
                spread_std = statistics.stdev(sample)
                expectations[product] = (spread_sma-2*spread_std, spread_sma+2*spread_std, hedge_ratio)
            else:
                if product in self.types["stationary"]:
                    lookback = 60
                elif product in self.types["trend"]:
                    lookback = 10
                if product == "DIVING_GEAR":
                    sample = self.history[product][-20:]
                    sma = statistics.mean(sample)
                    if len(self.ema_history[product]) == 0:
                        self.ema_history[product].append(sma)
                        ema = sma
                    else:
                        k = (2.0 / (self.time_period + 1.0))
                        ema = self.history[product][-1] * k + self.ema_history[product][-1] * (1 - k)
                        self.ema_history[product].append(ema)
                    atr = statistics.mean(self.true_range[product][-20:])
                    expectations[product] = (ema-2*atr,ema+2*atr)
                else:
                    sample = self.history[product][-lookback:]
                    sma = statistics.mean(sample) if len(sample) > 1 else 0
                    std = statistics.stdev(sample) if len(sample) > 1 else 0
                    expectations[product] = (sma-2*std,sma+2*std)
        return expectations
    
    def momentum_difference(self, product, rate):
        if len(self.history[product]) < rate + 4:
            return False
        a = self.history[product][-1] - self.history[product][-rate-1]
        b = self.history[product][-2] - self.history[product][-rate-2]
        return abs(a + b) != abs(a) + abs(b)
    
    def momentum_slopes(self, product, rate=10, num_slopes=10):
        slope_lst=[]
        hist = self.history[product]
        if len(hist) < rate+2:
            return slope_lst
        for i in range(num_slopes):
            if len(hist) == rate + 1 + i:
                break
            slope_lst.append(hist[-i-1] - hist[-rate-i-1])
        return slope_lst
    
    def avg_momentum_slopes(self, product, rate, num_slopes):
        momentum_slopes = self.momentum_slopes(product, rate, num_slopes)
        if momentum_slopes == []:
            return momentum_slopes
        return statistics.mean(momentum_slopes)
    
    def cross_method(self, product, rate, num_slopes):
        if self.momentum_difference(product, rate):
            if self.avg_momentum_slopes(product, rate, num_slopes) < 0:
                return "SELL"
            if self.avg_momentum_slopes(product, rate, num_slopes) > 0:
                return "BUY"
        return "NONE"
    
    def divergent_method(self, product, rate):
        # average price slope
        x = np.linspace(0,rate-1,num=rate)
        slope = np.polyfit(x, self.history[product][-rate:], 1)[0]
        # average momentum slope
        m_slopes = self.avg_momentum_slopes(product, rate, rate)
        if m_slopes < 0 and slope > 0:
            return "SELL"
        if m_slopes > 0 and slope < 0:
            return "BUY"
        return "NONE"

    def macd_position(self, product: str, span_1: int = 12, span_2: int = 26) -> str:
        mid_price_df = pd.DataFrame(self.history[product], columns = ['mid_prices'])
        ema12 = mid_price_df['mid_prices'].ewm(span=span_1, adjust=False).mean()
        ema26 = mid_price_df['mid_prices'].ewm(span=span_2, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        position = 0
        for i in range(1, len(mid_price_df)):
            if macd[i] > signal[i] and macd[i-1] <= signal[i-1]:
                # Enter a long position
                position = "BUY"
            elif macd[i] < signal[i] and macd[i-1] >= signal[i-1]:
                # Exit the long position
                position = "SELL"
        return position

    def sell(self, state, product, depth, ub, lim=float('inf'), market_making=True):
        orders = []
        bid = sorted([price for price in depth.buy_orders.keys() if price > ub])
        bid_volumes = [depth.buy_orders[price] for price in bid]
        vol = 0
        if product in state.position.keys():
            limit = self.limits[product] + state.position[product]
        else:
            limit = self.limits[product]
        limit = min(limit, lim)
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
        if market_making and limit > 0:
            print("SELL", str(limit)+"x", product, ub)
            orders.append(Order(product, ub, -limit))
            vol = limit
        return orders, vol
    
    def buy(self, state, product, depth, lb, lim=float('inf'), market_making=True):
        orders = []
        ask = sorted([price for price in depth.sell_orders.keys() if price < lb])
        ask_volumes = [depth.sell_orders[price] for price in ask]
        vol = 0
        if product in state.position.keys():
            limit = self.limits[product] - state.position[product]
        else:
            limit = self.limits[product]
        limit = min(limit, lim)
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
            vol += abs(best_vol)
        if market_making and limit > 0:
            print("BUY", str(limit)+"x", product, lb)
            orders.append(Order(product, lb, limit))
            vol = limit
        return orders, vol

    def stationary_good(self, state, product, order_depth, lb, ub):
        orders = []
        #buy
        orders += self.buy(state, product, order_depth, lb)[0]
        #sell
        orders += self.sell(state, product, order_depth, ub)[0]
        return orders
    
    def trending_good(self, state, product, order_depth, lb, ub, rt=10):
        orders = []
        if len(self.history[product]) < rt+3:
            orders += self.buy(state, product, order_depth, lb, market_making=False)[0]
            orders += self.sell(state, product, order_depth, ub, market_making=False)[0]
            return orders
        #buy
        if self.macd_position(product) == "BUY":
            orders += self.buy(state, product, order_depth, lb, market_making=False)[0]
        #sell
        elif self.macd_position(product) == "SELL":
            orders += self.sell(state, product, order_depth, ub, market_making=False)[0]
        return orders
        
    
    def paired_goods(self, state, product, product1, product2, depth_1, depth_2, lb, ub, hedge):
        # price taking in account order depth
        orders_1 = []
        orders_2 = []
        first_pos = 0
        if math.isnan(lb) or math.isnan(ub):
            return orders_1, orders_2
        if self.spread_history[product][-1] > ub:
            (order, first_pos) = self.sell(state, product1, depth_1, self.history[product1][-1])
            orders_1 += order
        elif self.spread_history[product][-1] < lb:
            (order, first_pos) = self.buy(state, product1, depth_1, self.history[product1][-1])
            orders_1 += order
        elif self.spread_history[product][-1] >= lb and self.spread_history[product][-1] <= ub and product2 in state.position.keys():
            if state.position[product1] > 0:
                first_pos = -state.position[product1]
                print("SELL", str(state.position[product1])+"x", product1, self.history[product1][-1])
                orders_2.append(Order(product1, self.history[product1][-1], first_pos))
            elif state.position[product1] < 0:
                first_pos = state.position[product1]
                print("BUY", str(state.position[product1])+"x", product1, self.history[product1][-1])
                orders_2.append(Order(product1, self.history[product1][-1], first_pos))
        
        sec_pos = round(-hedge*first_pos)
        if sec_pos > 0:
            orders_2 += self.buy(state, product2, depth_2, self.history[product2][-1], lim=sec_pos)[0]
        elif sec_pos < 0:
            orders_2 += self.sell(state, product2, depth_2, self.history[product2][-1], lim=abs(sec_pos))[0]

        return orders_1, orders_2

    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        result = {}
        self.update_hist(state)
        expectations = self.calc_expected(state)
        print(expectations)

        for product in expectations:
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

            if product in self.types["stationary"]:
                orders = self.stationary_good(state, product, order_depth, expectations[product][0], expectations[product][1])
                result[product] = orders
            elif product in self.types["trend"]:
                orders = self.trending_good(state, product, order_depth, expectations[product][0], expectations[product][1])
                result[product] = orders
            elif product in self.types["pair"]:
                product1 = product.split(":")[0]
                product2 = product.split(":")[1]
                orders_1, orders_2 = self.paired_goods(state, product, product1, product2, depth_1, depth_2, expectations[product][0], expectations[product][1], expectations[product][2])
                result[product1] = orders_1
                result[product2] = orders_2
            
        return result
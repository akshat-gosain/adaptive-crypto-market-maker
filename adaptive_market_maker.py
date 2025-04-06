import logging
import math
from decimal import Decimal
from typing import Dict, List

from hummingbot.core.data_type.common import OrderType, PriceType, TradeType
from hummingbot.core.data_type.order_candidate import OrderCandidate
from hummingbot.core.event.events import OrderFilledEvent
from hummingbot.strategy.script_strategy_base import ScriptStrategyBase
from hummingbot.data_feed.candles_feed.candles_factory import CandlesFactory, CandlesConfig
from hummingbot.connector.connector_base import ConnectorBase

class AdaptiveMarketMaker(ScriptStrategyBase):
    """
    Adaptive Market Making Strategy (A-S Inspired)
    
    This strategy extends the basic PMM by calculating spreads based on the
    Avellaneda-Stoikov model principles. It adjusts spreads based on:
    1. Market volatility
    2. Inventory position
    3. Risk aversion parameters
    """
    bid_spread = 0.001
    ask_spread = 0.001
    order_refresh_time = 15
    order_amount = 1
    create_timestamp = 0
    trading_pair = "SOL-USDT"
    exchange = "binance_paper_trade"
    price_source = PriceType.MidPrice

    candle_exchange = "binance"
    candles_interval = "1m"
    candles_length = 30
    max_records = 1000
     
    risk_aversion = 0.9            
    min_spread = 0.001            

    candles = CandlesFactory.get_candle(CandlesConfig(connector=candle_exchange,
                                                     trading_pair=trading_pair,
                                                     interval=candles_interval,
                                                     max_records=max_records))

    markets = {exchange: {trading_pair}}


    def __init__(self, connectors: Dict[str, ConnectorBase]):
        super().__init__(connectors)
        self.candles.start()
        self.log_with_clock(logging.INFO, "Adaptive Market Maker initialized")
        self.notify_hb_app("Adaptive Market Maker initialized")

    def on_stop(self):
        self.candles.stop()
        self.log_with_clock(logging.INFO, "Strategy stopped")

    def on_tick(self):
        if self.create_timestamp <= self.current_timestamp:
            self.log_with_clock(logging.INFO, "Tick - refreshing orders")
            self.cancel_all_orders()
            proposal: List[OrderCandidate] = self.create_proposal()
            proposal_adjusted: List[OrderCandidate] = self.adjust_proposal_to_budget(proposal)
            self.place_orders(proposal_adjusted)
            self.create_timestamp = self.order_refresh_time + self.current_timestamp

    def get_candles_with_features(self):
        candles_df = self.candles.candles_df
        
        candles_df.ta.rsi(length=self.candles_length, append=True)
        
        candles_df.ta.natr(length=self.candles_length, scalar=1, append=True)
        
        return candles_df

    def calculate_spreads(self):
        """
        Calculate optimal bid and ask spreads using A-S inspired approach
        """
        try:
            candles_df = self.get_candles_with_features()
            
            if candles_df.empty:
                self.log_with_clock(logging.INFO, "No candles data available yet, using default spreads")
                return self.bid_spread, self.ask_spread
                

            natr_col = f"NATR_{self.candles_length}"
            if natr_col in candles_df.columns:
                volatility = float(candles_df[natr_col].iloc[-1])
            else:
                volatility = 0.001  
                
            base_balance = float(self.connectors[self.exchange].get_balance(self.trading_pair.split("-")[0]))
            quote_balance = float(self.connectors[self.exchange].get_price_by_type(self.trading_pair, self.price_source)) * float(self.connectors[self.exchange].get_balance(self.trading_pair.split("-")[1]))
            
            total_value = base_balance + quote_balance
            if total_value > 0:
                inventory_ratio = base_balance / total_value
            else:
                inventory_ratio = 0.5
                
                
            target_ratio = 0.5
            inventory_deviation = inventory_ratio - target_ratio
            
            base_spread = max(self.min_spread, volatility * 5)
            
            if inventory_deviation > 0:  # Long position
                # Widen ask to sell more, tighten bid to buy less
                bid_spread = max(self.min_spread, base_spread * (1 - inventory_deviation * 0.5))
                ask_spread = max(self.min_spread, base_spread * (1 + inventory_deviation * 0.5))
            else:  # Short position
                # Tighten ask to sell less, widen bid to buy more
                inventory_deviation = abs(inventory_deviation)
                bid_spread = max(self.min_spread, base_spread * (1 + inventory_deviation * 0.5))
                ask_spread = max(self.min_spread, base_spread * (1 - inventory_deviation * 0.5))
            
            self.log_with_clock(logging.INFO, 
                               f"Calculated spreads: bid={bid_spread:.6f}, ask={ask_spread:.6f}, "
                               f"volatility={volatility:.6f}, inventory_ratio={inventory_ratio:.2f}")
            
            return bid_spread, ask_spread
        
        except Exception as e:
            self.log_with_clock(logging.ERROR, f"Error calculating spreads: {e}, using defaults")
            return self.bid_spread, self.ask_spread

    def create_proposal(self) -> List[OrderCandidate]:
        ref_price = self.connectors[self.exchange].get_price_by_type(self.trading_pair, self.price_source)
        
        bid_spread, ask_spread = self.calculate_spreads()
        
        buy_price = ref_price * Decimal(1 - bid_spread)
        sell_price = ref_price * Decimal(1 + ask_spread)
        
        best_bid = self.connectors[self.exchange].get_price(self.trading_pair, False)
        best_ask = self.connectors[self.exchange].get_price(self.trading_pair, True)
        
        buy_price = min(buy_price, best_bid)
        sell_price = max(sell_price, best_ask)

        buy_order = OrderCandidate(trading_pair=self.trading_pair, is_maker=True, order_type=OrderType.LIMIT,
                                   order_side=TradeType.BUY, amount=Decimal(self.order_amount), price=buy_price)

        sell_order = OrderCandidate(trading_pair=self.trading_pair, is_maker=True, order_type=OrderType.LIMIT,
                                    order_side=TradeType.SELL, amount=Decimal(self.order_amount), price=sell_price)

        self.log_with_clock(logging.INFO, 
                          f"Creating proposal: Ref: {ref_price}, Buy: {buy_price}, Sell: {sell_price}")
        
        return [buy_order, sell_order]

    def adjust_proposal_to_budget(self, proposal: List[OrderCandidate]) -> List[OrderCandidate]:
        proposal_adjusted = self.connectors[self.exchange].budget_checker.adjust_candidates(proposal, all_or_none=True)
        
        if len(proposal_adjusted) != len(proposal):
            self.log_with_clock(logging.WARNING, 
                               f"Order proposal adjusted: {len(proposal)} -> {len(proposal_adjusted)}")
        
        return proposal_adjusted

    def place_orders(self, proposal: List[OrderCandidate]) -> None:
        for order in proposal:
            self.place_order(connector_name=self.exchange, order=order)
            order_type = "BUY" if order.order_side == TradeType.BUY else "SELL"
            self.log_with_clock(logging.INFO, 
                              f"Placed {order_type} order: {order.amount} @ {order.price}")

    def place_order(self, connector_name: str, order: OrderCandidate):
        if order.order_side == TradeType.SELL:
            self.sell(connector_name=connector_name, trading_pair=order.trading_pair, amount=order.amount,
                      order_type=order.order_type, price=order.price)
        elif order.order_side == TradeType.BUY:
            self.buy(connector_name=connector_name, trading_pair=order.trading_pair, amount=order.amount,
                     order_type=order.order_type, price=order.price)

    def cancel_all_orders(self):
        orders = self.get_active_orders(connector_name=self.exchange)
        if orders:
            self.log_with_clock(logging.INFO, f"Canceling {len(orders)} active orders")
            for order in orders:
                self.cancel(self.exchange, order.trading_pair, order.client_order_id)

    def did_fill_order(self, event: OrderFilledEvent):
        msg = (f"{event.trade_type.name} {round(event.amount, 2)} {event.trading_pair} {self.exchange} at {round(event.price, 2)}")
        self.log_with_clock(logging.INFO, msg)
        self.notify_hb_app_with_timestamp(msg)

    def format_status(self) -> str:
        """
        Returns status of the current strategy and displays candles feed info
        """
        if not self.ready_to_trade:
            return "Market connectors are not ready."
        lines = []

        balance_df = self.get_balance_df()
        lines.extend(["", "  Balances:"] + ["    " + line for line in balance_df.to_string(index=False).split("\n")])

        try:
            df = self.active_orders_df()
            lines.extend(["", "  Orders:"] + ["    " + line for line in df.to_string(index=False).split("\n")])
        except ValueError:
            lines.extend(["", "  No active maker orders."])

        lines.extend(["\n----------------------------------------------------------------------\n"])
        lines.extend(["  Strategy Metrics:"])
        
        base_asset = self.trading_pair.split("-")[0]
        quote_asset = self.trading_pair.split("-")[1]
        base_balance = float(self.connectors[self.exchange].get_balance(base_asset))
        quote_balance = float(self.connectors[self.exchange].get_balance(quote_asset))
        mid_price = float(self.connectors[self.exchange].get_price_by_type(self.trading_pair, self.price_source))
        
        lines.extend([f"  Current Inventory: {base_balance:.4f} {base_asset}, {quote_balance:.2f} {quote_asset}"])
        lines.extend([f"  Current Price: {mid_price:.4f}"])
        
        total_value = quote_balance + (base_balance * mid_price)
        if total_value > 0:
            inventory_ratio = (base_balance * mid_price) / total_value * 100
            lines.extend([f"  Inventory Ratio: {inventory_ratio:.2f}% in {base_asset}"])
        
        bid_spread, ask_spread = self.calculate_spreads()
        lines.extend([f"  Bid Spread: {bid_spread*100:.4f}%, Ask Spread: {ask_spread*100:.4f}%"])
        
        lines.extend(["\n----------------------------------------------------------------------\n"])
        candles_df = self.get_candles_with_features()
        lines.extend([f"  Candles: {self.candles.name} | Interval: {self.candles.interval}", ""])
        
        if not candles_df.empty:
            display_df = candles_df.tail(5).iloc[::-1]
            lines.extend(["    " + line for line in display_df.to_string(index=False).split("\n")])

        return "\n".join(lines)

# Adaptive Crypto Market Maker

A sophisticated market making strategy for cryptocurrency trading built on the Hummingbot framework. This implementation features dynamic spread adjustment based on market volatility and inventory position, inspired by quantitative finance principles.

## Overview

This strategy extends basic pure market making by incorporating advanced mathematical principles to dynamically adjust spreads based on:

- Market volatility (using NATR indicator)
- Current inventory position
- Risk aversion parameters

Unlike static spread strategies, this adaptive approach provides better risk management during volatile markets and improved execution during calm periods.

## Implementation Details

The strategy uses the following key components:

1. **Dynamic Spread Calculation**: Spreads are calculated based on volatility and inventory position
2. **Inventory Management**: Automatically adjusts pricing to maintain target inventory ratios
3. **Risk-Adjusted Pricing**: Incorporates risk aversion parameters to balance profitability and risk

## Requirements

- Hummingbot 2.x or higher
- Python 3.8+
- Access to exchange API (configured in Hummingbot)

## Setup

1. Install Hummingbot following the [official documentation](https://docs.hummingbot.org/installation/)
2. Place `adaptive_market_maker.py` in your Hummingbot scripts directory:
   - Usually located at `hummingbot/scripts/`
3. Configure exchange connections in Hummingbot

## Usage

Start the strategy with:

```
start --script adaptive_market_maker.py
```

Monitor performance with:

```
status
```

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `trading_pair` | SOL-USDT | The trading pair to make markets on |
| `order_amount` | 1 | Size of each order |
| `order_refresh_time` | 15 | How often to refresh orders (seconds) |
| `risk_aversion` | 0.9 | Risk aversion parameter (higher = more conservative) |
| `min_spread` | 0.001 | Minimum spread as a decimal (0.001 = 0.1%) |

## Strategy Logic

The implementation calculates optimal bid and ask spreads around a reservation price that shifts based on inventory position. When holding more of the base asset than the target ratio, it widens ask spreads and tightens bid spreads to encourage inventory rebalancing.

The spread calculation considers:

1. Base volatility (from NATR indicator)
2. Current inventory ratio relative to target (default 50%)
3. Risk aversion parameter

## Performance Considerations

This strategy generally performs best in:
- Markets with moderate volatility
- Assets with sufficient trading volume
- Environments where spreads exceed exchange fees

## Disclaimer

This code is provided for educational and research purposes only. Trading cryptocurrencies involves significant risk. Use at your own risk.

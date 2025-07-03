# Avellaneda-Stoikov Adaptive Market Maker

> **For detailed mathematical derivation and strategy design, see:** [My Strategy.pdf](./My%20Strategy.pdf)

A sophisticated market making strategy for cryptocurrency trading built on the Hummingbot framework. This implementation is directly inspired by the **Avellaneda-Stoikov model** from quantitative finance, featuring dynamic spread adjustment based on market volatility and inventory position.

## Overview

This strategy extends basic pure market making by incorporating advanced mathematical principles from the Avellaneda-Stoikov framework to dynamically adjust spreads based on:

- **Market volatility** (using NATR indicator)
- **Current inventory position**
- **Risk aversion parameters**

By building on the Avellaneda-Stoikov model rather than static heuristics, this adaptive approach provides better risk management during volatile markets and improved execution during calm periods.

## Implementation Details

The strategy uses the following key components:

1. **Dynamic Spread Calculation**
   - Spreads are calculated according to the Avellaneda-Stoikov equations
   - Factors in volatility and inventory position

2. **Inventory Management**
   - Automatically adjusts pricing to maintain target inventory ratios
   - Rebalances holdings based on current position

3. **Risk-Adjusted Pricing**
   - Incorporates risk aversion parameters (γ)
   - Balances profitability and downside protection

## Requirements

- Hummingbot 2.x or higher
- Python 3.8+
- Access to exchange API (configured in Hummingbot)

## Setup

1. Install Hummingbot following the [official documentation](https://docs.hummingbot.org/installation/)
2. Place `adaptive_market_maker.py` in your Hummingbot scripts directory (typically `hummingbot/scripts/`)
3. Configure your exchange connections in Hummingbot

## Usage

Start the strategy:
```bash
start --script adaptive_market_maker.py
```

Monitor performance:
```bash
status
```

## Key Parameters

| Parameter            | Default  | Description                                            |
|----------------------|----------|--------------------------------------------------------|
| `trading_pair`       | SOL-USDT | The trading pair to make markets on                    |
| `order_amount`       | 1        | Size of each order                                     |
| `order_refresh_time` | 15       | How often to refresh orders (seconds)                  |
| `risk_aversion`      | 0.9      | Risk aversion parameter γ (higher = more conservative) |
| `min_spread`         | 0.001    | Minimum spread as a decimal (0.001 = 0.1%)             |

## Strategy Logic

We calculate an optimal reservation price and spread following Avellaneda-Stoikov:

### Reservation Price
$$r = s - q \cdot \gamma \cdot \sigma^2 \cdot (T - t)$$

### Optimal Spread
$$\text{spread} = \gamma \cdot \sigma^2 \cdot (T - t) + \frac{2}{\gamma} \ln\left(1 + \frac{\gamma}{k}\right)$$

**Where:**
- $s$ = mid-price
- $q$ = current inventory
- $\gamma$ = risk aversion
- $\sigma$ = market volatility (NATR)
- $T - t$ = time horizon remaining
- $k$ = arrival-rate parameter

## Disclaimer

This code is provided for educational and research purposes only. Trading cryptocurrencies involves significant risk.

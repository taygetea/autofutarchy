# Simple Prediction Market

A barebones prediction market implementation using an Automated Market Maker (AMM) mechanism.

## Features

- Binary prediction markets (YES/NO outcomes)
- Constant product AMM for automatic pricing
- RESTful API 
- Command-line interface
- No blockchain - just a simple server

## How it works

Markets use a constant product formula (like Uniswap):
- Each market has YES and NO token pools
- Price of YES = NO_pool / (YES_pool + NO_pool)
- Buying shares removes from one pool and adds to the other
- The product YES_pool × NO_pool remains constant

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the server:
```bash
python app.py
```

3. In another terminal, use the CLI:
```bash
# List markets
python cli.py list

# Create a user
python cli.py create_user alice

# Create a market
python cli.py create_market "Will BTC hit 100k?" 2025-12-31

# Trade
python cli.py trade user_1 market_1 YES 10

# Check user position
python cli.py user user_1
```

## API Endpoints

- `GET /markets` - List all markets
- `POST /markets` - Create a market
- `GET /markets/<id>` - Get market details
- `POST /users` - Create a user
- `GET /users/<id>` - Get user info
- `POST /trades` - Execute a trade
- `POST /markets/<id>/resolve` - Resolve a market

## Example: Trading

```python
# The market starts with equal pools (100 YES, 100 NO tokens)
# Initial prices: YES = $0.50, NO = $0.50

# Alice buys 10 YES shares
# Cost calculation: Need to maintain YES_pool × NO_pool = 10,000
# New YES_pool = 90, so new NO_pool = 10,000/90 = 111.11
# Cost = 111.11 - 100 = $11.11

# After trade:
# YES price = 111.11 / (90 + 111.11) = $0.553
# NO price = 90 / (90 + 111.11) = $0.447
```

## Next Steps

1. **Add LLM Integration** - Create agents that can analyze markets and trade
2. **Add WebSocket support** - Real-time price updates
3. **Add order book option** - For more sophisticated trading
4. **Add market categories** - Organize markets by topic
5. **Add betting limits** - Prevent market manipulation
6. **Add historical charts** - Visualize price movements
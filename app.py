"""
Simple Flask API for the prediction market
"""
from flask import Flask, request, jsonify
from datetime import datetime
from market import PredictionMarket, Side
import json

app = Flask(__name__)
pm = PredictionMarket()

# Create demo data only if database is empty
if not pm.markets and not pm.users:
    demo_user = pm.create_user("demo_user", initial_balance=10000)
    demo_market = pm.create_market(
        "Will Bitcoin reach $100k by end of 2025?",
        closes_at=datetime(2025, 12, 31)
    )
    print(f"Created demo user: {demo_user.id}")
    print(f"Created demo market: {demo_market.id}")
else:
    print(f"Loaded {len(pm.markets)} markets and {len(pm.users)} users from database")

@app.route('/')
def index():
    return jsonify({
        'message': 'Simple Prediction Market API',
        'endpoints': {
            'GET /markets': 'List all markets',
            'POST /markets': 'Create a new market',
            'GET /markets/<id>': 'Get market details',
            'POST /users': 'Create a new user',
            'GET /users/<id>': 'Get user details',
            'POST /trades': 'Execute a trade',
            'POST /markets/<id>/resolve': 'Resolve a market'
        }
    })

@app.route('/markets', methods=['GET'])
def list_markets():
    """List all markets"""
    markets = []
    for market_id, market in pm.markets.items():
        markets.append({
            'id': market_id,
            'question': market.question,
            'yes_price': market.get_price(Side.YES),
            'no_price': market.get_price(Side.NO),
            'resolved': market.resolved,
            'closes_at': market.closes_at.isoformat()
        })
    return jsonify(markets)

@app.route('/markets', methods=['POST'])
def create_market():
    """Create a new market"""
    data = request.json
    
    try:
        market = pm.create_market(
            question=data['question'],
            closes_at=datetime.fromisoformat(data['closes_at']),
            initial_liquidity=data.get('initial_liquidity', 100.0)
        )
        
        return jsonify({
            'id': market.id,
            'question': market.question,
            'created_at': market.created_at.isoformat(),
            'closes_at': market.closes_at.isoformat(),
            'yes_price': market.get_price(Side.YES),
            'no_price': market.get_price(Side.NO)
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/markets/<market_id>', methods=['GET'])
def get_market(market_id):
    """Get market details"""
    try:
        info = pm.get_market_info(market_id)
        return jsonify(info)
    except ValueError as e:
        return jsonify({'error': str(e)}), 404

@app.route('/users', methods=['POST'])
def create_user():
    """Create a new user"""
    data = request.json
    
    try:
        user = pm.create_user(
            username=data['username'],
            initial_balance=data.get('initial_balance', 1000.0)
        )
        
        return jsonify({
            'id': user.id,
            'username': user.username,
            'balance': user.balance
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/users', methods=['GET'])
def list_users():
    """List all users"""
    users = []
    for user_id, user in pm.users.items():
        users.append({
            'id': user_id,
            'username': user.username,
            'balance': user.balance,
            'num_positions': len([p for p in user.positions.values() if p.yes_shares > 0 or p.no_shares > 0])
        })
    return jsonify(users)

@app.route('/users/<user_id>', methods=['GET'])
def get_user(user_id):
    """Get user details"""
    try:
        info = pm.get_user_info(user_id)
        return jsonify(info)
    except ValueError as e:
        return jsonify({'error': str(e)}), 404

@app.route('/trades', methods=['POST'])
def execute_trade():
    """Execute a trade"""
    data = request.json
    
    try:
        side = Side.YES if data['side'].upper() == 'YES' else Side.NO
        
        trade = pm.buy_shares(
            user_id=data['user_id'],
            market_id=data['market_id'],
            side=side,
            shares=data['shares'],
            max_cost=data.get('max_cost')
        )
        
        # Save reasoning/comment if provided
        if 'reasoning' in data:
            pm.save_trade_comment(
                trade_id=trade.id,
                reasoning=data['reasoning'],
                model_name=data.get('model_name'),
                strategy=data.get('strategy'),
                confidence=data.get('confidence'),
                is_llm=data.get('is_llm_trader', False)
            )
        
        # Get updated market info
        market_info = pm.get_market_info(data['market_id'])
        
        return jsonify({
            'trade_id': trade.id,
            'cost': trade.cost,
            'price': trade.price,
            'shares': trade.shares,
            'side': trade.side.value,
            'timestamp': trade.timestamp.isoformat(),
            'new_yes_price': market_info['yes_price'],
            'new_no_price': market_info['no_price']
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/markets/<market_id>/trades', methods=['GET'])
def get_market_trades(market_id):
    """Get trades for a market with comments"""
    try:
        limit = request.args.get('limit', 50, type=int)
        trades = pm.get_trades_with_comments(market_id, limit)
        return jsonify(trades)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/trades/recent', methods=['GET'])
def get_recent_trades():
    """Get recent trades across all markets"""
    try:
        limit = request.args.get('limit', 50, type=int)
        trades = pm.get_trades_with_comments(limit=limit)
        return jsonify(trades)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/markets/<market_id>/resolve', methods=['POST'])
def resolve_market(market_id):
    """Resolve a market"""
    data = request.json
    
    try:
        outcome = data['outcome']  # Should be True or False
        payouts = pm.resolve_market(market_id, outcome)
        
        return jsonify({
            'market_id': market_id,
            'outcome': outcome,
            'payouts': payouts
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/markets/<market_id>', methods=['DELETE'])
def delete_market(market_id):
    """Delete a market"""
    try:
        pm.delete_market(market_id)
        return jsonify({
            'message': f'Market {market_id} deleted successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/admin/markets/<market_id>/pools', methods=['PUT'])
def set_market_pools(market_id):
    """Admin: Directly set market pool values"""
    data = request.json
    
    try:
        yes_pool = float(data['yes_pool'])
        no_pool = float(data['no_pool'])
        
        result = pm.set_market_pools(market_id, yes_pool, no_pool)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/admin/users/<user_id>/balance', methods=['PUT'])
def modify_user_balance(user_id):
    """Admin: Modify user balance"""
    data = request.json
    
    try:
        amount = float(data['amount'])
        result = pm.modify_user_balance(user_id, amount)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/traders/launch', methods=['POST'])
def launch_traders():
    """Launch LLM traders in a background thread"""
    data = request.json
    market_id = data['market_id']
    num_traders = data.get('num_traders', 3)
    rounds = data.get('rounds', 1)
    enable_search = data.get('enable_search', True)
    
    # Import the appropriate trader module
    if enable_search:
        from llm_trader_with_search import run_llm_traders_with_search
        
        # Run in a thread to not block the API
        import threading
        thread = threading.Thread(
            target=run_llm_traders_with_search,
            args=(market_id, num_traders, rounds, enable_search)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'status': 'launched',
            'market_id': market_id,
            'num_traders': num_traders,
            'rounds': rounds,
            'search_enabled': enable_search
        })
    else:
        from llm_trader import run_llm_traders
        
        import threading
        thread = threading.Thread(
            target=run_llm_traders,
            args=(market_id, num_traders, rounds)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'status': 'launched',
            'market_id': market_id,
            'num_traders': num_traders,
            'rounds': rounds,
            'search_enabled': False
        })

@app.route('/simulate', methods=['POST'])
def simulate_market():
    """Simulate market activity for testing"""
    data = request.json
    market_id = data['market_id']
    num_trades = data.get('num_trades', 10)
    
    # Create some test users
    users = []
    for i in range(5):
        user = pm.create_user(f"bot_{i}", initial_balance=5000)
        users.append(user)
    
    # Simulate random trades
    import random
    trades = []
    
    for _ in range(num_trades):
        user = random.choice(users)
        side = random.choice([Side.YES, Side.NO])
        shares = random.uniform(1, 20)
        
        try:
            trade = pm.buy_shares(user.id, market_id, side, shares)
            trades.append({
                'user': user.username,
                'side': side.value,
                'shares': shares,
                'cost': trade.cost,
                'price': trade.price
            })
        except Exception as e:
            # Skip failed trades (insufficient balance, etc)
            pass
    
    market_info = pm.get_market_info(market_id)
    
    return jsonify({
        'trades_executed': len(trades),
        'final_yes_price': market_info['yes_price'],
        'final_no_price': market_info['no_price'],
        'total_volume': market_info['volume'],
        'trades': trades
    })

if __name__ == '__main__':
    import atexit
    
    # Register cleanup function
    def cleanup():
        pm.close()
        print("\nDatabase connection closed")
    
    atexit.register(cleanup)
    
    print("\n=== Starting Flask app on http://localhost:5000 ===")
    print("Database: prediction_market.db")
    print("\nTry these commands:")
    print('  curl http://localhost:5000/markets')
    print('  python cli.py list')
    print('  python cli.py create_user alice')
    
    try:
        app.run(debug=True)
    except KeyboardInterrupt:
        cleanup()
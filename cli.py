#!/usr/bin/env python3
"""
Simple CLI for interacting with the prediction market
"""
import requests
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:5000"

def list_markets():
    """List all markets"""
    resp = requests.get(f"{BASE_URL}/markets")
    markets = resp.json()
    
    print("\n=== MARKETS ===")
    for market in markets:
        status = "RESOLVED" if market['resolved'] else "OPEN"
        print(f"\nID: {market['id']}")
        print(f"Question: {market['question']}")
        print(f"YES: ${market['yes_price']:.2f} | NO: ${market['no_price']:.2f}")
        print(f"Status: {status}")
        print(f"Closes: {market['closes_at']}")

def create_market(question, closes_at, liquidity=100):
    """Create a new market"""
    data = {
        'question': question,
        'closes_at': closes_at,
        'initial_liquidity': liquidity
    }
    
    resp = requests.post(f"{BASE_URL}/markets", json=data)
    if resp.status_code == 201:
        market = resp.json()
        print(f"\n✓ Market created!")
        print(f"ID: {market['id']}")
        print(f"Question: {market['question']}")
        print(f"Initial prices - YES: ${market['yes_price']:.2f}, NO: ${market['no_price']:.2f}")
    else:
        print(f"\n✗ Error: {resp.json()['error']}")

def create_user(username, balance=1000):
    """Create a new user"""
    data = {
        'username': username,
        'initial_balance': balance
    }
    
    resp = requests.post(f"{BASE_URL}/users", json=data)
    if resp.status_code == 201:
        user = resp.json()
        print(f"\n✓ User created!")
        print(f"ID: {user['id']}")
        print(f"Username: {user['username']}")
        print(f"Balance: ${user['balance']:.2f}")
    else:
        print(f"\n✗ Error: {resp.json()['error']}")

def trade(user_id, market_id, side, shares, max_cost=None):
    """Execute a trade"""
    data = {
        'user_id': user_id,
        'market_id': market_id,
        'side': side.upper(),
        'shares': shares
    }
    if max_cost:
        data['max_cost'] = max_cost
    
    resp = requests.post(f"{BASE_URL}/trades", json=data)
    if resp.status_code == 201:
        trade = resp.json()
        print(f"\n✓ Trade executed!")
        print(f"Bought {trade['shares']} {trade['side']} shares")
        print(f"Total cost: ${trade['cost']:.2f}")
        print(f"Price per share: ${trade['price']:.2f}")
        print(f"New market prices - YES: ${trade['new_yes_price']:.2f}, NO: ${trade['new_no_price']:.2f}")
    else:
        print(f"\n✗ Error: {resp.json()['error']}")

def get_user(user_id):
    """Get user info"""
    resp = requests.get(f"{BASE_URL}/users/{user_id}")
    if resp.status_code == 200:
        user = resp.json()
        print(f"\n=== USER: {user['username']} ===")
        print(f"Balance: ${user['balance']:.2f}")
        print(f"Total Value: ${user['total_value']:.2f}")
        
        if user['positions']:
            print("\nPositions:")
            for market_id, pos in user['positions'].items():
                print(f"\n  Market: {pos['market_question']}")
                print(f"  YES shares: {pos['yes_shares']}")
                print(f"  NO shares: {pos['no_shares']}")
                print(f"  Current value: ${pos['current_value']:.2f}")
    else:
        print(f"\n✗ Error: {resp.json()['error']}")

def simulate(market_id, num_trades=20):
    """Simulate trading activity"""
    data = {
        'market_id': market_id,
        'num_trades': num_trades
    }
    
    resp = requests.post(f"{BASE_URL}/simulate", json=data)
    result = resp.json()
    
    print(f"\n=== SIMULATION COMPLETE ===")
    print(f"Trades executed: {result['trades_executed']}")
    print(f"Final YES price: ${result['final_yes_price']:.2f}")
    print(f"Final NO price: ${result['final_no_price']:.2f}")
    print(f"Total volume: ${result['total_volume']:.2f}")

def delete_market(market_id):
    """Delete a market"""
    resp = requests.delete(f"{BASE_URL}/markets/{market_id}")
    if resp.status_code == 200:
        result = resp.json()
        print(f"\n✓ {result['message']}")
    else:
        print(f"\n✗ Error: {resp.json()['error']}")

def print_help():
    print("""
Simple Prediction Market CLI

Commands:
  list                          List all markets
  create_market <q> <date>      Create market (date: YYYY-MM-DD)
  create_user <username>        Create user
  trade <user> <market> <Y/N> <shares>  Execute trade
  user <user_id>                Show user info
  delete <market_id>            Delete a market (if no positions)
  simulate <market_id>          Simulate trading
  help                          Show this help

Examples:
  python cli.py list
  python cli.py create_market "Will it rain tomorrow?" 2024-12-31
  python cli.py create_user alice
  python cli.py trade user_1 market_1 YES 10
  python cli.py delete market_1
""")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_help()
        sys.exit(0)
    
    command = sys.argv[1].lower()
    
    try:
        if command == "list":
            list_markets()
        
        elif command == "create_market":
            if len(sys.argv) < 4:
                print("Usage: create_market <question> <closes_date>")
            else:
                question = sys.argv[2]
                closes_date = sys.argv[3]
                closes_at = datetime.fromisoformat(f"{closes_date}T23:59:59")
                create_market(question, closes_at.isoformat())
        
        elif command == "create_user":
            if len(sys.argv) < 3:
                print("Usage: create_user <username>")
            else:
                create_user(sys.argv[2])
        
        elif command == "trade":
            if len(sys.argv) < 6:
                print("Usage: trade <user_id> <market_id> <YES/NO> <shares>")
            else:
                trade(sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[5]))
        
        elif command == "user":
            if len(sys.argv) < 3:
                print("Usage: user <user_id>")
            else:
                get_user(sys.argv[2])
        
        elif command == "simulate":
            if len(sys.argv) < 3:
                print("Usage: simulate <market_id>")
            else:
                simulate(sys.argv[2])
        
        elif command == "delete":
            if len(sys.argv) < 3:
                print("Usage: delete <market_id>")
            else:
                delete_market(sys.argv[2])
        
        elif command == "help":
            print_help()
        
        else:
            print(f"Unknown command: {command}")
            print_help()
    
    except requests.exceptions.ConnectionError:
        print("\n✗ Error: Cannot connect to server. Make sure the Flask app is running.")
    except Exception as e:
        print(f"\n✗ Error: {e}")
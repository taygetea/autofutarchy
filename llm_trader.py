"""
LLM-based trader for the prediction market
"""
import requests
import json
from datetime import datetime
import llm
import random
import time

BASE_URL = "http://localhost:5000"

class LLMTrader:
    def __init__(self, model="openrouter/anthropic/claude-3.5-sonnet", name=None, strategy="balanced"):
        self.model_name = model
        self.model = llm.get_model(model)
        self.name = name or f"llm_{model.split('/')[-1][:8]}"
        self.strategy = strategy
        self.user_id = None
        self.trade_history = []
        self.last_action = None
        
    def register(self):
        """Register as a user in the market"""
        resp = requests.post(f"{BASE_URL}/users", json={
            'username': self.name,
            'initial_balance': 5000.0
        })
        
        if resp.status_code == 201:
            user = resp.json()
            self.user_id = user['id']
            print(f"[{self.name}] Registered with ID {self.user_id}")
            return True
        return False
    
    def analyze_market(self, market):
        """Use LLM to analyze a prediction market"""
        prompt = f"""You are a prediction market trader analyzing this market:

Question: {market['question']}
Current YES price: ${market['yes_price']:.2f}
Current NO price: ${market['no_price']:.2f}
Pool sizes: {market['yes_pool']:.1f} YES tokens, {market['no_pool']:.1f} NO tokens
Closes: {market['closes_at']}

IMPORTANT CONTEXT:
- This is a prediction market where prices represent probabilities
- YES price of ${market['yes_price']:.2f} means the market thinks there's a {market['yes_price']:.0%} chance the event happens
- If you buy YES shares at ${market['yes_price']:.2f} and the event happens, you get $1.00 per share
- If you buy NO shares at ${market['no_price']:.2f} and the event doesn't happen, you get $1.00 per share
- Current date: {datetime.now().strftime('%Y-%m-%d')}
- Market uses an AMM, so large trades will move the price
- Pool liquidity: You can buy at most ~{int(market['yes_pool'] * 0.5)} YES shares or ~{int(market['no_pool'] * 0.5)} NO shares
  (buying more would exhaust the pool)

CRITICAL INFORMATION FOR BITCOIN MARKETS:
- Bitcoin's current price is already OVER $100,000 USD
- Bitcoin crossed $100k in late 2024
- Current BTC price: ~$105,000 USD

Your trading strategy is: {self.strategy}
- aggressive: Take larger positions when confident
- conservative: Only trade on high confidence with smaller positions  
- balanced: Moderate positions based on confidence
- analytical: Only trade when confidence > 70%

Based on your knowledge and analysis:
1. BUY YES - if you think the event is MORE likely than {market['yes_price']:.0%}
2. BUY NO - if you think the event is LESS likely than {market['yes_price']:.0%}
3. HOLD - if the current price seems fair

Respond with a JSON object:
{{
  "action": "BUY_YES" | "BUY_NO" | "HOLD",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation",
  "fair_probability": 0.0-1.0
}}"""

        try:
            # Use simonw/llm library for model interaction
            response = self.model.prompt(prompt)
            content = response.text()
            # Find JSON in the response
            import re
            json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                print(f"[{self.name}] Failed to parse JSON from: {content}")
                return None
                
        except Exception as e:
            print(f"[{self.name}] Error analyzing market: {e}")
            return None
    
    def calculate_shares(self, confidence, balance, market_info=None):
        """Calculate how many shares to buy based on confidence and liquidity"""
        # More conservative approach for small liquidity pools
        # Start with smaller bets: 2% of balance max instead of 20%
        max_bet = balance * 0.02
        
        if self.strategy == "aggressive":
            bet_size = max_bet * confidence
        elif self.strategy == "conservative":
            bet_size = max_bet * confidence * 0.5
        elif self.strategy == "analytical":
            # Analytical strategy: only bet on high confidence
            bet_size = max_bet * confidence * 0.9 if confidence > 0.7 else 0
        else:  # balanced
            bet_size = max_bet * confidence * 0.75
            
        # Calculate shares - be more conservative
        # With 100 token pools, buying 10 shares costs ~$11
        shares = bet_size / 2.0  # Assume ~$2 per share to be safe
        
        # If we have market info, cap based on available liquidity
        if market_info:
            if self.last_action == "BUY_YES":
                # Don't try to buy more than 40% of the YES pool
                max_liquidity_shares = int(market_info['yes_pool'] * 0.4)
            else:
                # Don't try to buy more than 40% of the NO pool
                max_liquidity_shares = int(market_info['no_pool'] * 0.4)
            shares = min(shares, max_liquidity_shares)
        
        return max(1, min(20, int(shares)))  # Cap at 20 shares max
    
    def execute_trade(self, market_id, action, confidence, analysis=None):
        """Execute a trade based on analysis"""
        # Get current balance
        resp = requests.get(f"{BASE_URL}/users/{self.user_id}")
        if resp.status_code != 200:
            return None
            
        user_data = resp.json()
        balance = user_data['balance']
        
        if balance < 10:  # Minimum to trade
            print(f"[{self.name}] Insufficient balance: ${balance:.2f}")
            return None
        
        # Calculate trade size
        shares = self.calculate_shares(confidence, balance)
        side = "YES" if action == "BUY_YES" else "NO"
        
        # Execute trade
        trade_data = {
            'user_id': self.user_id,
            'market_id': market_id,
            'side': side,
            'shares': shares,
            'max_cost': balance * 0.9  # Don't spend everything
        }
        
        # Add reasoning if available
        if analysis:
            trade_data.update({
                'reasoning': analysis.get('reasoning', ''),
                'model_name': self.model_name,
                'strategy': self.strategy,
                'confidence': confidence,
                'is_llm_trader': True
            })
        
        resp = requests.post(f"{BASE_URL}/trades", json=trade_data)
        
        if resp.status_code == 201:
            trade = resp.json()
            self.trade_history.append(trade)
            print(f"[{self.name}] ✓ Bought {shares} {side} shares for ${trade['cost']:.2f}")
            print(f"[{self.name}]   Average price: ${trade['price']:.3f}/share")
            print(f"[{self.name}]   Market moved: YES ${trade['new_yes_price']:.3f} | NO ${trade['new_no_price']:.3f}")
            return trade
        else:
            error_msg = resp.json()['error']
            print(f"[{self.name}] ✗ Trade failed: {error_msg}")
            if "liquidity" in error_msg.lower():
                print(f"[{self.name}]   (Tried to buy {shares} shares, but pool too small)")
            return None
    
    def trade_on_market(self, market_id):
        """Analyze and potentially trade on a market"""
        # Get market info
        resp = requests.get(f"{BASE_URL}/markets/{market_id}")
        if resp.status_code != 200:
            return
            
        market = resp.json()
        
        print(f"\n[{self.name}] Analyzing market: {market['question']}")
        
        # Analyze with LLM
        analysis = self.analyze_market(market)
        
        if not analysis:
            return
            
        print(f"[{self.name}] Analysis: {analysis['action']} (confidence: {analysis['confidence']:.2f})")
        print(f"[{self.name}] Reasoning: {analysis['reasoning']}")
        
        # Execute trade if not HOLD
        if analysis['action'] != "HOLD" and analysis['confidence'] > 0.3:
            self.last_action = analysis['action']
            self.execute_trade(market_id, analysis['action'], analysis['confidence'], analysis)
        else:
            print(f"[{self.name}] Holding position")


def run_llm_traders(market_id, num_traders=3, rounds=1):
    """Run multiple LLM traders on a market"""
    
    # Different models and strategies (using modern models from orchestrator)
    trader_configs = [
        ("openrouter/google/gemini-2.5-flash", "aggressive"),
        ("openrouter/openai/o4-mini", "balanced"),
        ("openrouter/anthropic/claude-sonnet-4", "conservative"),
        ("openrouter/deepseek/deepseek-r1-0528", "balanced"),
        ("openrouter/moonshotai/kimi-k2", "aggressive"),
        ("openrouter/google/gemini-2.5-pro", "analytical"),
        ("openrouter/openai/gpt-4.1", "conservative"),
    ]
    
    # Create traders
    traders = []
    for i in range(min(num_traders, len(trader_configs))):
        model, strategy = trader_configs[i]
        trader = LLMTrader(model=model, strategy=strategy)
        if trader.register():
            traders.append(trader)
    
    print(f"\nRegistered {len(traders)} traders")
    
    # Run trading rounds
    for round_num in range(rounds):
        print(f"\n=== ROUND {round_num + 1} ===")
        
        # Shuffle order for fairness
        random.shuffle(traders)
        
        for trader in traders:
            trader.trade_on_market(market_id)
            time.sleep(1)  # Rate limiting
        
        # Show market state
        resp = requests.get(f"{BASE_URL}/markets/{market_id}")
        if resp.status_code == 200:
            market = resp.json()
            print(f"\nMarket prices after round {round_num + 1}:")
            print(f"YES: ${market['yes_price']:.3f} | NO: ${market['no_price']:.3f}")
            print(f"Volume: ${market['volume']:.2f}")
        
        if rounds > 1:
            time.sleep(3)  # Pause between rounds
    
    # Final summary
    print("\n=== FINAL POSITIONS ===")
    for trader in traders:
        resp = requests.get(f"{BASE_URL}/users/{trader.user_id}")
        if resp.status_code == 200:
            user = resp.json()
            print(f"\n{trader.name}:")
            print(f"  Balance: ${user['balance']:.2f}")
            print(f"  Total Value: ${user['total_value']:.2f}")
            for market_id, pos in user['positions'].items():
                if pos['yes_shares'] > 0 or pos['no_shares'] > 0:
                    print(f"  Position: {pos['yes_shares']:.1f} YES, {pos['no_shares']:.1f} NO")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python llm_trader.py <market_id> [num_traders] [rounds]")
        print("Example: python llm_trader.py market_2 3 2")
        sys.exit(1)
    
    market_id = sys.argv[1]
    num_traders = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    rounds = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    
    run_llm_traders(market_id, num_traders, rounds)
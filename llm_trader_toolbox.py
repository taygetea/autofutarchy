"""
LLM trader with proper tool use via llm library
"""
import requests
import json
from datetime import datetime
import llm
import random
import time
import os
from pathlib import Path
from typing import Optional, List, Dict
from exa_py import Exa

BASE_URL = "http://localhost:5000"

# Initialize Exa if available
exa_api_key = os.getenv("EXA_API_KEY")
exa = Exa(api_key=exa_api_key) if exa_api_key else None


class MarketToolbox(llm.Toolbox):
    """Toolbox providing market analysis tools for LLM traders"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self._market_cache = {}
        self._search_cache = {}
    
    def search_web(self, query: str, max_results: int = 3) -> str:
        """Search the web for current information about a topic."""
        if not exa:
            return "Web search unavailable - no API key configured"
        
        # Check cache first
        cache_key = f"{query}:{max_results}"
        if cache_key in self._search_cache:
            return self._search_cache[cache_key]
        
        try:
            results = exa.search_and_contents(
                query,
                text=True,
                num_results=max_results,
                use_autoprompt=True
            )
            
            output = []
            for i, result in enumerate(results.results, 1):
                output.append(f"{i}. {result.title}")
                output.append(f"   URL: {result.url}")
                output.append(f"   {result.text[:300]}...")
                output.append("")
            
            result_text = "\n".join(output)
            self._search_cache[cache_key] = result_text
            return result_text
            
        except Exception as e:
            return f"Search error: {str(e)}"
    
    def get_market_details(self, market_id: str) -> str:
        """Get detailed information about a specific market."""
        try:
            resp = requests.get(f"{self.base_url}/markets/{market_id}")
            if resp.status_code == 200:
                market = resp.json()
                return json.dumps({
                    "id": market["id"],
                    "question": market["question"],
                    "yes_price": market["yes_price"],
                    "no_price": market["no_price"],
                    "yes_pool": market.get("yes_pool", "N/A"),
                    "no_pool": market.get("no_pool", "N/A"),
                    "volume": market.get("volume", 0),
                    "closes_at": market["closes_at"],
                    "resolved": market["resolved"]
                }, indent=2)
            else:
                return f"Error fetching market {market_id}: {resp.status_code}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def get_recent_trades(self, market_id: str, limit: int = 10) -> str:
        """Get recent trades for a market to understand sentiment."""
        try:
            resp = requests.get(f"{self.base_url}/markets/{market_id}/trades?limit={limit}")
            if resp.status_code == 200:
                trades = resp.json()
                if not trades:
                    return "No trades yet"
                
                output = []
                for trade in trades[:limit]:
                    trader_type = "🤖 LLM" if trade.get("is_llm_trader") else "👤 Human"
                    output.append(
                        f"{trader_type} {trade['username']}: "
                        f"{trade['shares']:.1f} {trade['side']} @ ${trade['price']:.3f}"
                    )
                    if trade.get("reasoning"):
                        output.append(f"  Reasoning: {trade['reasoning'][:100]}...")
                
                return "\n".join(output)
            else:
                return f"Error fetching trades: {resp.status_code}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def list_markets(self, only_active: bool = True) -> str:
        """List all available markets."""
        try:
            resp = requests.get(f"{self.base_url}/markets")
            if resp.status_code == 200:
                markets = resp.json()
                if only_active:
                    markets = [m for m in markets if not m["resolved"]]
                
                output = []
                for market in markets:
                    output.append(
                        f"- {market['id']}: {market['question'][:60]}... "
                        f"(YES: ${market['yes_price']:.2f})"
                    )
                
                return "\n".join(output) if output else "No active markets"
            else:
                return f"Error fetching markets: {resp.status_code}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def read_file(self, filepath: str) -> str:
        """Read a file from the codebase (proposals, docs, code)."""
        try:
            path = Path(filepath)
            if not path.exists():
                return f"File not found: {filepath}"
            
            with open(path, 'r') as f:
                content = f.read()
            
            # Truncate very large files
            if len(content) > 10000:
                return content[:10000] + f"\n\n[Truncated - file has {len(content)} chars total]"
            
            return content
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    def list_files(self, pattern: str = "*") -> str:
        """List files in the project matching a pattern."""
        try:
            files = []
            for path in Path(".").glob(pattern):
                if path.is_file() and not str(path).startswith('.'):
                    files.append(str(path))
            
            return "\n".join(sorted(files)) if files else f"No files matching {pattern}"
        except Exception as e:
            return f"Error listing files: {str(e)}"
    
    def calculate_metrics(self) -> str:
        """Calculate current system metrics for governance decisions."""
        metrics = {}
        
        # Code metrics
        try:
            py_files = list(Path(".").glob("*.py"))
            total_lines = 0
            comment_lines = 0
            
            for file in py_files:
                with open(file, 'r') as f:
                    for line in f:
                        total_lines += 1
                        if line.strip().startswith('#'):
                            comment_lines += 1
            
            metrics["code_files"] = len(py_files)
            metrics["total_lines"] = total_lines
            metrics["comment_ratio"] = f"{(comment_lines/total_lines*100):.1f}%" if total_lines > 0 else "0%"
            
        except Exception as e:
            metrics["code_error"] = str(e)
        
        # Market metrics
        try:
            resp = requests.get(f"{self.base_url}/markets")
            if resp.status_code == 200:
                markets = resp.json()
                metrics["total_markets"] = len(markets)
                metrics["active_markets"] = sum(1 for m in markets if not m["resolved"])
                
                # Calculate total volume
                total_volume = 0
                for market in markets[:5]:  # Sample first 5 to avoid too many requests
                    detail = requests.get(f"{self.base_url}/markets/{market['id']}").json()
                    total_volume += detail.get("volume", 0)
                
                metrics["sample_volume"] = f"${total_volume:.2f}"
        except:
            pass
        
        return json.dumps(metrics, indent=2)


class ToolboxTrader:
    """LLM trader that uses tools to make informed decisions"""
    
    def __init__(self, model="openrouter/anthropic/claude-sonnet-4", name=None, strategy="balanced"):
        self.model_name = model
        self.name = name or f"tool_{model.split('/')[-1][:8]}"
        self.strategy = strategy
        self.user_id = None
        self.toolbox = MarketToolbox()
        
        # Get model with tools
        self.model = llm.get_model(model)
        
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
    
    def analyze_and_trade(self, market_id: str, market_type: str = "prediction"):
        """Analyze a market using tools and execute trades"""
        
        # Get basic market info first
        resp = requests.get(f"{BASE_URL}/markets/{market_id}")
        if resp.status_code != 200:
            print(f"[{self.name}] Failed to get market info")
            return
        
        market = resp.json()
        
        print(f"\n[{self.name}] Analyzing market: {market['question']}")
        
        # Craft prompt based on market type
        if market_type == "governance":
            prompt = f"""You are a governance trader analyzing a futarchy proposal market.

Market: {market['question']}
Current prices: YES ${market['yes_price']:.3f}, NO ${market['no_price']:.3f}

You have access to tools to:
- read_file: Read proposals, code, and documentation
- list_files: See what files exist
- calculate_metrics: Get current system metrics
- get_recent_trades: See what other traders think
- search_web: Get external information if needed

First, understand the proposal by reading relevant files. Then analyze whether implementing it would improve our metrics (code quality, performance, market health).

Your trading strategy is: {self.strategy}

After analysis, decide:
1. Should we implement this proposal? (buy YES or NO)
2. How confident are you? (affects trade size)
3. What's your reasoning?

Make your decision and explain it clearly."""

        else:  # Regular prediction market
            prompt = f"""You are a prediction market trader analyzing this market:

Question: {market['question']}
Current prices: YES ${market['yes_price']:.3f}, NO ${market['no_price']:.3f}
Closes: {market['closes_at']}

You have access to tools to:
- search_web: Get current information about the topic
- get_market_details: Get full market information
- get_recent_trades: See trading activity and sentiment
- list_markets: See other related markets

Current date: {datetime.now().strftime('%Y-%m-%d')}
Your trading strategy is: {self.strategy}

Use tools to gather information, then decide:
1. Is the event more or less likely than the current price suggests?
2. Should you buy YES or NO shares?
3. How confident are you?

Make your trading decision and explain your reasoning."""

        try:
            # Use chain to handle tool calls automatically
            conversation = self.model.conversation(tools=[self.toolbox])
            chain = conversation.chain(prompt)
            
            # Collect the full response
            full_response = ""
            for chunk in chain:
                full_response += chunk
                print(chunk, end="", flush=True)
            
            print()  # New line after streaming
            
            # Extract trading decision from response
            decision = self._parse_trading_decision(full_response)
            
            if decision:
                self._execute_trade(market_id, decision, full_response)
            else:
                print(f"[{self.name}] No clear trading decision made")
                
        except Exception as e:
            print(f"[{self.name}] Error during analysis: {e}")
    
    def _parse_trading_decision(self, response: str) -> Optional[Dict]:
        """Extract trading decision from LLM response"""
        # Look for trading signals in the response
        response_lower = response.lower()
        
        # Determine action
        if "buy yes" in response_lower or "buying yes" in response_lower:
            action = "BUY_YES"
        elif "buy no" in response_lower or "buying no" in response_lower:
            action = "BUY_NO"
        elif "hold" in response_lower or "not trading" in response_lower:
            return None
        else:
            # Try to infer from context
            if "should implement" in response_lower or "good idea" in response_lower:
                action = "BUY_YES"
            elif "should not implement" in response_lower or "bad idea" in response_lower:
                action = "BUY_NO"
            else:
                return None
        
        # Estimate confidence from language
        confidence = 0.5  # Default
        if "very confident" in response_lower or "strongly" in response_lower:
            confidence = 0.8
        elif "somewhat confident" in response_lower or "moderately" in response_lower:
            confidence = 0.6
        elif "not very confident" in response_lower or "uncertain" in response_lower:
            confidence = 0.3
        
        return {
            "action": action,
            "confidence": confidence,
            "reasoning": response[:500]  # First 500 chars as reasoning
        }
    
    def _execute_trade(self, market_id: str, decision: Dict, full_reasoning: str):
        """Execute the trading decision"""
        # Get current balance
        resp = requests.get(f"{BASE_URL}/users/{self.user_id}")
        if resp.status_code != 200:
            return
        
        user_data = resp.json()
        balance = user_data['balance']
        
        if balance < 10:
            print(f"[{self.name}] Insufficient balance: ${balance:.2f}")
            return
        
        # Calculate trade size based on confidence and strategy
        max_bet = balance * 0.02  # 2% of balance
        
        if self.strategy == "aggressive":
            bet_size = max_bet * decision["confidence"]
        elif self.strategy == "conservative":
            bet_size = max_bet * decision["confidence"] * 0.5
        else:  # balanced
            bet_size = max_bet * decision["confidence"] * 0.75
        
        shares = max(1, min(50, int(bet_size / 1.0)))  # Assume ~$1 per share
        
        side = "YES" if decision["action"] == "BUY_YES" else "NO"
        
        # Execute trade
        trade_data = {
            'user_id': self.user_id,
            'market_id': market_id,
            'side': side,
            'shares': shares,
            'reasoning': decision["reasoning"],
            'model_name': self.model_name,
            'strategy': self.strategy,
            'confidence': decision["confidence"],
            'is_llm_trader': True
        }
        
        resp = requests.post(f"{BASE_URL}/trades", json=trade_data)
        
        if resp.status_code == 201:
            trade = resp.json()
            print(f"\n[{self.name}] ✓ Executed: {shares} {side} shares for ${trade['cost']:.2f}")
            print(f"[{self.name}] New prices: YES ${trade['new_yes_price']:.3f} | NO ${trade['new_no_price']:.3f}")
        else:
            print(f"\n[{self.name}] ✗ Trade failed: {resp.json().get('error', 'Unknown')}")


def run_toolbox_traders(market_id: str, num_traders: int = 3, market_type: str = "prediction"):
    """Run multiple traders with tool access"""
    
    models = [
        ("openrouter/anthropic/claude-sonnet-4", "balanced"),
        ("openrouter/openai/o4-mini", "aggressive"),
        ("openrouter/google/gemini-2.5-flash", "conservative"),
    ]
    
    traders = []
    for i in range(min(num_traders, len(models))):
        model, strategy = models[i]
        trader = ToolboxTrader(model=model, strategy=strategy)
        if trader.register():
            traders.append(trader)
    
    print(f"\nRegistered {len(traders)} toolbox traders")
    
    # Each trader analyzes independently
    for trader in traders:
        trader.analyze_and_trade(market_id, market_type)
        time.sleep(2)  # Rate limiting
    
    # Show final market state
    resp = requests.get(f"{BASE_URL}/markets/{market_id}")
    if resp.status_code == 200:
        market = resp.json()
        print(f"\n=== Final Market State ===")
        print(f"Question: {market['question']}")
        print(f"YES: ${market['yes_price']:.3f} | NO: ${market['no_price']:.3f}")
        print(f"Volume: ${market.get('volume', 0):.2f}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python llm_trader_toolbox.py <market_id> [num_traders] [type]")
        print("  type: 'prediction' (default) or 'governance'")
        print("Example: python llm_trader_toolbox.py market_1 3 prediction")
        print("         python llm_trader_toolbox.py market_5 3 governance")
        sys.exit(1)
    
    market_id = sys.argv[1]
    num_traders = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    market_type = sys.argv[3] if len(sys.argv) > 3 else "prediction"
    
    run_toolbox_traders(market_id, num_traders, market_type)
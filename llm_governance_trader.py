"""
LLM-based governance trader that can analyze code and bet on proposals
"""
import requests
import json
from datetime import datetime
import llm
import os
from pathlib import Path
import subprocess

BASE_URL = "http://localhost:5000"

class GovernanceTrader:
    def __init__(self, model="openrouter/anthropic/claude-sonnet-4", name=None):
        self.model_name = model
        self.model = llm.get_model(model)
        self.name = name or f"gov_{model.split('/')[-1][:8]}"
        self.user_id = None
        
    def register(self):
        """Register as a user in the market"""
        resp = requests.post(f"{BASE_URL}/users", json={
            'username': self.name,
            'initial_balance': 10000.0  # More capital for governance decisions
        })
        
        if resp.status_code == 201:
            user = resp.json()
            self.user_id = user['id']
            print(f"[{self.name}] Registered with ID {self.user_id}")
            return True
        return False
    
    def read_codebase(self):
        """Read all Python files in the codebase"""
        code_files = {}
        for file in Path('.').glob('*.py'):
            try:
                with open(file, 'r') as f:
                    code_files[str(file)] = f.read()
            except:
                pass
        
        # Also read key documents
        for doc in ['README.md', 'GOVERNANCE.md', 'CLAUDE.md']:
            if os.path.exists(doc):
                with open(doc, 'r') as f:
                    code_files[doc] = f.read()
        
        return code_files
    
    def calculate_metrics(self):
        """Calculate current governance metrics"""
        metrics = {}
        
        # Code Quality (simplified)
        try:
            # Test coverage (would need pytest-cov in real implementation)
            metrics['test_coverage'] = 0  # No tests yet
            
            # Count lines of code and comments
            total_lines = 0
            comment_lines = 0
            for file in Path('.').glob('*.py'):
                with open(file, 'r') as f:
                    for line in f:
                        total_lines += 1
                        if line.strip().startswith('#'):
                            comment_lines += 1
            
            metrics['documentation_ratio'] = (comment_lines / total_lines * 100) if total_lines > 0 else 0
            
            # Simple complexity measure (functions per file)
            total_functions = 0
            for file in Path('.').glob('*.py'):
                with open(file, 'r') as f:
                    content = f.read()
                    total_functions += content.count('def ')
            
            metrics['avg_functions_per_file'] = total_functions / len(list(Path('.').glob('*.py')))
            
        except Exception as e:
            print(f"Error calculating metrics: {e}")
            
        # Market Health (via API)
        try:
            markets = requests.get(f"{BASE_URL}/markets").json()
            metrics['total_markets'] = len(markets)
            metrics['active_markets'] = sum(1 for m in markets if not m['resolved'])
            
            # Calculate total volume
            total_volume = 0
            for market in markets:
                market_detail = requests.get(f"{BASE_URL}/markets/{market['id']}").json()
                total_volume += market_detail.get('volume', 0)
            metrics['total_volume'] = total_volume
            
        except:
            pass
            
        return metrics
    
    def analyze_proposal(self, proposal_content, current_metrics):
        """Analyze a governance proposal"""
        code_files = self.read_codebase()
        
        # Create a comprehensive prompt
        prompt = f"""You are a governance trader in an autofutarchy system. Analyze this proposal:

{proposal_content}

CURRENT SYSTEM STATE:
- Total files: {len(code_files)}
- Current metrics: {json.dumps(current_metrics, indent=2)}

KEY CODE FILES:
{chr(10).join(f"- {name}: {len(content)} chars" for name, content in list(code_files.items())[:10])}

GOVERNANCE RULES (from GOVERNANCE.md):
{code_files.get('GOVERNANCE.md', 'No governance doc found')[:1000]}...

Your task:
1. Predict how this proposal will affect each metric
2. Estimate the probability of successful implementation
3. Consider risks and second-order effects
4. Make a trading decision

Respond with JSON:
{{
  "implementation_probability": 0.0-1.0,
  "predicted_metrics_change": {{
    "code_quality": -10 to +10,
    "performance": -10 to +10,
    "market_health": -10 to +10
  }},
  "reasoning": "detailed analysis",
  "recommendation": "STRONG_YES" | "YES" | "NEUTRAL" | "NO" | "STRONG_NO",
  "confidence": 0.0-1.0
}}"""

        try:
            response = self.model.prompt(prompt)
            content = response.text()
            
            # Extract JSON
            import re
            json_match = re.search(r'\{.+\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                print(f"[{self.name}] Failed to parse JSON from response")
                return None
                
        except Exception as e:
            print(f"[{self.name}] Error analyzing proposal: {e}")
            return None
    
    def trade_on_governance_market(self, market_id, proposal_content=None):
        """Trade on a governance-related market"""
        # Get market info
        resp = requests.get(f"{BASE_URL}/markets/{market_id}")
        if resp.status_code != 200:
            return
            
        market = resp.json()
        
        # Check if this is a governance market
        if "governance" not in market['question'].lower() and "proposal" not in market['question'].lower():
            print(f"[{self.name}] Not a governance market, skipping")
            return
        
        print(f"\n[{self.name}] Analyzing governance market: {market['question']}")
        
        # Get current metrics
        current_metrics = self.calculate_metrics()
        print(f"[{self.name}] Current metrics: {current_metrics}")
        
        # Analyze the proposal
        if not proposal_content:
            # Try to extract from market question
            proposal_content = market['question']
        
        analysis = self.analyze_proposal(proposal_content, current_metrics)
        
        if not analysis:
            return
            
        print(f"[{self.name}] Analysis: {analysis['recommendation']} (confidence: {analysis['confidence']:.2f})")
        print(f"[{self.name}] Reasoning: {analysis['reasoning'][:200]}...")
        
        # Decide trade based on recommendation
        if analysis['recommendation'] in ["STRONG_YES", "YES"] and analysis['confidence'] > 0.6:
            side = "YES"
            shares = 50 * analysis['confidence']  # Bigger trades for governance
        elif analysis['recommendation'] in ["STRONG_NO", "NO"] and analysis['confidence'] > 0.6:
            side = "NO" 
            shares = 50 * analysis['confidence']
        else:
            print(f"[{self.name}] Not confident enough to trade")
            return
        
        # Execute trade
        trade_data = {
            'user_id': self.user_id,
            'market_id': market_id,
            'side': side,
            'shares': int(shares),
            'reasoning': analysis['reasoning'],
            'model_name': self.model_name,
            'strategy': 'governance',
            'confidence': analysis['confidence'],
            'is_llm_trader': True
        }
        
        resp = requests.post(f"{BASE_URL}/trades", json=trade_data)
        
        if resp.status_code == 201:
            trade = resp.json()
            print(f"[{self.name}] ✓ Governance trade: {shares:.0f} {side} shares for ${trade['cost']:.2f}")
            print(f"[{self.name}]   Market moved to: YES ${trade['new_yes_price']:.3f} | NO ${trade['new_no_price']:.3f}")
        else:
            print(f"[{self.name}] ✗ Trade failed: {resp.json().get('error', 'Unknown error')}")


def run_governance_traders(market_id, num_traders=3):
    """Run multiple governance traders on a market"""
    
    # Use different models for diverse perspectives
    models = [
        "openrouter/anthropic/claude-sonnet-4",
        "openrouter/openai/o4-mini", 
        "openrouter/google/gemini-2.5-flash",
    ]
    
    traders = []
    for i in range(min(num_traders, len(models))):
        trader = GovernanceTrader(model=models[i])
        if trader.register():
            traders.append(trader)
    
    print(f"\nRegistered {len(traders)} governance traders")
    
    # Example proposal (in real implementation, would read from file)
    proposal_content = """
    # Proposal: Add Automated Market Resolution
    
    ## Description
    Implement automatic market resolution based on objective criteria
    
    ## Rationale
    - Reduces human intervention
    - Faster resolution times
    - More predictable outcomes
    
    ## Implementation
    - Add resolve_automatically() method to Market class
    - Create ResolutionOracle that checks external data
    - Run resolution check every hour via cron
    """
    
    # Each trader analyzes independently
    for trader in traders:
        trader.trade_on_governance_market(market_id, proposal_content)
    
    # Show final market state
    resp = requests.get(f"{BASE_URL}/markets/{market_id}")
    if resp.status_code == 200:
        market = resp.json()
        print(f"\nGovernance market after trading:")
        print(f"Question: {market['question']}")
        print(f"YES: ${market['yes_price']:.3f} | NO: ${market['no_price']:.3f}")
        print(f"Volume: ${market['volume']:.2f}")
        
        # The decision would be:
        if market['yes_price'] > 0.55:
            print(f"\n✅ DECISION: Implement the proposal (YES price > 55%)")
        else:
            print(f"\n❌ DECISION: Reject the proposal (YES price < 55%)")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python llm_governance_trader.py <market_id> [num_traders]")
        print("Example: python llm_governance_trader.py market_5 3")
        sys.exit(1)
    
    market_id = sys.argv[1]
    num_traders = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    
    run_governance_traders(market_id, num_traders)
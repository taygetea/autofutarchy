"""
Simple prediction market implementation using AMM (Automated Market Maker)
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, List
from enum import Enum
import math
import json


class Side(Enum):
    YES = "YES"
    NO = "NO"


@dataclass
class Market:
    id: str
    question: str
    created_at: datetime
    closes_at: datetime
    resolved: bool = False
    outcome: Optional[bool] = None
    yes_pool: float = 100.0  # Initial liquidity
    no_pool: float = 100.0   # Initial liquidity
    liquidity_parameter: float = 100.0  # k = yes_pool * no_pool
    
    def get_price(self, side: Side) -> float:
        """Get current price for YES or NO shares"""
        if side == Side.YES:
            return self.no_pool / (self.yes_pool + self.no_pool)
        else:
            return self.yes_pool / (self.yes_pool + self.no_pool)
    
    def get_cost(self, side: Side, shares: float) -> float:
        """Calculate cost to buy a specific number of shares"""
        if shares <= 0:
            return 0
        
        if side == Side.YES:
            # To buy YES shares, we remove from yes_pool
            new_yes_pool = self.yes_pool - shares
            if new_yes_pool <= 0:
                raise ValueError("Insufficient liquidity")
            # Calculate required NO tokens to maintain k
            new_no_pool = self.liquidity_parameter / new_yes_pool
            cost = new_no_pool - self.no_pool
        else:
            # To buy NO shares, we remove from no_pool
            new_no_pool = self.no_pool - shares
            if new_no_pool <= 0:
                raise ValueError("Insufficient liquidity")
            # Calculate required YES tokens to maintain k
            new_yes_pool = self.liquidity_parameter / new_no_pool
            cost = new_yes_pool - self.yes_pool
            
        return cost
    
    def set_pools(self, yes_pool: float, no_pool: float):
        """Directly set pool values (admin function)"""
        if yes_pool <= 0 or no_pool <= 0:
            raise ValueError("Pool values must be positive")
        
        self.yes_pool = yes_pool
        self.no_pool = no_pool
        self.liquidity_parameter = yes_pool * no_pool
    
    def execute_trade(self, side: Side, shares: float, max_cost: Optional[float] = None) -> float:
        """Execute a trade and return actual cost"""
        cost = self.get_cost(side, shares)
        
        if max_cost is not None and cost > max_cost:
            raise ValueError(f"Cost {cost:.2f} exceeds max cost {max_cost:.2f}")
        
        if side == Side.YES:
            self.yes_pool -= shares
            self.no_pool += cost
        else:
            self.no_pool -= shares
            self.yes_pool += cost
            
        # Update liquidity parameter
        self.liquidity_parameter = self.yes_pool * self.no_pool
        
        return cost


@dataclass
class Position:
    yes_shares: float = 0.0
    no_shares: float = 0.0
    
    def get_value_at_resolution(self, outcome: bool) -> float:
        """Calculate position value when market resolves"""
        if outcome:
            return self.yes_shares
        else:
            return self.no_shares


@dataclass
class User:
    id: str
    username: str
    balance: float = 1000.0  # Starting balance
    positions: Dict[str, Position] = field(default_factory=dict)
    
    def get_position(self, market_id: str) -> Position:
        if market_id not in self.positions:
            self.positions[market_id] = Position()
        return self.positions[market_id]
    
    def can_afford(self, cost: float) -> bool:
        return self.balance >= cost


@dataclass
class Trade:
    id: str
    user_id: str
    market_id: str
    side: Side
    shares: float
    cost: float
    price: float  # Average price paid
    timestamp: datetime


class PredictionMarket:
    def __init__(self, db_path: str = "prediction_market.db"):
        # Import here to avoid circular import
        from database import Database
        
        self.db = Database(db_path)
        
        # Load existing data from database
        self.markets: Dict[str, Market] = self.db.load_all_markets()
        self.users: Dict[str, User] = self.db.load_all_users()
        self.trades: List[Trade] = self.db.load_all_trades()
        self.next_id = self.db.get_next_id()
        
    def create_market(self, question: str, closes_at: datetime, 
                     initial_liquidity: float = 100.0) -> Market:
        """Create a new prediction market"""
        market_id = f"market_{self.next_id}"
        self.next_id += 1
        
        market = Market(
            id=market_id,
            question=question,
            created_at=datetime.now(),
            closes_at=closes_at,
            yes_pool=initial_liquidity,
            no_pool=initial_liquidity,
            liquidity_parameter=initial_liquidity * initial_liquidity
        )
        
        self.markets[market_id] = market
        self.db.save_market(market)  # Save to database
        return market
    
    def create_user(self, username: str, initial_balance: float = 1000.0) -> User:
        """Create a new user"""
        user_id = f"user_{self.next_id}"
        self.next_id += 1
        
        user = User(
            id=user_id,
            username=username,
            balance=initial_balance
        )
        
        self.users[user_id] = user
        self.db.save_user(user)  # Save to database
        return user
    
    def buy_shares(self, user_id: str, market_id: str, side: Side, 
                  shares: float, max_cost: Optional[float] = None) -> Trade:
        """Buy shares in a market"""
        user = self.users.get(user_id)
        market = self.markets.get(market_id)
        
        if not user:
            raise ValueError(f"User {user_id} not found")
        if not market:
            raise ValueError(f"Market {market_id} not found")
        if market.resolved:
            raise ValueError("Market is already resolved")
        if datetime.now() > market.closes_at:
            raise ValueError("Market is closed")
        
        # Calculate cost
        cost = market.get_cost(side, shares)
        
        if max_cost is not None and cost > max_cost:
            raise ValueError(f"Cost {cost:.2f} exceeds max cost {max_cost:.2f}")
        
        if not user.can_afford(cost):
            raise ValueError(f"Insufficient balance. Need {cost:.2f}, have {user.balance:.2f}")
        
        # Execute trade
        actual_cost = market.execute_trade(side, shares, max_cost)
        
        # Update user balance and position
        user.balance -= actual_cost
        position = user.get_position(market_id)
        if side == Side.YES:
            position.yes_shares += shares
        else:
            position.no_shares += shares
        
        # Record trade
        trade = Trade(
            id=f"trade_{self.next_id}",
            user_id=user_id,
            market_id=market_id,
            side=side,
            shares=shares,
            cost=actual_cost,
            price=actual_cost / shares,
            timestamp=datetime.now()
        )
        self.next_id += 1
        self.trades.append(trade)
        
        # Save everything to database
        self.db.save_market(market)  # Save updated pools
        self.db.save_user(user)      # Save updated balance and positions
        self.db.save_trade(trade)    # Save trade record
        self.db.conn.execute("UPDATE metadata SET value = ? WHERE key = 'next_id'", (str(self.next_id),))
        self.db.conn.commit()
        
        return trade
    
    def delete_market(self, market_id: str) -> bool:
        """Delete a market (only if not resolved and no active positions)"""
        market = self.markets.get(market_id)
        if not market:
            raise ValueError(f"Market {market_id} not found")
        
        if market.resolved:
            raise ValueError("Cannot delete resolved market")
        
        # Check if any users have positions in this market
        for user_id, user in self.users.items():
            position = user.positions.get(market_id)
            if position and (position.yes_shares > 0 or position.no_shares > 0):
                raise ValueError(f"Cannot delete market with active positions")
        
        # Remove all trades for this market
        self.trades = [t for t in self.trades if t.market_id != market_id]
        
        # Delete the market
        del self.markets[market_id]
        self.db.delete_market(market_id)  # Delete from database
        return True
    
    def resolve_market(self, market_id: str, outcome: bool) -> Dict[str, float]:
        """Resolve a market and pay out positions"""
        market = self.markets.get(market_id)
        if not market:
            raise ValueError(f"Market {market_id} not found")
        if market.resolved:
            raise ValueError("Market already resolved")
        
        market.resolved = True
        market.outcome = outcome
        self.db.save_market(market)  # Save resolved status
        
        # Pay out all positions
        payouts = {}
        for user_id, user in self.users.items():
            position = user.positions.get(market_id)
            if position:
                payout = position.get_value_at_resolution(outcome)
                user.balance += payout
                payouts[user_id] = payout
                self.db.save_user(user)  # Save updated balance
                
        return payouts
    
    def get_market_info(self, market_id: str) -> dict:
        """Get current market information"""
        market = self.markets.get(market_id)
        if not market:
            raise ValueError(f"Market {market_id} not found")
        
        return {
            'id': market.id,
            'question': market.question,
            'yes_price': market.get_price(Side.YES),
            'no_price': market.get_price(Side.NO),
            'yes_pool': market.yes_pool,
            'no_pool': market.no_pool,
            'volume': sum(t.cost for t in self.trades if t.market_id == market_id),
            'resolved': market.resolved,
            'outcome': market.outcome,
            'created_at': market.created_at.isoformat(),
            'closes_at': market.closes_at.isoformat()
        }
    
    def get_user_info(self, user_id: str) -> dict:
        """Get user information including positions"""
        user = self.users.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        positions = {}
        for market_id, position in user.positions.items():
            market = self.markets[market_id]
            current_value = (
                position.yes_shares * market.get_price(Side.YES) +
                position.no_shares * market.get_price(Side.NO)
            )
            positions[market_id] = {
                'yes_shares': position.yes_shares,
                'no_shares': position.no_shares,
                'current_value': current_value,
                'market_question': market.question
            }
        
        return {
            'id': user.id,
            'username': user.username,
            'balance': user.balance,
            'positions': positions,
            'total_value': user.balance + sum(p['current_value'] for p in positions.values())
        }
    
    def set_market_pools(self, market_id: str, yes_pool: float, no_pool: float):
        """Directly set market pool values (admin function)"""
        market = self.markets.get(market_id)
        if not market:
            raise ValueError(f"Market {market_id} not found")
        
        if market.resolved:
            raise ValueError("Cannot modify resolved market")
        
        # Set the pools
        market.set_pools(yes_pool, no_pool)
        
        # Save to database
        self.db.save_market(market)
        
        return {
            'market_id': market_id,
            'yes_pool': market.yes_pool,
            'no_pool': market.no_pool,
            'yes_price': market.get_price(Side.YES),
            'no_price': market.get_price(Side.NO)
        }
    
    def modify_user_balance(self, user_id: str, amount: float):
        """Add or subtract from user balance (admin function)"""
        user = self.users.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        new_balance = user.balance + amount
        if new_balance < 0:
            raise ValueError("Balance cannot be negative")
        
        user.balance = new_balance
        self.db.save_user(user)
        
        return {
            'user_id': user_id,
            'new_balance': user.balance,
            'amount_changed': amount
        }
    
    def save_trade_comment(self, trade_id: str, reasoning: str, model_name: str = None,
                          strategy: str = None, confidence: float = None, is_llm: bool = True):
        """Save reasoning/comment for a trade"""
        self.db.save_trade_comment(trade_id, reasoning, model_name, strategy, confidence, is_llm)
    
    def get_trades_with_comments(self, market_id: str = None, limit: int = 50):
        """Get trades with their comments/reasoning"""
        return self.db.load_trades_with_comments(market_id, limit)
    
    def close(self):
        """Close database connection"""
        if hasattr(self, 'db'):
            self.db.close()


# Example usage
if __name__ == "__main__":
    # Create market system
    pm = PredictionMarket()
    
    # Create a market
    market = pm.create_market(
        "Will AGI be achieved by 2030?",
        closes_at=datetime(2030, 1, 1)
    )
    print(f"Created market: {market.question}")
    print(f"Initial YES price: ${market.get_price(Side.YES):.2f}")
    print(f"Initial NO price: ${market.get_price(Side.NO):.2f}")
    
    # Create users
    alice = pm.create_user("alice")
    bob = pm.create_user("bob")
    
    # Alice buys YES shares
    trade1 = pm.buy_shares(alice.id, market.id, Side.YES, 10)
    print(f"\nAlice bought 10 YES shares for ${trade1.cost:.2f}")
    print(f"New YES price: ${market.get_price(Side.YES):.2f}")
    
    # Bob buys NO shares
    trade2 = pm.buy_shares(bob.id, market.id, Side.NO, 5)
    print(f"\nBob bought 5 NO shares for ${trade2.cost:.2f}")
    print(f"New NO price: ${market.get_price(Side.NO):.2f}")
    
    # Check positions
    print(f"\nAlice's info: {json.dumps(pm.get_user_info(alice.id), indent=2)}")
    print(f"\nMarket info: {json.dumps(pm.get_market_info(market.id), indent=2)}")
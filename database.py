"""
SQLite database persistence for the prediction market
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from market import Market, User, Position, Trade, Side

class Database:
    def __init__(self, db_path: str = "prediction_market.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()
    
    def create_tables(self):
        """Create all necessary tables"""
        cursor = self.conn.cursor()
        
        # Markets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS markets (
                id TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                closes_at TIMESTAMP NOT NULL,
                resolved BOOLEAN DEFAULT FALSE,
                outcome BOOLEAN,
                yes_pool REAL NOT NULL,
                no_pool REAL NOT NULL,
                liquidity_parameter REAL NOT NULL
            )
        """)
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                balance REAL NOT NULL
            )
        """)
        
        # Positions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                user_id TEXT NOT NULL,
                market_id TEXT NOT NULL,
                yes_shares REAL DEFAULT 0,
                no_shares REAL DEFAULT 0,
                PRIMARY KEY (user_id, market_id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (market_id) REFERENCES markets(id)
            )
        """)
        
        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                market_id TEXT NOT NULL,
                side TEXT NOT NULL,
                shares REAL NOT NULL,
                cost REAL NOT NULL,
                price REAL NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (market_id) REFERENCES markets(id)
            )
        """)
        
        # Metadata table for tracking next_id
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        
        # Initialize next_id if not exists
        cursor.execute("INSERT OR IGNORE INTO metadata (key, value) VALUES ('next_id', '1')")
        
        self.conn.commit()
    
    def get_next_id(self) -> int:
        """Get and increment the next ID counter"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM metadata WHERE key = 'next_id'")
        result = cursor.fetchone()
        next_id = int(result['value'])
        
        cursor.execute("UPDATE metadata SET value = ? WHERE key = 'next_id'", (str(next_id + 1),))
        self.conn.commit()
        
        return next_id
    
    def save_market(self, market: Market):
        """Save or update a market"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO markets 
            (id, question, created_at, closes_at, resolved, outcome, yes_pool, no_pool, liquidity_parameter)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            market.id,
            market.question,
            market.created_at.isoformat(),
            market.closes_at.isoformat(),
            market.resolved,
            market.outcome,
            market.yes_pool,
            market.no_pool,
            market.liquidity_parameter
        ))
        self.conn.commit()
    
    def load_market(self, market_id: str) -> Optional[Market]:
        """Load a market by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM markets WHERE id = ?", (market_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return Market(
            id=row['id'],
            question=row['question'],
            created_at=datetime.fromisoformat(row['created_at']),
            closes_at=datetime.fromisoformat(row['closes_at']),
            resolved=bool(row['resolved']),
            outcome=bool(row['outcome']) if row['outcome'] is not None else None,
            yes_pool=row['yes_pool'],
            no_pool=row['no_pool'],
            liquidity_parameter=row['liquidity_parameter']
        )
    
    def load_all_markets(self) -> Dict[str, Market]:
        """Load all markets"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM markets")
        
        markets = {}
        for row in cursor.fetchall():
            market = Market(
                id=row['id'],
                question=row['question'],
                created_at=datetime.fromisoformat(row['created_at']),
                closes_at=datetime.fromisoformat(row['closes_at']),
                resolved=bool(row['resolved']),
                outcome=bool(row['outcome']) if row['outcome'] is not None else None,
                yes_pool=row['yes_pool'],
                no_pool=row['no_pool'],
                liquidity_parameter=row['liquidity_parameter']
            )
            markets[market.id] = market
        
        return markets
    
    def delete_market(self, market_id: str):
        """Delete a market and related data"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM trades WHERE market_id = ?", (market_id,))
        cursor.execute("DELETE FROM positions WHERE market_id = ?", (market_id,))
        cursor.execute("DELETE FROM markets WHERE id = ?", (market_id,))
        self.conn.commit()
    
    def save_user(self, user: User):
        """Save or update a user"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO users (id, username, balance)
            VALUES (?, ?, ?)
        """, (user.id, user.username, user.balance))
        
        # Save positions
        for market_id, position in user.positions.items():
            cursor.execute("""
                INSERT OR REPLACE INTO positions (user_id, market_id, yes_shares, no_shares)
                VALUES (?, ?, ?, ?)
            """, (user.id, market_id, position.yes_shares, position.no_shares))
        
        self.conn.commit()
    
    def load_user(self, user_id: str) -> Optional[User]:
        """Load a user by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        user = User(
            id=row['id'],
            username=row['username'],
            balance=row['balance']
        )
        
        # Load positions
        cursor.execute("SELECT * FROM positions WHERE user_id = ?", (user_id,))
        for pos_row in cursor.fetchall():
            position = Position(
                yes_shares=pos_row['yes_shares'],
                no_shares=pos_row['no_shares']
            )
            user.positions[pos_row['market_id']] = position
        
        return user
    
    def load_all_users(self) -> Dict[str, User]:
        """Load all users"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM users")
        
        users = {}
        for row in cursor.fetchall():
            user = self.load_user(row['id'])
            if user:
                users[user.id] = user
        
        return users
    
    def save_trade(self, trade: Trade):
        """Save a trade"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO trades (id, user_id, market_id, side, shares, cost, price, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade.id,
            trade.user_id,
            trade.market_id,
            trade.side.value,
            trade.shares,
            trade.cost,
            trade.price,
            trade.timestamp.isoformat()
        ))
        self.conn.commit()
    
    def load_all_trades(self) -> List[Trade]:
        """Load all trades"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM trades ORDER BY timestamp")
        
        trades = []
        for row in cursor.fetchall():
            trade = Trade(
                id=row['id'],
                user_id=row['user_id'],
                market_id=row['market_id'],
                side=Side(row['side']),
                shares=row['shares'],
                cost=row['cost'],
                price=row['price'],
                timestamp=datetime.fromisoformat(row['timestamp'])
            )
            trades.append(trade)
        
        return trades
    
    def close(self):
        """Close database connection"""
        self.conn.close()
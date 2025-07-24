# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository

This project is hosted on GitHub at: https://github.com/taygetea/autofutarchy

## Project Narrative

We built a prediction market system from scratch, starting with a simple observation: an AI orchestrator (using simonw/llm) generated an impressively comprehensive but over-engineered specification for a "Multi-LLM Prediction Market Framework." Instead of implementing the complex microservices architecture it suggested, we took a pragmatic approach and built a working system in ~400 lines of Python.

The journey:
1. Started with the orchestrator's 24-week enterprise plan
2. Threw it out and built a simple Flask API + market mechanics
3. Added SQLite persistence when we realized data was lost on restart
4. Integrated LLMs as traders using the llm library
5. Added Exa search so traders could access real-time information
6. Built a Streamlit admin console for easy management
7. Added "god mode" controls for direct market manipulation

## Core Premise

The prediction market uses an Automated Market Maker (AMM) with a constant product formula (like Uniswap):
- Each market has YES and NO token pools
- Price of YES = NO_pool / (YES_pool + NO_pool)
- Buying shares removes from one pool and adds to the other
- The product YES_pool × NO_pool remains constant

This creates automatic price discovery without needing order matching. Multiple LLMs can trade on markets, each bringing different training data and reasoning styles, creating emergent consensus about future events.

## Philosophy

This project embodies "tools for thought" - not trying to build a production system, but rather a playground for experimenting with AI coordination mechanisms. The lack of authentication, the god-mode controls, and the simple architecture are all features, not bugs, for this use case.

The user approaches this with a hacker/experimenter mindset:
- **Pragmatic over perfect** - Rejected the over-engineered spec for something that works
- **Iterative development** - Built features as needed, not upfront
- **Power user focused** - Added admin "god mode" rather than proper auth
- **Integration friendly** - Uses preferred tools (uv for packages, simonw/llm for AI)
- **Research oriented** - Interested in emergent behaviors of AI agents in markets

## Common Development Commands

### Starting the System
```bash
# Terminal 1: Start the Flask API server (required)
python app.py

# Terminal 2: Start the Streamlit admin console
streamlit run streamlit_app.py
# or
./run_web.sh
```

### Running LLM Traders
```bash
# Basic LLM traders (model_id, num_traders, num_rounds)
python llm_trader.py market_1 3 2

# LLM traders with web search capability
python llm_trader_with_search.py market_1 3 2
```

### CLI Operations
```bash
# Create a market
python cli.py create_market "Will X happen by 2025?" 2025-12-31

# Create a user
python cli.py create_user alice

# Execute a trade
python cli.py trade user_1 market_1 YES 10

# List all markets
python cli.py list

# Delete a market
python cli.py delete market_1
```

### Development Tools (if using uv/pip with dev dependencies)
```bash
# Format code
black .

# Lint code
ruff check .

# Run tests (no tests currently exist)
pytest
```

## Architecture Overview

### Core Components

1. **market.py** - Core market mechanics
   - `Market` class: AMM implementation with constant product formula (k = YES_pool × NO_pool)
   - `PredictionMarket` class: Main orchestrator managing all entities
   - Price calculation: YES price = NO_pool / (YES_pool + NO_pool)

2. **database.py** - SQLite persistence layer
   - Direct SQL queries (no ORM)
   - Tables: markets, users, positions, trades, metadata
   - Handles all data persistence and retrieval

3. **app.py** - Flask REST API
   - Endpoints: /markets, /users, /trades, /simulate
   - Admin endpoints for direct pool manipulation
   - No authentication (by design)

4. **streamlit_app.py** - Web admin console
   - Full market and user management
   - "God mode" for direct pool value injection
   - Analytics and visualization
   - Access at http://localhost:8501

5. **LLM Integration**
   - Uses simonw/llm library for model abstraction
   - llm_trader.py: Basic trading logic
   - llm_trader_with_search.py: Enhanced with Exa web search
   - Models accessed via OpenRouter API

### Key Design Principles

- **Pragmatic over perfect**: Simple working implementation, not over-engineered
- **No authentication**: Experimental system, full admin access
- **Direct manipulation**: Admin can inject pool values and modify balances
- **Play money only**: No real monetary value
- **Extensible LLM support**: Easy to add new models via llm library

### Database Schema

The SQLite database (`prediction_market.db`) contains:
- `markets`: id, question, end_date, yes_pool, no_pool, k_constant, resolved, outcome
- `users`: id, name, balance
- `positions`: user_id, market_id, yes_shares, no_shares
- `trades`: id, timestamp, user_id, market_id, position, quantity, price, cost
- `metadata`: key, value (stores next_id counter)

### API Integration Notes

- Flask API must be running on port 5000 for Streamlit UI to work
- LLM traders require OPENROUTER_API_KEY environment variable
- Exa search requires EXA_API_KEY for web-enabled traders
- All API responses are JSON

## Working with LLM Traders

The LLM traders use a structured approach:
1. Analyze market question
2. (Optional) Search web for relevant information
3. Estimate probability of YES outcome
4. Calculate expected value
5. Decide trade action and size

When modifying trader behavior, key files are:
- `llm_trader.py`: Lines 80-120 contain the main prompt
- `llm_trader_with_search.py`: Lines 100-140 contain search integration

## Common Pitfalls

1. **API not running**: Streamlit UI requires Flask API on port 5000
2. **Database locks**: SQLite can lock during concurrent access
3. **Pool manipulation**: Changing pools directly affects k constant
4. **Model availability**: Some models may require specific API keys or credits

## Experimental Features

- **Surrogate markets**: Create markets about the prediction market itself
- **Arbitrage testing**: Use pool injection to create price discrepancies
- **Multi-model consensus**: Run different LLMs to see emergent agreement
- **Information asymmetry**: Compare traders with/without web search

## Future Experiments to Try

1. **Consensus emergence**: Create controversial markets and watch different LLMs debate through trading
2. **Information asymmetry**: Give some traders web search, others not, see price discovery
3. **Market manipulation**: Use pool injection to create arbitrage opportunities
4. **Long-running markets**: Let traders continuously update predictions as new information emerges
5. **Meta-markets**: Create markets about the prediction market itself

## Bitcoin Price Context

The system was tested when Bitcoin was already over $100k (July 2025). This led to interesting market corrections when LLMs learned current prices through web search.

## Model List (from orchestrator.py)

Current models available via OpenRouter (July 2025):
- `openrouter/anthropic/claude-sonnet-4`
- `openrouter/openai/o4-mini`
- `openrouter/google/gemini-2.5-flash`
- `openrouter/deepseek/deepseek-r1-0528`
- `openrouter/moonshotai/kimi-k2`

## Recent Development - LLM Trader Reasoning Display

### Session Summary (July 2025)

We successfully implemented a public trade feed with LLM reasoning, similar to Manifold Markets:

1. **Database Schema Updates**:
   - Added `trade_comments` table to store reasoning, model_name, strategy, confidence
   - Added methods to save and retrieve trades with comments
   - Joined trades with users and comments for display

2. **LLM Trader Modifications**:
   - Modified `execute_trade()` to accept and pass analysis/reasoning
   - Updated both `llm_trader.py` and `llm_trader_with_search.py`
   - Reasoning now flows from analysis → trade execution → database → UI

3. **API Enhancements**:
   - `/trades` endpoint now accepts reasoning data
   - Added `/markets/{id}/trades` to get trades with comments
   - Added `/trades/recent` for cross-market activity
   - Added `/traders/launch` to start traders in background threads

4. **Streamlit UI Updates**:
   - Trade feeds now show 🤖/👤 icons, reasoning, confidence, strategy
   - LLM Trader tab has working "Launch" button (no more copy-paste commands!)
   - Added refresh buttons (🔄) and auto-refresh option in sidebar
   - Shows recent LLM trader activity across all markets

5. **Example from Testing**:
   - Market 74: "Will PLA Rocket Force launch ordnance at US/allied assets before 2033?"
   - LLMs debated: Gemini (aggressive) bought YES citing capabilities/timeframe
   - Claude & O4 (conservative/balanced) bought NO citing rationality/low probability
   - Market moved from ~40% → 23% YES as NO buyers dominated

### Key Achievement
The system now provides transparent reasoning for every LLM trade, making markets more informative and engaging. Users can see not just what AI traders do, but why they do it - creating a richer prediction market experience where trades tell stories.
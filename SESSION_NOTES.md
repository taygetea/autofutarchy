# Session Notes - Autofutarchy Development

## Session Date: 2025-07-24

### Summary
This session focused on implementing futarchy (governance by prediction markets) for the autofutarchy system itself, creating a self-improving codebase where LLMs vote on code changes through markets.

### Key Accomplishments

1. **Authentication System**
   - Added simple password auth to streamlit_app.py
   - Public users can view markets and trades
   - Admin users (password: gnon123) can create markets, launch LLM traders, manipulate pools
   - Committed and pushed to GitHub

2. **Futarchy Implementation**
   - Created GOVERNANCE.md explaining how futarchy works for code decisions
   - Core principle: "Vote on values, bet on beliefs"
   - Markets predict if code changes will improve metrics (code quality, performance, market health)
   - Created proposals/001-add-pytest.md as first governance proposal

3. **LLM Traders with Tool Use**
   - Created llm_governance_trader.py - LLMs that read code and bet on proposals
   - Created llm_trader_toolbox.py - Clean implementation using llm library's tool support
   - Implemented MarketToolbox class with tools:
     - search_web() - Web search via Exa
     - read_file() - Read any file in repo
     - list_files() - Browse codebase
     - get_market_details() - Market info
     - calculate_metrics() - System health metrics

### Current Issue: OpenRouter Models Don't Support Tools

**The Problem:**
- llm-openrouter plugin is installed and models are available
- But OpenRouter models (like openrouter/anthropic/claude-sonnet-4) don't support tools through the plugin
- Error: "OpenRouter: openrouter/anthropic/claude-sonnet-4 does not support tools"

**What We Know:**
- The models themselves DO support tools (Claude, GPT-4, Gemini all have tool use)
- There's apparently a PR open to add tool support to llm-openrouter
- The OpenRouterChat class in the plugin doesn't implement tool methods

**Next Steps:**
1. Check the llm-openrouter GitHub for the PR adding tool support
2. Either:
   - Wait for/help with the PR
   - Fork and add tool support ourselves
   - Use a different approach (maybe direct OpenRouter API calls with tool definitions)
   - Use models through their native plugins (would need separate API keys)

### Other Notes
- Created governance market: "Should we implement Proposal 001 (Add Pytest)?"
- System is ready for self-governance once we fix the tool support issue
- The autofutarchy concept is working - just need the technical implementation

### Environment
- Running on VPS at /root/code/autofutarchy
- Accessible at https://gnon.moe/market
- Flask API on port 5000, Streamlit on port 8501
- Using uv for package management
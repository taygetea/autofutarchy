"""
Streamlit Web UI for Prediction Market
"""
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import time

# Configuration
API_URL = "http://localhost:5000"

# Page config
st.set_page_config(
    page_title="Prediction Market",
    page_icon="📊",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .stButton button {
        width: 100%;
    }
    .market-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Helper functions
def api_call(method, endpoint, data=None):
    """Make API call to Flask backend"""
    url = f"{API_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        elif method == "DELETE":
            response = requests.delete(url)
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            st.error(f"API Error: {response.json().get('error', 'Unknown error')}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to API. Make sure Flask server is running on port 5000.")
        return None

# Initialize session state
if 'user_id' not in st.session_state:
    st.session_state.user_id = "user_1"  # Default admin user
if 'refresh_counter' not in st.session_state:
    st.session_state.refresh_counter = 0

# Title and header
st.title("🎯 Prediction Market Admin Console")
st.markdown("*Full administrative control over the prediction market*")

# Sidebar for quick actions
with st.sidebar:
    st.header("🎮 Admin Controls")
    
    # Trading user selector
    st.subheader("Trading As:")
    users = api_call("GET", "/users")
    if users:
        user_options = {u['id']: f"{u['username']} (${u['balance']:.2f})" for u in users}
        st.session_state.user_id = st.selectbox(
            "Select User",
            options=list(user_options.keys()),
            format_func=lambda x: user_options[x],
            index=0 if st.session_state.user_id not in user_options else list(user_options.keys()).index(st.session_state.user_id)
        )
    
    # Quick create user
    st.subheader("Quick Create User")
    with st.form("quick_create_user"):
        new_username = st.text_input("Username")
        new_balance = st.number_input("Initial Balance", value=1000.0, min_value=0.0)
        if st.form_submit_button("Create"):
            if new_username:
                result = api_call("POST", "/users", {
                    "username": new_username,
                    "initial_balance": new_balance
                })
                if result:
                    st.success(f"Created {new_username}")
                    st.rerun()
    
    # Refresh button
    if st.button("🔄 Refresh"):
        st.session_state.refresh_counter += 1
        st.rerun()

# Main content area
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 Markets", 
    "➕ Create Market", 
    "📊 Analytics", 
    "🤖 LLM Traders",
    "👥 User Management",
    "⚙️ Admin Controls"
])

with tab1:
    st.header("Active Markets")
    
    # Get all markets
    markets = api_call("GET", "/markets")
    
    if markets:
        # Sort by volume or recent activity
        for market in markets:
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.subheader(market['question'])
                    st.caption(f"Closes: {market['closes_at']} | ID: {market['id']}")
                
                with col2:
                    # Price display
                    yes_price = market['yes_price']
                    no_price = market['no_price']
                    
                    # Create a simple price visualization
                    fig = go.Figure(go.Indicator(
                        mode = "gauge+number",
                        value = yes_price * 100,
                        title = {'text': "YES %"},
                        domain = {'x': [0, 1], 'y': [0, 1]},
                        gauge = {
                            'axis': {'range': [None, 100]},
                            'bar': {'color': "green"},
                            'steps': [
                                {'range': [0, 50], 'color': "lightgray"},
                                {'range': [50, 100], 'color': "lightgreen"}
                            ],
                            'threshold': {
                                'line': {'color': "red", 'width': 4},
                                'thickness': 0.75,
                                'value': 50
                            }
                        }
                    ))
                    fig.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20))
                    st.plotly_chart(fig, use_container_width=True, key=f"gauge_{market['id']}")
                
                with col3:
                    st.metric("YES Price", f"${yes_price:.2f}")
                    st.metric("NO Price", f"${no_price:.2f}")
                    
                    # Admin controls
                    with st.expander("🔧 Admin Controls", expanded=False):
                        # Delete market
                        if st.button(f"🗑️ Delete Market", key=f"delete_{market['id']}", type="secondary"):
                            if st.session_state.get(f"confirm_delete_{market['id']}", False):
                                result = api_call("DELETE", f"/markets/{market['id']}")
                                if result:
                                    st.success(f"Deleted market: {market['id']}")
                                    time.sleep(1)
                                    st.rerun()
                            else:
                                st.session_state[f"confirm_delete_{market['id']}"] = True
                                st.warning("Click again to confirm deletion")
                        
                        # Resolve market
                        if not market['resolved']:
                            st.write("**Resolve Market:**")
                            col_yes, col_no = st.columns(2)
                            with col_yes:
                                if st.button("✅ YES", key=f"resolve_yes_{market['id']}"):
                                    result = api_call("POST", f"/markets/{market['id']}/resolve", {"outcome": True})
                                    if result:
                                        st.success("Resolved as YES")
                                        time.sleep(1)
                                        st.rerun()
                            with col_no:
                                if st.button("❌ NO", key=f"resolve_no_{market['id']}"):
                                    result = api_call("POST", f"/markets/{market['id']}/resolve", {"outcome": False})
                                    if result:
                                        st.success("Resolved as NO")
                                        time.sleep(1)
                                        st.rerun()
                    
                    if not market['resolved']:
                        # Trading interface
                        st.write("**Trade:**")
                        trade_side = st.radio(
                            "Side",
                            ["YES", "NO"],
                            key=f"side_{market['id']}",
                            horizontal=True
                        )
                        
                        shares = st.number_input(
                            "Shares",
                            min_value=1,
                            max_value=100,
                            value=10,
                            key=f"shares_{market['id']}"
                        )
                        
                        if st.button("Execute Trade", key=f"trade_{market['id']}"):
                            trade_data = {
                                'user_id': st.session_state.user_id,
                                'market_id': market['id'],
                                'side': trade_side,
                                'shares': shares
                            }
                            
                            result = api_call("POST", "/trades", trade_data)
                            if result:
                                st.success(f"Bought {shares} {trade_side} shares for ${result['cost']:.2f}")
                                time.sleep(1)
                                st.rerun()
                
                st.divider()
    else:
        st.info("No markets available")

with tab2:
    st.header("Create New Market")
    
    with st.form("create_market"):
        question = st.text_input("Question", placeholder="Will X happen by Y date?")
        
        col1, col2 = st.columns(2)
        with col1:
            closes_date = st.date_input("Closing Date")
        with col2:
            initial_liquidity = st.number_input("Initial Liquidity", min_value=50, value=100)
        
        if st.form_submit_button("Create Market"):
            if question:
                market_data = {
                    'question': question,
                    'closes_at': closes_date.isoformat() + "T23:59:59",
                    'initial_liquidity': initial_liquidity
                }
                
                result = api_call("POST", "/markets", market_data)
                if result:
                    st.success(f"Market created: {result['id']}")
                    time.sleep(1)
                    st.rerun()

with tab3:
    st.header("Market Analytics")
    
    markets = api_call("GET", "/markets")
    if markets:
        # Get detailed info for each market to calculate volume
        detailed_markets = []
        total_volume = 0
        
        for market in markets:
            # Get detailed market info including volume
            detailed = api_call("GET", f"/markets/{market['id']}")
            if detailed:
                detailed_markets.append(detailed)
                total_volume += detailed.get('volume', 0)
        
        # Create a DataFrame for analysis
        df = pd.DataFrame(detailed_markets)
        
        # Overall statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Markets", len(markets))
        with col2:
            st.metric("Total Volume", f"${total_volume:.2f}")
        with col3:
            avg_yes = df['yes_price'].mean()
            st.metric("Avg YES Price", f"{avg_yes:.1%}")
        with col4:
            resolved = sum(1 for m in detailed_markets if m['resolved'])
            st.metric("Resolved", resolved)
        
        # Price distribution
        st.subheader("Price Distribution")
        if 'volume' in df.columns and df['volume'].sum() > 0:
            fig = px.scatter(df, x='yes_price', y='volume', 
                            hover_data=['question'], 
                            title='Market Prices vs Volume',
                            labels={'yes_price': 'YES Price', 'volume': 'Trading Volume ($)'})
            st.plotly_chart(fig, use_container_width=True)
        else:
            # If no volume, just show price distribution
            fig = px.histogram(df, x='yes_price', 
                             title='Distribution of YES Prices',
                             labels={'yes_price': 'YES Price', 'count': 'Number of Markets'})
            st.plotly_chart(fig, use_container_width=True)
        
        # Market table
        st.subheader("All Markets")
        display_df = df[['question', 'yes_price', 'no_price', 'resolved']].copy()
        if 'volume' in df.columns:
            display_df['volume'] = df['volume']
            display_df['volume'] = '$' + display_df['volume'].round(2).astype(str)
        display_df['yes_price'] = (display_df['yes_price'] * 100).round(1).astype(str) + '%'
        display_df['no_price'] = (display_df['no_price'] * 100).round(1).astype(str) + '%'
        st.dataframe(display_df, use_container_width=True)

with tab4:
    st.header("LLM Trader Control Panel")
    
    st.info("🤖 Launch AI traders to analyze and trade on markets")
    
    # Select market for trading
    markets = api_call("GET", "/markets")
    if markets:
        market_options = {m['id']: m['question'] for m in markets if not m['resolved']}
        
        selected_market = st.selectbox(
            "Select Market",
            options=list(market_options.keys()),
            format_func=lambda x: market_options[x]
        )
        
        col1, col2, col3 = st.columns(3)
        with col1:
            num_traders = st.number_input("Number of Traders", min_value=1, max_value=5, value=3)
        with col2:
            rounds = st.number_input("Trading Rounds", min_value=1, max_value=5, value=1)
        with col3:
            enable_search = st.checkbox("Enable Web Search", value=True)
        
        if st.button("🚀 Launch LLM Traders", type="primary"):
            st.info("Note: LLM traders would run via the Python script. Launch them with:")
            if enable_search:
                command = f"python llm_trader_with_search.py {selected_market} {num_traders} {rounds}"
            else:
                command = f"python llm_trader.py {selected_market} {num_traders} {rounds}"
            st.code(command)
            
            st.write("The traders will:")
            st.write("- Analyze the market question")
            st.write("- Search for relevant information" if enable_search else "- Use their training data")
            st.write("- Make trading decisions")
            st.write("- Move the market price")

with tab5:
    st.header("👥 User Management")
    
    # Get all users
    users = api_call("GET", "/users")
    
    if users:
        st.subheader(f"All Users ({len(users)} total)")
        
        # Create a dataframe for display
        users_df = pd.DataFrame(users)
        users_df = users_df.sort_values('balance', ascending=False)
        
        # Display summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Users", len(users))
        with col2:
            st.metric("Total Balance", f"${users_df['balance'].sum():,.2f}")
        with col3:
            st.metric("Avg Balance", f"${users_df['balance'].mean():,.2f}")
        with col4:
            active_users = len(users_df[users_df['num_positions'] > 0])
            st.metric("Active Traders", active_users)
        
        # User table with actions
        st.subheader("User List")
        
        # Add search/filter
        search_term = st.text_input("🔍 Search users", placeholder="Filter by username or ID...")
        
        if search_term:
            mask = users_df['username'].str.contains(search_term, case=False) | users_df['id'].str.contains(search_term, case=False)
            filtered_df = users_df[mask]
        else:
            filtered_df = users_df
        
        # Display users
        for _, user in filtered_df.iterrows():
            with st.expander(f"**{user['username']}** (ID: {user['id']}) - Balance: ${user['balance']:,.2f}"):
                # Get detailed user info
                user_details = api_call("GET", f"/users/{user['id']}")
                
                if user_details:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Balance", f"${user_details['balance']:,.2f}")
                    with col2:
                        st.metric("Total Value", f"${user_details['total_value']:,.2f}")
                    with col3:
                        st.metric("Active Positions", user['num_positions'])
                    
                    # Show positions if any
                    if user_details['positions']:
                        st.write("**Positions:**")
                        for market_id, pos in user_details['positions'].items():
                            if pos['yes_shares'] > 0 or pos['no_shares'] > 0:
                                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                                with col1:
                                    st.write(f"📊 {pos['market_question'][:50]}...")
                                with col2:
                                    st.write(f"YES: {pos['yes_shares']:.1f}")
                                with col3:
                                    st.write(f"NO: {pos['no_shares']:.1f}")
                                with col4:
                                    st.write(f"Value: ${pos['current_value']:.2f}")
                    else:
                        st.info("No active positions")
                    
                    # Admin actions
                    st.write("**Admin Actions:**")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        # Add balance
                        add_amount = st.number_input(
                            "Add balance", 
                            min_value=0.0, 
                            max_value=10000.0, 
                            value=1000.0,
                            key=f"add_balance_{user['id']}"
                        )
                        if st.button("💰 Add Balance", key=f"btn_add_{user['id']}"):
                            result = api_call("PUT", f"/admin/users/{user['id']}/balance", {
                                "amount": add_amount
                            })
                            if result:
                                st.success(f"✅ Added ${add_amount:.2f} to {user['username']}. New balance: ${result['new_balance']:.2f}")
                                time.sleep(1)
                                st.rerun()
    else:
        st.info("No users found")
    
    # Create new users in bulk
    st.subheader("Create Test Users")
    with st.form("create_test_users"):
        num_users = st.number_input("Number of users to create", min_value=1, max_value=10, value=3)
        initial_balance = st.number_input("Initial balance per user", min_value=100, max_value=10000, value=1000)
        
        if st.form_submit_button("Create Users"):
            created_users = []
            for i in range(int(num_users)):
                username = f"test_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}"
                result = api_call("POST", "/users", {
                    "username": username,
                    "initial_balance": initial_balance
                })
                if result:
                    created_users.append(result)
            
            if created_users:
                st.success(f"Created {len(created_users)} users")
                for user in created_users:
                    st.write(f"- {user['username']} (ID: {user['id']}, Balance: ${user['balance']})")

with tab6:
    st.header("⚙️ Admin Controls")
    
    # Database management
    st.subheader("🗄️ Database Management")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📊 Show Database Stats"):
            # We'll need to add an endpoint for this, for now show what we can
            markets = api_call("GET", "/markets")
            if markets:
                st.metric("Total Markets", len(markets))
                st.metric("Active Markets", sum(1 for m in markets if not m['resolved']))
    
    with col2:
        if st.button("🗑️ Delete All Test Markets"):
            if st.session_state.get("confirm_delete_all", False):
                markets = api_call("GET", "/markets")
                deleted = 0
                if markets:
                    for market in markets:
                        if "test" in market['question'].lower() or "bitcoin" in market['question'].lower():
                            result = api_call("DELETE", f"/markets/{market['id']}")
                            if result:
                                deleted += 1
                st.success(f"Deleted {deleted} test markets")
                st.session_state["confirm_delete_all"] = False
                time.sleep(1)
                st.rerun()
            else:
                st.session_state["confirm_delete_all"] = True
                st.warning("Click again to confirm deletion of ALL test markets")
    
    # Direct market manipulation
    st.subheader("🎯 Direct Market Manipulation")
    st.warning("⚠️ These controls bypass normal trading mechanics!")
    
    market_to_edit = st.selectbox(
        "Select market to manipulate",
        options=[m['id'] for m in api_call("GET", "/markets") or []],
        format_func=lambda x: next((m['question'] for m in api_call("GET", "/markets") if m['id'] == x), x)
    )
    
    if market_to_edit:
        # Get current market state
        market_info = api_call("GET", f"/markets/{market_to_edit}")
        if market_info:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Current YES Pool", f"{market_info.get('yes_pool', 'N/A')}")
                st.metric("Current YES Price", f"${market_info['yes_price']:.3f}")
            with col2:
                st.metric("Current NO Pool", f"{market_info.get('no_pool', 'N/A')}")
                st.metric("Current NO Price", f"${market_info['no_price']:.3f}")
            
            # Pool manipulation form
            st.write("**Set New Pool Values:**")
            with st.form(f"pool_edit_{market_to_edit}"):
                col1, col2 = st.columns(2)
                with col1:
                    new_yes_pool = st.number_input(
                        "New YES Pool",
                        min_value=1.0,
                        max_value=10000.0,
                        value=float(market_info.get('yes_pool', 100.0)),
                        step=10.0
                    )
                with col2:
                    new_no_pool = st.number_input(
                        "New NO Pool",
                        min_value=1.0,
                        max_value=10000.0,
                        value=float(market_info.get('no_pool', 100.0)),
                        step=10.0
                    )
                
                # Show what the new prices would be
                new_yes_price = new_no_pool / (new_yes_pool + new_no_pool)
                new_no_price = new_yes_pool / (new_yes_pool + new_no_pool)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"New YES Price: ${new_yes_price:.3f}")
                with col2:
                    st.info(f"New NO Price: ${new_no_price:.3f}")
                
                if st.form_submit_button("💉 Inject New Pool Values", type="primary"):
                    result = api_call("PUT", f"/admin/markets/{market_to_edit}/pools", {
                        "yes_pool": new_yes_pool,
                        "no_pool": new_no_pool
                    })
                    if result:
                        st.success(f"✅ Pools updated! New prices - YES: ${result['yes_price']:.3f}, NO: ${result['no_price']:.3f}")
                        time.sleep(1)
                        st.rerun()
    
    # System controls
    st.subheader("🖥️ System Controls")
    
    if st.button("🔄 Force Refresh All Data"):
        st.session_state.refresh_counter += 1
        st.rerun()
    
    # Show system info
    st.info("""
    **Admin Capabilities:**
    - Delete any market (with confirmation)
    - Resolve markets as YES/NO
    - Create test users in bulk
    - View any user by ID
    - Delete test markets in bulk
    - View market details and pools
    
    **Note:** Some advanced features (like direct pool manipulation) would require API modifications.
    """)

# Footer
st.divider()
st.caption("Built with Streamlit • Connected to Flask API • Data stored in SQLite")

# Auto-refresh for live data (optional)
# if st.checkbox("Auto-refresh (every 5 seconds)"):
#     time.sleep(5)
#     st.rerun()
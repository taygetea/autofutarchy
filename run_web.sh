#!/bin/bash

echo "Starting Prediction Market Web Interface..."
echo "==========================================="
echo ""
echo "Make sure the Flask API is running on port 5000!"
echo ""
echo "If not running, open another terminal and run:"
echo "  python app.py"
echo ""
echo "Starting Streamlit UI..."
echo ""

streamlit run streamlit_app.py --server.port 8501
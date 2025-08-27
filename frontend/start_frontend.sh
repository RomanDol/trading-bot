#!/bin/bash
cd /root/trading-bot/frontend
source venv/bin/activate
export PYTHONPATH="/root/trading-bot:$PYTHONPATH"
python3 bot_ui.py

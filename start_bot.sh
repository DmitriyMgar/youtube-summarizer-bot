#!/bin/bash
cd /home/botuser/youtube-summarizer-bot
source venv/bin/activate
export PYTHONPATH=/home/botuser/youtube-summarizer-bot
exec python src/main.py
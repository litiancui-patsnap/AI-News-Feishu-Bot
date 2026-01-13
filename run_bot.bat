@echo off
cd /d e:\projects\scrapegraph_demo
python ai_news_bot.py >> logs\bot_%date:~0,4%%date:~5,2%%date:~8,2%.log 2>&1

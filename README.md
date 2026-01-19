# AI-News-Feishu-Bot

AI资讯飞书机器人 - 自动抓取AI资讯并推送到飞书群

## 功能特性

- 🔍 使用 DuckDuckGo 搜索最新 AI 资讯
- 🤖 使用 ScrapeGraphAI + Ollama 智能提取文章核心内容
- 🌐 自动将英文内容翻译为中文
- 📤 自动推送到飞书群聊
- ⏰ 支持定时任务（每天 9:50 自动运行）

## 环境要求

- Python 3.8+
- Ollama（需安装 mistral-nemo 模型）
- Windows 系统（定时任务）

## 安装步骤

1. 克隆项目
```bash
git clone <repository-url>
cd AI-News-Feishu-Bot
```

2. 安装依赖
```bash
pip install -r requirements.txt
playwright install
```

3. 配置 Ollama
```bash
ollama pull mistral-nemo:latest
ollama serve
```

4. 配置环境变量
```bash
copy .env.example .env
```
编辑 `.env` 文件，配置以下参数:
- `FEISHU_WEBHOOK_URL`: 飞书 Webhook URL (必填)
- `MAX_NEWS_ITEMS`: 每日推送资讯数量 (可选,默认3条)
- `SEARCH_QUERY`: 搜索关键词 (可选,默认"AI artificial intelligence news 2026")
- `PUSH_TIME`: 定时推送时间 (可选,默认9:50)

5. 运行程序
```bash
python ai_news_bot.py
```

## 配置定时任务

运行以下命令设置每天 9:50 自动执行：
```bash
powershell -ExecutionPolicy Bypass -File setup_task.ps1
```

## 项目结构

```
├── ai_news_bot.py      # 主程序
├── config.py           # 配置文件
├── requirements.txt    # 依赖列表
├── run_bot.bat        # 批处理脚本
├── setup_task.ps1     # 定时任务配置脚本
└── logs/              # 日志目录
```

## 技术栈

- ScrapeGraphAI - 智能网页抓取
- Ollama - 本地 LLM
- DuckDuckGo Search - 搜索引擎
- 飞书 Webhook - 消息推送

# AI-News-Feishu-Bot

自动抓取 AI 新闻，提炼中文摘要，并推送到飞书群。

## 当前模型接入

- 默认使用 LiteLLM 提供的 OpenAI 兼容接口：
  - `OPENAI_BASE_URL=http://192.168.106.73:4000/v1`
  - `OPENAI_GENERAL_MODEL=gpt-5.4`
  - `OPENAI_CODING_MODEL=gpt-5.4-codex`
- 当前项目里的新闻提取、翻译、洞察生成默认走 `gpt-5.4`
- 保留 `Ollama` 入口，只需把 `LLM_PROVIDER=ollama` 并启动本地模型即可切回

## 功能

- 使用 DuckDuckGo 搜索最新 AI 新闻
- 对搜索结果做严格发布时间校验，过旧或无日期内容直接丢弃
- 使用 ScrapeGraphAI 提取文章正文并生成中文摘要
- 使用统一 LLM 调用层生成翻译和今日洞察
- 生成信息图并发送到飞书
- 支持 Windows 定时任务

## 环境要求

- Python 3.8+
- Windows
- 若使用默认配置：可访问 LiteLLM 网关
- 若使用 Ollama：本机已安装并启动 `mistral-nemo:latest`

## 安装

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

3. 复制环境变量

```bash
copy .env.example .env
```

4. 编辑 `.env`

默认 LiteLLM 配置已经写好，关键字段如下：

```env
LLM_PROVIDER=litellm
OPENAI_BASE_URL=http://192.168.106.73:4000/v1
OPENAI_API_KEY=sk-***
OPENAI_GENERAL_MODEL=gpt-5.4
OPENAI_CODING_MODEL=gpt-5.4-codex
SEARCH_TIME_LIMIT=d
NEWS_MAX_AGE_HOURS=48
```

如果要切回本地 Ollama：

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral-nemo:latest
```

然后确保本地模型已经启动：

```bash
ollama pull mistral-nemo:latest
ollama serve
```

## 运行

```bash
python ai_news_bot.py
```

若当天没有通过发布时间校验的新内容，程序会直接跳过发送，不再回退到旧闻。

## 定时任务

```bash
powershell -ExecutionPolicy Bypass -File setup_task.ps1
```

## 项目结构

```text
ai_news_bot.py           主流程
config.py                环境变量与模型配置
llm_client.py            统一 LLM 调用层
generate_news_infographic.py
requirements.txt
setup_task.ps1
```

## 说明

- `gpt-5.4` 适合当前新闻抽取、摘要和中文润色场景
- `gpt-5.4-codex` 已保留为可配置入口，便于后续接入更偏结构化或代码型任务
- `OLLAMA_*` 配置未删除，仍可作为本地模型备用路径
- 信息图优先使用本地 `Pillow` 模板生成
- `INFOGRAPHIC_API_FALLBACK` 默认关闭，模板失败时会直接回退到默认首图，不再调用外部图片模型

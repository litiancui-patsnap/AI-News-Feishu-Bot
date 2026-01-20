from ai_news_bot import send_to_feishu
from config import MAX_NEWS_ITEMS

# 使用真实来源的测试数据
test_data = [
    {
        "title": "OpenAI 发布 GPT-5 模型，性能提升显著",
        "summary": "OpenAI 今日正式发布了 GPT-5 模型，在推理能力、多模态理解和代码生成方面都有显著提升。新模型采用了全新的训练架构，参数规模达到万亿级别。",
        "url": "https://techcrunch.com/2026/01/19/openai-gpt5-release"
    },
    {
        "title": "谷歌推出 Gemini 2.0，挑战 GPT-5 地位",
        "summary": "谷歌发布 Gemini 2.0 模型，声称在多项基准测试中超越 GPT-5。该模型特别强化了多语言支持和实时信息检索能力，并集成到 Google 全系产品中。",
        "url": "https://www.theverge.com/2026/01/19/google-gemini-2"
    },
    {
        "title": "AI 监管新规出台，要求模型透明度",
        "summary": "欧盟通过新的 AI 监管法案，要求所有大型语言模型必须公开训练数据来源和模型决策过程。该法案将于 2026 年 6 月正式生效，影响全球 AI 产业。",
        "url": "https://www.reuters.com/technology/ai-regulation-eu"
    },
    {
        "title": "微软发布 Copilot Pro 企业版",
        "summary": "微软推出面向企业的 Copilot Pro 版本，集成了更强大的代码生成和文档处理能力。新版本支持私有部署，确保企业数据安全。",
        "url": "https://www.forbes.com/microsoft-copilot-pro"
    },
    {
        "title": "AI芯片市场竞争加剧，英伟达面临挑战",
        "summary": "AMD和英特尔相继发布新一代AI芯片，性能直逼英伟达H100。市场分析师预测，AI芯片市场将进入多强竞争时代，价格有望下降。",
        "url": "https://www.bloomberg.com/news/ai-chip-competition"
    }
]

# 根据配置截取测试数据
test_data = test_data[:MAX_NEWS_ITEMS]

if send_to_feishu(test_data):
    print(f"测试卡片发送成功！(共{len(test_data)}条资讯)")
else:
    print("发送失败")

from ai_news_bot import send_to_feishu

test_data = [
    {
        "title": "OpenAI 发布 GPT-5 模型，性能提升显著",
        "summary": "OpenAI 今日正式发布了 GPT-5 模型，在推理能力、多模态理解和代码生成方面都有显著提升。新模型采用了全新的训练架构，参数规模达到万亿级别。",
        "url": "https://example.com/news1"
    },
    {
        "title": "谷歌推出 Gemini 2.0，挑战 GPT-5 地位",
        "summary": "谷歌发布 Gemini 2.0 模型，声称在多项基准测试中超越 GPT-5。该模型特别强化了多语言支持和实时信息检索能力，并集成到 Google 全系产品中。",
        "url": "https://example.com/news2"
    },
    {
        "title": "AI 监管新规出台，要求模型透明度",
        "summary": "欧盟通过新的 AI 监管法案，要求所有大型语言模型必须公开训练数据来源和模型决策过程。该法案将于 2026 年 6 月正式生效，影响全球 AI 产业。",
        "url": "https://example.com/news3"
    }
]

if send_to_feishu(test_data):
    print("测试卡片发送成功！")
else:
    print("发送失败")

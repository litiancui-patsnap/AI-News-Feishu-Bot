from ai_news_bot import send_to_feishu
from config import MAX_NEWS_ITEMS

# 使用真实来源的测试数据
test_data = [
    {
        "title": "某市发布城市绿化养护精细化管理标准",
        "summary": "某市园林部门发布新的城市绿化养护标准，覆盖乔灌木修剪、草坪管护、灌溉和病虫害防治等关键环节。",
        "url": "https://example.com/landscape-maintenance-standard",
    },
    {
        "title": "智慧园林平台接入智能灌溉和巡检数据",
        "summary": "一家智慧园林服务商升级管养平台，接入土壤湿度、气象和巡检数据，用于优化绿地浇灌和养护排班。",
        "url": "https://example.com/smart-landscape-platform",
    },
    {
        "title": "3DGS 三维重建用于园区绿化资产管理",
        "summary": "某园区管理项目使用 3DGS 和 GIS 数据构建三维绿化资产台账，支持树木定位、养护记录和巡检问题追踪。",
        "url": "https://example.com/3dgs-green-asset-management",
    },
    {
        "title": "空间大模型用于城市绿地识别试点",
        "summary": "某研究团队探索空间大模型在城市绿地识别和变化监测中的应用，帮助养护单位更快发现裸土、缺株和异常区域。",
        "url": "https://example.com/spatial-model-green-space",
    },
    {
        "title": "园林机械企业发布新能源修剪设备",
        "summary": "一家园林机械企业发布新能源绿篱修剪和草坪养护设备，主打低噪音、低维护和适合市政绿化场景。",
        "url": "https://example.com/landscape-equipment",
    }
]

# 根据配置截取测试数据
test_data = test_data[:MAX_NEWS_ITEMS]

if send_to_feishu(test_data):
    print(f"测试卡片发送成功！(共{len(test_data)}条资讯)")
else:
    print("发送失败")

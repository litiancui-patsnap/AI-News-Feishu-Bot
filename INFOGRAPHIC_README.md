# AI 新闻信息图生成功能

## 📋 功能说明

本功能为 AI 日报系统添加了自动生成信息图的能力，可以为"今日焦点"新闻生成专属的可视化信息图。

## 🎯 功能特点

- ✅ 为每日第一条"今日焦点"新闻生成专属信息图
- ✅ 根据新闻分类自动选择视觉风格
- ✅ 支持一键启用/禁用
- ✅ 失败自动降级到默认首图
- ✅ 完整的错误处理机制

## 📁 新增文件

- `generate_news_infographic.py` - 信息图生成 Python 包装脚本
- `images/generated/` - 生成的信息图存储目录

## 🔧 配置说明

### 环境变量配置 (.env)

```env
# 是否启用信息图生成 (true/false)
ENABLE_INFOGRAPHIC=false

# 信息图输出目录
INFOGRAPHIC_OUTPUT_DIR=./images/generated
```

### API 配置 (.claude/.claude/config/api-config.json)

```json
{
  "gemini": {
    "apiKey": "your-api-key-here",
    "baseUrl": "https://api.ai-code.club",
    "model": "imagen-3.0-generate-001"
  }
}
```

## 🚀 使用方法

### 方法 1：启用信息图生成

1. 确保 Gemini API 可用
2. 在 `.env` 中设置 `ENABLE_INFOGRAPHIC=true`
3. 运行 `python ai_news_bot.py`

### 方法 2：使用默认首图（当前推荐）

1. 在 `.env` 中设置 `ENABLE_INFOGRAPHIC=false`
2. 运行 `python ai_news_bot.py`
3. 系统将使用 `images/ai_banner.png` 作为首图

## 🧪 测试

### 测试信息图生成功能

```bash
python generate_news_infographic.py
```

### 测试完整流程

```bash
python ai_news_bot.py
```

## 📊 工作流程

```
搜索 AI 新闻
    ↓
抓取文章内容
    ↓
生成摘要
    ↓
[ENABLE_INFOGRAPHIC=true]
    ↓
为今日焦点生成信息图
    ↓ (成功)
上传到飞书
    ↓
发送卡片消息

[失败降级]
    ↓
使用默认首图 (ai_banner.png)
    ↓
上传到飞书
    ↓
发送卡片消息
```

## ⚠️ 当前状态

**图片生成 API 暂不可用**

当前使用的 API 服务商（api.ai-code.club）的图片生成模型暂时不可用，返回错误：
```
model_not_found: 分组 default 下模型 imagen-3.0-generate-001 无可用渠道
```

**建议操作：**
1. 保持 `ENABLE_INFOGRAPHIC=false`，使用默认首图
2. 等待 API 服务商恢复图片生成功能
3. 或更换其他支持图片生成的 API 服务商

## 🔄 分支管理

- `main` 分支：稳定版本，使用默认首图
- `feature/ai-generated-infographic` 分支：包含信息图生成功能

### 切换分支

```bash
# 切换到稳定版本（不使用 AI 生成图片）
git checkout main

# 切换到新功能分支（包含 AI 生成图片功能）
git checkout feature/ai-generated-infographic
```

## 🎨 信息图设计

### 视觉风格映射

| 新闻分类 | 视觉风格 |
|---------|---------|
| 🖥️ 芯片/硬件 | 科技蓝色，电路板纹理 |
| 📜 政策/伦理 | 专业灰蓝色，文档图标 |
| 🏭 产业/公司 | 商务蓝绿色，图表元素 |
| 🧠 模型/技术 | 渐变紫蓝色，神经网络图案 |
| 📊 周报/深度 | 深蓝色，数据可视化 |

### Prompt 模板

信息图生成使用智能 prompt 模板，包含：
- 新闻标题和摘要
- 分类对应的视觉风格
- 布局要求（16:9 横向）
- 配色方案（蓝色系 + 橙色强调）
- 文字层次要求

## 📈 性能影响

| 指标 | 禁用信息图 | 启用信息图 |
|------|-----------|-----------|
| 执行时间 | 60-90秒 | 70-120秒 |
| API 调用 | 0次/天 | 1次/天 |
| 失败风险 | 低 | 中（有降级） |

## 🔮 未来优化

1. **更换 API 服务商**：寻找稳定的图片生成 API
2. **本地生成**：使用 Stable Diffusion 本地模型
3. **模板系统**：预设计模板 + 动态文字叠加
4. **缓存机制**：相似新闻复用图片

## 📝 更新日志

### 2026-02-09
- ✅ 创建信息图生成功能
- ✅ 集成到 AI 新闻机器人
- ✅ 添加配置开关和降级策略
- ⚠️ 发现 API 模型不可用，默认禁用功能

---

**版本**: 1.0.0
**分支**: feature/ai-generated-infographic
**状态**: 开发完成，等待 API 可用

# Nova Sonic 实时语音交互演示

[English Version](README_EN.md) | 中文版本

Nova Sonic 是一个基于 Amazon Bedrock Nova Sonic 2 的实时语音交互演示项目，展示了先进的AI语音交互能力。

## 🆕 最新更新 (Nova Sonic 2)

### 多语言支持
Nova Sonic 2 现已支持多种语言：
- **英语** (美国、英国)
- **西班牙语** (美国、西班牙)
- **法语** (法国、加拿大)
- **德语**
- **意大利语**
- **日语**
- **葡萄牙语** (巴西)
- **印地语**
- **阿拉伯语**
- **中文普通话**
- **韩语**

### 文本输入模态
除了语音交互外，现在还支持**文本输入**功能：
- 用户可以通过文本框直接输入文字与模型交互
- 模型会以语音和文本形式回复
- 支持语音和文本混合交互模式
- 点击示例提示可快速发送常用问题

### 异步工具调用
支持**异步工具调用**，提升用户体验：
- 工具执行时模型会继续语音交互
- 实时显示工具调用状态和进度
- 支持长时间运行的工具（如订单跟踪）
- 工具完成后自动继续对话

### 更多语音选择
提供 **16 种不同的语音**供选择：
- 英语：Tiffany, Matthew, Amy, Olivia
- 西班牙语：Lupe, Carlos
- 法语：Ambre, Florian
- 德语：Tina, Lennart
- 意大利语：Beatrice, Lorenzo
- 葡萄牙语：Carolina, Leo
- 印地语：Kiara, Arjun

## 🌟 主要特点

- **模型版本**：Amazon Nova Sonic 2 (amazon.nova-2-sonic-v1:0)
- **区域可用性**：US East (N. Virginia)
- **成本效益**：
  - 语音模态：$0.003/1K 输入 tokens, $0.012/1K 输出 tokens
  - 文本模态：$0.000319/1K 输入 tokens, $0.002651/1K 输出 tokens
- **超低延迟**：端到端延迟约 300ms
- **全球可访问**：可以从国内直接访问，没有限制
- **智能交互**：
  - 支持 Tool Use 功能（同步和异步）
  - 支持语音打断 (Barge-in)
  - 内置背景降噪功能
  - 支持文本和语音双模态输入
- **高并发支持**：默认配额支持 20 并发请求
- **实时网络监测**：显示网络延迟和连接状态

## 💡 应用场景

- AI 硬件设备
- AI 智能助手
- 语言教学（口语老师）
- Role Play 互动
- 客户服务
- 智能家居控制
- 多语言翻译助手

## 🔧 支持的工具

Nova Sonic 目前支持以下工具：

| 工具名称 | 描述 | 异步支持 |
|---------|------|---------|
| **getDateAndTimeTool** | 获取当前日期和时间信息 | ✅ |
| **trackOrderTool** | 通过订单ID检索实时订单跟踪信息 | ✅ |
| **getWeatherTool** | 获取指定位置的当前天气信息 | ✅ |
| **getMoodSuggestionTool** | 根据情绪状态获取个性化建议 | ✅ |
| **searchTool** | 搜索互联网获取实时信息 | ✅ |
| **speakerControlTool** | 控制智能音箱设备 | ✅ |

## 🛠️ 安装指南

### 系统要求
- Python 3.12+
- Ubuntu/Debian 系统

### 安装步骤

```bash
# 安装系统依赖
sudo apt-get update
sudo apt-get install -y portaudio19-dev python3-dev

# 创建虚拟环境
sudo apt install python3.12-venv
python3.12 -m venv venv
source venv/bin/activate

# 安装 Python 依赖
pip3.12 install -r requirements.txt
```

### 配置 AWS 凭证

确保配置了有效的 AWS 凭证，可以通过以下方式之一：
- 环境变量：`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- AWS CLI 配置：`~/.aws/credentials`
- IAM 角色（推荐用于 EC2）

### 运行服务

```bash
# 开发模式
uvicorn main:app --host 0.0.0.0 --port 8100 --reload

# 生产模式
uvicorn main:app --host 0.0.0.0 --port 8100
```

## 🌐 在线演示

访问我们的演示网站：[Nova Sonic Demo](https://nova-sonic.teague.live/)

登录凭据：
- 用户名：nova
- 密码：nova

## 🎥 演示视频

观看 Nova Sonic 演示视频：

[![Nova Sonic Demo](https://img.shields.io/badge/观看演示-Nova%20Sonic-blue)](https://d18k98y33mzd4b.cloudfront.net/Nova+Sonic+Demo+Recording.mp4)

## 📁 项目结构

```
web-nova-sonic/
├── main.py              # FastAPI 主应用
├── templates/
│   └── index.html       # 前端页面
├── static/
│   ├── js/
│   │   ├── main.js      # 主要 JavaScript
│   │   └── tool-logs.js # 工具日志功能
│   └── images/          # 图片资源
├── requirements.txt     # Python 依赖
└── README.md           # 项目文档
```

## 🔗 相关资源

- [Amazon Nova Sonic 官方文档](https://docs.aws.amazon.com/bedrock/latest/userguide/nova-sonic.html)
- [AWS Bedrock 定价](https://aws.amazon.com/bedrock/pricing/)
- [官方示例代码](https://github.com/aws-samples/amazon-nova-samples/tree/main/speech-to-speech/amazon-nova-2-sonic)

---

© 2025 Nova Sonic Demo. All rights reserved.

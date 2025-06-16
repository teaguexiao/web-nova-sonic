# Nova Sonic 实时语音交互演示

[English Version](README_EN.md) | 中文版本

Nova Sonic 是一个基于 Amazon Bedrock Nova 的实时语音交互演示项目，展示了先进的AI语音交互能力。

### 🌟 主要特点

- **区域可用性**：目前仅在 US East (N. Virginia) 发布
- **成本效益**：比 GPT4O 便宜 80%
- **超低延迟**：端到端延迟约 300ms
- **全球可访问**：可以从国内直接访问，没有限制
- **智能交互**：
  - 支持 Tool Use 功能
  - 支持语音打断
  - 内置背景降噪功能
- **高并发支持**：默认配额支持 20 并发请求
- **应用场景**：特别适用于需要语音实时交互的场景
  - AI 硬件设备
  - AI 智能助手
  - 语言教学（口语老师）
  - Role Play 互动

### 🔧 支持的工具

Nova Sonic 目前支持以下工具：

- **getDateAndTimeTool**：获取当前日期和时间信息
- **trackOrderTool**：通过订单ID检索实时订单跟踪信息和详细状态更新，提供预计送达日期
- **getWeatherTool**：获取指定位置的当前天气信息
- **getMoodSuggestionTool**：根据当前情绪状态获取个性化建议以改善心情
- **searchTool**：搜索互联网获取实时信息和问题答案
- **speakerControlTool**：控制家中的智能音箱，支持开关、音量调节等功能

### 🛠️ 安装前提条件

在安装本项目前，请确保安装以下系统依赖：

```bash
sudo apt-get update
sudo apt-get install -y portaudio19-dev python3-dev
sudo apt install python3.12-venv
python3.12 -m venv venv
source venv/bin/activate
pip3.12 install -r requirements.txt
```

### 🌐 在线演示

访问我们的演示网站：[Nova Sonic Demo](https://nova-sonic.teague.live/)

登录凭据：
- 用户名：nova
- 密码：nova

### 🎥 演示视频

观看 Nova Sonic 演示视频：

[![Nova Sonic Demo](https://img.shields.io/badge/观看演示-Nova%20Sonic-blue)](https://d18k98y33mzd4b.cloudfront.net/Nova+Sonic+Demo+Recording.mp4)

---

© 2025 Nova Sonic Demo. All rights reserved. 
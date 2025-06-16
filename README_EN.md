# Nova Sonic Real-time Voice Interaction Demo

[中文版本](README.md) | English Version

Nova Sonic is a real-time voice interaction demonstration project based on Amazon Bedrock Nova, showcasing advanced AI voice interaction capabilities.

### 🌟 Key Features

- **Regional Availability**: Currently only available in US East (N. Virginia)
- **Cost-Effective**: 80% cheaper than GPT4O
- **Ultra-Low Latency**: End-to-end latency of ~300ms
- **Global Access**: Directly accessible from mainland China without restrictions
- **Intelligent Interaction**:
  - Tool Use support
  - Voice interruption capability
  - Built-in background noise reduction
- **High Concurrency**: Default quota of 20 concurrent requests
- **Use Cases**: Ideal for scenarios requiring real-time voice interaction
  - AI hardware devices
  - AI assistants
  - Language teaching (oral English teachers)
  - Role-playing scenarios

### 🔧 Supported Tools

Nova Sonic currently supports the following tools:

- **getDateAndTimeTool**: Get information about the current date and time
- **trackOrderTool**: Retrieves real-time order tracking information and detailed status updates for customer orders by order ID, providing estimated delivery dates
- **getWeatherTool**: Get current weather information for a specified location
- **getMoodSuggestionTool**: Get personalized suggestions to improve mood or emotional state based on current feelings
- **searchTool**: Search the internet for real-time information and answers to questions
- **speakerControlTool**: Control a smart speaker at home with functions like on, off, volume up, and volume down

### 🛠️ Installation Prerequisites

Before installing this project, please ensure you have the following system dependencies installed:

```bash
sudo apt-get update
sudo apt-get install -y portaudio19-dev python3-dev
sudo apt install python3.12-venv
python3.12 -m venv venv
source venv/bin/activate
pip3.12 install -r requirements.txt
```

### 🌐 Live Demo

Visit our demo website: [Nova Sonic Demo](https://nova-sonic.teague.live/)

Login credentials:
- Username: nova
- Password: nova

### 🎥 Demo Video

Watch Nova Sonic in action:

[![Nova Sonic Demo](https://img.shields.io/badge/Watch%20Demo-Nova%20Sonic-blue)](https://d18k98y33mzd4b.cloudfront.net/Nova+Sonic+Demo+Recording.mp4)

---

© 2025 Nova Sonic Demo. All rights reserved. 
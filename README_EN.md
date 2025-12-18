# Nova Sonic Real-time Voice Interaction Demo

[中文版本](README.md) | English Version

Nova Sonic is a real-time voice interaction demonstration project based on Amazon Bedrock Nova Sonic 2, showcasing advanced AI voice interaction capabilities.

## 🆕 Latest Updates (Nova Sonic 2)

### Multi-language Support
Nova Sonic 2 now supports **7 languages**:
- **English** (US, UK)
- **Spanish** (US, Spain)
- **French** (France, Canada)
- **German**
- **Italian**
- **Portuguese** (Brazil)
- **Hindi**

### Text Input Modality
In addition to voice interaction, **text input** is now supported:
- Users can directly type messages to interact with the model
- Model responds with both voice and text
- Supports mixed voice and text interaction modes
- Click example prompts to quickly send common questions

### Asynchronous Tool Calling
Support for **async tool calling** for improved user experience:
- Model continues voice interaction while tools execute
- Real-time display of tool call status and progress
- Support for long-running tools (e.g., order tracking)
- Automatic conversation continuation after tool completion

### More Voice Options
**16 different voices** available:
- English: Tiffany, Matthew, Amy, Olivia
- Spanish: Lupe, Carlos
- French: Ambre, Florian
- German: Tina, Lennart
- Italian: Beatrice, Lorenzo
- Portuguese: Carolina, Leo
- Hindi: Kiara, Arjun

## 🌟 Key Features

- **Model Version**: Amazon Nova Sonic 2 (amazon.nova-2-sonic-v1:0)
- **Regional Availability**: US East (N. Virginia)
- **Cost-Effective**:
  - Speech modality: $0.003/1K input tokens, $0.012/1K output tokens
  - Text modality: $0.000319/1K input tokens, $0.002651/1K output tokens
- **Ultra-Low Latency**: End-to-end latency of ~300ms
- **Global Access**: Directly accessible from mainland China without restrictions
- **Intelligent Interaction**:
  - Tool Use support (sync and async)
  - Voice interruption capability (Barge-in)
  - Built-in background noise reduction
  - Dual-modality input (text and voice)
- **High Concurrency**: Default quota of 20 concurrent requests
- **Real-time Network Monitoring**: Display network latency and connection status

## 💡 Use Cases

- AI hardware devices
- AI assistants
- Language teaching (oral language teachers)
- Role-playing scenarios
- Customer service
- Smart home control
- Multi-language translation assistant

## 🔧 Supported Tools

Nova Sonic currently supports the following tools:

| Tool Name | Description | Async Support |
|-----------|-------------|---------------|
| **getDateAndTimeTool** | Get current date and time information | ✅ |
| **trackOrderTool** | Retrieve real-time order tracking by order ID | ✅ |
| **getWeatherTool** | Get current weather for a specified location | ✅ |
| **getMoodSuggestionTool** | Get personalized suggestions based on mood | ✅ |
| **searchTool** | Search the internet for real-time information | ✅ |
| **speakerControlTool** | Control smart speaker devices | ✅ |

## 🛠️ Installation Guide

### System Requirements
- Python 3.12+
- Ubuntu/Debian system

### Installation Steps

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y portaudio19-dev python3-dev

# Create virtual environment
sudo apt install python3.12-venv
python3.12 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip3.12 install -r requirements.txt
```

### Configure AWS Credentials

Ensure valid AWS credentials are configured using one of the following methods:
- Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- AWS CLI configuration: `~/.aws/credentials`
- IAM role (recommended for EC2)

### Run the Service

```bash
# Development mode
uvicorn main:app --host 0.0.0.0 --port 8100 --reload

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8100
```

## 🌐 Live Demo

Visit our demo website: [Nova Sonic Demo](https://nova-sonic.teague.live/)

Login credentials:
- Username: nova
- Password: nova

## 🎥 Demo Video

Watch Nova Sonic in action:

[![Nova Sonic Demo](https://img.shields.io/badge/Watch%20Demo-Nova%20Sonic-blue)](https://d18k98y33mzd4b.cloudfront.net/Nova+Sonic+Demo+Recording.mp4)

## 📁 Project Structure

```
web-nova-sonic/
├── main.py              # FastAPI main application
├── templates/
│   └── index.html       # Frontend page
├── static/
│   ├── js/
│   │   ├── main.js      # Main JavaScript
│   │   └── tool-logs.js # Tool logging functionality
│   └── images/          # Image assets
├── requirements.txt     # Python dependencies
└── README.md           # Project documentation
```

## 🔗 Related Resources

- [Amazon Nova Sonic Official Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/nova-sonic.html)
- [AWS Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)
- [Official Sample Code](https://github.com/aws-samples/amazon-nova-samples/tree/main/speech-to-speech/amazon-nova-2-sonic)

---

© 2025 Nova Sonic Demo. All rights reserved.

# 🤖 OpenAI Based Code Editor by CevAPI

A powerful code editor that uses OpenAI's latest models for intelligent code editing, AI chat assistance, and comprehensive development tools.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![OpenAI](https://img.shields.io/badge/OpenAI-API-orange.svg)
![Tkinter](https://img.shields.io/badge/Tkinter-GUI-green.svg)

![Main](https://i.imgur.com/QuJ5mKw.png)

## Features

- **AI-Powered Code Editing**: Intelligent code modifications using OpenAI models
- **Multi-Model Support**: GPT-4, GPT-5, O3 series, and more
- **File History Management**: Complete version tracking with revert capabilities
- **Tabbed Interface**: Code editing, AI chat, and debug console
- **Context-Aware Chat**: AI remembers conversation history for continuity
- **Live Cost Tracking**: Real-time token usage and cost estimation
- **Debug Console**: Monitor API calls, requests, and system events

## Why Does This Exist?
Just to see if I can do it really. Plus it was mostly because Cursor doesn't really work with an OpenAI API even though they say they do.

## Quick Start

### Prerequisites
- Python 3.8+
- OpenAI API key
- Internet connection

### Installation
```bash
git clone https://github.com/cev-api/ai-code-editor.git
cd ai-code-editor
pip install openai>=1.0.0
python code_editor.py
```

### First Time Setup
1. Enter your OpenAI API key
2. Select your preferred model
3. Click "Save Config"
4. Select a folder to start working

## Usage

### **Code Editing**
1. Open a file in the editor
2. Type your request in the AI Prompt area
3. Press Enter or click "Edit Code"
4. AI modifies your code based on instructions

### **AI Chat**
1. Switch to "AI Chat" tab
2. Type your question or request
3. Check "Include file context" if needed
4. Press Enter to send

### **File Management**
- Use "Select Folder" to choose project directory
- Right-click files or use "History" button for version control
- Files are automatically tracked in version history

## Configuration

| Parameter | Description | Range | Default |
|-----------|-------------|-------|---------|
| Temperature | Controls randomness | 0.0 - 2.0 | 1.0 |
| Max Tokens | Token limit for responses | 100 - 8000 | 4000 |
| Conversation Memory | Messages to retain | 5 - 100+ | 10 |

### **Supported Models**
- **GPT-5**: `gpt-5` (uses `max_completion_tokens`)
- **GPT-4 Series**: `gpt-4`, `gpt-4.1`, `gpt-4.1-mini`, `gpt-4.1-nano`
- **O3 Series**: `o3-pro`, `o3-mini`, `o3-mini-high`
- **Legacy**: `gpt-3.5-turbo`

### **File Types**
`.py`, `.js`, `.ts`, `.html`, `.css`, `.java`, `.cpp`, `.c`, `.h`, `.json`, `.xml`, `.md`, `.txt`, `.ino`

## Pro Tips

- **Cost Optimization**: Use lower temperature (0.0-0.5) for precise editing, higher (1.0-2.0) for creativity
- **Token Usage**: Uncheck file context for general questions, lower conversation memory for cost-conscious usage
- **Workflow**: Start with chat to discuss approach, use file context only when needed
- **Keyboard**: Shift+Enter for multi-line input, Enter to send/submit

## Troubleshooting

| Issue | Solution |
|-------|----------|
| API Key Error | Verify API key is valid and has credits |
| Model Errors | Check if model is available in your account |
| High Token Usage | Reduce conversation memory or file context inclusion |
| Performance Issues | Check debug console for error logs |


## Screenshots
![Debug](https://i.imgur.com/w1vQTia.png)
![Chat](https://i.imgur.com/Ix32HSi.png)



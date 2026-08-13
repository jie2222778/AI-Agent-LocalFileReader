# AI‑Agent‑LocalFileReader
> 轻量级单文件AI Agent，基于大模型实现本地文档自动读取问答。
软件工程学生课程/简历Demo项目，单人独立实现。

## 📖 项目介绍
传统ChatGPT无法访问你电脑本地文件。
本AI Agent实现**工具调用能力**：
用户提问后，Agent自主判断是否需要读取本地txt / docx(Word)文档；
调用本地Python工具读取磁盘文件，把文档内容交给大模型，完成总结、问答。

核心模块：
1. 工具层：read_txt / read_docx，负责读取本地文档
2. Tool描述清单：给大模型的工具说明书，描述工具能力与入参
3. 工具映射表：字符串工具名映射到真实Python函数
4. Agent循环中间人逻辑：多次与大模型交互，完成工具调用闭环

> 技术要点：LLM工具调用、Prompt工程、对话记忆管理、文件解析、环境变量管理。

## 🛠 技术栈
- Python 3.10+
- openai sdk
- python‑docx（解析Word文档）
- python‑dotenv（管理密钥）

## 📦 安装依赖
```bash
pip install openai python‑docx python‑dotenv

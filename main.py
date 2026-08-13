import os
import json
from dotenv import load_dotenv
from docx import Document
from openai import OpenAI

def read_txt(file_path: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="gbk") as f:
            content = f.read()
        return content


def read_docx(file_path: str) -> str:
    doc = Document(file_path)
    all_text = []
    for para in doc.paragraphs:
        para_text = para.text
        if para_text.strip() != "":
            all_text.append(para_text)
    full_content = "\n".join(all_text)
    return full_content


tool_list = [
    {
        "tool_name": "read_txt",
        "description": "读取本地txt文本文件，返回文件全部文字内容",
        "params": {
            "file_path": "字符串，本地txt文件的路径，例如 note.txt"
        }
    },
    {
        "tool_name": "read_docx",
        "description": "读取本地docx Word文档，返回文档全部文字内容",
        "params": {
            "file_path": "字符串，本地docx文件的路径，例如 report.docx"
        }
    }
]

tool_func_map = {
    "read_txt": read_txt,
    "read_docx": read_docx
}


load_dotenv()
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")
)


def agent_run(user_query: str):
    messages = [
        {
            "role": "system",
            "content": f"""
你是本地文档阅读AI Agent助手。
可用工具列表：{json.dumps(tool_list, ensure_ascii=False)}

规则：
1. 如果需要读取本地文件，输出JSON格式工具调用，格式：
{{"tool_call":{{"tool_name":"xxx","params":{{"file_path":"xxx"}}}}}}
2. 不需要调用工具，直接输出回答文本。
3. 绝对不要编造文件内容，没有获取文件内容不要作答。
4. 获取工具返回内容之后，基于文档内容回答用户问题。
只允许二选一输出：要么纯回答文本，要么上面规定的JSON工具调用。
"""
        },
        {"role": "user", "content": user_query}
    ]

    max_loop = 3
    for _ in range(max_loop):
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        ai_msg = resp.choices[0].message
        messages.append(ai_msg.model_dump())

        ai_content = ai_msg.content.strip()

    
        try:
            tool_call_data = json.loads(ai_content)
            if "tool_call" in tool_call_data:
              
                call_info = tool_call_data["tool_call"]
                tool_name = call_info["tool_name"]
                file_path_arg = call_info["params"]["file_path"]

                func = tool_func_map[tool_name]
                tool_result = func(file_path=file_path_arg)

             
                messages.append({
                    "role": "tool",
                    "content": f"工具返回结果:\n{tool_result}"
                })
                continue  
        except json.JSONDecodeError:
    
            return ai_content

    return "达到最大循环次数，任务终止"


if __name__ == "__main__":
    print("==== Local File AI Agent ====")
    user_input = input("请输入你的问题：")
    ans = agent_run(user_input)
    print("\nAgent Answer:\n")
    print(ans)

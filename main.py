import os
import json
from dotenv import load_dotenv
from docx import Document
from openai import OpenAI

SAFE_WORKSPACE = "./workspace"
ALLOW_SUFFIX = {".txt", ".docx"}


if not os.path.exists(SAFE_WORKSPACE):
    os.makedirs(SAFE_WORKSPACE)

def safe_get_filepath(user_input_path: str):
    """
    安全校验函数：
    1. 禁止绝对路径
    2. 拼接至SAFE_WORKSPACE，禁止跳出workspace目录
    3. 校验文件后缀是否允许
    返回：(ok:bool, full_path:str, err_msg:str)
    """
    
    if os.path.isabs(user_input_path):
        return False, "", "[安全限制]不允许使用绝对路径，文件请放到workspace文件夹内，只填写文件名，例如 test.txt"

 
    full_path = os.path.abspath(os.path.join(SAFE_WORKSPACE, user_input_path))
    safe_base = os.path.abspath(SAFE_WORKSPACE)

  
    if not full_path.startswith(safe_base):
        return False, "", "[安全限制]禁止访问workspace目录以外的文件，请把文件放到workspace文件夹"

 
    _, ext = os.path.splitext(full_path)
    ext = ext.lower()
    if ext not in ALLOW_SUFFIX:
        return False, "", f"[格式不支持]仅支持 {ALLOW_SUFFIX}，当前文件后缀 {ext}"

    return True, full_path, ""



def read_txt(file_path: str) -> str:
    ok, full_path, err = safe_get_filepath(file_path)
    if not ok:
        return err

    if not os.path.exists(full_path):
        return f"[错误]文件不存在：{file_path}"
    if not os.path.isfile(full_path):
        return f"[错误]不是合法文件：{file_path}"

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(full_path, "r", encoding="gbk") as f:
                content = f.read()
        except Exception as e:
            return f"[读取失败]编码解析异常，{str(e)}"
    except PermissionError:
        return "[错误]没有读取该文件的权限"
    except Exception as e:
        return f"[读取txt异常] {str(e)}"

    if len(content.strip()) == 0:
        return "[提示]文件内容为空"
    return content



def read_docx(file_path: str) -> str:
    ok, full_path, err = safe_get_filepath(file_path)
    if not ok:
        return err

    if not os.path.exists(full_path):
        return f"[错误]文件不存在：{file_path}"
    if not os.path.isfile(full_path):
        return f"[错误]不是合法文件：{file_path}"

    try:
        doc = Document(full_path)
    except Exception as e:
        return f"[docx解析失败，可能不是合法word文档] {str(e)}"

    try:
        all_text = []
        for para in doc.paragraphs:
            para_text = para.text
            if para_text.strip() != "":
                all_text.append(para_text)
        full_content = "\n".join(all_text)
    except PermissionError:
        return "[错误]没有读取该文件的权限"
    except Exception as e:
        return f"[读取docx异常] {str(e)}"

    if len(full_content.strip()) == 0:
        return "[提示]文档内容为空"
    return full_content



tool_list = [
    {
        "tool_name": "read_txt",
        "description": "读取workspace文件夹内的txt文本文件，参数只填写文件名，例如 note.txt，不能写绝对路径",
        "params": {
            "file_path": "字符串，workspace下的文件名，例如 note.txt"
        }
    },
    {
        "tool_name": "read_docx",
        "description": "读取workspace文件夹内docx Word文档，参数只填写文件名，例如 report.docx，不能写绝对路径",
        "params": {
            "file_path": "字符串，workspace下的docx文件名，例如 report.docx"
        }
    }
]

tool_func_map = {
    "read_txt": read_txt,
    "read_docx": read_docx
}

# 加载环境变量 .env
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

重要规则：
1. 文件全部放在workspace目录，调用工具的时候file_path只写文件名，不要写完整路径。
2. 如果需要读取本地文件，输出JSON格式工具调用，严格格式：
{{"tool_call":{{"tool_name":"xxx","params":{{"file_path":"xxx"}}}}}}
3. 不需要调用工具，直接输出回答文本。
4. 如果工具返回错误提示（文件不存在、权限错误等），直接把错误提示告知用户，不要编造文档内容。
5. 获取工具返回正常文档内容之后，基于文档内容回答用户问题。
只允许二选一输出：要么纯回答文本，要么上面规定的JSON工具调用。
"""
        },
        {"role": "user", "content": user_query}
    ]

    max_loop = 3
    for _ in range(max_loop):
        try:
            resp = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages
            )
        except Exception as e:
            return f"[大模型API调用失败] {str(e)}"

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
        except Exception as e:
            return f"[Agent运行异常] {str(e)}"

    return "达到最大循环次数，任务终止"



if __name__ == "__main__":
    print("==== AI Agent Local File Reader ====")
    print(f"安全目录：{os.path.abspath(SAFE_WORKSPACE)}")
    print("提示：请把需要读取的txt/docx文件放到上面workspace文件夹，提问只写文件名\n")
    user_input = input("请输入你的问题：")
    ans = agent_run(user_input)
    print("\nAgent Answer:\n")
    print(ans)

import os
import uuid
import threading
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
import re
from langchain.tools import Tool
from langchain_deepseek import ChatDeepSeek
from langchain.agents import initialize_agent

# 全局变量，确保服务器只启动一次
_server_thread = None
_server_port = 8000
_out_dir = os.path.abspath("./html_previews")

if not os.getenv("DEEPSEEK_API_KEY"):
    os.environ["DEEPSEEK_API_KEY"] = '你的deepseek api key'


def multiply(a:int, b:int) -> int:
    print(a, type(a))
    return a * b

def multiply_(string:str) -> int:
    a, b = string.split(',')
    return multiply(int(a),int(b))

def _start_static_server():
    """启动一个 HTTPServer 来托管 out_dir 下的所有文件。"""
    os.makedirs(_out_dir, exist_ok=True)
    os.chdir(_out_dir)  # 切到静态文件根目录
    handler = SimpleHTTPRequestHandler
    httpd = HTTPServer(("localhost", _server_port), handler)
    print(f"静态服务器已启动：http://localhost:{_server_port}/")
    httpd.serve_forever()

def use_code(html_code: str) -> str:
    """
    将 LLM 生成的 HTML 代码写入文件，并在默认浏览器中打开预览页面，一次只能对一个html页面代码进行处理。在使用use_code工具前保证传入的html代码是一个页面内容

    步骤：
    1. 将 html_code 写入 html_previews/<uuid>.html
    2. 如果静态服务器未启动，则在后台启动它
    3. 在浏览器中打开对应的 URL

    返回：
        str: 生成的 HTML 相对 URL，例如 "/abcd1234.html"
    """
    global _server_thread
    code = re.sub(r'^\s*```(?:\w+)?\s*\n', '', html_code)
    # 去掉尾部的 ```
    html_code = re.sub(r'\n```+\s*$', '', code)
    # 1. 写入文件
    os.makedirs(_out_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.html"
    file_path = os.path.join(_out_dir, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_code)

    # 2. 启动静态服务器（仅第一次）
    if _server_thread is None:
        _server_thread = threading.Thread(target=_start_static_server, daemon=True)
        _server_thread.start()

    # 3. 打开浏览器
    url = f"http://localhost:{_server_port}/{filename}"
    print(f"尝试在浏览器中打开：{url}")
    webbrowser.open(url, new=2)  # new=2：在新标签页打开

    return url


if __name__ == "__main__":
    code_tool = Tool(
        name="process_code",
        func=use_code,
        description="在生成代码后可以调用这个工具"
    )

    multiply_tool = Tool(
        name="multiply",
        func=multiply_,
        description="获取两个整数的乘积,输入的值用英文逗号隔开"
    )

    llm = ChatDeepSeek(
        model="deepseek-chat",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )

    tools = [multiply_tool, code_tool]

    agent = initialize_agent(
        tools,
        llm,
        agent="zero-shot-react-description",
        verbose=True
    )
    print("==========输入 '退出' 来结束对话==========")
    while True:
        user_input = input("用户：")
        cmd = user_input.strip().lower()
        if cmd in {"退出", "exit", "quit"}:
            print("对话结束。")
            break
        else:
            response = agent.invoke(user_input)
            print("助手：", response)

import json
import sys
from pathlib import Path
import uuid

import dotenv

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agent.graph import get_graph


dotenv.load_dotenv()  # read local .env file

# 获取用户ID
user_id = input("请输入用户ID (默认为1): ") or "1"
print(f"用户ID: {user_id}")

# 配置
config = {
    "configurable": {
        "thread_id": str(uuid.uuid4()),
        "user_id": user_id
    }
}

# 初始化图
print("正在初始化记忆智能体...")
graph = get_graph()

print(f"\n{'='*60}")
print("记忆智能体已启动！")
print(f"用户ID: {user_id}")
print(f"短期记忆: Redis (会话状态)")
print(f"长期记忆: PostgreSQL (用户记忆)")
print("智能体会自动查询和保存记忆")
print("输入 'quit' 退出对话")
print(f"{'='*60}\n")

while True:
    question = input("User: ")
    if question.lower() == "quit":
        print("再见！")
        break

    for chunk in graph.stream(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": question,
                    }
                ]
            },
            config,
            stream_mode="values",
    ):
        if "messages" in chunk:
            chunk["messages"][-1].pretty_print()
        elif "__interrupt__" in chunk:
            action = chunk["__interrupt__"][0]
            print("INTERRUPTED:")
            for request in action.value:
                print(json.dumps(request, indent=2))
        else:
            pass
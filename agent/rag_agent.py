import json
import uuid

import dotenv

from agent.graph import get_graph


dotenv.load_dotenv()  # read local .env file
config = {"configurable": {"thread_id": str(uuid.uuid4()), "user_id": "1"}}
graph = get_graph()
while True:
    question = input("User: ")
    if question == "quit":
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

# import matplotlib
# matplotlib.use("TkAgg")  # 或 QtAgg

# import matplotlib.pyplot as plt
# from PIL import Image
#
# img = Image.open(io.BytesIO(graph.get_graph().draw_mermaid_png()))
# plt.imshow(img)
# plt.axis('off')  # 不显示坐标轴
# plt.show()

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, wrap_model_call, ModelResponse, SummarizationMiddleware
from langchain.agents.structured_output import ToolStrategy

from agent.agent_context import Context
from agent.response_format import ResponseFormat
from llm.get_llm import get_llm
from memory.get_memory import get_memory, get_store
from prompt.prompt import SYSTEM_PROMPT
from tools import get_tools

basic_model = get_llm("qwen-flash")
advanced_model = get_llm("qwen-plus")


@wrap_model_call
def dynamic_model_selection(request: ModelRequest, handler) -> ModelResponse:
    """Choose model based on conversation complexity."""
    message_count = len(request.state["messages"])
    print(f"Message count: {message_count}")

    if message_count > 3:
        # Use an advanced model for longer conversations
        model = advanced_model
    else:
        model = basic_model

    return handler(request.override(model=model))


agent = create_agent(
    model=basic_model,
    system_prompt=SYSTEM_PROMPT,
    tools=get_tools(),
    context_schema=Context,
    response_format=ToolStrategy(ResponseFormat),
    checkpointer=get_memory(),
    store=get_store(),
    middleware=[
        dynamic_model_selection,
        # SummarizationMiddleware(
        #             model=basic_model,
        #             trigger=("messages", 5),
        #             keep=("messages", 3),
        #         ),
    ],
    debug=True,
)

# `thread_id` is a unique identifier for a given conversation.
config = {"configurable": {"thread_id": "1"}}
#
# response = agent.invoke(
#     {"messages": [{"role": "user", "content": "what is the weather outside?"}]},
#     config=config,
#     context=Context(user_id="1")
# )
#
# print(response['structured_response'])
# ResponseFormat(
#     punny_response="Florida is still having a 'sun-derful' day! The sunshine is playing 'ray-dio' hits all day long! I'd say it's the perfect weather for some 'solar-bration'! If you were hoping for rain, I'm afraid that idea is all 'washed up' - the forecast remains 'clear-ly' brilliant!",
#     weather_conditions="It's always sunny in Florida!"
# )


# Note that we can continue the conversation using the same `thread_id`.
# response = agent.invoke(
#     {"messages": [{"role": "user", "content": "thank you!"}]},
#     config=config,
#     context=Context(user_id="1")
# )
#
# print(response['structured_response'])
# ResponseFormat(
#     punny_response="You're 'thund-erfully' welcome! It's always a 'breeze' to help you stay 'current' with the weather. I'm just 'cloud'-ing around waiting to 'shower' you with more forecasts whenever you need them. Have a 'sun-sational' day in the Florida sunshine!",
#     weather_conditions=None
# )

# response = agent.invoke(
#     {"messages": [{"role": "user", "content": "Where is my location?"}]},
#     config=config,
#     context=Context(user_id="2")
# )
#
# print(response['structured_response'])

while True:
    user_input = input("User: ")
    # response = agent.invoke(
    #     {"messages": [{"role": "user", "content": user_input}]},
    #     config=config,
    #     context=Context(user_id="1")
    # )
    for chunk in agent.stream({
        "messages": [{"role": "user", "content": user_input}]
    },  config=config,
        context=Context(user_id="1"),
        stream_mode="values"):
        # Each chunk contains the full state at that point
        # latest_message = chunk["messages"][-1]
        # if latest_message.content:
        #     print(f"Agent: {latest_message.content}")
        # elif latest_message.tool_calls:
        #     print(f"Calling tools: {[tc['name'] for tc in latest_message.tool_calls]}")
        chunk["messages"][-1].pretty_print()
    # print(f"Assistant: {response['structured_response']}")

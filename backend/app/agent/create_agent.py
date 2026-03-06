from typing import Union

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, wrap_model_call, ModelResponse, SummarizationMiddleware, \
    ModelCallLimitMiddleware, ToolCallLimitMiddleware, LLMToolSelectorMiddleware
from langchain.agents.structured_output import ToolStrategy, ProviderStrategy

from langchain.agents.middleware import before_model, after_model, AgentState, hook_config, dynamic_prompt, ModelRequest

from llm.llm_factory import get_llm
from prompt.prompt import SYSTEM_PROMPT
from tools import get_tools
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

basic_model = get_llm("qwen-flash")
advanced_model = get_llm("qwen-plus")

class Context:
    """Custom runtime context schema."""
    user_id: str
    user_name: str


class ResponseFormat:
    """Response schema for the agent."""
    # A punny response (always required)
    punny_response: str
    # Any interesting information about the weather if available
    weather_conditions: str | None = None


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


@dynamic_prompt
def personalized_prompt(request: ModelRequest) -> str:
    user_name = request.runtime.context.user_name
    return f"You are a helpful assistant. Address the user as {user_name}."

agent = create_agent(
    model=basic_model,
    system_prompt=SYSTEM_PROMPT,
    tools=get_tools(),
    context_schema=Context,
    response_format=ToolStrategy(ResponseFormat),
    checkpointer=InMemorySaver(),
    store=InMemoryStore(),
    middleware=[
        personalized_prompt,
        dynamic_model_selection,
        # SummarizationMiddleware(
        #             model=basic_model,
        #             trigger=("messages", 5),
        #             keep=("messages", 3),
        #         ),
        ModelCallLimitMiddleware(
            thread_limit=10,
            run_limit=3,
            exit_behavior="end",
        ),
        ToolCallLimitMiddleware(
            # tool_name="tavily_search",
            thread_limit=5,
            run_limit=3,
        ),
        LLMToolSelectorMiddleware(
            model=basic_model,
            max_tools=3,
            always_include=["tavily_search"],
        ),
    ],
    debug=True,
)

# 配置线程ID，指定最大循环次数
config = {
    "configurable": {"thread_id": "1"},
    # "recursion_limit": 10,
}

while True:
    user_input = input("User: ")
    # response = agent.invoke(
    #     {"messages": [{"role": "user", "content": user_input}]},
    #     config=config,
    #     context=Context(user_id="1")
    # )
    for chunk in agent.stream({
        "messages": [{"role": "user", "content": user_input}],
    }, config=config,
            context=Context(user_id="1", user_name="Jason"),
            stream_mode="values"):
        # Each chunk contains the full state at that point
        # latest_message = chunk["messages"][-1]
        # if latest_message.content:
        #     print(f"Agent: {latest_message.content}")
        # elif latest_message.tool_calls:
        #     print(f"Calling tools: {[tc['name'] for tc in latest_message.tool_calls]}")
        chunk["messages"][-1].pretty_print()
    # print(f"Assistant: {response['structured_response']}")

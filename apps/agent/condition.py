from apps.agent.state import GraphState
from langgraph.graph import END
from langgraph.types import Send


def route_condition(state: GraphState) -> str:
  """路由条件"""
  route_decision = state["route_decision"]
  if route_decision == "knowledge_base_search":
    return "query_transform"
  elif route_decision == "plan_and_execute":
    return "planner"
  else:
    return "direct_answer"

def generate_response_router(state: GraphState) -> str:
  """generate_response 统一出边：工具调用 → 评估 → 结束"""
  messages = state.get("messages", [])
  last_message = messages[-1] if messages else None

  # 1. 如果 LLM 请求了工具调用 → 走 tool_node
  if last_message and hasattr(last_message, "tool_calls") and last_message.tool_calls:
    return "tool_node"

  # 2. 如果还没评估过且有 draft_answer → 走 evaluate_node
  reflection = state.get("reflection")
  reflection_count = state.get("reflection_count", 0)
  if reflection_count < 3 and (reflection is None or not reflection.passed):
    if state.get("draft_answer"):
      return "evaluate_node"

  # 3. 其他情况 → 结束
  return END
  

def assign_workers(state: GraphState) -> str:
  """Assign a worker to each step in the plan"""

  # Kick off section writing in parallel via Send() API
  return [Send("work_step", s) for s in state["plan"]["steps"]]
  

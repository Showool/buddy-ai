"""
LangGraph 流程图生成工具
"""

import logging
from pathlib import Path
from ..config import settings

logger = logging.getLogger(__name__)


def generate_workflow_diagram():
    """
    生成 LangGraph 工作流程图 PNG 图片

    Returns:
        生成的 PNG 文件路径
    """
    try:
        from .graph import get_graph

        # 获取 compiled graph
        compiled_graph = get_graph()

        # 确保 docs 目录存在
        docs_dir = Path(settings.PROJECT_ROOT) / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)

        # 生成 PNG 图片
        output_file = docs_dir / "langgraph_workflow.png"
        _generate_png_from_graph(compiled_graph, output_file)

    except Exception as e:
        logger.error(f"❌ 生成流程图失败: {e}")
        return None


def _generate_png_from_graph(compiled_graph, output_file: Path):
    """
    使用 LangGraph 方法生成 PNG 图片

    正确的调用方式：compiled_graph.get_graph().draw_mermaid_png()

    Args:
        compiled_graph: LangGraph 的 CompiledGraph 对象
        output_file: 输出的 PNG 文件路径
    """
    try:
        # 先获取 StateGraph，然后调用 draw_mermaid_png
        state_graph = compiled_graph.get_graph()
        png_data = state_graph.draw_mermaid_png()

        # 保存到文件
        with open(output_file, "wb") as f:
            f.write(png_data)

        logger.info(f"✅ LangGraph 流程图已生成: {output_file}")

    except Exception as e:
        logger.warning(f"⚠️  PNG 生成失败: {e}")
        logger.info("💡 提示：流程图生成失败不影响系统运行")

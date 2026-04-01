"""
时间工具模块 - 统一使用中国北京时间
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# 北京时区
BEIJING_TZ = ZoneInfo("Asia/Shanghai")


def get_beijing_now() -> datetime:
    """
    获取当前北京时间

    Returns:
        datetime: 带有北京时区的当前时间
    """
    return datetime.now(BEIJING_TZ)


def to_beijing_time(dt: datetime) -> datetime:
    """
    将datetime转换为北京时间

    Args:
        dt: 输入的datetime对象

    Returns:
        datetime: 转换为北京时区的datetime对象
    """
    if dt.tzinfo is None:
        # 如果没有时区信息，假设为UTC并转换为北京时间
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(BEIJING_TZ)


def datetime_to_iso(dt: datetime) -> str:
    """
    将datetime转换为ISO格式字符串（北京时间）

    Args:
        dt: 输入的datetime对象

    Returns:
        str: ISO格式的时间字符串
    """
    beijing_dt = to_beijing_time(dt)
    return beijing_dt.isoformat()

from snowflake import SnowflakeGenerator

_gen = SnowflakeGenerator(1)  # 1 是 machine_id


def generate_id() -> int:
    return next(_gen)

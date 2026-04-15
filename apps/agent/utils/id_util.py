
def generate_id() -> int:
  from snowflake import SnowflakeGenerator
  gen = SnowflakeGenerator(1)  # 1 是 machine_id
  return next(gen)  # 纯数字 int

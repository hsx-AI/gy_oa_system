# 假期数据

按年定义假期与调休，供考勤、请假、智能建议等使用。

## 数据来源

**数据库表 holiday**：`holiday(year, date, type)`，便于后台维护。

- 表结构：`year SMALLINT, date VARCHAR(10), type VARCHAR(20)`，主键 `(year, date)`
- 新年度可自行 `INSERT INTO holiday (year, date, type) VALUES (...)` 或通过后台维护

## 数据格式说明

- **date**：`YYYY-M-D` 或 `YYYY-MM-DD`，如 `2025-1-1`、`2025-10-01`
- **type**：`放假`（节假日/休息）、`上班`（调休补班日）
- 未出现在列表中的日期：按周末/工作日正常判断（周六日休息，周一到五上班）
- 列表中的「放假」：该日视为休息
- 列表中的「上班」：该日视为工作日（通常为调休补班）

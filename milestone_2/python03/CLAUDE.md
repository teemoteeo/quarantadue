# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Data Quest: Mastering Python Collections for Data Engineering** (42 school, python03, v2.4)

Seven standalone exercises building a "PixelMetrics 3000" game analytics platform. Each exercise lives in its own directory and is submitted as a single Python file.

## Rules

- Python 3.10+, flake8 compliant, all functions must have type hints
- Only `sys` is allowed for imports (except where noted per exercise)
- No file I/O — all data must come from command-line arguments or be hardcoded in-memory
- `try/except` blocks required wherever input parsing can fail

## Running exercises

```bash
python3 ex0/ft_command_quest.py hello world 42
python3 ex1/ft_score_analytics.py 1500 2300 1800 2100 1950
python3 ex2/ft_coordinate_system.py
python3 ex3/ft_achievement_tracker.py
python3 ex4/ft_inventory_system.py sword:1 potion:5 shield:2
python3 ex5/ft_data_stream.py
python3 ex6/ft_analytics_dashboard.py
```

## Linting

```bash
flake8 ex0/ft_command_quest.py
# or check all at once:
flake8 ex*/ft_*.py
```

## Testing tools (from `data_quest_tools.tar.gz`)

```bash
tar -xzf data_quest_tools.tar.gz
python3 data_generator.py                        # generate test commands for all exercises
python3 data_generator.py 1 --count 10 --format argv  # generate argv-ready data for ex1
python3 exercise_0_help.py                       # explore sys.argv mechanics
python3 exercise_1_helper.py                     # realistic score data patterns
python3 advanced_data_helper.py                  # complex data + performance tests
```

## Exercise map

| Dir  | File                        | Status | Collection | Authorized builtins |
|------|-----------------------------|--------|------------|---------------------|
| ex0/ | ft_command_quest.py         | ✅ Done | —          | sys, sys.argv, len(), print() |
| ex1/ | ft_score_analytics.py       | ✅ Done | list       | sys.argv, len(), sum(), max(), min(), int(), print() |
| ex2/ | ft_coordinate_system.py     | 🚧 WIP  | tuple      | sys, sys.argv, math, math.sqrt(), tuple(), int(), float(), print(), split() |
| ex3/ | ft_achievement_tracker.py   | ❌ Todo | set        | set(), len(), print(), union(), intersection(), difference() |
| ex4/ | ft_inventory_system.py      | ❌ Todo | dict       | dict(), len(), print(), keys(), values(), items(), get(), update(), sys, sys.argv |
| ex5/ | ft_data_stream.py           | ❌ Todo | generator  | next(), iter(), range(), len(), print(), typing.Generator |
| ex6/ | ft_analytics_dashboard.py   | ❌ Todo | comprehensions | len(), print(), sum(), max(), min(), sorted() |

## Key implementation notes

- **ex2**: Use `math.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)` for 3D Euclidean distance; demonstrate tuple unpacking
- **ex3**: Hardcode three players' achievement sets; show `union`, `intersection`, `difference` to find common/rare achievements
- **ex4**: Items stored as nested dicts with `name`, `type`, `quantity`, `value`; parse `key:value` pairs from `sys.argv`
- **ex5**: Use `yield` to create lazy data streams; contrast memory usage of streaming vs storing; include Fibonacci and prime generators
- **ex6**: Must clearly demonstrate all three comprehension types (list, dict, set); use hardcoded sample gaming data; focus on clarity over complex analytics

import pytest

from parser import MazeConfig, parse_input
from generator import MazeGenerator, NORTH, EAST, SOUTH, WEST


def write_config(tmp_path, **overrides):
    defaults = {
        "WIDTH": "10",
        "HEIGHT": "10",
        "ENTRY": "0,0",
        "EXIT": "9,9",
        "OUTPUT_FILE": str(tmp_path / "maze.txt"),
        "PERFECT": "TRUE",
    }
    defaults.update(overrides)
    cfg = tmp_path / "config.txt"
    cfg.write_text(
        "\n".join(f"{k}={v}" for k, v in defaults.items()) + "\n"
    )
    return cfg


def test_parse_valid_config(tmp_path):
    cfg = write_config(tmp_path, SEED="42")
    config = parse_input(str(cfg))
    assert config.width == 10
    assert config.height == 10
    assert config.entry == (0, 0)
    assert config.exit == (9, 9)
    assert config.perfect is True
    assert config.seed == 42
    assert config.validate()


def test_parse_seed_absent(tmp_path):
    cfg = write_config(tmp_path)
    config = parse_input(str(cfg))
    assert config.seed is None


def test_parse_seed_empty(tmp_path):
    cfg = write_config(tmp_path, SEED="")
    config = parse_input(str(cfg))
    assert config.seed is None


def test_missing_key_raises(tmp_path):
    cfg = tmp_path / "config.txt"
    cfg.write_text(
        "HEIGHT=10\nENTRY=0,0\nEXIT=9,9\n"
        "OUTPUT_FILE=x.txt\nPERFECT=TRUE\n"
    )
    with pytest.raises(KeyError):
        parse_input(str(cfg))


def test_validate_entry_equals_exit():
    config = MazeConfig(10, 10, (5, 5), (5, 5), "out.txt", True)
    assert not config.validate()


def test_validate_out_of_bounds_x():
    config = MazeConfig(10, 10, (0, 0), (10, 5), "out.txt", True)
    assert not config.validate()


def test_validate_out_of_bounds_y():
    config = MazeConfig(10, 10, (0, 0), (5, 10), "out.txt", True)
    assert not config.validate()


def test_validate_out_of_bounds_entry():
    config = MazeConfig(10, 10, (10, 0), (5, 5), "out.txt", True)
    assert not config.validate()


def test_seed_reproducibility():
    cfg = MazeConfig(15, 15, (0, 0), (14, 14), "out.txt", True, seed=12345)
    g1 = MazeGenerator(cfg)
    g2 = MazeGenerator(cfg)
    assert g1.grid == g2.grid


def test_output_file_format(tmp_path):
    out = tmp_path / "maze.txt"
    cfg = MazeConfig(10, 10, (0, 0), (9, 9), str(out), True, seed=7)
    gen = MazeGenerator(cfg)
    gen.write_output(str(out))
    assert out.exists()
    text = out.read_text()
    lines = text.split("\n")
    rows = lines[:10]
    assert all(len(r) == 10 for r in rows), "row width mismatch"
    hex_chars = set("0123456789ABCDEF")
    assert all(c in hex_chars for r in rows for c in r)
    assert lines[10] == ""
    assert lines[11] == "0,0"
    assert lines[12] == "9,9"
    path = lines[13]
    assert path != ""
    assert all(c in "NESW" for c in path)


def test_wall_coherence():
    cfg = MazeConfig(20, 15, (0, 0), (19, 14), "out.txt", True, seed=99)
    gen = MazeGenerator(cfg)
    grid = gen.grid
    for y in range(cfg.height):
        for x in range(cfg.width):
            cell = grid[y][x]
            if x + 1 < cfg.width:
                e = bool(cell & (1 << EAST))
                w = bool(grid[y][x + 1] & (1 << WEST))
                assert e == w, f"E/W mismatch at ({x},{y})"
            if y + 1 < cfg.height:
                s = bool(cell & (1 << SOUTH))
                n = bool(grid[y + 1][x] & (1 << NORTH))
                assert s == n, f"S/N mismatch at ({x},{y})"


def test_bfs_path_validity(tmp_path):
    out = tmp_path / "maze.txt"
    cfg = MazeConfig(20, 15, (0, 0), (19, 14), str(out), True, seed=99)
    gen = MazeGenerator(cfg)
    gen.write_output(str(out))
    text = out.read_text()
    lines = text.split("\n")
    rows = lines[:15]
    grid = [[int(c, 16) for c in r] for r in rows]
    entry = tuple(int(v) for v in lines[16].split(","))
    exit_ = tuple(int(v) for v in lines[17].split(","))
    path = lines[18]
    assert entry == (0, 0)
    assert exit_ == (19, 14)
    moves = {
        'N': (0, -1, NORTH),
        'E': (1, 0, EAST),
        'S': (0, 1, SOUTH),
        'W': (-1, 0, WEST),
    }
    x, y = entry
    for ch in path:
        dx, dy, wb = moves[ch]
        assert not (grid[y][x] & (1 << wb)), (
            f"wall blocks step {ch} at ({x},{y})"
        )
        x += dx
        y += dy
    assert (x, y) == exit_

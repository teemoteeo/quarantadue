#!/usr/bin/env python3


class MazeConfig:
    def __init__(self, width: int, height: int,
                 maze_entry: tuple, maze_exit: tuple,
                 output_file: str, perfect: bool,
                 seed: int | None = None) -> None:
        self.width = width
        self.height = height
        self.entry = maze_entry
        self.exit = maze_exit
        self.output_file = output_file
        self.perfect = perfect
        self.seed = seed

    def validate(self) -> bool:
        valid = True
        x_en, y_en = self.entry
        x_ex, y_ex = self.exit
        if self.entry == self.exit:
            valid = False
        elif (
                x_en >= self.width or
                x_ex >= self.width or
                y_en >= self.height or
                y_ex >= self.height
                ):
            valid = False
        return valid


def parse_input(configuration: str) -> MazeConfig:
    config = {}
    with open(configuration, "r") as file:
        text = file.readlines()
        lines = [line for line in text if not line.startswith("#")]
        for line in lines:
            key, value = line.split("=")
            config[key] = value

    width = int(config["WIDTH"])
    height = int(config["HEIGHT"])
    entry_x, entry_y = config["ENTRY"].split(",")
    maze_entry = (int(entry_x), int(entry_y))
    exit_x, exit_y = config["EXIT"].split(",")
    maze_exit = (int(exit_x), int(exit_y))
    output_file = config["OUTPUT_FILE"].strip("\n")
    perfect = False
    if config["PERFECT"].strip().upper() == "TRUE":
        perfect = True

    seed: int | None = None
    if "SEED" in config:
        seed_str = config["SEED"].strip()
        if seed_str:
            seed = int(seed_str)

    maze = MazeConfig(
            width, height, maze_entry,
            maze_exit, output_file, perfect, seed
            )

    return maze


# if __name__ == "__main__":
#     myMaze = parse_input("config.txt")
#     if myMaze.validate():
#         print(f"{vars(myMaze)}")
#     else:
#         print("NECCA")

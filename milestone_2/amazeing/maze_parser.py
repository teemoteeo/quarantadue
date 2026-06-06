#!/usr/bin/env python3


VALID_ALGORITHMS: frozenset[str] = frozenset({"DFS", "PRIM", "KRUSKAL"})


class MazeConfig:
    """
    La classe contiene la config del labirinto che ho parsato.
    """

    def __init__(self, width: int, height: int,
                 maze_entry: tuple, maze_exit: tuple,
                 output_file: str, perfect: bool,
                 seed: int | None = None,
                 algorithm: str = "DFS",
                 place_42: bool = True) -> None:
        """
        Inizializzo la MazeConfig

        width: larghezza lab in celle
        height: altezza lab in celle
        entry: coordinate entrata
        exit: coordinate uscita
        output_file: file dove scrivo il lab che ho creato
        perfect: 'True' se 1 path, 'False' se >1
        seed: Random seed per ricreare altro labirinto
        algorithm: tipo di algo per lab
        place_42: 'True' se c'è 42, 'False' se no
        """
        self.width = width
        self.height = height
        self.entry = maze_entry
        self.exit = maze_exit
        self.output_file = output_file
        self.perfect = perfect
        self.seed = seed
        self.algorithm = algorithm
        self.place_42 = place_42

    def validate(self) -> bool:
        """
        Controllo che alcuni parametri siano validi.
        Dimensioni, entrata, uscita non negative.
        Entrate e uscita stesse coordinate o fuori dal lab.

        Ritorno 'True' se tutto ok, altrimenti 'False'
        """
        valid = True
        x_en, y_en = self.entry
        x_ex, y_ex = self.exit
        if self.width <= 0 or self.height <= 0:
            valid = False
        elif x_en < 0 or y_en < 0 or x_ex < 0 or y_ex < 0:
            valid = False
        elif self.entry == self.exit:
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
    """
    Faccio parsing config.txt.
    Se commento (#) skippo.
    Splitto con "=", recupero e converto valori e li inserisco
    in nuove variabili.

    Se non posso splittare una linea -> ValueError
    Se non c'è valore o non valido -> ValueError
    Se non c'è config file -> FileNotFoundError
    """
    config = {}
    with open(configuration, "r") as file:
        text = file.readlines()
        for lineno, raw in enumerate(text, start=1):
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                key, value = raw.split("=", 1)
            except ValueError:
                raise ValueError(
                    f"Malformed config line {lineno}: "
                    f"{raw.rstrip()!r} (expected KEY=VALUE)"
                )
            key = key.strip()
            if not key:
                raise ValueError(
                    f"Malformed config line {lineno}: "
                    f"{raw.rstrip()!r} (empty key)"
                )
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

    algorithm = "DFS"
    if "ALGORITHM" in config:
        algo_str = config["ALGORITHM"].strip().upper()
        if algo_str:
            if algo_str not in VALID_ALGORITHMS:
                raise ValueError(
                    f"Invalid ALGORITHM {algo_str!r} "
                    f"(expected one of {sorted(VALID_ALGORITHMS)})"
                )
            algorithm = algo_str

    maze = MazeConfig(
            width, height, maze_entry,
            maze_exit, output_file, perfect, seed,
            algorithm,
            )

    return maze

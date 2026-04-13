#!/usr/bin/env python3

import alchemy


if __name__ == "__main__":
    print("=== Alembic 4 ===")
    print("Accessing the alchemy module using 'import alchemy'")
    print("Testing create_air(): ", alchemy.create_air())
    print("Now show that not all functions can be reached\n"
          "This will raise an exception!")
    print("Testing create_earth(): ",
          alchemy.create_earth())  # type: ignore[attr-defined]

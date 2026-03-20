class SecurePlant:
    """a plant with protected attributes and validation."""

    def __init__(self, name: str, height: int, age: int):
        """initialize a secure plant with name, height, and age."""
        self.name = name
        self._height = height
        self._age = age

    def set_height(self, height: int) -> None:
        """set height, rejecting negative values."""
        if height < 0:
            print(f"Invalid operation attempted: height "
                  f"{height}cm [REJECTED].")
            print("Security: Negative height rejected.")
            return
        self._height = height

    def set_age(self, age: int) -> None:
        """set age, rejecting negative values."""
        if age < 0:
            print(f"Invalid operation attempted: age {age} years [REJECTED].")
            print("Security: Negative age rejected.")
            return
        self._age = age

    def get_height(self) -> int:
        """return the plant's height."""
        return self._height

    def get_age(self) -> int:
        """return the plant's age."""
        return self._age


if __name__ == "__main__":
    print("=== Garden Security System ===")

    rose = SecurePlant("Rose", 25, 30)
    print(f"Plant created: {rose.name}")

    print(f"Height updated: {rose.get_height()}cm [OK]")
    print(f"Age updated: {rose.get_age()} days [OK]")

    print()
    rose.set_height(-10)

    print(f"\nCurrent plant: {rose.name} ({rose.get_height()}cm, "
          f"{rose.get_age()} days)")

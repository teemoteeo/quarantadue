import sys
import os
import site


def in_virtualenv() -> bool:
    """Detect if running inside a virtual environment."""
    if hasattr(sys, "real_prefix"):
        return True
    return sys.base_prefix != sys.prefix


def print_inside() -> None:
    env_path: str = sys.prefix
    env_name: str = os.path.basename(env_path)
    print("MATRIX STATUS: Welcome to the construct")
    print()
    print(f"Current Python: {sys.executable}")
    print(f"Virtual Environment: {env_name}")
    print(f"Environment Path: {env_path}")
    print()
    print("SUCCESS: You're in an isolated environment!")
    print("Safe to install packages without affecting")
    print("the global system.")
    print()
    print("Package installation path:")
    site_packages: list[str] = [
        p for p in site.getsitepackages() if p.startswith(env_path)
    ]
    if site_packages:
        print(site_packages[0])
    else:
        print(site.getsitepackages()[0])


def print_outside() -> None:
    print("MATRIX STATUS: You're still plugged in")
    print()
    print(f"Current Python: {sys.executable}")
    print("Virtual Environment: None detected")
    print()
    print("WARNING: You're in the global environment!")
    print("The machines can see everything you install.")
    print()
    print("To enter the construct, run:")
    print("python -m venv matrix_env")
    print("source matrix_env/bin/activate # On Unix")
    print("matrix_env\\Scripts\\activate # On Windows")
    print()
    print("Then run this program again.")


def main() -> None:
    try:
        if in_virtualenv():
            print_inside()
        else:
            print_outside()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

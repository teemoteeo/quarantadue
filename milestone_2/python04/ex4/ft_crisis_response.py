#!/usr/bin/env python3
# need standard_archive.txt to run program
import os


def crisis_handler(filename: str) -> None:
    try:
        with open(filename, "r") as f:
            content = f.read().strip()
        print(f"ROUTINE ACCESS: Attempting access to '{filename}'...")
        print(f"SUCCESS: Archive recovered - ``{content}''")
        print("STATUS: Normal operations resumed\n")
    except FileNotFoundError:
        print(f"CRISIS ALERT: Attempting access to '{filename}'...")
        print("RESPONSE: Archive not found in storage matrix")
        print("STATUS: Crisis handled, system stable\n")
    except PermissionError:
        print(f"CRISIS ALERT: Attempting access to '{filename}'...")
        print("RESPONSE: Security protocols deny access")
        print("STATUS: Crisis handled, security maintained\n")
    finally:
        print("All crisis scenarios handled successfully. Archives secure.")


if __name__ == "__main__":
    print("=== CYBER ARCHIVES - CRISIS RESPONSE SYSTEM ===\n")

    with open("classified_vault.txt", "w") as f:
        f.write("TOP SECRET\n")
    os.chmod("classified_vault.txt", 0o000)

    crisis_handler("lost_archive.txt")
    crisis_handler("classified_vault.txt")
    crisis_handler("standard_archive.txt")

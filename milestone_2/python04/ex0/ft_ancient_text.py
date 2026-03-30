#!/usr/bin/env python3
# need ancient_fragment.txt to run program


if __name__ == "__main__":
    print("=== CYBER ARCHIVES - DATA RECOVERY SYSTEM ===")

    try:
        with open("ancient_fragment.txt", "r") as f:
            print("\nAccessing Storage Vault: ancient_fragment.txt")
            print("Connection established...")
            recovered_text = f.read()
            print("\nRECOVERED DATA:")
            print(f"\n{recovered_text}")
            print("Data recovery complete. Storage unit disconnected.")
    except FileNotFoundError:
        print("\nERROR: Storage vault not found. Run data generator first.")

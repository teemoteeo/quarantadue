#!/usr/bin/env python3


if __name__ == "__main__":
    print("=== CYBER ARCHIVES - DATA RECOVERY SYSTEM ===")

    try:
        with open("ancient_fragment.txt", "r") as f:
            recovered_text = f.read()
            print("\nAccessing Storage Vault: ancient_fragment.txt")
            print("Connection enstablished...")
            print(f"\n{recovered_text}")
            print("Data recovery complete. Storage unit disconnected,")
    except FileNotFoundError as e:
        print("\nERROR: Storage vault not found. Run data generator first.")



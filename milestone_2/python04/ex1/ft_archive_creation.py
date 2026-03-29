#!/usr/bin/env python3

if __name__ == "__main__":
    print("=== CYBER ARCHIVES - PRESERVATION SYSTEM ===")
    print("\nInitializing new storage unit: new_discovery.txt")
    print("Storage unit created successfully...")
    print("\nInscribing preservation data...")
   
    with open("new_discovery.txt", "w") as f:
        entries = [
            "[ENTRY 001] New quantum algorithm discovered",
            "[ENTRY 002] Efficiency increased by 347%",
            "[ENTRY 003] Archived by Data Archivist trainee",
        ]

        for entry in entries:
            f.write(entry + "\n")
            print(entry)
        print("\nData inscription complete. Storage unit sealed.")
        print("Archive 'new_discovery.txt' ready for long-term preservation")

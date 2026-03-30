#!/usr/bin/env python3


if __name__ == "__main__":
    print("=== CYBER ARCHIVES - VAULT SECURITY SYSTEM ===\n")

    with open("classified_data.txt", "r") as f:
        print("Initiating secure vault access...")
        print("Vault connection established with failsafe protocols\n")
        print("SECURE EXTRACTION:")
        print(f.read())

    with open("security_protocols.txt", "r") as f:
        protocols = f.read()
    with open("new_vault.txt", "w") as f:
        f.write(protocols)
    print("\nSECURE PRESERVATION:")
    print(protocols)
    print("Vault automatically sealed upon completion.\n")

    print("All vault operations completed with maximum security.")

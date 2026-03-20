*This project has been created as part of the 42 curriculum by tcostant.*

# Born2BeRoot

## Description
Setup a secure Debian VM with a non-root user, sudo, SSH (root login disabled), UFW firewall, and a monitoring script.

## Instructions
1. Install Debian on VirtualBox, NAT network, port forwarding host 2222 → guest 4242.
2. Create user with sudo. Configure SSH on port 4242.
3. Enable firewall: `ufw allow 4242; ufw enable`.
4. Place `monitoring.sh` in `/root`, make executable, run to see system stats.

## Resources
- Debian Documentation, UFW Guide
- AI used for script guidance and command clarification.

## System choices
- OS: Debian for stability; Rocky Linux heavier.
- Security: AppArmor (easier) vs SELinux.
- Firewall: UFW (simple) vs firewalld.
- VM: VirtualBox (cross-platform).


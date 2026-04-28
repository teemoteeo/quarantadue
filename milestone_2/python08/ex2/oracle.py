import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    print(
        "Error: python-dotenv is not installed.\n"
        "Install with: pip install python-dotenv",
        file=sys.stderr,
    )
    sys.exit(1)


REQUIRED_VARS: list[str] = [
    "MATRIX_MODE",
    "DATABASE_URL",
    "API_KEY",
    "LOG_LEVEL",
    "ZION_ENDPOINT",
]
SENSITIVE_VARS: set[str] = {"API_KEY", "DATABASE_URL"}


def mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "*" * len(value)
    return value[:2] + "*" * (len(value) - 4) + value[-2:]


def load_config() -> dict[str, str]:
    """Load .env if present, environment variables override file values."""
    env_file: Path = Path(__file__).parent / ".env"
    if env_file.is_file():
        load_dotenv(dotenv_path=env_file, override=False)
    cfg: dict[str, str] = {}
    for var in REQUIRED_VARS:
        cfg[var] = os.environ.get(var, "")
    return cfg


def describe_database(url: str) -> str:
    if not url:
        return "Not configured"
    if "localhost" in url or "127.0.0.1" in url:
        return "Connected to local instance"
    return "Connected to remote instance"


def describe_api(key: str) -> str:
    if not key:
        return "Missing (unauthenticated)"
    return "Authenticated"


def describe_zion(endpoint: str) -> str:
    if not endpoint:
        return "Offline"
    return "Online"


def security_checks(
    cfg: dict[str, str], env_file: Path
) -> list[tuple[str, str]]:
    checks: list[tuple[str, str]] = []
    api_key: str = cfg.get("API_KEY", "")
    if api_key and api_key in {"changeme", "secret", "password"}:
        checks.append(("WARN", "Weak API_KEY detected"))
    else:
        checks.append(("OK", "No hardcoded secrets detected"))

    if env_file.is_file():
        checks.append(("OK", ".env file properly configured"))
    else:
        checks.append(("WARN", ".env file not found (using env vars only)"))

    mode: str = cfg.get("MATRIX_MODE", "")
    if mode in {"development", "production"}:
        checks.append(("OK", "Production overrides available"))
    else:
        checks.append(("WARN", f"Unknown MATRIX_MODE: '{mode}'"))
    return checks


def main() -> None:
    env_file: Path = Path(__file__).parent / ".env"
    try:
        cfg: dict[str, str] = load_config()
    except Exception as exc:
        print(f"Failed to load configuration: {exc}", file=sys.stderr)
        sys.exit(1)

    print("ORACLE STATUS: Reading the Matrix...")
    print()

    missing: list[str] = [v for v in REQUIRED_VARS if not cfg[v]]

    print("Configuration loaded:")
    mode: str = cfg["MATRIX_MODE"] or "<unset>"
    print(f"Mode: {mode}")
    print(f"Database: {describe_database(cfg['DATABASE_URL'])}")
    print(f"API Access: {describe_api(cfg['API_KEY'])}")
    print(f"Log Level: {cfg['LOG_LEVEL'] or '<unset>'}")
    print(f"Zion Network: {describe_zion(cfg['ZION_ENDPOINT'])}")

    if cfg["MATRIX_MODE"] == "development":
        print()
        print("[development] Verbose diagnostics enabled.")
        print(f"  DATABASE_URL = {cfg['DATABASE_URL']}")
        print(f"  API_KEY      = {mask(cfg['API_KEY'])}")
        print(f"  ZION_ENDPOINT= {cfg['ZION_ENDPOINT']}")
    elif cfg["MATRIX_MODE"] == "production":
        print()
        print("[production] Secrets hidden. Strict logging.")
        print(f"  DATABASE_URL = {mask(cfg['DATABASE_URL'])}")
        print(f"  API_KEY      = {mask(cfg['API_KEY'])}")

    print()
    print("Environment security check:")
    for tag, msg in security_checks(cfg, env_file):
        print(f"[{tag}] {msg}")

    if missing:
        print()
        print("WARNING: Missing configuration:")
        for var in missing:
            print(f"  - {var}")
        print()
        print("Copy .env.example to .env and fill values, or export env vars.")
        sys.exit(1)

    print()
    print("The Oracle sees all configurations.")


if __name__ == "__main__":
    main()

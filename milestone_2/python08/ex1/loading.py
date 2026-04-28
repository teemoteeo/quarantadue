import sys
import importlib
import importlib.metadata as md


REQUIRED: dict[str, str] = {
    "pandas": "Data manipulation ready",
    "numpy": "Numerical computation ready",
    "matplotlib": "Visualization ready",
}
OPTIONAL: dict[str, str] = {
    "requests": "Network access ready",
}


def check_dependencies() -> dict[str, object]:
    """Detect installed packages, report versions, gracefully note missing."""
    report: dict[str, object] = {}
    for pkg, desc in {**REQUIRED, **OPTIONAL}.items():
        try:
            importlib.import_module(pkg)
            version: str = md.version(pkg)
            print(f"[OK] {pkg} ({version}) - {desc}")
            report[pkg] = version
        except (ImportError, md.PackageNotFoundError):
            if pkg in REQUIRED:
                print(f"[MISSING] {pkg} - {desc}")
                report[pkg] = None
    return report


def print_install_instructions() -> None:
    print()
    print("Missing dependencies detected.")
    print()
    print("Install with pip:")
    print("  pip install -r requirements.txt")
    print()
    print("Install with Poetry:")
    print("  poetry install")
    print()
    print("Difference:")
    print("  pip   -> flat requirements.txt, no lockfile, no env mgmt.")
    print("  Poetry -> pyproject.toml + poetry.lock, reproducible builds,")
    print("           handles virtualenv creation and resolves dep graph.")


def compare_package_managers(report: dict[str, object]) -> None:
    print()
    print("Package manager comparison:")
    print(f"{'package':<12}{'version':<12}source")
    for pkg, ver in report.items():
        if ver is None:
            continue
        print(f"{pkg:<12}{str(ver):<12}pip or Poetry (same wheel)")


def analyze_matrix_data() -> None:
    import numpy as np
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rng = np.random.default_rng(seed=42)
    n: int = 1000
    print(f"Processing {n} data points...")

    timestamps = np.arange(n)
    signal = rng.normal(loc=0.0, scale=1.0, size=n).cumsum()
    noise = rng.normal(loc=0.0, scale=0.5, size=n)

    df = pd.DataFrame({
        "tick": timestamps,
        "signal": signal,
        "noise": noise,
        "combined": signal + noise,
    })

    print("Generating visualization...")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df["tick"], df["signal"], label="signal")
    ax.plot(df["tick"], df["combined"], label="signal + noise", alpha=0.6)
    ax.set_title("Matrix data stream")
    ax.set_xlabel("tick")
    ax.set_ylabel("value")
    ax.legend()
    fig.tight_layout()
    fig.savefig("matrix_analysis.png")
    plt.close(fig)


def main() -> None:
    print("LOADING STATUS: Loading programs...")
    print()
    print("Checking dependencies:")
    report = check_dependencies()

    missing = [p for p in REQUIRED if report.get(p) is None]
    if missing:
        print_install_instructions()
        sys.exit(1)

    print()
    print("Analyzing Matrix data...")
    try:
        analyze_matrix_data()
    except Exception as exc:
        print(f"Analysis failed: {exc}", file=sys.stderr)
        sys.exit(1)

    print()
    print("Analysis complete!")
    print("Results saved to: matrix_analysis.png")
    compare_package_managers(report)


if __name__ == "__main__":
    main()

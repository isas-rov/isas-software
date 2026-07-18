"""Minimal package entry point used for installation checks."""

from isas import __version__


def main() -> None:
    """Print a safe status message without connecting to vehicle hardware."""
    print(f"ISAS software {__version__} — hardware output is disabled")


if __name__ == "__main__":
    main()

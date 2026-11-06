import subprocess
from datetime import UTC, datetime
from pathlib import Path


def get_commit(d: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "describe", "--always", "--dirty"],
            cwd=d,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "desconhecido"

    return result.stdout.strip()


def get_output_path(name: str, d: Path, official: bool, N: int | None = None) -> Path:
    base = d / "resultados"
    stem = name if N is None else f"{name}_N_{N:_}"

    if official:
        output_path = base / f"{stem}.txt"

        if output_path.exists():
            raise FileExistsError(f"Arquivo {output_path} já existe.")

    else:
        date = datetime.now(UTC).strftime("%Y%m%dT%H%M%S_%f")
        output_path = base / "local" / f"{stem}_{date}.txt"

    return output_path

import subprocess
from pathlib import Path


def obter_commit(diretorio: Path) -> str:
    try:
        resultado = subprocess.run(
            ["git", "describe", "--always", "--dirty"],
            cwd=diretorio,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "desconhecido"

    return resultado.stdout.strip()

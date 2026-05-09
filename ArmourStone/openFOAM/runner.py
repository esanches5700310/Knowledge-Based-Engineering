from pathlib import Path
import subprocess


def run_command(command: str, case_dir: Path) -> None:
    log_file = case_dir / f"log.{command}"

    with open(log_file, "w") as log:
        subprocess.run(
            command,
            cwd=case_dir,
            stdout=log,
            stderr=subprocess.STDOUT,
            shell=True,
            check=True,
        )


def run_openfoam_case(case_dir: Path) -> None:
    run_command("blockMesh", case_dir)
    run_command("checkMesh", case_dir)
    run_command("simpleFoam", case_dir)
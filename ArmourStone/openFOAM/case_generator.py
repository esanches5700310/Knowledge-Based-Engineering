from pathlib import Path
import shutil


def create_case_from_template(case_name: str) -> Path:
    base_dir = Path(__file__).resolve().parents[1]

    template_dir = base_dir / "openfoam" / "templates" / "simple_jet_2d"
    cases_dir = base_dir / "cases"
    case_dir = cases_dir / case_name

    if case_dir.exists():
        shutil.rmtree(case_dir)

    shutil.copytree(template_dir, case_dir)

    return case_dir


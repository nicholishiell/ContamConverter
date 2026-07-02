import argparse
import shutil
import zipfile
from importlib import resources
from pathlib import Path

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TMP_EXTRACT_DIR = Path("tmp-fmus")
WINDOWS_PROJECT_FILE_PATH = "binaries\\win32\\contam.prj"
CONVERTED_FMU_ARCHIVE_FILENAME = Path("Converted-ContamFMU.fmu")

WEATHER_FILE_TOKEN = "! weather file"
CONTAM_FILE_TOKEN = "! contaminant file"

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def update_project_file(project_file_path: Path, ctm_path: Path, wth_path: Path) -> None:
    """Update the project file to point to the provided .ctm and .wth files."""
    lines = project_file_path.read_text().splitlines(keepends=True)

    for index, line in enumerate(lines):
        if WEATHER_FILE_TOKEN in line:
            lines[index] = f"{wth_path} {WEATHER_FILE_TOKEN}\n"
        elif CONTAM_FILE_TOKEN in line:
            lines[index] = f"{ctm_path} {CONTAM_FILE_TOKEN}\n"

    project_file_path.write_text("".join(lines))

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def extract_fmu(contam_fmu_path: Path) -> None:
    TMP_EXTRACT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(contam_fmu_path, "r") as archive:
            archive.extractall(TMP_EXTRACT_DIR)
    except (zipfile.BadZipFile, OSError) as exc:
        raise ValueError(f"Could not open FMU archive: {contam_fmu_path}") from exc

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def delete_tmp_extract_dir() -> None:
    """Delete the temporary FMU extraction directory if it exists."""
    if TMP_EXTRACT_DIR.is_dir():
        shutil.rmtree(TMP_EXTRACT_DIR)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def _copy_packaged_runtime_file(file_name: str, destination: Path) -> None:
    resource = resources.files("contamconverter").joinpath("files", file_name)
    with resources.as_file(resource) as runtime_file:
        shutil.copy(runtime_file, destination / file_name)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def convert(contam_fmu_path: Path, ctm_path: Path, wth_path: Path) -> Path:
    extract_fmu(contam_fmu_path)

    linux64_dir = TMP_EXTRACT_DIR / "binaries" / "linux64"
    linux64_dir.mkdir(parents=True, exist_ok=True)

    project_file_path = TMP_EXTRACT_DIR / WINDOWS_PROJECT_FILE_PATH
    if not project_file_path.is_file():
        raise FileNotFoundError(f"Project file not found in FMU: {project_file_path}. Perhaps archive is already converted?")

    linux64_project_file_path = linux64_dir / "contam.prj"
    shutil.copy(project_file_path, linux64_project_file_path)

    _copy_packaged_runtime_file("ContamFMU.so", linux64_dir)
    _copy_packaged_runtime_file("contamx3.exe", linux64_dir)

    update_project_file(linux64_project_file_path, ctm_path, wth_path)

    converted_fmu_path = Path.cwd() / CONVERTED_FMU_ARCHIVE_FILENAME
    with zipfile.ZipFile(converted_fmu_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in TMP_EXTRACT_DIR.rglob("*"):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(TMP_EXTRACT_DIR))

    delete_tmp_extract_dir()
    return converted_fmu_path

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert CONTAM model inputs.")
    parser.add_argument("--contam_fmu", required=True, help="Path to the ContamFMU.fmu file")
    parser.add_argument("--ctm_file", required=True, help="Path to the .ctm file")
    parser.add_argument("--wth_file", required=True, help="Path to the .wth file")
    return parser.parse_args()


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def main() -> None:
    args = parse_args()

    contam_fmu_path = Path(args.contam_fmu).expanduser().resolve(strict=False)
    ctm_path = Path(args.ctm_file).expanduser().resolve(strict=False)
    wth_path = Path(args.wth_file).expanduser().resolve(strict=False)

    missing_files = [str(path) for path in (contam_fmu_path, ctm_path, wth_path) if not path.is_file()]
    if missing_files:
        raise SystemExit("The following file(s) do not exist: " + ", ".join(missing_files))

    try:
        output = convert(contam_fmu_path, ctm_path, wth_path)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from None

    print(f"Created converted FMU at: {output}")

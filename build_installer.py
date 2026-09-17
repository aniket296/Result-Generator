"""
build_installer.py
One-Click Build Automation Script for Teacher Result Card Generator Windows Installer.

Features:
- Automatically discovers Inno Setup 6 (ISCC.exe) across PATH, Program Files, and AppData.
- Validates PyInstaller executable and dependencies in dist/.
- Auto-generates application icon assets if missing.
- Supports optional '--build-app' flag to compile PyInstaller binary before creating installer.
- Compiles installer/setup_script.iss and reports the final installer path and size.

Usage:
    python build_installer.py              # Build installer using existing dist/ executable
    python build_installer.py --build-app  # Compile PyInstaller executable first, then build installer
"""
import os
import shutil
import subprocess
import sys

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
INSTALLER_DIR = os.path.join(PROJECT_DIR, "installer")
ISS_SCRIPT = os.path.join(INSTALLER_DIR, "setup_script.iss")
DIST_DIR = os.path.join(PROJECT_DIR, "dist")
EXE_PATH_ONEDIR = os.path.join(DIST_DIR, "TeacherResultSoftware", "TeacherResultSoftware.exe")
EXE_PATH_ONEFILE = os.path.join(DIST_DIR, "TeacherResultSoftware.exe")
OUTPUT_DIR = os.path.join(PROJECT_DIR, "dist_installer")
FINAL_INSTALLER_NAME = "TeacherResultSoftware_Setup_v2.0.exe"
FINAL_INSTALLER_PATH = os.path.join(OUTPUT_DIR, FINAL_INSTALLER_NAME)


def find_iscc() -> str | None:
    """Locate the Inno Setup command-line compiler (ISCC.exe)."""
    # 1. Check system PATH
    which_path = shutil.which("ISCC.exe") or shutil.which("ISCC")
    if which_path and os.path.exists(which_path):
        return which_path

    # 2. Check standard Windows installation directories
    candidate_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
    ]

    # Check Local AppData Programs
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        candidate_paths.append(
            os.path.join(local_app_data, "Programs", "Inno Setup 6", "ISCC.exe")
        )
        candidate_paths.append(
            os.path.join(local_app_data, "Programs", "Inno Setup 5", "ISCC.exe")
        )

    # Check ProgramFiles env variables
    for env_var in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
        base = os.environ.get(env_var, "")
        if base:
            candidate_paths.append(os.path.join(base, "Inno Setup 6", "ISCC.exe"))
            candidate_paths.append(os.path.join(base, "Inno Setup 5", "ISCC.exe"))

    for path in candidate_paths:
        if os.path.isfile(path):
            return path

    return None


def ensure_assets() -> None:
    """Ensure installer icon and assets exist, auto-generating if necessary."""
    ico_path = os.path.join(INSTALLER_DIR, "assets", "app_icon.ico")
    if not os.path.exists(ico_path):
        print("[Assets] Icon missing. Generating app_icon.ico...")
        try:
            from installer.generate_assets import generate_app_icon
            generate_app_icon(ico_path)
            print(f"[Assets] Created {ico_path}")
        except Exception as err:
            print(f"[Assets] Warning: Failed to generate icon automatically: {err}")


def build_pyinstaller_app() -> bool:
    """Runs build.py to produce fresh PyInstaller binaries."""
    build_script = os.path.join(PROJECT_DIR, "build.py")
    if not os.path.exists(build_script):
        print(f"[Error] build.py not found at {build_script}")
        return False

    print("\n" + "=" * 65)
    print(" [Step 1/2] Compiling Python Application with PyInstaller...")
    print("=" * 65)
    res = subprocess.run([sys.executable, build_script], cwd=PROJECT_DIR)
    return res.returncode == 0


def main() -> int:
    print("=" * 65)
    print(" Teacher Result Card Generator - Installer Build Automation")
    print("=" * 65)

    build_app_first = "--build-app" in sys.argv

    # 1. Optionally build PyInstaller app first
    if build_app_first:
        if not build_pyinstaller_app():
            print("\n[Error] PyInstaller build failed. Aborting installer packaging.")
            return 1

    # 2. Check for PyInstaller executable
    has_onedir = os.path.exists(EXE_PATH_ONEDIR)
    has_onefile = os.path.exists(EXE_PATH_ONEFILE)

    if not has_onedir and not has_onefile:
        print("\n[Error] Compiled application not found in dist/ folder.")
        print(f"        Expected at: {EXE_PATH_ONEDIR}")
        print("\n[Tip] Run with '--build-app' or build the application manually first:")
        print("      python build.py")
        print("      python build_installer.py")
        return 1

    print(f"[1/3] Verified application binaries in dist/")
    if has_onedir:
        print(f"      Target: {EXE_PATH_ONEDIR}")
    else:
        print(f"      Target: {EXE_PATH_ONEFILE}")

    # 3. Ensure assets exist
    print("[2/3] Verifying installer assets...")
    ensure_assets()

    # 4. Locate Inno Setup Compiler
    print("[3/3] Locating Inno Setup compiler (ISCC.exe)...")
    iscc_bin = find_iscc()

    if not iscc_bin:
        print("\n" + "!" * 65)
        print(" [ERROR] Inno Setup 6 (ISCC.exe) was not found on this machine.")
        print("!" * 65)
        print("\nTo compile the Windows installer, please install Inno Setup 6:")
        print("  1. Official Download: https://jrsoftware.org/isdl.php")
        print("  2. Or install via Windows Package Manager (winget):")
        print("     winget install JRSoftware.InnoSetup")
        print("\nAfter installation, re-run this script:")
        print("  python build_installer.py")
        print("=" * 65)
        return 1

    print(f"      Found ISCC compiler: {iscc_bin}")

    # 5. Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 6. Run Inno Setup Compiler
    print("\n" + "-" * 65)
    print(f" Compiling Inno Setup Script: {os.path.basename(ISS_SCRIPT)}")
    print("-" * 65)

    cmd = [iscc_bin, ISS_SCRIPT]
    try:
        proc = subprocess.run(cmd, cwd=INSTALLER_DIR, check=True)
    except subprocess.CalledProcessError as cpe:
        print(f"\n[Error] Inno Setup compilation failed with exit code {cpe.returncode}")
        return cpe.returncode
    except Exception as exc:
        print(f"\n[Error] Failed to execute ISCC.exe: {exc}")
        return 1

    # 7. Verify generated installer output
    if os.path.exists(FINAL_INSTALLER_PATH):
        size_mb = os.path.getsize(FINAL_INSTALLER_PATH) / (1024 * 1024)
        print("\n" + "=" * 65)
        print(" INSTALLER BUILD COMPLETED SUCCESSFULLY! 🎉")
        print("=" * 65)
        print(f" Installer Binary : {FINAL_INSTALLER_PATH}")
        print(f" File Size        : {size_mb:.2f} MB")
        print(f" Ready for Windows distribution & deployment.")
        print("=" * 65 + "\n")
        return 0
    else:
        print(f"\n[Warning] Inno Setup completed, but output file not found at:")
        print(f"          {FINAL_INSTALLER_PATH}")
        return 1


if __name__ == "__main__":
    sys.exit(main())


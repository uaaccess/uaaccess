import os
import sys
import venv
from subprocess import run, CalledProcessError

def run_command(command):
    """Run a shell command and handle errors."""
    try:
        result = run(command, shell=True, check=True, text=True)
        return result.returncode == 0
    except CalledProcessError as e:
        print(f"Command failed: {e}")
        sys.exit(e.returncode)

def create_virtual_env(venv_dir):
    """Create a virtual environment."""
    if not os.path.exists(venv_dir):
        print("Creating virtual environment...")
        venv.EnvBuilder(with_pip=True).create(venv_dir)
    else:
        print("Virtual environment already exists.")

def install_packages(venv_bin, packages):
    """Install required packages in the virtual environment."""
    for package in packages:
        print(f"Installing package '{package}'...")
        run_command(f"{os.path.join(venv_bin, 'pip')} install {package}")

def update_packages(venv_bin, run_after_update=False):
    print("Updating project dependencies...")
    command = f"{os.path.join(venv_bin, 'briefcase')} dev -r"
    if not run_after_update:
        command += " --no-run"
    return run_command(command)

def build_package(venv_bin, build_as_zip=True):
    """Build and package the project."""
    print("Building the project...")
    update_packages(venv_bin)
    package_type = 'zip' if build_as_zip else 'msi'
    print(f"Packaging the project as {package_type.upper()}...")
    run_command(f"{os.path.join(venv_bin, 'briefcase')} package -p {package_type} -u")

def main():
    # Configuration
    required_packages = ["briefcase"]
    build_as_zip = False  # Change to true to build as Zip

    # Paths
    project_dir = os.getcwd()
    venv_dir = os.path.join(project_dir, "uaaccess_env")
    venv_bin = os.path.join(venv_dir, "Scripts") if os.name == "nt" else os.path.join(venv_dir, "bin")

    # Check if running inside a virtual environment
    if os.getenv('VIRTUAL_ENV'):
        print("Virtual environment already active.")
        install_packages(venv_bin, required_packages)
        build_package(venv_bin, build_as_zip)
    else:
        create_virtual_env(venv_dir)
        install_packages(venv_bin, required_packages)

        # Provide activation instructions for the user
        activate_script = os.path.join(venv_bin, 'activate')
        if not os.path.exists(activate_script):
            print(f"Error: Activation script not found at {activate_script}")
            sys.exit(1)

        print("\nVirtual environment setup complete!")
        print(f"Activate the virtual environment by running:")
        if os.name == "nt":
            print(f"  {activate_script}")
        else:
            print(f"  source {activate_script}")
        print("Then rerun this script to build and package the project.")

if __name__ == "__main__":
    main()

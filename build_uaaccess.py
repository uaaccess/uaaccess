import os
import subprocess
import sys
from importlib.metadata import version, PackageNotFoundError

def run_command(command, env=None, cwd=None):
    """Run a shell command and handle errors."""
    try:
        result = subprocess.run(command, shell=True, check=True, text=True, env=env, cwd=cwd)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")
        sys.exit(e.returncode)

def virtual_env_exists(venv_dir):
    """Check if the virtual environment directory exists."""
    return os.path.exists(venv_dir)

def is_virtual_env_active():
    """Check if a virtual environment is active."""
    return os.getenv('VIRTUAL_ENV') is not None

def install_packages(venv_scripts, packages):
    """Check if required packages are installed and install them if not."""
    for package in packages:
        try:
            pkg_version = version(package)
            print(f"Package '{package}' is already installed (version {pkg_version}).")
        except PackageNotFoundError:
            print(f"Package '{package}' is not installed. Installing...")
            pip_install_command = f"{os.path.join(venv_scripts, 'pip')} install {package}"
            run_command(pip_install_command)
        except Exception as e:
            print(f"Unexpected error while checking package '{package}': {e}")
            sys.exit(1)

def activate_virtual_env(venv_dir):
    """Activate the virtual environment."""
    activate_script = os.path.join(venv_dir, "Scripts", "activate")
    if not os.path.exists(activate_script):
        print("Activation script not found. Ensure the virtual environment is set up correctly.")
        sys.exit(1)
    print("Activating virtual environment...")
    os.environ['VIRTUAL_ENV'] = venv_dir

def build_project(venv_scripts):
    """Build the project in development mode."""
    briefcase_command = f"{os.path.join(venv_scripts, 'briefcase')} dev -r"
    print("Building the project in development mode...")
    run_command(briefcase_command)

def package_project(venv_scripts, build_as_zip):
    """Package the project."""
    package_type = 'zip' if build_as_zip else 'msi'
    briefcase_package_command = f"{os.path.join(venv_scripts, 'briefcase')} package -p {package_type} -u"
    print(f"Packaging the project as {package_type.upper()}...")
    run_command(briefcase_package_command)

def main():
    # Configuration
    build_as_zip = False  # Set to False if you want an MSI instead of a ZIP
    required_packages = ["briefcase"]  # List of required packages

    # Paths
    project_dir = os.getcwd()
    venv_dir = os.path.join(project_dir, "uaaccess_env")
    venv_scripts = os.path.join(venv_dir, "Scripts")

    # Check and create virtual environment if necessary
    if not virtual_env_exists(venv_dir):
        print("Virtual environment not found. Creating one...")
        run_command(f"python -m venv {venv_dir}")
    else:
        print("Virtual environment found.")

    # Activate virtual environment if not active
    if not is_virtual_env_active():
        activate_virtual_env(venv_dir)
    else:
        print("Virtual environment is already active.")

    # Ensure required packages are installed
    install_packages(venv_scripts, required_packages)

    # Build the project
    build_project(venv_scripts)

    # Package the project
    package_project(venv_scripts, build_as_zip)

    print("Build process completed successfully.")

if __name__ == "__main__":
    main()

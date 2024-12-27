# uaaccess
A screen-reader-accessible alternative to the Universal Audio Console software.

## Development instructions

To develop the project, or to build a package, follow these instructions:

1. Install the [visual studio build tools](https://download.visualstudio.microsoft.com/download/pr/655265af-cd2f-4919-97b2-3198ac560526/72224eda2843205f7b6abbbd93da8426d05f25571f8a02b4915a6d61cbbf1b13/vs_BuildTools.exe) and select the "Desktop development with C++" workload. You do not need to install the full visual studio product.
2. Install python 3.12.x. Python 3.13 is not supported at this time.
3. Clone this repository: `git clone https://github.com/uaaccess/uaaccess.git` then `cd uaaccess`.
4. Create a virtual environment: `python -m venv uaaccess_env`.
5. Activate the environment you just created with e.g. `uaaccess_env\scripts\activate`.
6. With the environment activated, run `pip install briefcase`. Then:
    * If you want to run the code, run `briefcase dev -r`. This will hopefully only need to be run once, and will install all dependencies. In future, unless dependency versions are updated, you need only run `briefcase dev`.
    * If you want to build a distributable package, run `briefcase package -p zip -u` (or, if you want to build an MSI, change `zip` in the aforementioned command to `msi`). The resulting package will be in the `dist` directory.

## License

This software is licensed under the GNU General Public License 3.0.

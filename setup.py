import shutil
from pathlib import Path
from setuptools import setup, find_packages
import versioneer

setup(
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    packages=find_packages(where="picalor_core"),
    package_dir={"": "picalor_core"},
    include_package_data=True,
)

# Because stuptools mangles the interpreter in this
# script which is supposed to run in ipython interpreter
pc_bindir = Path.home().joinpath(".local").joinpath("bin")
pc_bindir.mkdir(parents=True, exist_ok=True)
pc_rootdir = Path(__file__).parent.absolute()
pc_scriptfile = pc_rootdir.joinpath("picalor_core/picalor/scripts/picalor-interactive")
shutil.copy(pc_scriptfile, pc_bindir)

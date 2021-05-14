"""Functions to add additional libraries to the tests."""

import os
import pathlib
import subprocess

from test_utils.general import get_files


STD = "--std=08"
WORK_DIR = "sim_build"
ABSOLUTE_PATH = pathlib.Path(__file__).parent.absolute()


def analyze_util():
    """Analyze the utility library."""
    work = "util"
    source_path = ABSOLUTE_PATH / ".." / ".." / "src" / "util"
    source_files = get_files(source_path, "*.vhd")

    if outdated(f"{WORK_DIR}/{work}-obj08.cf", source_files):
        os.makedirs(f"{WORK_DIR}", exist_ok=True)

        analyze_command = ["ghdl", "-i", STD, f"--work={work}", f"--workdir={WORK_DIR}"]
        analyze_command.extend(source_files)
        subprocess.run(analyze_command, check=True)


def analyze_window_ctrl_lib():
    """Analyze the window control library."""
    analyze_util()

    work = "window_ctrl_lib"
    source_path = ABSOLUTE_PATH / ".." / ".." / "src" / "window_ctrl"
    source_files = get_files(source_path, "*.vhd")

    if outdated(f"{WORK_DIR}/{work}-obj08.cf", source_files):
        os.makedirs(f"{WORK_DIR}", exist_ok=True)

        analyze_command = ["ghdl", "-i", STD, f"--work={work}", f"--workdir={WORK_DIR}"]
        analyze_command.extend(source_files)
        subprocess.run(analyze_command, check=True)


def analyze_uart_lib():
    """Analyze the UART library."""
    work = "uart_lib"
    source_path = ABSOLUTE_PATH / ".." / ".." / "submodules" / "icestick-uart" / "hdl"
    source_files = get_files(source_path, "*.vhd")

    if outdated(f"{WORK_DIR}/{work}-obj08.cf", source_files):
        os.makedirs(f"{WORK_DIR}", exist_ok=True)

        analyze_command = ["ghdl", "-i", STD, f"--work={work}", f"--workdir={WORK_DIR}"]
        analyze_command.extend(source_files)
        subprocess.run(analyze_command, check=True)


def outdated(output: str, dependencies: list) -> bool:
    """Check whether files are outdated with regards to a reference output."""
    if not os.path.isfile(output):
        return True

    output_mtime = os.path.getmtime(output)

    dep_mtime = 0
    for file in dependencies:
        mtime = os.path.getmtime(file)
        if mtime > dep_mtime:
            dep_mtime = mtime

    if dep_mtime > output_mtime:
        return True
    return False

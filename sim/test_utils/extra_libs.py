"""Functions to add additional libraries to the tests."""

import os
import pathlib
import subprocess

from test_utils.general import get_files


STD = "--std=08"
WORK_DIR = "sim_build"


def analyze_util():
    work = "util"
    source_path = (
        pathlib.Path(__file__).parent.absolute() / ".." / ".." / "src" / "util"
    )
    source_files = get_files(source_path, "*.vhd")

    if outdated(f"{WORK_DIR}/{work}-obj08.cf", source_files):
        os.makedirs(f"{WORK_DIR}", exist_ok=True)

        analyze_command = ["ghdl", "-i", STD, f"--work={work}", f"--workdir={WORK_DIR}"]
        analyze_command.extend(source_files)
        subprocess.run(analyze_command, check=True)


def analyze_window_ctrl_lib():
    analyze_util()

    work = "window_ctrl_lib"
    source_path = (
        pathlib.Path(__file__).parent.absolute() / ".." / ".." / "src" / "window_ctrl"
    )
    source_files = get_files(source_path, "*.vhd")

    if outdated(f"{WORK_DIR}/{work}-obj08.cf", source_files):
        os.makedirs(f"{WORK_DIR}", exist_ok=True)

        analyze_command = ["ghdl", "-i", STD, f"--work={work}", f"--workdir={WORK_DIR}"]
        analyze_command.extend(source_files)
        subprocess.run(analyze_command, check=True)


def outdated(output, dependencies):
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

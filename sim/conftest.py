from dataclasses import dataclass
import os
import pathlib
import random
import subprocess
from typing import Sequence, Tuple

import numpy as np

from test_utils.general import get_files

# https://stackoverflow.com/questions/44624407/how-to-reduce-log-line-size-in-cocotb
os.environ["COCOTB_REDUCED_LOG_FMT"] = "1"
os.environ["SIM"] = "ghdl"

# https://stackoverflow.com/questions/35911252/disable-tensorflow-debugging-information
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # ERROR


# Use fixed seeds to get reproducible results.
random.seed(42)
np.random.seed(42)


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


@dataclass
class Library:
    name: int
    files: Sequence[Tuple[str, str]]


def pytest_addoption(parser):
    parser.addoption("--waves", action="store_true", help="Record the waveform.")


def pytest_configure(config):
    # Analyze all needed libraries.
    work_dir = "sim_build"
    libs = (
        # Analyze utils first to provide dependencies.
        Library("util", (("../src/util", "*.vhd"),)),
        Library("bnn_lib", (("../src", "*.vhd"),)),
        Library("fmf", (("../submodules/fmf", "*.vhd"),)),
        Library(
            "interface_lib",
            (
                ("../submodules/icestick-uart/hdl", "*.vhd"),
                ("../submodules/sdram-fpga", "*.vhd"),
                ("../sim/hdl_helpers", "ecp5pll.vhd"),
            ),
        ),
        Library("sim_lib", (("hdl_helpers", "sdram_wrapper.vhd"),)),
        Library("window_ctrl_lib", (("../src/window_ctrl", "*.vhd"),)),
    )

    for lib in libs:
        source_files = []
        for path, pattern in lib.files:
            source_files.extend(
                get_files(pathlib.Path(__file__).parent.absolute() / path, pattern)
            )

        if outdated(f"{work_dir}/{lib.name}-obj08.cf", source_files):
            os.makedirs(f"{work_dir}", exist_ok=True)

            analyze_command = [
                "ghdl",
                "-i",
                "--std=08",
                f"--work={lib.name}",
                f"--workdir={work_dir}",
            ]
            analyze_command.extend(source_files)
            subprocess.run(analyze_command, check=True)

    # Optionally add waveforms. This slows down the simulation.
    if config.getoption("--waves"):
        os.environ["WAVES"] = "1"

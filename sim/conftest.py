import os
import random

import numpy as np

from test_utils.extra_libs import (
    analyze_util,
    analyze_window_ctrl_lib,
    analyze_uart_lib,
)

# https://stackoverflow.com/questions/44624407/how-to-reduce-log-line-size-in-cocotb
os.environ["COCOTB_REDUCED_LOG_FMT"] = "1"
os.environ["SIM"] = "ghdl"

# https://stackoverflow.com/questions/35911252/disable-tensorflow-debugging-information
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # ERROR


# Use fixed seeds to get reproducible results.
random.seed(42)
np.random.seed(42)


def pytest_addoption(parser):
    parser.addoption("--waves", action="store_true", help="Record the waveform.")


def pytest_configure(config):
    analyze_util()
    analyze_window_ctrl_lib()
    analyze_uart_lib()

    if config.getoption("--waves"):
        os.environ["WAVES"] = "1"

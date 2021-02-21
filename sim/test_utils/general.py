"""Collection of general test utilities."""

import dataclasses
import pathlib
from random import randint
from typing import List, Optional, Sequence

import pytest


@pytest.fixture
def record_waveform(request):
    return request.config.getoption("--wave")


def position_to_index(col: int, row: int, width: int, height: int) -> int:
    index = row * width + col
    assert index < width * height
    return index


def generate_random_image(
    channel: int, width: int, height: int, bitwidth: int = 8
) -> List[int]:
    image = []
    for _ in range(height * width * channel):
        image.append(randint(0, 2 ** bitwidth - 1))
    return image


def index_to_position(index: int, width: int, height: int) -> tuple:
    """Convert a one dimensional stream index to a two dimensional
    image position."""
    if index < width:
        xpos = index
        ypos = 0
    else:
        ypos, xpos = divmod(index, width)
    assert ypos < height
    return xpos, ypos


def print_row_by_row(
    name: str, list_: List[int], width: int, height: int, channel: int
):
    print(f"{name}:")
    for row in range(height):
        print(list_[row * width * channel : (row + 1) * width * channel])


def get_files(path: pathlib.Path, pattern: str) -> List[str]:
    return [p.resolve() for p in list(path.glob(pattern))]


def concatenate_integers(integer_list: List[int], bitwidth=1) -> int:
    concatenated_integer = 0
    for value in integer_list:
        if value > 2 ** bitwidth:
            raise ValueError(f"Value {value} exeeds range.")
        concatenated_integer = (concatenated_integer << bitwidth) + value
    return concatenated_integer


def concatenate_channel(image, channel, bitwidth=1):
    return [
        concatenate_integers(
            image[pixel_index : pixel_index + channel], bitwidth=bitwidth
        )
        for pixel_index in range(0, len(image), channel)
    ]

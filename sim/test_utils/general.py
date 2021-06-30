"""Collection of general test utilities."""

import pathlib
from random import randint
from typing import List

from bitstring import Bits


def position_to_index(col: int, row: int, width: int, height: int) -> int:
    """Convert a position into an index of a one dimensional stream."""
    index = row * width + col
    assert index < width * height
    return index


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


def get_files(path: pathlib.Path, pattern: str) -> List[str]:
    """Obtain all files matching a pattern in a specific path."""
    return [p.resolve() for p in list(path.glob(pattern))]


def concatenate_integers(integer_list: List[int], bitwidth=1) -> int:
    """Concatenate multiple integers into a single integer."""
    concatenated_integer = 0
    for value in integer_list:
        if value > 2 ** bitwidth:
            raise ValueError(f"Value {value} exeeds range.")
        concatenated_integer = (concatenated_integer << bitwidth) + value
    return concatenated_integer


def concatenate_channel(image, channel, bitwidth=1):
    """Concatenate the channels of an image."""
    return [
        concatenate_integers(
            image[pixel_index : pixel_index + channel], bitwidth=bitwidth
        )
        for pixel_index in range(0, len(image), channel)
    ]


def to_fixedint(number: int, bitwidth: int, is_unsigned: bool = True):
    """Convert signed int to fixed int."""
    if is_unsigned:
        number_dict = {"uint": number, "length": bitwidth}
    else:
        number_dict = {"int": number, "length": bitwidth}
    return int(Bits(**number_dict).bin, 2)


def from_fixedint(number: int, bitwidth: int, is_unsigned: bool = True):
    """Convert fixed int to signed int."""
    number_bin = bin(number)[2:].zfill(bitwidth)
    if is_unsigned:
        return Bits(bin=number_bin).uint
    return Bits(bin=number_bin).int

#!/usr/bin/python3

"""Simple UART sender and receiver to test the bnn."""

import time
from random import randint
import serial
import serial.tools.list_ports


def test_uart():
    """Test whether an UART transmission on the serial port works."""
    available_ports = list(serial.tools.list_ports.grep("0403:6015"))
    print(f"{len(available_ports)} serial ports found.")

    port = available_ports[0]
    print("port ", port.device)
    with serial.Serial(port.device, baudrate=115200, timeout=0.1) as ser:
        # words = [randint(0, 255) for _ in range(28 * 28)]
        words = [0 for _ in range(28 * 28)]

        # sanity test
        for word in words:
            ser.write(word.to_bytes(1, "big"))

        rcv = ser.read(1024)
        print(rcv)
        print([int(r) for r in rcv])
        assert (
            len(rcv) == 10
        ), f"Got {len(rcv)} values. Expected 10."  # 10 output classes

        # performance
        # cnt = 100
        # t_start = time.time()
        # for _ in range(cnt):
        #     for word in words:
        #         ser.write(word.to_bytes(1, "big"))
        #     ser.read(10)
        # t_end = time.time()
        # print((t_end - t_start) / cnt)


if __name__ == "__main__":
    test_uart()

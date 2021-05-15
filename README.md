# pocket-bnn

pocket-bnn is a framework to map small Binarized Neural Networks (BNN) on a FPGA. It is based on the experience gained in [pocket-cnn](https://github.com/marph91/pocket-cnn). This is no processor, but rather the BNN is mapped directly on the FPGA. There is no communication needed, except of providing the image and reading the result.

## Installation and Usage

To run a simple demo, execute the following commands:

```bash
# train a bnn
make model

# generate a vhdl toplevel from the model
# synthesize, PnR, generate bitstream
make bnn.bit

# program the board
make prog
```

The BNN will be accessible through UART. There is an example script, which can be used: `python playground/06_test_uart.py`. The result should be corresponding to the BNN test.

There are a few programs and python modules that need to be installed, like [LARQ](https://github.com/larq/larq) and the open source toolchain to program the ULX3S. For now, they need to be installed manually.

A few stats for the example are:

- Accuracy on Mnist: 75 %
- Resource usage: 17276/41820 (41%) of TRELLIS_SLICE
- Frequency: 25 MHz (Max. frequency: 132 MHz)

In simulation, the full BNN inference is done in less than 10 us at 100 MHz. More stats will follow, since this is the first example.

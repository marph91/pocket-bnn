import cocotb
from cocotb_test.simulator import run

from test_utils.cocotb_helpers import Tick


@cocotb.test()
async def run_test(dut):
    # No clock is needed here. The simulation pll generates a 100 MHz frequency.
    clock_period = 10  # ns
    tick = Tick(clock_period=clock_period)

    dut.i_bnn_uart.btn = 0
    await tick.wait_multiple(10100)  # init should be done after 100 us
    dut.i_bnn_uart.btn = int("01000000", 2)
    dut.i_bnn_uart.sl_ready_uart_tx = 1
    await tick.wait()
    dut.i_bnn_uart.btn = 0
    await tick.wait_multiple(200)


def test_bnn_uart():
    generics = {}
    run(
        toplevel="sdram_wrapper",
        module="test_sdram",
        compile_args=["--work=sim_lib", "--std=08", "-fsynopsys", "-frelaxed"],
        sim_args=["--ieee-asserts=disable"],
        parameters=generics,
    )

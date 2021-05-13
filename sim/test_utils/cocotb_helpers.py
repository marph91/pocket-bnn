"""Collection of common cocotb helper functions."""

from cocotb_bus.monitors import Monitor
from cocotb.triggers import RisingEdge, Timer


def get_safe_int(signal, default: int = 0):
    try:
        return signal.value.integer
    except ValueError:
        return default


# TODO: evaluate streambusmonitor
# https://github.com/cocotb/cocotb/blob/master/examples/mean/tests/test_mean.py#L16
class ImageMonitor(Monitor):
    """Observes single input or output of DUT."""

    def __init__(self, name, signal, valid, clock, output_channels, bitwidth=1):
        self.name = name
        self.signal = signal
        self.valid = valid
        self.clock = clock
        self.output = []
        self.bitwidth = bitwidth
        self.output_channels = output_channels

        super().__init__()

    def clear(self):
        """Clear the current output."""
        self.output = []

    async def _monitor_recv(self):
        clock_edge = RisingEdge(self.clock)

        while True:
            await clock_edge

            if get_safe_int(self.valid) == 1:
                vec = self.signal.value.binstr
                output = [
                    int(vec[ch * self.bitwidth : (ch + 1) * self.bitwidth], 2)
                    for ch in range(self.output_channels)
                ]
                self.output.extend(output)


class Tick:
    """Convenience class to avoid specifying the unit always."""

    def __init__(self, clock_period: int = 10, units: str = "ns"):
        self.clock_period = clock_period
        self.units = units
        self.tick = Timer(clock_period, units=units)

    async def wait(self):
        """Wait a single clock tick."""
        await self.tick

    async def wait_multiple(self, tick_count: int = 1):
        """Wait multiple clock ticks."""
        await Timer(self.clock_period * tick_count, units=self.units)

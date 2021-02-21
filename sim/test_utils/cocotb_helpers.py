"""Collection of common cocotb helper functions."""

from cocotb.monitors import Monitor
from cocotb.triggers import RisingEdge, Timer


# TODO: evaluate streambusmonitor
# https://github.com/cocotb/cocotb/blob/master/examples/mean/tests/test_mean.py#L16
class ImageMonitor(Monitor):
    """Observes single input or output of DUT."""

    def __init__(self, name, signal, valid, clock, output_channels):
        self.name = name
        self.signal = signal
        self.valid = valid
        self.clock = clock
        self.output = []
        self.eol_count = 0
        self.output_channels = output_channels

        super().__init__()

    def clear(self):
        """Clear the current output."""
        self.output = []

    async def _monitor_recv(self):
        clock_edge = RisingEdge(self.clock)

        while True:
            await clock_edge
            try:
                valid = self.valid.value.integer
            except ValueError:
                valid = 0
            if valid == 1:
                vec = self.signal.value.binstr
                output = [
                    int(vec[ch * 8 : (ch + 1) * 8], 2)
                    for ch in range(self.output_channels)
                ]
                self.output.extend(output)

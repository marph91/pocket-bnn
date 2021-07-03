import nmigen as nm


# https://github.com/nmigen/nmigen/blob/b38b2cdad74c85c026a9313f8882f52460eb82e6/nmigen/hdl/mem.py


class MaximumPooling(nm.Elaboratable):
    """Three dimensional (height, width, channel) maximum pooling."""

    def __init__(self, channel, dim=2, bitwidth=1):
        # Parameter
        if dim != 2:
            raise ValueError("Only supported dim is 2 for now.")
        if bitwidth != 1:
            raise ValueError("Only supported bitwidth is 1 for now.")
        self.dim = dim
        self.channel = channel
        self.bitwidth = bitwidth

        # Ports
        self.valid_in = nm.Signal()
        self.data_in = nm.Array(
            nm.Array(
                nm.Array(
                    nm.Signal(bitwidth, name=f"in_{ch=}_{w=}_{h=}") for h in range(dim)
                )
                for w in range(dim)
            )
            for ch in range(channel)
        )
        self.data_out = nm.Array(
            nm.Signal(bitwidth, name=f"out_{ch=}") for ch in range(channel)
        )
        self.valid_out = nm.Signal()

    def elaborate(self, platform):
        m = nm.Module()

        with m.If(self.valid_in):
            for ch in range(self.channel):
                # If any input is set, the output gets set.
                m.d.sync += self.data_out[ch].eq(0)
                for w in range(self.dim):
                    for h in range(self.dim):
                        with m.If(self.data_in[ch][w][h]):
                            m.d.sync += self.data_out[ch].eq(1)

        m.d.sync += self.valid_out.eq(self.valid_in)

        return m

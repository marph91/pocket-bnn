import nmigen as nm


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
                nm.Signal(bitwidth, name=f"in_{ch=}_{spatial_index=}")
                for spatial_index in range(dim ** 2)
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
                for spatial_index in range(self.dim ** 2):
                    with m.If(self.data_in[ch][spatial_index]):
                        m.d.sync += self.data_out[ch].eq(1)

        m.d.sync += self.valid_out.eq(self.valid_in)

        return m

import unittest

from nmigen.sim import Simulator

import sim.common as cm
from src.maximum_pooling import MaximumPooling


class Tests(unittest.TestCase):
    # https://github.com/nmigen/nmigen/blob/b38b2cdad74c85c026a9313f8882f52460eb82e6/tests/test_sim.py

    def test_maximum_pooling(self):
        dut = MaximumPooling(3)
        sim = Simulator(dut)
        sim.add_clock(1e-6)  # 1 MHz

        sim_finished = False
        data_in = []

        def stimuli():
            # arbitrary input for one cycle
            input_array = [
                [1, 0, 0, 0],
                [0, 0, 0, 0],
                [1, 0, 0, 0],
            ]
            data_in.append(input_array)
            yield from cm.assign_array_2d(input_array, dut.data_in)
            yield dut.valid_in.eq(1)
            yield

            # new input, but not valid
            input_array = [
                [0, 0, 0, 0],
                [0, 0, 0, 1],
                [0, 1, 0, 0],
            ]
            data_in.append(input_array)
            yield from cm.assign_array_2d(input_array, dut.data_in)
            yield dut.valid_in.eq(0)
            yield

            # new input is valid now
            yield dut.valid_in.eq(1)
            yield
            yield dut.valid_in.eq(0)
            yield

            # valid input for multiple cycles
            input_array = [
                [1, 0, 0, 0],
                [1, 1, 1, 1],
                [1, 0, 0, 0],
            ]
            data_in.append(input_array)
            yield from cm.assign_array_2d(input_array, dut.data_in)
            yield dut.valid_in.eq(1)
            yield
            input_array = [
                [0, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
            ]
            data_in.append(input_array)
            yield from cm.assign_array_2d(input_array, dut.data_in)
            yield
            yield dut.valid_in.eq(0)
            yield
            yield

            nonlocal sim_finished
            sim_finished = True

        def check_latency(latency=1):
            valid_in = []
            valid_out = []
            while not sim_finished:
                valid_in.append((yield dut.valid_in))
                valid_out.append((yield dut.valid_out))
                yield
            self.assertEqual(valid_in[:-latency], valid_out[latency:])

        def check_output():
            data_out = []
            while not sim_finished:
                if (yield dut.valid_out):
                    data_out.append((yield from cm.yield_array(dut.data_out)))
                yield
            for in_, out_ in zip(data_in, data_out):
                for ch in range(len(in_)):
                    reference = max(in_[ch])
                    self.assertEqual(reference, out_[ch], f"{in_=}, {out_=}")

        sim.add_sync_process(stimuli)
        sim.add_sync_process(check_latency)
        sim.add_sync_process(check_output)
        with sim.write_vcd("up_counter.vcd"):
            sim.run()


# sim.run()

# with sim.write_vcd("up_counter.vcd"):
#     sim.run()
# # --- CONVERT ---
# from nmigen.back import verilog
# top = MaximumPooling(25)
# with open("up_counter.v", "w") as f:
#     f.write(verilog.convert(top, ports=[top.valid_in]))

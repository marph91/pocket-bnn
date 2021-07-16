import unittest

from nmigen.sim import Simulator

import sim.common as cm
from src.convolution import Convolution


def flatten(object):
    flattened = []
    for item in object:
        if isinstance(item, (list, tuple, set)):
            flattened.extend(flatten(item))
        else:
            flattened.append(item)
    return flattened


class Tests(unittest.TestCase):
    # https://github.com/nmigen/nmigen/blob/b38b2cdad74c85c026a9313f8882f52460eb82e6/tests/test_sim.py

    def test_convolution(self):
        # TODO: parameterize test
        dut = Convolution(3, channel_out=2, batch_normalization=False)
        sim = Simulator(dut)
        sim.add_clock(1e-6)  # 1 MHz

        sim_finished = False

        data_in = []

        # TODO: non burst and random
        # [randint(0, 2 ** input_channel_bitwidth - 1) for _ in range(input_length)],
        # [randint(0, 1) for _ in range(input_length)],
        def stimuli():
            # arbitrary input for one cycle
            activations = [[0] * 2 ** dut.dim * dut.bitwidth] * dut.channel_in
            weights = [
                [[0] * 2 ** dut.dim * dut.bitwidth] * dut.channel_in
            ] * dut.channel_out
            data_in.append((activations, weights))
            yield from cm.assign_array_2d(activations, dut.data_in)
            yield from cm.assign_array_3d(weights, dut.weights)
            yield dut.valid_in.eq(1)
            yield

            activations = [[0] * 2 ** dut.dim * dut.bitwidth] * dut.channel_in
            weights = [
                [[1] * 2 ** dut.dim * dut.bitwidth] * dut.channel_in
            ] * dut.channel_out
            data_in.append((activations, weights))
            yield from cm.assign_array_2d(activations, dut.data_in)
            yield from cm.assign_array_3d(weights, dut.weights)
            yield

            activations = [[1] * 2 ** dut.dim * dut.bitwidth] * dut.channel_in
            weights = [
                [[0] * 2 ** dut.dim * dut.bitwidth] * dut.channel_in
            ] * dut.channel_out
            data_in.append((activations, weights))
            yield from cm.assign_array_2d(activations, dut.data_in)
            yield from cm.assign_array_3d(weights, dut.weights)
            yield

            activations = [[1] * 2 ** dut.dim * dut.bitwidth] * dut.channel_in
            weights = [
                [[1] * 2 ** dut.dim * dut.bitwidth] * dut.channel_in
            ] * dut.channel_out
            data_in.append((activations, weights))
            yield from cm.assign_array_2d(activations, dut.data_in)
            yield from cm.assign_array_3d(weights, dut.weights)
            yield
            yield dut.valid_in.eq(0)
            yield
            yield
            yield
            yield
            yield

            nonlocal sim_finished
            sim_finished = True

        def check_output():
            data_out = []
            while not sim_finished:
                if (yield dut.valid_out):
                    data_out.append((yield from cm.yield_array(dut.data_out)))
                yield
            for in_, out_ in zip(data_in, data_out):
                reference_outputs = []
                for weights_channel in in_[1]:  # output channel
                    reference_output = 0
                    for activation, weights in zip(
                        flatten(in_[0]), flatten(weights_channel)
                    ):
                        reference_output += activation ^ weights
                    reference_outputs.append(reference_output)
                self.assertEqual(
                    reference_outputs, out_, f"{reference_outputs=}, {out_=}"
                )

        sim.add_sync_process(stimuli)
        sim.add_sync_process(check_output)
        with sim.write_vcd("convolution.vcd"):
            sim.run()

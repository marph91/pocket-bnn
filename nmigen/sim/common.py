def assign_array_2d(input_array, signal):
    # TODO: generalize
    for ch in range(len(signal)):
        for spatial_index in range(len(signal[0])):
            yield signal[ch][spatial_index].eq(input_array[ch][spatial_index])


def assign_array_3d(input_array, signal):
    for ch_out in range(len(signal)):
        for ch_in in range(len(signal[0])):
            for spatial_index in range(len(signal[0][0])):
                yield signal[ch_out][ch_in][spatial_index].eq(
                    input_array[ch_out][ch_in][spatial_index]
                )


def yield_array(array):
    result = []
    for index in range(len(array)):
        result.append((yield array[index]))
    return result

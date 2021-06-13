# Parallelism of CNN in FPGA designs

<https://ieeexplore.ieee.org/document/7428073> specifies four types of parallelism, in regard to the convolutional layer:

1. inter kernel parallelism: The same set of operations (i. e. kernel) is applied for each pixel in the output map. This is not applicable in our implementation, because there is a pixel stream and the kernel have to be applied pixel by pixel. However, this would be useful when using a processor based approach, where all input pixel are accesible at the same time.
2. inter layer parallelism: As soon as a pixel of one layer is computed, the next layer can process it. This is not real parallelism, since the layers can't be computed in parallel. However, it can be pipelined in our design. This couldn't be used in the processor based approach, since one layer is calculated at a time.
3. inter output parallelism (IOP): The output channel of a output pixel can be computed in parallel.
4. intra kernel parallelism (IKP): The multiplications to compute one output channel, can be done in parallel.

Design considerations:

Parallelism | No IOP | Full IOP | No IKP | Full IKP | Total
-|-|-|-|-|-
RAM bitwidth | 1 | output channel | 1 | kernel size \* kernel size \* input channel | IOP \* IKP \* data bitwidth
RAM type | BRAM possible | LUTRAM | BRAM possible | LUTRAM | -
Latency and input repetition | output channel | 1 | kernel size \* kernel size \* input channel | 1 | IOP \* IKP
Handshake | Needed | Possibly not needed | Needed | Possibly not needed | -

For now, full parallelsim (IOP and IKP) was implemented. This yields a latency of 1 cycle, independent of the other parameter. Thus no handshake and no input repetition was needed. On the other side, the required RAM bitwidth is dependent on the parameter. Due to the high bandwith requirements, only LUTRAM could be used.

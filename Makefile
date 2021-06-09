format:
	vsg --configuration vsg_config.yaml --fix
	black . --exclude /submodules/

sim:
	cd sim && pytest $(SIM_ARGS)
.PHONY: sim

model:
	cd playground && python 05_intro_modified.py

toplevel:
	cd playground && python 04_custom_toplevel.py

ROOT_DIR = $(shell pwd)
SOURCES_UART = \
	$(ROOT_DIR)/submodules/icestick-uart/hdl/uart_rx.vhd \
	$(ROOT_DIR)/submodules/icestick-uart/hdl/uart_tx.vhd
SOURCES_UTIL = \
	$(ROOT_DIR)/src/util/array_pkg.vhd \
	$(ROOT_DIR)/src/util/math_pkg.vhd \
	$(ROOT_DIR)/src/util/bram.vhd \
	$(ROOT_DIR)/src/util/bram_dual_port.vhd \
	$(ROOT_DIR)/src/util/brom.vhd \
	$(ROOT_DIR)/src/util/basic_counter.vhd \
	$(ROOT_DIR)/src/util/pixel_counter.vhd \
	$(ROOT_DIR)/src/util/adder_tree.vhd \
	$(ROOT_DIR)/src/util/serializer.vhd
SOURCES_WINDOW_CTRL = \
	$(ROOT_DIR)/src/window_ctrl/channel_repeater.vhd \
	$(ROOT_DIR)/src/window_ctrl/line_buffer.vhd \
	$(ROOT_DIR)/src/window_ctrl/window_buffer.vhd \
	$(ROOT_DIR)/src/window_ctrl/window_ctrl.vhd
SOURCES_BNN = \
	$(ROOT_DIR)/src/average_pooling.vhd \
	$(ROOT_DIR)/src/batch_normalization.vhd \
	$(ROOT_DIR)/src/convolution.vhd \
	$(ROOT_DIR)/src/window_convolution_activation.vhd \
	$(ROOT_DIR)/src/maximum_pooling.vhd \
	$(ROOT_DIR)/src/window_maximum_pooling.vhd \
	$(ROOT_DIR)/src/bnn.vhd \
	$(ROOT_DIR)/src/interface/bnn_uart.vhd

GHDL_FLAGS = --std=08

bnn.json: toplevel
	mkdir -p build/syn && \
	cd build/syn && \
	ghdl -a $(GHDL_FLAGS) --work=uart_lib $(SOURCES_UART) && \
	ghdl -a $(GHDL_FLAGS) --work=util $(SOURCES_UTIL) && \
	ghdl -a $(GHDL_FLAGS) --work=window_ctrl_lib $(SOURCES_WINDOW_CTRL) && \
	ghdl -a $(GHDL_FLAGS) --work=bnn_lib $(SOURCES_BNN) && \
	ghdl --synth $(GHDL_FLAGS) --work=bnn_lib bnn_uart && \
	yosys -m ghdl -p 'ghdl $(GHDL_FLAGS) --work=bnn_lib --no-formal bnn_uart; synth_ecp5 -abc9 -json bnn.json'
	
bnn_out.config: bnn.json
	cd build/syn && \
	nextpnr-ecp5 --85k --package CABGA381 --json bnn.json --lpf ../../syn/ulx3s_v20.lpf --textcfg bnn_out.config --lpf-allow-unconstrained

bnn.bit: bnn_out.config
	cd build/syn && \
	ecppack bnn_out.config bnn.bit

prog:
	fujprog build/syn/bnn.bit

clean:
	rm -rf sim/sim_build
	rm -rf build

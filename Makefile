format:
	vsg --configuration vsg_config.yaml --fix
	black .

sim:
	cd sim && pytest $(SIM_ARGS)
.PHONY: sim

toplevel:
	cd playground && python 04_custom_toplevel.py

ROOT_DIR = $(shell pwd)
SOURCES_UTIL = \
	$(ROOT_DIR)/src/util/array_pkg.vhd \
	$(ROOT_DIR)/src/util/math_pkg.vhd \
	$(ROOT_DIR)/src/util/bram.vhd \
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
	$(ROOT_DIR)/src/bnn.vhd

GHDL_FLAGS = --std=08

bnn.json: toplevel
	mkdir -p build/syn && \
	cd build/syn && \
	ghdl -a $(GHDL_FLAGS) --work=util $(SOURCES_UTIL) && \
	ghdl -a $(GHDL_FLAGS) --work=window_ctrl_lib $(SOURCES_WINDOW_CTRL) && \
	ghdl -a $(GHDL_FLAGS) --work=bnn_lib $(SOURCES_BNN) && \
	ghdl --synth $(GHDL_FLAGS) --work=bnn_lib bnn_uart && \
	yosys -m ghdl -p 'ghdl $(GHDL_FLAGS) --work=bnn_lib --no-formal bnn_uart; synth_ecp5 -abc9 -json bnn.json'
	
ulx3s_out.config: bnn.json
	cd build/syn && \
	export PYTHONHOME=/home/martin/anaconda3 && \
	export LD_LIBRARY_PATH=$(LD_LIBRARY_PATH):/home/martin/anaconda3/lib && \
	nextpnr-ecp5 --85k --package CABGA381 --json bnn.json --lpf ../../syn/ulx3s_v20.lpf --textcfg ulx3s_out.config

ulx3s.bit: ulx3s_out.config
	cd build/syn && \
	export PYTHONHOME=/home/martin/anaconda3 && \
	export LD_LIBRARY_PATH=$(LD_LIBRARY_PATH):/home/martin/anaconda3/lib && \
	ecppack ulx3s_out.config ulx3s.bit

prog:
	fujprog build/syn/ulx3s.bit

clean:
	rm -rf sim/sim_build
	rm -rf build

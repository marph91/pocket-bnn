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

syn: toplevel
	export PYTHONHOME=/home/martin/anaconda3 && \
	export LD_LIBRARY_PATH=$(LD_LIBRARY_PATH):/home/martin/anaconda3/lib && \
	mkdir -p build/syn && \
	cd build/syn && \
	ghdl -a $(GHDL_FLAGS) --work=util $(SOURCES_UTIL) && \
	ghdl -a $(GHDL_FLAGS) --work=window_ctrl_lib $(SOURCES_WINDOW_CTRL) && \
	ghdl -a $(GHDL_FLAGS) --work=cnn_lib $(SOURCES_BNN) && \
	ghdl --synth $(GHDL_FLAGS) --work=cnn_lib bnn && \
	yosys -m ghdl -p 'ghdl $(GHDL_FLAGS) --work=cnn_lib --no-formal bnn; synth_ecp5 -abc9 -json bnn.json' && \
	nextpnr-ecp5 --85k --package CABGA381 --json bnn.json
.PHONY: syn

clean:
	rm -rf sim/sim_build
	rm -rf build

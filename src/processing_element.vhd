
library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

library json;
  use json.json.all;

library cnn_lib;

library util;
  use util.math_pkg.all;

entity processing_element is
  generic (
    -- TODO: input bitwidth, for now = 1

    C_CONVOLUTION_KERNEL_SIZE : integer := 3;
    C_CONVOLUTION_STRIDE      : integer := 1;

    C_MAXIMUM_POOLING_KERNEL_SIZE : integer := 2;
    C_MAXIMUM_POOLING_STRIDE      : integer := 2;

    C_INPUT_CHANNEL  : integer := 8;
    C_OUTPUT_CHANNEL : integer := 8;

    C_IMG_WIDTH  : integer := 4;
    C_IMG_HEIGHT : integer := 4;

    C_WEIGHTS_FILE : string := "../sim/weights.json";
    C_LAYER_NAME   : string := "pe1"
  );
  port (
    isl_clk   : in    std_logic;
    isl_start : in    std_logic;
    isl_valid : in    std_logic;
    islv_data : in    std_logic_vector(7 downto 0);
    oslv_data : out   std_logic_vector(7 downto 0);
    osl_valid : out   std_logic
  );
end entity processing_element;

architecture behavioral of processing_element is

  signal sl_valid_convolution : std_logic := '0';
  signal slv_data_convolution : std_logic_vector(C_OUTPUT_CHANNEL - 1 downto 0);

  signal sl_valid_out : std_logic := '0';
  signal slv_data_out : std_logic_vector(oslv_data'range);

  -- constant C_JSON_CONTENT  : t_json    := jsonLoad(C_WEIGHTS_FILE);
  -- constant C_WEIGHTS : integer_vector := jsonGetIntegerArray(C_JSON_CONTENT, "weights"); -- TODO: C_LAYER_NAME
  -- constant C_THRESHOLDS : integer_vector := jsonGetIntegerArray(C_JSON_CONTENT, "thresholds");

  -- TODO: verify correct order

  function concatenate_integer_vector (input_vector : integer_vector; bitwidth : natural) return std_logic_vector is
    variable concatenated_integers : std_logic_vector(input_vector'length * bitwidth - 1 downto 0);
  begin
    report to_string(input_vector(0)) severity note;
    for index in input_vector'range loop
      concatenated_integers((index + 1) * bitwidth - 1 downto index * bitwidth) := std_logic_vector(to_unsigned(input_vector(index), bitwidth));
    end loop;
    return concatenated_integers;
  end function;

  -- TODO: Obtain bitwidths from json.
  constant C_TOTAL_INPUT_SIZE    : integer := C_CONVOLUTION_KERNEL_SIZE ** 2 * C_INPUT_CHANNEL;
  constant C_BITWIDTH_WEIGHTS    : integer := 1;
  constant C_BITWIDTH_THRESHOLDS : integer := log2(C_TOTAL_INPUT_SIZE + 1);
  -- signal slv_weights   : std_logic_vector(C_BITWIDTH_WEIGHTS * C_TOTAL_INPUT_SIZE * C_OUTPUT_CHANNEL - 1 downto 0) := concatenate_integer_vector(C_WEIGHTS, C_BITWIDTH_WEIGHTS);
  -- signal slv_threshold : std_logic_vector(C_BITWIDTH_THRESHOLDS * C_OUTPUT_CHANNEL - 1 downto 0) := concatenate_integer_vector(C_THRESHOLDS, C_BITWIDTH_THRESHOLDS);
  signal slv_weights   : std_logic_vector(C_BITWIDTH_WEIGHTS * C_TOTAL_INPUT_SIZE * C_OUTPUT_CHANNEL - 1 downto 0) := (others => '1');
  signal slv_threshold : std_logic_vector(C_BITWIDTH_THRESHOLDS * C_OUTPUT_CHANNEL - 1 downto 0) := (others => '0');

begin

  i_window_convolution_activation : entity cnn_lib.window_convolution_activation
    generic map (
      C_KERNEL_SIZE => C_CONVOLUTION_KERNEL_SIZE,
      C_STRIDE      => C_CONVOLUTION_STRIDE,

      C_INPUT_CHANNEL  => C_INPUT_CHANNEL,
      C_OUTPUT_CHANNEL => C_OUTPUT_CHANNEL,

      C_IMG_WIDTH  => C_IMG_WIDTH,
      C_IMG_HEIGHT => C_IMG_HEIGHT
    )
    port map (
      isl_clk        => isl_clk,
      isl_start      => isl_start,
      isl_valid      => isl_valid,
      islv_data      => islv_data,
      islv_weights   => slv_weights,
      islv_threshold => slv_threshold,
      oslv_data      => slv_data_convolution,
      osl_valid      => sl_valid_convolution
    );

  i_window_maximum_pooling : entity cnn_lib.window_maximum_pooling
    generic map (
      C_KERNEL_SIZE => C_CONVOLUTION_KERNEL_SIZE,
      C_STRIDE      => C_CONVOLUTION_STRIDE,

      C_CHANNEL => C_OUTPUT_CHANNEL,

      C_IMG_WIDTH  => C_IMG_WIDTH,
      C_IMG_HEIGHT => C_IMG_HEIGHT
    )
    port map (
      isl_clk   => isl_clk,
      isl_start => isl_start,
      isl_valid => sl_valid_convolution,
      islv_data => slv_data_convolution,
      oslv_data => slv_data_out,
      osl_valid => sl_valid_out
    );

  oslv_data <= slv_data_out;
  osl_valid <= sl_valid_out;

end architecture behavioral;

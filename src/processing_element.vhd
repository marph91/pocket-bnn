
library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

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
    C_IMG_HEIGHT : integer := 4
  );
  port (
    isl_clk        : in    std_logic;
    isl_start      : in    std_logic;
    isl_valid      : in    std_logic;
    islv_weights   : in    std_logic_vector(C_CONVOLUTION_KERNEL_SIZE ** 2 * C_INPUT_CHANNEL * C_OUTPUT_CHANNEL - 1 downto 0);
    islv_threshold : in    std_logic_vector(log2(C_CONVOLUTION_KERNEL_SIZE ** 2 * C_INPUT_CHANNEL + 1) * C_OUTPUT_CHANNEL - 1 downto 0);
    islv_data      : in    std_logic_vector(7 downto 0);
    oslv_data      : out   std_logic_vector(7 downto 0);
    osl_valid      : out   std_logic
  );
end entity processing_element;

architecture behavioral of processing_element is

  signal sl_valid_convolution : std_logic := '0';
  signal slv_data_convolution : std_logic_vector(C_OUTPUT_CHANNEL - 1 downto 0);

  signal sl_valid_out : std_logic := '0';
  signal slv_data_out : std_logic_vector(oslv_data'range);

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
      islv_weights   => islv_weights,
      islv_threshold => islv_threshold,
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

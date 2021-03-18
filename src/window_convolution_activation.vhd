
library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

library cnn_lib;

library util;
  use util.math_pkg.all;

library window_ctrl_lib;

entity window_convolution_activation is
  generic (
    -- TODO: input bitwidth, for now = 1

    C_KERNEL_SIZE : integer range 1 to 7 := 3;
    C_STRIDE      : integer              := 1;

    C_INPUT_CHANNEL           : integer               := 4;
    C_OUTPUT_CHANNEL          : integer               := 8;
    C_OUTPUT_CHANNEL_BITWIDTH : integer range 1 to 32 := 1;

    C_IMG_WIDTH  : integer := 4;
    C_IMG_HEIGHT : integer := 4
  );
  port (
    isl_clk   : in    std_logic;
    isl_start : in    std_logic;
    isl_valid : in    std_logic;
    islv_data : in    std_logic_vector(C_INPUT_CHANNEL - 1 downto 0);
    -- islv_weights and islv_threshold are constants
    islv_weights   : in    std_logic_vector(C_KERNEL_SIZE * C_KERNEL_SIZE * C_INPUT_CHANNEL * C_OUTPUT_CHANNEL - 1 downto 0);
    islv_threshold : in    std_logic_vector(C_OUTPUT_CHANNEL * log2(C_KERNEL_SIZE ** 2 * C_INPUT_CHANNEL + 1) - 1 downto 0);
    oslv_data      : out   std_logic_vector(C_OUTPUT_CHANNEL * C_OUTPUT_CHANNEL_BITWIDTH - 1 downto 0);
    osl_valid      : out   std_logic
  );
end entity window_convolution_activation;

architecture behavioral of window_convolution_activation is

  signal sl_valid_window_ctrl : std_logic := '0';
  signal slv_data_window_ctrl : std_logic_vector(C_KERNEL_SIZE * C_KERNEL_SIZE * C_INPUT_CHANNEL - 1 downto 0);

  signal slv_valid_convolution : std_logic_vector(C_OUTPUT_CHANNEL - 1 downto 0);

  type t_slv_array_1d is array(natural range <>) of std_logic_vector;

  constant C_POST_CONVOLUTION_BITWIDTH : integer := log2(C_KERNEL_SIZE ** 2 * C_INPUT_CHANNEL + 1);
  signal   a_data_convolution          : t_slv_array_1d(0 to C_OUTPUT_CHANNEL - 1)(C_POST_CONVOLUTION_BITWIDTH - 1 downto 0);

  signal slv_valid_batch_normalization : std_logic_vector(C_OUTPUT_CHANNEL - 1 downto 0);
  signal slv_data_batch_normalization  : std_logic_vector(C_OUTPUT_CHANNEL * C_OUTPUT_CHANNEL_BITWIDTH - 1 downto 0);
  signal a_data_batch_normalization    : t_slv_array_1d(0 to C_OUTPUT_CHANNEL - 1)(C_OUTPUT_CHANNEL_BITWIDTH - 1 downto 0);

  signal sl_valid_out : std_logic := '0';
  signal slv_data_out : std_logic_vector(oslv_data'range);

  signal a_weights   : t_slv_array_1d(0 to C_OUTPUT_CHANNEL - 1)(C_KERNEL_SIZE * C_KERNEL_SIZE * C_INPUT_CHANNEL - 1 downto 0);
  signal a_threshold : t_slv_array_1d(0 to C_OUTPUT_CHANNEL - 1)(C_POST_CONVOLUTION_BITWIDTH - 1 downto 0);

  function get_slice (vector: std_logic_vector; int_byte_index : natural; int_slice_size : natural) return std_logic_vector is
  begin
    return vector((int_byte_index + 1) * int_slice_size - 1 downto int_byte_index * int_slice_size);
  end function;

  function get_fastest_increment (vector: std_logic_vector; int_index : natural; int_slice_size : natural) return std_logic_vector is
    variable vector_out : std_logic_vector(vector'length / int_slice_size - 1 downto 0);
  begin
    for i in 0 to vector'length / int_slice_size - 1 loop
      vector_out(i) := vector(int_index + i * int_slice_size);
    end loop;
    return vector_out;
  end function;

begin

  i_window_ctrl : entity window_ctrl_lib.window_ctrl
    generic map (
      C_BITWIDTH    => 1 * C_INPUT_CHANNEL,
      C_CH_IN       => 1,
      C_CH_OUT      => 1,
      C_IMG_WIDTH   => C_IMG_WIDTH,
      C_IMG_HEIGHT  => C_IMG_HEIGHT,
      C_KERNEL_SIZE => C_KERNEL_SIZE,
      C_STRIDE      => C_STRIDE,
      C_PARALLEL_CH => 1
    )
    port map (
      isl_clk   => isl_clk,
      isl_start => isl_start,
      isl_valid => isl_valid,
      islv_data => islv_data,
      oslv_data => slv_data_window_ctrl,
      osl_valid => sl_valid_window_ctrl,
      osl_rdy   => open
    );

  gen_convolution : for output_channel in 0 to C_OUTPUT_CHANNEL - 1 generate

    i_convolution : entity cnn_lib.convolution
      generic map (
        C_KERNEL_SIZE   => C_KERNEL_SIZE,
        C_INPUT_CHANNEL => C_INPUT_CHANNEL
      )
      port map (
        isl_clk      => isl_clk,
        isl_valid    => sl_valid_window_ctrl,
        islv_data    => slv_data_window_ctrl,
        islv_weights => a_weights(output_channel),
        oslv_data    => a_data_convolution(output_channel),
        osl_valid    => slv_valid_convolution(output_channel)
      );

    -- output channel increments fastest
    a_weights(output_channel) <= get_fastest_increment(islv_weights, output_channel, C_OUTPUT_CHANNEL);

    gen_batch_normalization : if C_OUTPUT_CHANNEL_BITWIDTH = 1 generate

      i_batch_normalization : entity cnn_lib.batch_normalization
        generic map (
          C_POST_CONVOLUTION_BITWIDTH => C_POST_CONVOLUTION_BITWIDTH
        )
        port map (
          isl_clk        => isl_clk,
          isl_valid      => slv_valid_convolution(output_channel),
          islv_data      => a_data_convolution(output_channel),
          islv_threshold => a_threshold(output_channel),
          oslv_data      => a_data_batch_normalization(output_channel),
          osl_valid      => slv_valid_batch_normalization(output_channel)
        );

      -- TODO: output channel increments fastest, not slowest
      a_threshold(output_channel)                                                                                                          <= get_slice(islv_threshold, output_channel, C_POST_CONVOLUTION_BITWIDTH);
      slv_data_batch_normalization((output_channel + 1) * C_OUTPUT_CHANNEL_BITWIDTH - 1 downto output_channel * C_OUTPUT_CHANNEL_BITWIDTH) <= a_data_batch_normalization(output_channel);
    else generate
      slv_data_batch_normalization((output_channel + 1) * C_OUTPUT_CHANNEL_BITWIDTH - 1 downto output_channel * C_OUTPUT_CHANNEL_BITWIDTH) <= std_logic_vector(resize(unsigned(a_data_convolution(output_channel)), C_OUTPUT_CHANNEL_BITWIDTH));
      slv_valid_batch_normalization(output_channel)                                                                                        <= slv_valid_convolution(output_channel);
    end generate gen_batch_normalization;

  end generate gen_convolution;

  oslv_data <= slv_data_batch_normalization;
  osl_valid <= slv_valid_batch_normalization(0);

end architecture behavioral;

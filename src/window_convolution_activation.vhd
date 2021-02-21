
library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

library cnn_lib;

library window_ctrl_lib;

entity window_convolution_activation is
  generic (
    -- TODO: input bitwidth, for now = 1

    C_KERNEL_SIZE : integer range 2 to 3 := 2;
    C_STRIDE      : integer              := 1;

    C_INPUT_CHANNEL  : integer;
    C_OUTPUT_CHANNEL : integer;

    C_IMG_WIDTH  : integer;
    C_IMG_HEIGHT : integer;

    C_POST_CONVOLUTION_BITWIDTH : integer := 8
  );
  port (
    isl_clk   : in    std_logic;
    isl_start : in    std_logic;
    isl_valid : in    std_logic;
    islv_data : in    std_logic_vector(C_INPUT_CHANNEL - 1 downto 0);
    -- islv_weights and islv_threshold are constants
    islv_weights   : in    std_logic_vector(C_KERNEL_SIZE * C_KERNEL_SIZE * C_INPUT_CHANNEL * C_OUTPUT_CHANNEL - 1 downto 0);
    islv_threshold : in    std_logic_vector(C_POST_CONVOLUTION_BITWIDTH * C_OUTPUT_CHANNEL - 1 downto 0);
    oslv_data      : out   std_logic_vector(C_OUTPUT_CHANNEL - 1 downto 0);
    osl_valid      : out   std_logic
  );
end entity window_convolution_activation;

architecture behavioral of window_convolution_activation is

  signal sl_valid_window_ctrl : std_logic := '0';
  signal slv_data_window_ctrl : std_logic_vector(C_KERNEL_SIZE * C_KERNEL_SIZE * C_INPUT_CHANNEL - 1 downto 0);

  signal sl_valid_convolution : std_logic := '0';

  type t_slv_array_1d is array(natural range <>) of std_logic_vector;

  signal a_data_convolution : t_slv_array_1d(0 to C_OUTPUT_CHANNEL - 1)(C_POST_CONVOLUTION_BITWIDTH - 1 downto 0);

  signal sl_valid_batch_normalization : std_logic := '0';
  signal slv_data_batch_normalization : std_logic_vector(C_OUTPUT_CHANNEL * 1 - 1 downto 0);
  signal a_data_batch_normalization   : t_slv_array_1d(0 to C_OUTPUT_CHANNEL - 1)(1 - 1 downto 0);

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
        C_KERNEL_SIZE               => C_KERNEL_SIZE,
        C_INPUT_CHANNEL             => C_INPUT_CHANNEL,
        C_POST_CONVOLUTION_BITWIDTH => C_POST_CONVOLUTION_BITWIDTH
      )
      port map (
        isl_clk      => isl_clk,
        isl_valid    => sl_valid_window_ctrl,
        islv_data    => slv_data_window_ctrl,
        islv_weights => a_weights(output_channel),
        oslv_data    => a_data_convolution(output_channel),
        osl_valid    => sl_valid_convolution
      );

    -- TODO: output channel increments fastest, not slowest
    a_weights(output_channel) <= get_fastest_increment(islv_weights, output_channel, C_OUTPUT_CHANNEL);

    -- one batch normalization for each output channel
    i_batch_normalization : entity cnn_lib.batch_normalization
      generic map (
        C_POST_CONVOLUTION_BITWIDTH => C_POST_CONVOLUTION_BITWIDTH
      )
      port map (
        isl_clk        => isl_clk,
        isl_valid      => sl_valid_convolution,
        islv_data      => a_data_convolution(output_channel),
        islv_threshold => a_threshold(output_channel),
        oslv_data      => a_data_batch_normalization(output_channel),
        osl_valid      => sl_valid_batch_normalization
      );

    -- TODO: output channel increments fastest, not slowest
    a_threshold(output_channel)                                                          <= get_slice(islv_threshold, output_channel, C_POST_CONVOLUTION_BITWIDTH);
    slv_data_batch_normalization((output_channel + 1) * 1 - 1 downto output_channel * 1) <= a_data_batch_normalization(output_channel);
  end generate gen_convolution;

  oslv_data <= slv_data_batch_normalization;
  osl_valid <= sl_valid_batch_normalization;

end architecture behavioral;
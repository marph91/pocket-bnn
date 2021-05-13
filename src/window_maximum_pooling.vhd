
library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

library bnn_lib;

library window_ctrl_lib;

entity window_maximum_pooling is
  generic (
    C_KERNEL_SIZE : integer range 0 to 3 := 2;
    C_STRIDE      : integer              := 2;

    C_CHANNEL : integer;

    C_IMG_WIDTH  : integer;
    C_IMG_HEIGHT : integer
  );
  port (
    isl_clk   : in    std_logic;
    isl_start : in    std_logic;
    isl_valid : in    std_logic;
    islv_data : in    std_logic_vector(C_CHANNEL - 1 downto 0);
    oslv_data : out   std_logic_vector(C_CHANNEL - 1 downto 0);
    osl_valid : out   std_logic
  );
end entity window_maximum_pooling;

architecture behavioral of window_maximum_pooling is

  signal sl_valid_window_ctrl : std_logic := '0';
  signal slv_data_window_ctrl : std_logic_vector(C_KERNEL_SIZE * C_KERNEL_SIZE * C_CHANNEL - 1 downto 0);

  signal sl_valid_maximum_pooling : std_logic := '0';
  signal slv_data_maximum_pooling : std_logic_vector(oslv_data'range);

begin

  gen_no_maximum_pooling : if C_KERNEL_SIZE = 0 generate
    slv_data_maximum_pooling <= islv_data;
    sl_valid_maximum_pooling <= isl_valid;
  else generate

    i_window_ctrl : entity window_ctrl_lib.window_ctrl
      generic map (
        C_BITWIDTH    => C_CHANNEL * 1,
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

    i_maximum_pooling : entity bnn_lib.maximum_pooling
      generic map (
        C_KERNEL_SIZE => C_KERNEL_SIZE,
        C_CHANNEL     => C_CHANNEL
      )
      port map (
        isl_clk   => isl_clk,
        isl_valid => sl_valid_window_ctrl,
        islv_data => slv_data_window_ctrl,
        oslv_data => slv_data_maximum_pooling,
        osl_valid => sl_valid_maximum_pooling
      );

  end generate gen_no_maximum_pooling;

  oslv_data <= slv_data_maximum_pooling;
  osl_valid <= sl_valid_maximum_pooling;

end architecture behavioral;

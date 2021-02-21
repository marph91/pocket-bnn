
library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

library cnn_lib;

entity processing_element is
  generic (
    -- TODO: input bitwidth, for now = 1

    C_KERNEL_SIZE   : integer range 2 to 3 := 2;
    C_INPUT_CHANNEL : integer;
    -- C_OUTPUT_CHANNEL : integer; --> 1 output channel

    C_POST_CONVOLUTION_BITWIDTH : integer := 8
  );
  port (
    isl_clk   : in    std_logic;
    isl_valid : in    std_logic;
    islv_data : in    std_logic_vector(7 downto 0);
    oslv_data : out   std_logic_vector(7 downto 0);
    osl_valid : out   std_logic
  );
end entity processing_element;

architecture behavioral of processing_element is

  signal sl_add                    : std_logic := '0';
  signal slv_multiplication_result : std_logic_vector(islv_data'range);

  signal sl_valid_out : std_logic := '0';
  signal slv_data_out : std_logic_vector(oslv_data'range);

begin

  proc_processing_element : process (isl_clk) is
  begin

    if (rising_edge(isl_clk)) then
      -- window_convolution_activation
      -- window_maximum_pooling
    end if;

  end process proc_processing_element;

  oslv_data <= slv_data_out;
  osl_valid <= sl_valid_out;

end architecture behavioral;

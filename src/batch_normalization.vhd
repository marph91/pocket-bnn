
library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

-- basically the simple threshold replaces batch normalization + ReLU
-- The threshold is calculated at synthesis time by using the batch norm parameters.

entity batch_normalization is
  generic (
    C_POST_CONVOLUTION_BITWIDTH : integer := 8
  );
  port (
    isl_clk        : in    std_logic;
    isl_valid      : in    std_logic;
    islv_data      : in    std_logic_vector(C_POST_CONVOLUTION_BITWIDTH - 1 downto 0);
    islv_threshold : in    std_logic_vector(C_POST_CONVOLUTION_BITWIDTH - 1 downto 0);
    oslv_data      : out   std_logic_vector(0 downto 0);
    osl_valid      : out   std_logic
  );
end entity batch_normalization;

architecture behavioral of batch_normalization is

  signal sl_valid_out : std_logic := '0';
  signal slv_data_out : std_logic_vector(oslv_data'range);

begin

  proc_batch_normalization : process (isl_clk) is
  begin

    if (rising_edge(isl_clk)) then
      sl_valid_out    <= '0';
      slv_data_out(0) <= '0';

      if (isl_valid = '1') then
        if (unsigned(islv_data) > unsigned(islv_threshold)) then
          slv_data_out(0) <= '1';
        end if;

        sl_valid_out <= '1';
      end if;
    end if;

  end process proc_batch_normalization;

  oslv_data <= slv_data_out;
  osl_valid <= sl_valid_out;

end architecture behavioral;

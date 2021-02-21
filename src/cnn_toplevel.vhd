
library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity cnn is
  port (
    isl_clk   : in    std_logic;
    isl_valid : in    std_logic;
    islv_data : in    std_logic_vector(7 downto 0);
    oslv_data : out   std_logic_vector(7 downto 0);
    osl_valid : out   std_logic
  );
end entity cnn;

architecture behavioral of cnn is

  signal sl_add                    : std_logic := '0';
  signal slv_multiplication_result : std_logic_vector(islv_data'range);

  signal sl_valid_out : std_logic := '0';
  signal slv_data_out : std_logic_vector(oslv_data'range);

begin

  proc_cnn : process (isl_clk) is
  begin

    if (rising_edge(isl_clk)) then
      -- loop processing elements
      -- average pooling/fc
    end if;

  end process proc_cnn;

  oslv_data <= slv_data_out;
  osl_valid <= sl_valid_out;

end architecture behavioral;

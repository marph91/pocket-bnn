
library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity brom is
  generic (
    C_DATA_WIDTH : integer                                                    := 8;
    C_ADDR_WIDTH : integer                                                    := 9;
    C_INIT_VALUE : std_logic_vector(C_ADDR_WIDTH * C_DATA_WIDTH - 1 downto 0) := (others => '1')
  );
  port (
    islv_addr : in    std_logic_vector(C_ADDR_WIDTH - 1 downto 0);
    oslv_data : out   std_logic_vector(C_DATA_WIDTH - 1 downto 0)
  );
end entity brom;

architecture behavioral of brom is

begin

  proc_bram : process (islv_addr) is

    variable int_addr : integer range 0 to 2 ** C_ADDR_WIDTH - 1;

  begin

    int_addr := to_integer(unsigned(islv_addr));
    oslv_data <= C_INIT_VALUE((int_addr + 1) * C_DATA_WIDTH - 1 downto int_addr * C_DATA_WIDTH);

  end process proc_bram;

end architecture behavioral;

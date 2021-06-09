
library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity bram_dual_port is
  generic (
    C_DATA_WIDTH : integer := 8;
    C_ADDR_WIDTH : integer := 9
  );
  port (
    isl_wclk   : in    std_logic;
    isl_rclk   : in    std_logic;
    isl_we     : in    std_logic;
    islv_waddr : in    std_logic_vector(C_ADDR_WIDTH - 1 downto 0);
    islv_data  : in    std_logic_vector(C_DATA_WIDTH - 1 downto 0);
    islv_raddr : in    std_logic_vector(C_ADDR_WIDTH - 1 downto 0);
    oslv_data  : out   std_logic_vector(C_DATA_WIDTH - 1 downto 0)
  );
end entity bram_dual_port;

architecture behavioral of bram_dual_port is

  type t_ram is array(0 to 2 ** C_ADDR_WIDTH - 1) of std_logic_vector(C_DATA_WIDTH - 1 downto 0);

  signal a_ram : t_ram;

begin

  proc_write : process (isl_wclk) is
  begin

    if (rising_edge(isl_wclk)) then
      if (isl_we = '1') then
        a_ram(to_integer(unsigned(islv_waddr))) <= islv_data;
      end if;
    end if;

  end process proc_write;

  proc_read : process (isl_rclk) is
  begin

    if (rising_edge(isl_rclk)) then
      oslv_data <= a_ram(to_integer(unsigned(islv_raddr)));
    end if;

  end process proc_read;

end architecture behavioral;

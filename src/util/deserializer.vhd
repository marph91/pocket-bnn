library ieee;
  use ieee.std_logic_1164.all;

entity deserializer is
  generic (
    C_DATA_COUNT    : integer := 4;
    C_DATA_BITWIDTH : integer := 8
  );
  port (
    isl_clk   : in    std_logic;
    isl_valid : in    std_logic;
    islv_data : in    std_logic_vector(C_DATA_BITWIDTH - 1 downto 0);
    oslv_data : out   std_logic_vector(C_DATA_COUNT * C_DATA_BITWIDTH - 1 downto 0);
    osl_valid : out   std_logic
  );
end entity deserializer;

architecture rtl of deserializer is

  signal int_input_count : integer range 0 to C_DATA_COUNT - 1 := 0;
  signal slv_data_out    : std_logic_vector(oslv_data'range) := (others => '0');
  signal sl_valid_out    : std_logic := '0';

begin

  proc_deserializer : process (isl_clk) is
  begin

    if (rising_edge(isl_clk)) then
      sl_valid_out <= '0';

      if (isl_valid = '1') then
        slv_data_out <= islv_data & slv_data_out(slv_data_out'high downto C_DATA_BITWIDTH);

        if (int_input_count /= C_DATA_COUNT - 1) then
          int_input_count <= int_input_count + 1;
        else
          int_input_count <= 0;
          sl_valid_out    <= '1';
        end if;
      end if;
    end if;

  end process proc_deserializer;

  osl_valid <= sl_valid_out;
  oslv_data <= slv_data_out;

end architecture rtl;

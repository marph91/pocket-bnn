library ieee;
  use ieee.std_logic_1164.all;

entity serializer is
  generic (
    C_DATA_COUNT    : integer := 4;
    C_DATA_BITWIDTH : integer := 8
  );
  port (
    isl_clk   : in    std_logic;
    isl_valid : in    std_logic;
    islv_data : in    std_logic_vector(C_DATA_COUNT * C_DATA_BITWIDTH - 1 downto 0);
    oslv_data : out   std_logic_vector(C_DATA_BITWIDTH - 1 downto 0);
    osl_valid : out   std_logic
  );
end entity serializer;

architecture rtl of serializer is

  type t_data is array (0 to C_DATA_COUNT - 1) of std_logic_vector(C_DATA_BITWIDTH - 1 downto 0);

  signal a_data : t_data;

  signal int_output_valid_cycles : integer range 0 to C_DATA_COUNT;

  function get_slice (vector: std_logic_vector; int_byte_index : natural; int_slice_size : natural) return std_logic_vector is
  begin
    return vector((int_byte_index + 1) * int_slice_size - 1 downto int_byte_index * int_slice_size);
  end function;

begin

  proc_serializer : process (isl_clk) is
  begin

    if (rising_edge(isl_clk)) then
      a_data <= a_data(1 to a_data'high) & a_data(0);

      if (isl_valid = '1') then
        assert int_output_valid_cycles = 0;
        int_output_valid_cycles <= C_DATA_COUNT;
        for i in a_data'range loop
          a_data(i)             <= get_slice(islv_data, i, C_DATA_BITWIDTH);
        end loop;
      end if;

      if (int_output_valid_cycles > 0) then
        int_output_valid_cycles <= int_output_valid_cycles - 1;
      end if;
    end if;

  end process proc_serializer;

  osl_valid <= '1' when int_output_valid_cycles > 0 else
               '0';
  oslv_data <= a_data(0);

end architecture rtl;


library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity convolution is
  generic (
    -- TODO: input bitwidth, for now = 1

    C_KERNEL_SIZE   : integer range 2 to 7 := 2;
    C_INPUT_CHANNEL : integer              := 1;

    C_POST_CONVOLUTION_BITWIDTH : integer := 8
  );
  port (
    isl_clk   : in    std_logic;
    isl_valid : in    std_logic;
    islv_data : in    std_logic_vector(C_KERNEL_SIZE * C_KERNEL_SIZE * C_INPUT_CHANNEL - 1 downto 0);
    -- maybe weights + 1 for bias
    islv_weights : in    std_logic_vector(C_KERNEL_SIZE * C_KERNEL_SIZE * C_INPUT_CHANNEL - 1 downto 0);
    oslv_data    : out   std_logic_vector(C_POST_CONVOLUTION_BITWIDTH - 1 downto 0);
    osl_valid    : out   std_logic
  );
end entity convolution;

architecture behavioral of convolution is

  signal sl_add                    : std_logic := '0';
  signal slv_multiplication_result : std_logic_vector(islv_data'range);

  signal sl_valid_out : std_logic := '0';
  signal slv_data_out : std_logic_vector(oslv_data'range);

begin

  proc_convolution : process (isl_clk) is

    -- TODO: log2(islv_data'range)
    variable usig_ones_count : unsigned(oslv_data'range);

  begin

    if (rising_edge(isl_clk)) then
      sl_valid_out <= '0';
      sl_add       <= '0';

      if (isl_valid = '1') then
        -- or map directly to hardware (islv_weights as constant)
        slv_multiplication_result <= islv_data xnor islv_weights;

        sl_add <= '1';
      end if;

      if (sl_add = '1') then
        usig_ones_count := (others => '0');
        for i in slv_multiplication_result'range loop
          if (slv_multiplication_result(i) = '1') then
            usig_ones_count := usig_ones_count + 1;
          end if;
        end loop;

        slv_data_out <= std_logic_vector(usig_ones_count);
        sl_valid_out <= '1';
      end if;
    end if;

  end process proc_convolution;

  oslv_data <= slv_data_out;
  osl_valid <= sl_valid_out;

end architecture behavioral;

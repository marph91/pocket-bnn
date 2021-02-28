
library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;
  use ieee.math_real.all;

library util;
  use util.math_pkg.all;

entity convolution is
  generic (
    -- TODO: input bitwidth, for now = 1

    C_KERNEL_SIZE   : integer range 1 to 7 := 3;
    C_INPUT_CHANNEL : integer              := 1
  );
  port (
    isl_clk   : in    std_logic;
    isl_valid : in    std_logic;
    islv_data : in    std_logic_vector(C_KERNEL_SIZE * C_KERNEL_SIZE * C_INPUT_CHANNEL - 1 downto 0);
    -- maybe weights + 1 for bias
    islv_weights : in    std_logic_vector(C_KERNEL_SIZE * C_KERNEL_SIZE * C_INPUT_CHANNEL - 1 downto 0);
    oslv_data    : out   std_logic_vector(log2(C_KERNEL_SIZE * C_KERNEL_SIZE * C_INPUT_CHANNEL + 1) - 1 downto 0);
    osl_valid    : out   std_logic
  );
end entity convolution;

architecture behavioral of convolution is

  function find_best_parallelity return integer is
  begin

    if (C_INPUT_CHANNEL > C_KERNEL_SIZE) then
      if (C_INPUT_CHANNEL mod 4 = 0) then
        if (C_INPUT_CHANNEL mod 8 = 0) then
          if (C_INPUT_CHANNEL mod 16 = 0) then
            return 16;
          end if;
          return 8;
        end if;
        return 4;
      end if;
    end if;

    return C_KERNEL_SIZE;
  end function find_best_parallelity;

  constant C_PARALLEL_POPCOUNT : integer := find_best_parallelity;
  constant C_SPLIT             : integer := integer(ceil(real(islv_data'length) / real(C_PARALLEL_POPCOUNT)));

  type t_ones_count is array(natural range<>) of unsigned(oslv_data'range);

  signal a_ones_count : t_ones_count(0 to C_SPLIT);

  signal sl_add                    : std_logic := '0';
  signal sl_popcount               : std_logic := '0';
  signal slv_multiplication_result : std_logic_vector(islv_data'range);

  signal sl_valid_out : std_logic := '0';
  signal slv_data_out : std_logic_vector(oslv_data'range);

begin

  proc_convolution : process (isl_clk) is

    variable v_usig_popcount       : unsigned(oslv_data'range);
    variable v_usig_popcount_total : unsigned(oslv_data'range);

  begin

    if (rising_edge(isl_clk)) then
      assert (C_INPUT_CHANNEL mod C_PARALLEL_POPCOUNT = 0) or
        (C_KERNEL_SIZE mod C_PARALLEL_POPCOUNT = 0) severity failure;

      sl_popcount  <= '0';
      sl_add       <= '0';
      sl_valid_out <= '0';

      if (isl_valid = '1') then
        -- or map directly to hardware (islv_weights as constant)
        slv_multiplication_result <= islv_data xnor islv_weights;
        a_ones_count              <= (others => (others => '0'));
        sl_popcount               <= '1';
      end if;

      -- TODO: The split/adder can be improved.
      if (sl_popcount = '1') then
        for split in 0 to C_SPLIT - 1 loop
          v_usig_popcount := (others => '0');
          for i in 0 to C_PARALLEL_POPCOUNT - 1 loop
            if (slv_multiplication_result(i + split * C_PARALLEL_POPCOUNT) = '1') then
              v_usig_popcount := v_usig_popcount + 1;
            end if;
          end loop;
          a_ones_count(split) <= v_usig_popcount;
        end loop;

        sl_add <= '1';
      end if;

      if (sl_add = '1') then
        v_usig_popcount_total   := (others => '0');
        for split in 0 to C_SPLIT - 1 loop
          v_usig_popcount_total := v_usig_popcount_total + a_ones_count(split);
        end loop;

        sl_valid_out <= '1';
        slv_data_out <= std_logic_vector(v_usig_popcount_total);
      end if;
    end if;

  end process proc_convolution;

  oslv_data <= slv_data_out;
  osl_valid <= sl_valid_out;

end architecture behavioral;

library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;
  use ieee.math_real.all;

library util;
  use util.array_pkg.all;

entity adder_tree is
  generic (
    C_INPUT_COUNT     : integer              := 4;
    C_INPUT_BITWIDTH  : integer              := 8;
    C_UNSIGNED        : integer range 0 to 1 := 1;
    C_OUTPUT_BITWIDTH : integer              := 8
  );
  port (
    isl_clk   : in    std_logic;
    isl_valid : in    std_logic;
    islv_data : in    std_logic_vector(C_INPUT_COUNT * C_INPUT_BITWIDTH - 1 downto 0);
    oslv_data : out   std_logic_vector(C_OUTPUT_BITWIDTH - 1 downto 0);
    osl_valid : out   std_logic
  );
end entity adder_tree;

architecture rtl of adder_tree is

  constant C_STAGES             : integer := integer(ceil(log2(real(C_INPUT_COUNT))));
  constant C_INPUTS_FIRST_STAGE : integer := 2 ** C_STAGES;

  -- Stage of the adder tree.
  signal slv_sum_stage : std_logic_vector(C_STAGES downto 0) := (others => '0');

  -- Pipelined sum.
  -- For example C_INPUTS_FIRST_STAGE = 8:
  -- stage 1: a_sums(0 to 7)
  -- stage 2: a_sums(8 to 11)
  -- stage 3: a_sums(12 to 13)
  -- stage 4: a_sums(14) -> final sum

  type t_sums is array (natural range <>) of signed(C_OUTPUT_BITWIDTH + C_UNSIGNED - 1 downto 0);

  signal a_sums : t_sums(0 to 2 * C_INPUTS_FIRST_STAGE - 1);

  function convert_input (input_vector : std_logic_vector) return t_sums is
    variable v_sum_init    : t_sums(0 to C_INPUTS_FIRST_STAGE - 1);
    variable v_input_datum : std_logic_vector(C_INPUT_BITWIDTH - 1 downto 0);
  begin
    v_sum_init := (others => (others => '0'));

    -- Pad with zeros to widen from input bitwidth to output bitwidth.
    assert C_OUTPUT_BITWIDTH >= C_INPUT_BITWIDTH + C_STAGES; -- Input gets extended by 1 bit at each stage.
    v_input_datum := (others => '0');

    for i in 0 to C_INPUT_COUNT - 1 loop

      v_input_datum := get_slice(input_vector, i, C_INPUT_BITWIDTH);

      if (C_UNSIGNED = 1) then
        -- Pad a zero (sign) bit in case of unsigned input.
        v_sum_init(i) := resize(signed('0' & v_input_datum), v_sum_init(0)'length);
      else
        v_sum_init(i) := resize(signed(v_input_datum), v_sum_init(0)'length);
      end if;

    end loop;
    return v_sum_init;
  end function convert_input;

begin

  proc_adder_tree : process (isl_clk) is

    variable v_current_index : integer range 0 to a_sums'length;

  begin

    if (rising_edge(isl_clk)) then
      slv_sum_stage                         <= slv_sum_stage(slv_sum_stage'high - 1 downto 0) & isl_valid;
      a_sums(0 to C_INPUTS_FIRST_STAGE - 1) <= convert_input(islv_data);

      v_current_index := 0;
      for i in slv_sum_stage'reverse_range loop
        if (slv_sum_stage(i) = '1') then
          for j in 0 to 2 ** (C_STAGES - i) / 2 - 1 loop
            a_sums(v_current_index + 2 ** (C_STAGES - i) + j) <= a_sums(v_current_index + 2 * j) +
                                                                 a_sums(v_current_index + 2 * j + 1);
          end loop;
        end if;
        v_current_index := v_current_index + 2 ** (C_STAGES - i);
      end loop;
    end if;

  end process proc_adder_tree;

  osl_valid <= slv_sum_stage(slv_sum_stage'high);
  oslv_data <= std_logic_vector(a_sums(a_sums'high - 1)(C_OUTPUT_BITWIDTH - 1 downto 0));

end architecture rtl;


library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;
  use ieee.math_real.all;

library util;
  use util.math_pkg.all;

entity convolution is
  generic (
    C_KERNEL_SIZE            : integer range 1 to 7 := 3;
    C_INPUT_CHANNEL          : integer              := 1;
    C_INPUT_CHANNEL_BITWIDTH : integer              := 1
  );
  port (
    isl_clk      : in    std_logic;
    isl_valid    : in    std_logic;
    islv_data    : in    std_logic_vector(C_KERNEL_SIZE * C_KERNEL_SIZE * C_INPUT_CHANNEL * C_INPUT_CHANNEL_BITWIDTH - 1 downto 0);
    islv_weights : in    std_logic_vector(C_KERNEL_SIZE * C_KERNEL_SIZE * C_INPUT_CHANNEL - 1 downto 0);
    oslv_data    : out   std_logic_vector(log2(C_KERNEL_SIZE * C_KERNEL_SIZE * C_INPUT_CHANNEL * C_INPUT_CHANNEL_BITWIDTH + 1) - 1 downto 0);
    osl_valid    : out   std_logic
  );
end entity convolution;

architecture behavioral of convolution is

  constant C_PARALLEL_POPCOUNT : integer := 4;
  constant C_SPLIT             : integer := integer(ceil(real(islv_data'length) / real(C_PARALLEL_POPCOUNT)));
  constant C_PADDED_BITWIDTH   : integer := C_PARALLEL_POPCOUNT * C_SPLIT;

  signal sl_add       : std_logic := '0';
  signal sl_popcount  : std_logic := '0';
  signal slv_product  : std_logic_vector(C_PADDED_BITWIDTH - 1 downto 0) := (others => '0');
  signal slv_popcount : std_logic_vector(C_SPLIT * 3 - 1 downto 0);

  signal sl_valid_out : std_logic := '0';
  signal slv_data_out : std_logic_vector(oslv_data'range);

begin

  i_adder_tree : entity util.adder_tree
    generic map (
      C_INPUT_COUNT     => C_SPLIT,
      C_INPUT_BITWIDTH  => 3,
      C_OUTPUT_BITWIDTH => oslv_data'length
    )
    port map (
      isl_clk   => isl_clk,
      isl_valid => sl_add,
      islv_data => slv_popcount,
      oslv_data => slv_data_out,
      osl_valid => sl_valid_out
    );

  gen_matrix_multiplication : if C_INPUT_CHANNEL_BITWIDTH = 1 generate

    proc_xnor_popcount : process (isl_clk) is

      variable v_usig_popcount       : unsigned(2 downto 0);
      variable v_usig_popcount_total : unsigned(oslv_data'range);

    begin

      if (rising_edge(isl_clk)) then
        sl_popcount <= '0';
        sl_add      <= '0';

        if (isl_valid = '1') then
          -- or map directly to hardware (islv_weights as constant)
          -- pad zeros for the adder tree
          slv_product <= (islv_data xnor islv_weights) & (slv_product'length - islv_data'length - 1 downto 0 => '0');
          sl_popcount <= '1';
        end if;

        -- If using bram, one would be needed for each adder stage.
        if (sl_popcount = '1') then
          for slice in 0 to slv_product'length / C_PARALLEL_POPCOUNT - 1 loop
            v_usig_popcount := (others => '0');
            for i in 0 to C_PARALLEL_POPCOUNT - 1 loop
              if (slv_product(i + slice * C_PARALLEL_POPCOUNT) = '1') then
                v_usig_popcount := v_usig_popcount + 1;
              end if;
            end loop;
            slv_popcount((slice + 1) * 3 - 1 downto slice * 3) <= std_logic_vector(v_usig_popcount);
          end loop;

          sl_add <= '1';
        end if;
      end if;

    end process proc_xnor_popcount;

  else generate

    gen_input : for input_channel in 0 to C_INPUT_CHANNEL - 1 generate

      proc_add_sign : process (isl_clk) is

        variable v_usig_popcount       : unsigned(2 downto 0);
        variable v_usig_popcount_total : unsigned(oslv_data'range);

      begin

        if (rising_edge(isl_clk)) then
          sl_popcount <= '0';
          sl_add      <= '0';

          if (isl_valid = '1') then
            -- islv_data * +-1
            -- assign slices to adder tree
            -- extend adder tree by signed addition
            sl_add <= '1';
          end if;
        end if;

      end process proc_add_sign;

    end generate gen_input;

  end generate gen_matrix_multiplication;

  oslv_data <= slv_data_out;
  osl_valid <= sl_valid_out;

end architecture behavioral;

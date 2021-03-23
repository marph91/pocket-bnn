
library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;
  use ieee.math_real.all;

library util;
  use util.array_pkg.all;
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
    islv_data    : in    std_logic_vector(C_KERNEL_SIZE ** 2 * C_INPUT_CHANNEL * C_INPUT_CHANNEL_BITWIDTH - 1 downto 0);
    islv_weights : in    std_logic_vector(C_KERNEL_SIZE ** 2 * C_INPUT_CHANNEL - 1 downto 0);
    oslv_data    : out   std_logic_vector(C_INPUT_CHANNEL_BITWIDTH + log2(C_KERNEL_SIZE ** 2 * C_INPUT_CHANNEL + 1) downto 0);
    osl_valid    : out   std_logic
  );
end entity convolution;

architecture behavioral of convolution is

  signal sl_valid_out : std_logic := '0';
  signal slv_data_out : std_logic_vector(oslv_data'range);

begin

  gen_matrix_multiplication : if C_INPUT_CHANNEL_BITWIDTH = 1 generate
    constant C_PARALLEL_POPCOUNT       : integer := 4;
    constant C_SPLIT                   : integer := integer(ceil(real(islv_data'length) / real(C_PARALLEL_POPCOUNT)));
    constant C_INPUT_BITWIDTH_ADDER    : integer := log2(C_PARALLEL_POPCOUNT + 1);
    constant C_PADDED_BITWIDTH_PRODUCT : integer := C_PARALLEL_POPCOUNT * C_SPLIT;

    signal sl_add       : std_logic := '0';
    signal sl_popcount  : std_logic := '0';
    signal slv_product  : std_logic_vector(C_PADDED_BITWIDTH_PRODUCT - 1 downto 0) := (others => '0');
    signal slv_popcount : std_logic_vector(C_SPLIT * C_INPUT_BITWIDTH_ADDER - 1 downto 0);

    signal slv_data_adder : std_logic_vector(C_INPUT_BITWIDTH_ADDER + log2(C_KERNEL_SIZE ** 2 * C_INPUT_CHANNEL + 1) - 1 downto 0);
  begin

    proc_xnor_popcount : process (isl_clk) is

      variable v_usig_popcount : unsigned(2 downto 0);

    begin

      report to_string(slv_data_out'length) & " " & to_string(slv_data_adder'length);

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
            slv_popcount((slice + 1) * C_INPUT_BITWIDTH_ADDER - 1 downto slice * C_INPUT_BITWIDTH_ADDER) <= std_logic_vector(v_usig_popcount);
          end loop;

          sl_add <= '1';
        end if;
      end if;

    end process proc_xnor_popcount;

    i_adder_tree : entity util.adder_tree
      generic map (
        C_INPUT_COUNT     => C_SPLIT,
        C_INPUT_BITWIDTH  => C_INPUT_BITWIDTH_ADDER,
        C_OUTPUT_BITWIDTH => slv_data_adder'length
      )
      port map (
        isl_clk   => isl_clk,
        isl_valid => sl_add,
        islv_data => slv_popcount,
        oslv_data => slv_data_adder,
        osl_valid => sl_valid_out
      );

    -- Adder output is unsigned, output is signed.
    -- Adder output has to big bitwidth, because of the grouping. It can be resized.
    slv_data_out <= std_logic_vector(resize(signed('0' & slv_data_adder), slv_data_out'length));

  else generate
    -- + 1, because of multiplication by +-1
    constant C_PRODUCT_BITWIDTH : integer := C_INPUT_CHANNEL_BITWIDTH + 1;
    signal   sl_add             : std_logic := '0';
    signal   slv_product        : std_logic_vector(C_KERNEL_SIZE ** 2 * C_INPUT_CHANNEL * C_PRODUCT_BITWIDTH - 1 downto 0);

  begin

    gen_input : for input_channel in 0 to C_INPUT_CHANNEL - 1 generate

      proc_add_sign : process (isl_clk) is

        variable v_int_index        : integer;
        variable v_slv_input_datum  : std_logic_vector(C_PRODUCT_BITWIDTH - 1 downto 0);
        variable v_slv_output_datum : std_logic_vector(C_PRODUCT_BITWIDTH - 1 downto 0);

      begin

        if (rising_edge(isl_clk)) then
          sl_add <= '0';

          if (isl_valid = '1') then
            for ch in 0 to C_INPUT_CHANNEL - 1 loop
              for k in 0 to C_KERNEL_SIZE ** 2 - 1 loop
                v_int_index       := k + ch * C_KERNEL_SIZE ** 2;
                v_slv_input_datum := '0' & get_slice(islv_data, v_int_index, C_PRODUCT_BITWIDTH - 1);
                -- Calculate product, i. e. input data * +-1
                if (islv_weights(v_int_index) = '1') then
                  v_slv_output_datum := v_slv_input_datum;
                else
                  v_slv_output_datum := std_logic_vector(-signed(v_slv_input_datum));
                end if;
                slv_product((v_int_index + 1) * C_PRODUCT_BITWIDTH - 1 downto v_int_index * C_PRODUCT_BITWIDTH) <= v_slv_output_datum;
              end loop;
            end loop;
            sl_add                                                                                              <= '1';
          end if;
        end if;

      end process proc_add_sign;

      i_adder_tree : entity util.adder_tree
        generic map (
          C_INPUT_COUNT     => C_KERNEL_SIZE ** 2 * C_INPUT_CHANNEL,
          C_INPUT_BITWIDTH  => C_PRODUCT_BITWIDTH,
          C_UNSIGNED        => 0,
          C_OUTPUT_BITWIDTH => oslv_data'length
        )
        port map (
          isl_clk   => isl_clk,
          isl_valid => sl_add,
          islv_data => slv_product,
          oslv_data => slv_data_out,
          osl_valid => sl_valid_out
        );

    end generate gen_input;

  end generate gen_matrix_multiplication;

  oslv_data <= slv_data_out;
  osl_valid <= sl_valid_out;

end architecture behavioral;


library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

library util;
  use util.array_pkg.all;
  use util.math_pkg.all;

entity line_buffer is
  generic (
    C_BITWIDTH : integer := 8;

    C_CH        : integer range 1 to 1024 := 16;
    C_IMG_WIDTH : integer range 1 to 2048 := 20;

    C_KERNEL_SIZE : integer range 1 to 7 := 3
  );
  port (
    isl_clk   : in    std_logic;
    isl_valid : in    std_logic;
    islv_data : in    std_logic_vector(C_BITWIDTH - 1 downto 0);
    oa_data   : out   t_slv_array_1d(0 to C_KERNEL_SIZE - 1)(C_BITWIDTH - 1 downto 0);
    osl_valid : out   std_logic
  );
end entity line_buffer;

architecture ram of line_buffer is

  -- Save the image rows in lutram or blockram.

  constant C_BRAM_SIZE       : integer := C_IMG_WIDTH * C_CH - 1;
  constant C_BRAM_DATA_WIDTH : integer := (C_KERNEL_SIZE - 1) * C_BITWIDTH;

  signal sl_valid_out : std_logic := '0';
  signal a_data_out   : t_slv_array_1d(0 to C_KERNEL_SIZE - 1)(C_BITWIDTH - 1 downto 0) := (others => (others => '0'));

  signal   usig_addr_cnt     : unsigned(log2(C_BRAM_SIZE - 1) - 1 downto 0) := (others => '0');
  constant C_BRAM_ADDR_WIDTH : integer := usig_addr_cnt'LENGTH;

  signal sl_bram_en        : std_logic;
  signal slv_bram_data_in  : std_logic_vector(C_BRAM_DATA_WIDTH - 1 downto 0);
  signal slv_bram_data_out : std_logic_vector(C_BRAM_DATA_WIDTH - 1 downto 0);

begin

  i_bram : entity util.bram
    generic map (
      C_DATA_WIDTH => C_BRAM_DATA_WIDTH,
      C_ADDR_WIDTH => C_BRAM_ADDR_WIDTH
    )
    port map (
      isl_clk   => isl_clk,
      isl_en    => sl_bram_en,
      isl_we    => '1',
      islv_addr => std_logic_vector(usig_addr_cnt),
      islv_data => slv_bram_data_in,
      oslv_data => slv_bram_data_out
    );

  -- incoming data is written to BRAM and also output
  slv_bram_data_in(C_BITWIDTH - 1 downto 0) <= islv_data;
  sl_bram_en                                <= isl_valid;

  -- move data one line "down"

  gen_bram_input : for i in 0 to (C_KERNEL_SIZE - 3) generate
    -- TODO: Use assign_slice and get_slice.
    slv_bram_data_in((C_BITWIDTH - 1) + (i + 1) * C_BITWIDTH downto (i + 1) * C_BITWIDTH)
 <= slv_bram_data_out((C_BITWIDTH - 1) + i * C_BITWIDTH downto i * C_BITWIDTH);
  end generate gen_bram_input;

  proc_counter : process (isl_clk) is
  begin

    if (rising_edge(isl_clk)) then
      if (isl_valid = '1') then
        -- type cast to avoid ghdl synthesis error:
        -- error: synth_static_dyadic_predefined: unhandled IIR_PREDEFINED_IEEE_NUMERIC_STD_NE_UNS_NAT
        -- TODO: report bug
        if (to_integer(usig_addr_cnt) /= C_BRAM_SIZE - 2) then
          usig_addr_cnt <= usig_addr_cnt + 1;
        else
          usig_addr_cnt <= (others => '0');
        end if;
      end if;
    end if;

  end process proc_counter;

  proc_output_assign : process (isl_clk) is
  begin

    if (rising_edge(isl_clk)) then
      if (isl_valid = '1') then
        a_data_out(0)       <= islv_data;
        for i in 0 to C_KERNEL_SIZE - 2 loop
          a_data_out(i + 1) <= get_slice(slv_bram_data_out, i, C_BITWIDTH);
        end loop;
      end if;

      sl_valid_out <= isl_valid;
    end if;

  end process proc_output_assign;

  osl_valid <= sl_valid_out;
  oa_data   <= a_data_out;

end architecture ram;

architecture shift_register of line_buffer is

  -- Save the image rows in lutram or blockram.

  signal sl_valid_out : std_logic := '0';
  signal a_data_out   : t_slv_array_1d(0 to C_KERNEL_SIZE - 1)(C_BITWIDTH - 1 downto 0) := (others => (others => '0'));

  type t_buffer_array is array (natural range <>) of std_logic_vector(islv_data'range);

  signal a_buffer : t_buffer_array(0 to (C_KERNEL_SIZE - 1) * C_IMG_WIDTH * C_CH - 1);

begin

  proc_input_assign : process (isl_clk) is
  begin

    if (rising_edge(isl_clk)) then
      if (isl_valid = '1') then
        a_buffer <= islv_data & a_buffer(0 to a_buffer'high - 1);
      end if;
    end if;

  end process proc_input_assign;

  proc_output_assign : process (isl_clk) is
  begin

    if (rising_edge(isl_clk)) then
      if (isl_valid = '1') then
        a_data_out(0)   <= islv_data;
        for i in 1 to C_KERNEL_SIZE - 1 loop
          a_data_out(i) <= a_buffer(i * C_IMG_WIDTH * C_CH - 1);
        end loop;
      end if;

      sl_valid_out <= isl_valid;
    end if;

  end process proc_output_assign;

  osl_valid <= sl_valid_out;
  oa_data   <= a_data_out;

end architecture shift_register;

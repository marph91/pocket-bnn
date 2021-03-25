
library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;
  use ieee.fixed_pkg.all;
  use ieee.fixed_float_types.all;

library util;
  use util.array_pkg.all;
  use util.math_pkg.all;

entity average_pooling is
  generic (
    C_BITWIDTH : integer := 8;

    C_CHANNEL    : integer range 1 to 512 := 4;
    C_IMG_WIDTH  : integer range 1 to 512 := 6;
    C_IMG_HEIGHT : integer range 1 to 512 := 6
  );
  port (
    isl_clk   : in    std_logic;
    isl_start : in    std_logic;
    isl_valid : in    std_logic;
    islv_data : in    std_logic_vector(C_CHANNEL * C_BITWIDTH - 1 downto 0);
    oslv_data : out   std_logic_vector(C_BITWIDTH - 1 downto 0);
    osl_valid : out   std_logic
  );
end entity average_pooling;

architecture behavioral of average_pooling is

  -- temporary higher int width to prevent overflow while summing up channel/pixel
  -- new bitwidth = log2(C_IMG_HEIGHT*C_IMG_WIDTH*(2^old bitwidth)) = log2(C_IMG_HEIGHT*C_IMG_WIDTH) + old bitwidth -> new bw = lb(16*(2^7)) = 12
  constant C_INTW_SUM   : integer := C_BITWIDTH + log2(C_IMG_HEIGHT * C_IMG_WIDTH + 1);
  constant C_FRACW_REZI : integer range 1 to 16 := 16;

  signal sl_calculate_average    : std_logic := '0';
  signal sl_calculate_average_d1 : std_logic := '0';
  signal sl_calculate_average_d2 : std_logic := '0';

  -- fixed point multiplication yields: A'left + B'left + 1 downto -(A'right + B'right)
  signal ufix_average    : ufixed(C_INTW_SUM downto - C_FRACW_REZI) := (others => '0');
  attribute use_dsp : string;
  attribute use_dsp of ufix_average : signal is "yes";
  signal ufix_average_d1 : ufixed(C_INTW_SUM downto - C_FRACW_REZI) := (others => '0');

  -- TODO: try real instead of ufixed
  -- to_ufixed() yields always one fractional bit. Thus the reciprocal has at least 2 integer bits.
  constant C_RECIPROCAL : ufixed(0 downto - C_FRACW_REZI) := reciprocal(to_ufixed(C_IMG_HEIGHT * C_IMG_WIDTH, C_FRACW_REZI - 1, 0));
  signal   slv_average  : std_logic_vector(C_BITWIDTH - 1 downto 0) := (others => '0');

  signal int_data_in_cnt  : integer range 0 to C_IMG_WIDTH * C_IMG_HEIGHT - 1 := 0;
  signal int_data_out_cnt : integer range 0 to C_CHANNEL := 0;

  type t_1d_array is array (natural range <>) of unsigned(C_INTW_SUM - 1 downto 0);

  signal a_ch_buffer : t_1d_array(0 to C_CHANNEL - 1) := (others => (others => '0'));

  signal sl_output_valid : std_logic := '0';

begin

  -------------------------------------------------------
  -- Process: Average Pooling (average of each channel)
  -- Stage 1: sum up the values of every channel
  -- Stage 2*: multiply with reciprocal
  -- Stage 3: pipeline DSP output
  -- Stage 4: resize output
  -- *Stage 2 is entered when full image except of last pixel (C_IMG_HEIGHT*C_IMG_WIDTH) is loaded
  -------------------------------------------------------
  proc_average_pooling : process (isl_clk) is
  begin

    if (rising_edge(isl_clk)) then
      sl_calculate_average <= '0';

      if (isl_start = '1') then
        a_ch_buffer     <= (others => (others => '0'));
        int_data_in_cnt <= 0;
      else
        if (isl_valid = '1') then
          if (int_data_in_cnt = C_IMG_HEIGHT * C_IMG_WIDTH - 1) then
            int_data_in_cnt  <= 0;
            int_data_out_cnt <= C_CHANNEL;
          else
            int_data_in_cnt <= int_data_in_cnt + 1;
          end if;

          for ch in 0 to C_CHANNEL - 1 loop
            a_ch_buffer(ch) <= resize(
                                      a_ch_buffer(ch) +
                                      unsigned(get_slice(islv_data, ch, C_BITWIDTH)),
                                      a_ch_buffer(0)'length);
          end loop;
        end if;

        ------------------------DIVIDE OPTIONS---------------------------
        -- 1. simple divide
        -- ufix_average <= a_ch_buffer(0)/to_ufixed(C_IMG_HEIGHT*C_IMG_WIDTH, 8, 0);
        --
        -- 2. divide with round properties (round, guard bits)
        -- ufix_average <= divide(a_ch_buffer(0), to_ufixed(C_IMG_HEIGHT*C_IMG_WIDTH, 8, 0), fixed_truncate, 0)
        --
        -- 3. multiply with reciprocal -> best for timing and ressource usage!
        -- ufix_average <= a_ch_buffer(0) * C_RECIPROCAL;
        -----------------------------------------------------------------

        if (int_data_out_cnt /= 0) then
          assert isl_valid = '0' severity failure;
          int_data_out_cnt     <= int_data_out_cnt - 1;
          sl_calculate_average <= '1';
        end if;
        sl_calculate_average_d1 <= sl_calculate_average;
        sl_calculate_average_d2 <= sl_calculate_average_d1;
        sl_output_valid         <= sl_calculate_average_d2;

        if (sl_calculate_average = '1') then
          a_ch_buffer  <= a_ch_buffer(a_ch_buffer'high) & a_ch_buffer(0 to a_ch_buffer'high - 1);
          ufix_average <= to_ufixed(a_ch_buffer(a_ch_buffer'high), C_INTW_SUM - 1, 0) * C_RECIPROCAL;
        end if;

        if (sl_calculate_average_d1 = '1') then
          ufix_average_d1 <= ufix_average;
        end if;

        if (sl_calculate_average_d2 = '1') then
          slv_average <= to_slv(resize(ufix_average_d1, C_BITWIDTH - 1, 0, fixed_wrap, fixed_round));
        end if;
      end if;
    end if;

  end process proc_average_pooling;

  oslv_data <= slv_average;
  osl_valid <= sl_output_valid;

end architecture behavioral;

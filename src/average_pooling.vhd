
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

  -- fixed point multiplication yields: A'left + B'left + 1 downto -(A'right + B'right)
  signal ufix_average    : ufixed(C_INTW_SUM downto - C_FRACW_REZI) := (others => '0');
  attribute use_dsp : string;
  attribute use_dsp of ufix_average : signal is "yes";
  signal ufix_average_d1 : ufixed(C_INTW_SUM downto - C_FRACW_REZI) := (others => '0');

  -- TODO: try real instead of ufixed
  -- to_ufixed() yields always one fractional bit. Thus the reciprocal has at least one integer bit.
  constant C_RECIPROCAL : ufixed(0 downto - C_FRACW_REZI) := reciprocal(to_ufixed(C_IMG_HEIGHT * C_IMG_WIDTH, C_FRACW_REZI - 1, 0));
  signal   slv_average  : std_logic_vector(C_BITWIDTH - 1 downto 0) := (others => '0');

  signal int_open_averages : integer range 0 to C_CHANNEL := 0;
  signal sl_full_image     : std_logic := '0';

  type t_1d_array is array (natural range <>) of unsigned(C_INTW_SUM - 1 downto 0);

  signal a_ch_buffer : t_1d_array(0 to C_CHANNEL - 1) := (others => (others => '0'));

  signal sl_output_valid : std_logic := '0';

  type t_state is (CLEAR_BUFFER, SUM, CALCULATE_AVERAGE, PIPELINE_AVERAGE, OUTPUT_AVERAGE);

  signal state : t_state := CLEAR_BUFFER;

begin

  i_pixel_count : entity util.basic_counter
    generic map (
      C_MAX        => C_IMG_HEIGHT * C_IMG_WIDTH,
      C_COUNT_DOWN => 0
    )
    port map (
      isl_clk     => isl_clk,
      isl_reset   => isl_start,
      isl_valid   => isl_valid,
      oint_count  => open,
      osl_maximum => sl_full_image
    );

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
      sl_output_valid <= '0';

      if (isl_start = '1') then
        state <= CLEAR_BUFFER;
      end if;

      case state is

        when CLEAR_BUFFER =>
          a_ch_buffer <= (others => (others => '0'));
          state       <= SUM;

        when SUM =>
          if (isl_valid = '1') then
            for ch in 0 to C_CHANNEL - 1 loop
              a_ch_buffer(ch) <= resize(a_ch_buffer(ch) +
                                        unsigned(get_slice(islv_data, ch, C_BITWIDTH)),
                                        a_ch_buffer(0)'length);
            end loop;
          end if;

          if (sl_full_image = '1') then
            state             <= CALCULATE_AVERAGE;
            int_open_averages <= C_CHANNEL;
          end if;

        when CALCULATE_AVERAGE =>
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
          a_ch_buffer  <= a_ch_buffer(a_ch_buffer'high) & a_ch_buffer(0 to a_ch_buffer'high - 1);
          ufix_average <= to_ufixed(a_ch_buffer(a_ch_buffer'high), C_INTW_SUM - 1, 0) * C_RECIPROCAL;

          int_open_averages <= int_open_averages - 1;
          state             <= PIPELINE_AVERAGE;

        when PIPELINE_AVERAGE =>
          ufix_average_d1 <= ufix_average;
          state           <= OUTPUT_AVERAGE;

        when OUTPUT_AVERAGE =>
          slv_average     <= to_slv(resize(ufix_average_d1, C_BITWIDTH - 1, 0, fixed_wrap, fixed_round));
          sl_output_valid <= '1';

          if (int_open_averages /= 0) then
            state <= CALCULATE_AVERAGE;
          else
            state <= CLEAR_BUFFER;
          end if;

      end case;

    end if;

  end process proc_average_pooling;

  oslv_data <= slv_average;
  osl_valid <= sl_output_valid;

end architecture behavioral;

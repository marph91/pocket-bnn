-- UART interface wrapper for the bnn on an ulx3s board.

library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

library bnn_lib;

library interface_lib;

library util;

entity bnn_uart is
  generic (
    C_BITS        : integer range 5 to 8 := 8;
    C_QUARTZ_FREQ : integer              := 25000000 -- Hz
  );
  port (
    clk_25mhz : in    std_logic;
    btn       : in    std_logic_vector(6 downto 0);
    ftdi_txd  : in    std_logic;
    ftdi_rxd  : out   std_logic;
    led       : out   std_logic_vector(7 downto 0);
    -- SDRAM interface (For use with 16Mx16bit or 32Mx16bit SDR DRAM, depending on version)
    sdram_csn  : out   std_logic;                     -- chip select
    sdram_clk  : out   std_logic;                     -- clock to SDRAM
    sdram_cke  : out   std_logic;                     -- clock enable to SDRAM
    sdram_rasn : out   std_logic;                     -- SDRAM RAS
    sdram_casn : out   std_logic;                     -- SDRAM CAS
    sdram_wen  : out   std_logic;                     -- SDRAM write-enable
    sdram_a    : out   unsigned(12 downto 0);         -- SDRAM address bus
    sdram_ba   : out   unsigned( 1 downto 0);         -- SDRAM bank-address
    sdram_dqm  : out   std_logic_vector( 1 downto 0); -- byte select
    sdram_d    : inout std_logic_vector(15 downto 0)  -- data bus to/from SDRAM
  );
end entity bnn_uart;

architecture behavioral of bnn_uart is

  alias isl_clk is clk_25mhz;
  alias isl_start is btn(3);
  alias isl_data is ftdi_txd;
  alias osl_data is ftdi_rxd;

  constant C_CLOCK_FREQUENCY : integer := 100000000; -- 100 MHz
  signal   slv_clocks        : std_logic_vector(3 downto 0);
  signal   btn_d1            : std_logic_vector(6 downto 0) := (others => '0');

  -- sdram controller
  signal sl_sdram_request         : std_logic := '0';
  signal sl_sdram_acknowledgement : std_logic := '0';
  signal sl_sdram_write_enable    : std_logic := '0';
  signal usig_sdram_addr          : unsigned(2 + 13 + 9 - 1 downto 0) := (others => '0');
  signal slv_sdram_input_data     : std_logic_vector(31 downto 0) := (others => '0');
  signal sl_sdram_output_valid    : std_logic := '0';
  signal slv_sdram_output_data    : std_logic_vector(31 downto 0) := (others => '0');

  type t_sdram_state is (IDLE, WRITE_REQ, READ_REQ, LAST_READ_FINISHED, SEND);

  signal sdram_state : t_sdram_state := IDLE;

  -- Arbitrary count
  constant C_COUNT   : integer := 10;
  signal   int_count : integer range 0 to C_COUNT := 0;

  -- BRAM to buffer SDRAM output
  signal sl_bram_valid_out, sl_bram_we       : std_logic := '0';
  signal slv_bram_data_out, slv_bram_data_in : std_logic_vector(31 downto 0) := (others => '0');
  signal slv_bram_addr                       : std_logic_vector(9 downto 0) := (others => '0');

  -- UART
  constant C_BAUDRATE       : integer := 115200; -- words / s
  constant C_CYCLES_PER_BIT : integer := C_QUARTZ_FREQ / C_BAUDRATE;

  signal sl_valid_out_uart_rx : std_logic := '0';
  signal slv_data_out_uart_rx : std_logic_vector(C_BITS - 1 downto 0) := (others => '0');
  signal sl_ready_uart_tx     : std_logic := '0';

  -- BNN
  signal sl_finish : std_logic := '0';

  signal sl_valid_out_bnn : std_logic := '0';
  signal slv_data_out_bnn : std_logic_vector(C_BITS - 1 downto 0) := (others => '0');

  -- glue

  type t_output_array is array(0 to 9) of std_logic_vector(C_BITS - 1 downto 0);

  signal   a_output_buffer         : t_output_array := (others => (others => '0'));
  signal   sl_valid_buffer         : std_logic := '0';
  signal   int_valid_buffer_values : integer range 0 to a_output_buffer'length := 0;
  constant C_ZEROS                 : std_logic_vector(C_BITS - 1 downto 0) := (others => '0');

  type t_output_state is (IDLE, FILL, READY_TO_SEND, SEND);

  signal output_state : t_output_state := IDLE;

begin

  i_clk : entity interface_lib.ecp5pll
    generic map (

      OUT0_HZ  => C_CLOCK_FREQUENCY,
      OUT0_DEG => 0,
      OUT1_HZ  => C_CLOCK_FREQUENCY,
      OUT1_DEG => 180
    )
    port map (

      clk_i  => clk_25mhz,
      clk_o  => slv_clocks,
      locked => open
    );

  i_uart_rx : entity interface_lib.uart_rx
    generic map (
      C_BITS           => C_BITS,
      C_CYCLES_PER_BIT => C_CYCLES_PER_BIT
    )
    port map (
      isl_clk   => isl_clk,
      isl_data  => isl_data,
      oslv_data => slv_data_out_uart_rx,
      osl_valid => sl_valid_out_uart_rx
    );

  i_bnn : entity bnn_lib.bnn
    port map (
      isl_clk    => isl_clk,
      isl_start  => isl_start,
      isl_valid  => sl_valid_out_uart_rx,
      islv_data  => slv_data_out_uart_rx,
      oslv_data  => slv_data_out_bnn,
      osl_valid  => sl_valid_out_bnn,
      osl_finish => sl_finish
    );

  sdram_clk <= slv_clocks(0); -- TODO: Use slv_clocks(1), which is shifted by 180 degree?

  i_sdram_controller : entity interface_lib.sdram
    generic map (
      CLK_FREQ         => real(C_CLOCK_FREQUENCY / 1000000),
      CAS_LATENCY      => 2,
      SDRAM_COL_WIDTH  => 9,
      SDRAM_ROW_WIDTH  => 13,
      SDRAM_BANK_WIDTH => 2,
      ADDR_WIDTH       => 2 + 13 + 9,
      T_DESL           => 100000.0,
      T_MRD            => 15.0,
      T_RC             => 60.0,
      T_RCD            => 15.0,
      T_RP             => 15.0,
      T_WR             => 14.0,
      T_REFI           => 7810.0
    )
    port map (
      reset => isl_start,
      clk   => slv_clocks(0),
      req   => sl_sdram_request,
      ack   => sl_sdram_acknowledgement,
      we    => sl_sdram_write_enable,
      addr  => usig_sdram_addr,
      -- write and read data
      data  => slv_sdram_input_data,
      valid => sl_sdram_output_valid,
      q     => slv_sdram_output_data,
      -- SDRAM chip connection
      sdram_cke   => sdram_cke,
      sdram_we_n  => sdram_wen,
      sdram_ras_n => sdram_rasn,
      sdram_cas_n => sdram_casn,
      sdram_cs_n  => sdram_csn,
      sdram_ba    => sdram_ba,
      sdram_a     => sdram_a,
      sdram_dq    => sdram_d,
      sdram_dqm   => sdram_dqm
    );

  sdram_fsm : process (slv_clocks(0)) is

    variable v_int_count : integer;

  begin

    if (rising_edge(slv_clocks(0))) then
      led <= (others => '0');

      btn_d1 <= btn;

      if (isl_start = '1') then
        sdram_state <= IDLE;
      end if;

      case sdram_state is

        when IDLE =>
          led(0) <= '1';

          sl_sdram_request      <= '0';
          sl_sdram_write_enable <= '0';
          usig_sdram_addr       <= (others => '0');
          slv_sdram_input_data  <= (others => '0');

          if (btn(6) and not btn_d1(6)) then
            sdram_state           <= WRITE_REQ;
            sl_sdram_request      <= '1';
            sl_sdram_write_enable <= '1';
            int_count             <= 0;
          end if;

        when WRITE_REQ =>
          led(1) <= '1';

          if (sl_sdram_acknowledgement = '1') then
            v_int_count := int_count;
            if (int_count /= C_COUNT) then
              v_int_count := v_int_count + 1;
              slv_sdram_input_data <= std_logic_vector(to_unsigned(v_int_count, slv_sdram_input_data'length));
            else
              v_int_count := C_COUNT - 1;
              sl_sdram_request      <= '1';
              sl_sdram_write_enable <= '0';

              sdram_state <= READ_REQ;
            end if;

            usig_sdram_addr <= "00" &
                               to_unsigned(0, 13) &
                               to_unsigned(v_int_count, 9);

            int_count <= v_int_count;
          end if;

        when READ_REQ =>
          led(2) <= '1';

          if (sl_sdram_acknowledgement = '1') then
            v_int_count := int_count;

            if (int_count /= 0) then
              v_int_count := v_int_count - 1;
            else
              v_int_count := C_COUNT;
              sdram_state      <= LAST_READ_FINISHED;
              sl_sdram_request <= '0';
            end if;

            usig_sdram_addr <= "00" &
                               to_unsigned(0, 13) &
                               to_unsigned(v_int_count mod 4, 9);

            int_count <= v_int_count;
          end if;

        when LAST_READ_FINISHED =>
          led(3) <= '1';

          if (sl_sdram_output_valid = '1') then
            sdram_state <= SEND;
          end if;

        when SEND =>
          led(4) <= '1';

          if (slv_bram_addr = (slv_bram_addr'range => '0')) then
            sdram_state <= IDLE;
          end if;

      end case;

    end if;

  end process sdram_fsm;

  sdram_output : process (slv_clocks(0)) is
  begin

    if (rising_edge(slv_clocks(0))) then
      sl_bram_we        <= '0';
      sl_bram_valid_out <= '0';

      if (sdram_state = READ_REQ or sdram_state = LAST_READ_FINISHED) then
        if (sl_sdram_output_valid = '1') then
          slv_bram_addr    <= std_logic_vector(unsigned(slv_bram_addr) + 1);
          sl_bram_we       <= '1';
          slv_bram_data_in <= slv_sdram_output_data;
        end if;
      end if;

      if (sdram_state = SEND) then
        if (sl_ready_uart_tx = '1' and sl_bram_valid_out = '0') then
          if (slv_bram_addr /= (slv_bram_addr'range => '0')) then
            sl_bram_valid_out <= '1';
            slv_bram_addr     <= std_logic_vector(unsigned(slv_bram_addr) - 1);
          end if;
        end if;
      end if;
    end if;

  end process sdram_output;

  i_bram : entity util.bram
    generic map (
      C_DATA_WIDTH => 32,
      C_ADDR_WIDTH => 10
    )
    port map (
      isl_clk   => slv_clocks(0),
      isl_en    => '1',
      isl_we    => sl_bram_we,
      islv_addr => slv_bram_addr,
      islv_data => slv_bram_data_in,
      oslv_data => slv_bram_data_out
    );

  i_uart_tx : entity interface_lib.uart_tx
    generic map (
      C_BITS           => C_BITS,
      C_CYCLES_PER_BIT => C_CLOCK_FREQUENCY / C_BAUDRATE
    )
    port map (
      isl_clk   => slv_clocks(0),
      isl_valid => sl_bram_valid_out,
      islv_data => slv_bram_data_out(7 downto 0),
      osl_data  => osl_data,
      osl_ready => sl_ready_uart_tx
    );

end architecture behavioral;

-- UART interface wrapper for the bnn on an ulx3s board.

library ieee;
  use ieee.std_logic_1164.all;

library bnn_lib;

library uart_lib;

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
    led       : out   std_logic_vector(7 downto 0)
  );
end entity bnn_uart;

architecture behavioral of bnn_uart is

  alias isl_clk is clk_25mhz;
  alias isl_start is btn(3);
  alias isl_data is ftdi_txd;
  alias osl_data is ftdi_rxd;

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

  -- debug
  led(0)                 <= not sl_ready_uart_tx;
  led(1)                 <= '1' when int_valid_buffer_values /= 0 else
                            '0';
  led(3)                 <= isl_data;
  led(4)                 <= osl_data;
  led(led'high downto 5) <= (others => '0');

  proc_bnn_calc_debug : process (isl_clk) is
  begin

    if (rising_edge(isl_clk)) then
      if (isl_start = '1') then
        led(2) <= '0';
      elsif (sl_valid_out_uart_rx = '1') then
        led(2) <= '1';
      elsif (sl_finish = '1') then
        led(2) <= '0';
      end if;
    end if;

  end process proc_bnn_calc_debug;

  i_uart_rx : entity uart_lib.uart_rx
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

  proc_output_buffer : process (isl_clk) is
  begin

    if (rising_edge(isl_clk)) then
      sl_valid_buffer <= '0';

      case output_state is

        when IDLE =>
          assert sl_valid_out_bnn = '0'
            severity failure;

          int_valid_buffer_values <= 0;
          output_state            <= FILL;

        when FILL =>
          if (sl_valid_out_bnn = '1') then
            a_output_buffer         <= a_output_buffer(1 to a_output_buffer'high) & slv_data_out_bnn;
            int_valid_buffer_values <= int_valid_buffer_values + 1;
          end if;

          if (int_valid_buffer_values = a_output_buffer'length) then
            output_state <= READY_TO_SEND;
          end if;

        when READY_TO_SEND =>
          assert sl_valid_out_bnn = '0'
            severity failure;

          if (sl_ready_uart_tx = '1') then
            int_valid_buffer_values <= int_valid_buffer_values - 1;
            sl_valid_buffer         <= '1';
            output_state            <= SEND;
          end if;

        when SEND =>
          a_output_buffer <= a_output_buffer(1 to a_output_buffer'high) & C_ZEROS;

          if (int_valid_buffer_values /= 0) then
            output_state <= READY_TO_SEND;
          else
            output_state <= IDLE;
          end if;

      end case;

    end if;

  end process proc_output_buffer;

  i_uart_tx : entity uart_lib.uart_tx
    generic map (
      C_BITS           => C_BITS,
      C_CYCLES_PER_BIT => C_CYCLES_PER_BIT
    )
    port map (
      isl_clk   => isl_clk,
      isl_valid => sl_valid_buffer,
      islv_data => a_output_buffer(0),
      osl_data  => osl_data,
      osl_ready => sl_ready_uart_tx
    );

end architecture behavioral;

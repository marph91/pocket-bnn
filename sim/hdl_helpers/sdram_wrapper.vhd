-- Wrapper, which connects SDRAM simulation model with SDRAM controller for simulation purposes.

library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

library bnn_lib;
library fmf;

entity sdram_wrapper is
end entity sdram_wrapper;

architecture behavioral of sdram_wrapper is

  signal sdram_csn : std_logic := '0';
  signal sdram_clk : std_logic := '0';
  signal sdram_cke : std_logic := '0';
  signal sdram_rasn : std_logic := '0';
  signal sdram_casn : std_logic := '0';
  signal sdram_wen : std_logic := '0';
  signal sdram_a : unsigned(12 downto 0) := (others => '0');
  signal sdram_ba : unsigned(1 downto 0) := (others => '0');
  signal sdram_dqm : std_logic_vector(1 downto 0) := (others => '0');
  signal sdram_d : std_logic_vector(15 downto 0) := (others => '0');

begin

  i_bnn_uart : entity bnn_lib.bnn_uart
  port map
  (
    clk_25mhz => 'U',
    btn       => (others => 'U'),
    ftdi_txd  => 'U',
    ftdi_rxd  => open,
    led       => open,
    -- SDRAM interface (For use with 16Mx16bit or 32Mx16bit SDR DRAM, depending on version)
    sdram_csn  => sdram_csn,
    sdram_clk  => sdram_clk,
    sdram_cke  => sdram_cke,
    sdram_rasn => sdram_rasn,
    sdram_casn => sdram_casn,
    sdram_wen  => sdram_wen,
    sdram_a    => sdram_a,
    sdram_ba   => sdram_ba,
    sdram_dqm  => sdram_dqm,
    sdram_d    => sdram_d
  );

  i_sdram : entity fmf.mt48lc32m16a2
  port map
  (
    BA0    => sdram_ba(0),
    BA1    => sdram_ba(1),
    DQMH   => sdram_dqm(1),
    DQML   => sdram_dqm(0),
    DQ0    => sdram_d(0),
    DQ1    => sdram_d(1),
    DQ2    => sdram_d(2),
    DQ3    => sdram_d(3),
    DQ4    => sdram_d(4),
    DQ5    => sdram_d(5),
    DQ6    => sdram_d(6),
    DQ7    => sdram_d(7),
    DQ8    => sdram_d(8),
    DQ9    => sdram_d(9),
    DQ10   => sdram_d(10),
    DQ11   => sdram_d(11),
    DQ12   => sdram_d(12),
    DQ13   => sdram_d(13),
    DQ14   => sdram_d(14),
    DQ15   => sdram_d(15),
    CLK    => sdram_clk,
    CKE    => sdram_cke,
    A0     => sdram_a(0),
    A1     => sdram_a(1),
    A2     => sdram_a(2),
    A3     => sdram_a(3),
    A4     => sdram_a(4),
    A5     => sdram_a(5),
    A6     => sdram_a(6),
    A7     => sdram_a(7),
    A8     => sdram_a(8),
    A9     => sdram_a(9),
    A10    => sdram_a(10),
    A11    => sdram_a(11),
    A12    => sdram_a(12),
    WENeg  => sdram_wen,
    RASNeg => sdram_rasn,
    CSNeg  => sdram_csn,
    CASNeg => sdram_casn
  );

end architecture behavioral;

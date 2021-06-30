library ieee;
  use ieee.std_logic_1164.all;

-- Most of generics and ports are ignored for simplicity.
entity ecp5pll is
  generic
  (
    in_hz        : natural := 25000000;
    out0_hz      : natural := 25000000;
    out0_deg     : natural :=        0;
    out0_tol_hz  : natural :=        0;
    out1_hz      : natural :=        0;
    out1_deg     : natural :=        0;
    out1_tol_hz  : natural :=        0;
    out2_hz      : natural :=        0;
    out2_deg     : natural :=        0;
    out2_tol_hz  : natural :=        0;
    out3_hz      : natural :=        0;
    out3_deg     : natural :=        0;
    out3_tol_hz  : natural :=        0;
    reset_en     : natural :=        0;
    standby_en   : natural :=        0;
    dynamic_en   : natural :=        0
  );
  port
  (
    clk_i        : in  std_logic;
    clk_o        : out std_logic_vector(3 downto 0);
    reset        : in  std_logic := '0';
    standby      : in  std_logic := '0';
    phasesel     : in  std_logic_vector(1 downto 0) := "00";
    phasedir,
    phasestep,
    phaseloadreg : std_logic := '0';
    locked       : out std_logic
  );
end;

architecture sim of ecp5pll is
  signal slv_clk : std_logic_vector(clk_o'range) := (others => '0');
begin
  slv_clk(0) <= not slv_clk(0) after 5 ns;
  slv_clk(1) <= not slv_clk(0);

  clk_o <= slv_clk;
  locked <= '1';
end sim;

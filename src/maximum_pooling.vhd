
library ieee;
  use ieee.std_logic_1164.all;

entity maximum_pooling is
  generic (
    C_KERNEL_SIZE : integer range 2 to 3 := 2;
    C_CHANNEL     : integer              := 1
  );
  port (
    isl_clk   : in    std_logic;
    isl_valid : in    std_logic;
    islv_data : in    std_logic_vector(C_KERNEL_SIZE * C_KERNEL_SIZE * C_CHANNEL - 1 downto 0);
    oslv_data : out   std_logic_vector(C_CHANNEL - 1 downto 0);
    osl_valid : out   std_logic
  );
end entity maximum_pooling;

architecture behavioral of maximum_pooling is

  signal sl_valid_out : std_logic := '0';
  signal slv_data_out : std_logic_vector(oslv_data'range);

begin

  proc_output_valid : process (isl_clk) is
  begin

    if (rising_edge(isl_clk)) then
      sl_valid_out <= isl_valid;
    end if;

  end process proc_output_valid;

  gen_channel : for channel in 0 to C_CHANNEL - 1 generate

    proc_maximum_pooling : process (isl_clk) is

      variable slv_roi : std_logic_vector(C_KERNEL_SIZE * C_KERNEL_SIZE - 1 downto 0);

    begin

      if (rising_edge(isl_clk)) then
        if (isl_valid = '1') then
          for col in 0 to C_KERNEL_SIZE - 1 loop
            for row in 0 to C_KERNEL_SIZE - 1 loop
              slv_roi(col + row * C_KERNEL_SIZE) := islv_data(channel + col * C_CHANNEL + row * C_CHANNEL * C_KERNEL_SIZE);
            end loop;
          end loop;

          if (slv_roi = (slv_roi'range => '0')) then
            slv_data_out(channel) <= '0';
          else
            slv_data_out(channel) <= '1';
          end if;
        end if;
      end if;

    end process proc_maximum_pooling;

  end generate gen_channel;

  oslv_data <= slv_data_out;
  osl_valid <= sl_valid_out;

end architecture behavioral;

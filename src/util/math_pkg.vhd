
library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;
  use ieee.fixed_pkg.all;

package math_pkg is

  function log2 (x : integer) return integer;

  function is_power_of_two (int_value : integer) return std_logic;

  function is_power_of_two (slv_value : std_logic_vector) return std_logic;

  function max (l, r : sfixed) return sfixed;

end package math_pkg;

package body math_pkg is

  -- compute the binary logarithm

  function log2 (x : integer) return integer is
    variable i : integer;
  begin
    i := 0;
    while 2 ** i < x loop
      i := i + 1;
    end loop;
    return i;
  end function log2;

  -- check whether an integer is a power of two

  function is_power_of_two (int_value : integer) return std_logic is
  begin
    return is_power_of_two(std_logic_vector(to_unsigned(int_value, 32)));
  end function is_power_of_two;

  function is_power_of_two (slv_value : std_logic_vector) return std_logic is
    variable v_got_one    : std_logic;
    variable v_only_zeros : std_logic;
  begin
    -- positive values, f. e.: 1000, 0100, 0010, 0001, 0000
    -- negative values, f. e.: 1111, 1110, 1100, 1000

    v_got_one := '0';
    v_only_zeros := '0';

    if (slv_value(slv_value'high) = '0') then
      -- positive: Zero or one '1' should occur.
      for i in slv_value'high - 1 downto slv_value'low loop
        if (slv_value(i) = '1') then
          if (v_got_one = '0') then
            v_got_one := '1';
          else
            return '0';
          end if;
        end if;
      end loop;
    else
      -- negative: Wait for the first '0'. From then on, only '0' should occur.
      for i in slv_value'high - 1 downto slv_value'low loop
        if (slv_value(i) = '1') then
          if (v_only_zeros = '1') then
            return '0';
          end if;
        else
          v_only_zeros := '1';
        end if;
      end loop;
    end if;

    return '1';
  end function is_power_of_two;

  -- obtain the maximum of two signed fixed point numbers

  function max (l, r : sfixed) return sfixed is
  begin

    if (l > r) then
      return l;
    else
      return r;
    end if;

  end max;

end package body math_pkg;

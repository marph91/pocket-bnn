  use std.textio.all;

library ieee;
  use ieee.std_logic_1164.all;
  use ieee.fixed_pkg.all;

package array_pkg is

  -- TODO: make the bitwidth parametrizable

  type t_slv_array_1d is array(natural range <>) of std_logic_vector;

  type t_slv_array_2d is array(natural range <>, natural range <>) of std_logic_vector;

  type t_int_array_1d is array (natural range <>) of integer;

  type t_int_array_2d is array (natural range <>, natural range <>) of integer;

  type t_ram is array(natural range <>) of std_logic_vector;

  type t_kernel_array is array (natural range <>) of t_slv_array_2d;

  function array_to_slv (array_in : t_kernel_array) return std_logic_vector;

  function get_slice (vector: std_logic_vector; int_index : natural; int_slice_size : natural) return std_logic_vector;

  function get_fastest_increment (vector: std_logic_vector; int_index : natural; int_slice_size : natural) return std_logic_vector;

  procedure assign_slice (signal vector : inout std_logic_vector; int_index : in natural; value : in std_logic_vector);

end package array_pkg;

package body array_pkg is

  function array_to_slv (array_in : t_kernel_array) return std_logic_vector is
    variable slv_out        : std_logic_vector((array_in'LENGTH * array_in(0)'LENGTH(1) * array_in(0)'LENGTH(2)) * array_in(0)(0, 0)'LENGTH - 1 downto 0);
    variable bitwidth       : integer;
    variable rows           : integer;
    variable cols           : integer;
    variable channel        : integer;
    variable out_index_high : integer;
    variable out_index_low  : integer;
  begin
    bitwidth := array_in(0)(0, 0)'LENGTH;
    rows := array_in(0)'LENGTH(2);
    cols := array_in(0)'LENGTH(1);
    channel := array_in'LENGTH;
    for current_row in array_in(0)'RANGE(2) loop
      for current_col in array_in(0)'RANGE(1) loop
        for current_channel in array_in'RANGE loop
          -- TODO: How to support assign_slice for variable vector? Overloading is not possible.
          out_index_high := (current_channel + current_col * channel + current_row * cols * channel + 1) * bitwidth - 1;
          out_index_low := (current_channel + current_col * channel + current_row * cols * channel) * bitwidth;
          slv_out(out_index_high downto out_index_low) := array_in(current_channel)(current_col, current_row);
        end loop;
      end loop;
    end loop;
    return slv_out;
  end function;

  function get_slice (vector: std_logic_vector; int_index : natural; int_slice_size : natural) return std_logic_vector is
  begin
    return vector((int_index + 1) * int_slice_size - 1 downto int_index * int_slice_size);
  end function;

  function get_fastest_increment (vector: std_logic_vector; int_index : natural; int_slice_size : natural) return std_logic_vector is
    variable vector_out : std_logic_vector(vector'length / int_slice_size - 1 downto 0);
  begin
    for i in 0 to vector'length / int_slice_size - 1 loop
      vector_out(i) := vector(int_index + i * int_slice_size);
    end loop;
    return vector_out;
  end function;

  procedure assign_slice (signal vector : inout std_logic_vector; int_index : in natural; value : in std_logic_vector) is
    variable v_int_slice_size : integer;
  begin
    v_int_slice_size := value'length;
    vector((int_index + 1) * v_int_slice_size - 1 downto int_index * v_int_slice_size) <= value;
  end procedure;

end package body array_pkg;

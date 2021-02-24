
library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity bnn is
  generic (
    C_ARCHITECTURE_FILE : string := "../sim/architecture.json";
    C_WEIGHTS_FILE      : string := "../sim/weights.json";
    C_LAYER_NAME        : string := "pe1"
  );
  port (
    isl_clk   : in    std_logic;
    isl_valid : in    std_logic;
    islv_data : in    std_logic_vector(7 downto 0);
    oslv_data : out   std_logic_vector(7 downto 0);
    osl_valid : out   std_logic
  );
end entity bnn;

architecture behavioral of bnn is

  signal sl_add                    : std_logic := '0';
  signal slv_multiplication_result : std_logic_vector(islv_data'range);

  signal sl_valid_out : std_logic := '0';
  signal slv_data_out : std_logic_vector(oslv_data'range);

  -- constant C_JSON_CONTENT  : t_json    := jsonLoad(C_ARCHITECTURE_FILE);
  -- constant C_WEIGHTS : integer_vector := jsonGetIntegerArray(C_JSON_CONTENT, "weights"); -- TODO: C_LAYER_NAME
  -- constant C_THRESHOLDS : integer_vector := jsonGetIntegerArray(C_JSON_CONTENT, "thresholds");

  -- processing element (PE) configuration
  -- TODO: verify json image size with vhdl calculation
  constant C_PE_COUNT : integer;

  type t_pe_parameter is record
    C_LAYER_NAME : string;

    C_PAD : integer;

    C_WEIGHTS_FILE            : string;
    C_CONVOLUTION_KERNEL_SIZE : integer;
    C_CONVOLUTION_STRIDE      : integer;

    C_MAXIMUM_POOLING_KERNEL_SIZE : integer;
    C_MAXIMUM_POOLING_STRIDE      : integer;

    C_INPUT_CHANNEL  : integer;
    C_OUTPUT_CHANNEL : integer;
    C_IMG_WIDTH      : integer;
    C_IMG_HEIGHT     : integer;
  end record t_pe_parameter;

  type t_pe_parameter_vector is array(natural range <>) of t_pe_parameter;

  constant C_PE_PARAMETER : t_pe_parameter_vector(0 to C_PE_COUNT - 1);

begin

  proc_cnn : process (isl_clk) is
  begin

    if (rising_edge(isl_clk)) then
      -- loop processing elements
      -- average pooling/fc
    end if;

  end process proc_cnn;

  oslv_data <= slv_data_out;
  osl_valid <= sl_valid_out;

end architecture behavioral;

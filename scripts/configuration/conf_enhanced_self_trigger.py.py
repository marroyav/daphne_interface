#!/usr/bin/env python3
import click
from enum import Enum, IntEnum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from ivtools import Daphne

# Constants
RED = "\033[31m"
GREEN = "\033[32m"
BLUE = "\033[34m"
YELLOW = "\033[33m"
RESET = "\033[0m"
VALID_IPS = [4, 7, 9, 11, 12, 13, 6]

# Enums for better type safety and documentation
class RegisterAddress(IntEnum):
    """Memory-mapped register addresses for DAPHNE"""
    # Self-trigger configuration registers
    ENABLE_INPUTS = 0x6001
    TP_CONFIG = 0x6002
    COMPENSATOR = 0x6003
    INVERTER = 0x6004
    ADHOC_CMD = 0x6010
    XCORR_THRESH = 0x6100
    
    # System registers
    FW_VERSION = 0x9000
    RESET_COUNTERS = 0x4004
    TEST_REGISTER = 0xAA55
    
    # Status registers
    AFE_ALIGN_STATUS = 0x2002
    CLOCK_STATUS = 0x4000
    SFP_STATUS = 0x1975

class OperationMode(Enum):
    WRITE = auto()
    READ = auto()
    VERBOSE_READ = auto()

class TriggerMode(Enum):
    """Output link trigger modes"""
    DISABLED = 0
    STREAMING = 2
    SELF_TRIGGERED = 3

@dataclass
class TPConfig:
    """Detailed breakdown of TP_CONFIG register (0x6002)"""
    filter_output_selector: int  # bits[1:0]
    unused_bits: int            # bits[7:2]
    slope_calculation: int      # bit[8]
    spe_slope_threshold: int    # bits[15:9]
    pedestal_length: int        # bits[20:16]
    spybuffer_trigger_sel: int  # bits[26:21]
    unused_high_bits: int       # bits[31:27]

    @classmethod
    def from_int(cls, value: int) -> 'TPConfig':
        """Create TPConfig from 32-bit register value"""
        return cls(
            filter_output_selector=(value & 0b11),
            unused_bits=(value >> 2) & 0b111111,
            slope_calculation=(value >> 8) & 0b1,
            spe_slope_threshold=(value >> 9) & 0b1111111,
            pedestal_length=(value >> 16) & 0b11111,
            spybuffer_trigger_sel=(value >> 21) & 0b111111,
            unused_high_bits=(value >> 27) & 0b11111
        )

    def to_int(self) -> int:
        """Convert TPConfig to 32-bit register value"""
        return (
            (self.filter_output_selector & 0b11) |
            ((self.unused_bits & 0b111111) << 2) |
            ((self.slope_calculation & 0b1) << 8) |
            ((self.spe_slope_threshold & 0b1111111) << 9) |
            ((self.pedestal_length & 0b11111) << 16) |
            ((self.spybuffer_trigger_sel & 0b111111) << 21) |
            ((self.unused_high_bits & 0b11111) << 27)
        )

    def describe(self) -> str:
        """Return detailed description of the configuration"""
        filter_modes = [
            "AFE compensated signal (Deprecated: use '01')",
            "AFE compensator signal + digital inverter",
            "Selftrigger correlation signal",
            "Raw unfiltered signal"
        ]
        
        slope_samples = 16 if self.slope_calculation == 0 else 20
        
        return f"""
{BLUE}TP_CONFIG Register Details (0x6002):{RESET}
  Filter Output Selector (bits[1:0]={self.filter_output_selector:02b}): 
    {filter_modes[self.filter_output_selector]}
  Slope Calculation (bit[8]={self.slope_calculation}): 
    {slope_samples} samples used for peak detection
  SPE Slope Threshold (bits[15:9]={self.spe_slope_threshold:07b}): 
    {self.spe_slope_threshold} ADC counts
  Pedestal Length (bits[20:16]={self.pedestal_length:05b}): 
    {8 * self.pedestal_length} samples (max 256)
  SpyBuffer Trigger Select (bits[26:21]={self.spybuffer_trigger_sel:06b}): 
    {'Internal spybuffer disabled' if self.spybuffer_trigger_sel > 39 else f'Channel {self.spybuffer_trigger_sel}'}
  Full Register Value: 0x{self.to_int():08X}
"""

@dataclass
class RegisterConfig:
    """Configuration for a single register"""
    address: RegisterAddress
    value: int
    size_bits: int
    description: str
    read_only: bool = False

@dataclass
class SelfTriggerConfig:
    """Complete self-trigger configuration"""
    enable_inputs: int
    tp_config: TPConfig
    compensator: int
    inverter: int
    adhoc_cmd: int
    xcorr_thresh: int

# Default configuration with documentation
DEFAULT_TP_CONFIG = TPConfig(
    filter_output_selector=1,    # AFE compensator + digital inverter
    unused_bits=0,
    slope_calculation=1,         # 20 samples for slope calculation
    spe_slope_threshold=12,      # 12 ADC counts
    pedestal_length=8,           # 64 samples (8 * 8)
    spybuffer_trigger_sel=40,    # Internal spybuffer disabled
    unused_high_bits=0
)

DEFAULT_CONFIG = SelfTriggerConfig(
    enable_inputs=0xFF81818181,  # 40-bit mask for input enables
    tp_config=DEFAULT_TP_CONFIG,
    compensator=0xFF81818181,    # 40-bit AFE compensator mask
    inverter=0xFF00000000,       # 40-bit digital inverter mask
    adhoc_cmd=0x07,              # 8-bit ad-hoc trigger command
    xcorr_thresh=0xFFFFF         # 42-bit cross-correlation threshold
)

def validate_ip_address(ip_address: str) -> List[int]:
    """Validate and parse IP address input"""
    if ip_address.upper() == "ALL":
        return VALID_IPS
    
    try:
        selected_ips = list(map(int, ip_address.split(",")))
    except ValueError:
        raise ValueError(f"Invalid IP address input. Use 'ALL' or comma-separated numbers.")
    
    invalid_ips = [ip for ip in selected_ips if ip not in VALID_IPS]
    if invalid_ips:
        raise ValueError(f"Invalid IP(s) detected: {invalid_ips}. Valid options: {VALID_IPS}.")
    
    return selected_ips

def clamp_discrimination_threshold(value: int) -> int:
    """Clamp discrimination threshold to 14-bit signed range (-8192 to 8191)"""
    return max(-8192, min(value, 8191))

def clamp_correlation_threshold(value: int) -> int:
    """Clamp correlation threshold to 28-bit unsigned range"""
    return max(0, min(value, (1 << 28) - 1))

def calculate_xcorr_value(corr_thresh: int, disc_thresh: int) -> int:
    """Calculate 42-bit cross-correlation register value"""
    disc_clamped = clamp_discrimination_threshold(disc_thresh)
    disc_14bit = (disc_clamped + (1 << 14)) & 0x3FFF if disc_clamped < 0 else disc_clamped & 0x3FFF
    corr_clamped = clamp_correlation_threshold(corr_thresh)
    return (disc_14bit << 28) | (corr_clamped & 0x0FFFFFFF)

def create_register_configs(config: SelfTriggerConfig, corr_thresh: int, disc_thresh: int) -> Dict[str, RegisterConfig]:
    """Create register configurations from parameters"""
    xcorr_val = calculate_xcorr_value(corr_thresh, disc_thresh)
    
    return {
        "enable_inputs": RegisterConfig(
            address=RegisterAddress.ENABLE_INPUTS,
            value=config.enable_inputs,
            size_bits=40,
            description="40-bit mask for self-trigger input enables"
        ),
        "tp_config": RegisterConfig(
            address=RegisterAddress.TP_CONFIG,
            value=config.tp_config.to_int(),
            size_bits=32,
            description="32-bit self-trigger module configuration"
        ),
        "compensator": RegisterConfig(
            address=RegisterAddress.COMPENSATOR,
            value=config.compensator,
            size_bits=40,
            description="40-bit mask for AFE compensators"
        ),
        "inverter": RegisterConfig(
            address=RegisterAddress.INVERTER,
            value=config.inverter,
            size_bits=40,
            description="40-bit mask for digital inverters"
        ),
        "adhoc_cmd": RegisterConfig(
            address=RegisterAddress.ADHOC_CMD,
            value=config.adhoc_cmd,
            size_bits=8,
            description="8-bit ad-hoc trigger command"
        ),
        "xcorr_thresh": RegisterConfig(
            address=RegisterAddress.XCORR_THRESH,
            value=xcorr_val,
            size_bits=42,
            description="42-bit cross-correlation threshold (28-bit corr + 14-bit disc)"
        )
    }

def read_device_config(interface: Daphne, reg_configs: Dict[str, RegisterConfig]) -> Dict[str, int]:
    """Read current configuration from device"""
    config = {}
    for reg_name, config_spec in reg_configs.items():
        try:
            value = interface.read_reg(config_spec.address, 1)[2]
            config[reg_name] = value
            print(f"{GREEN}Read {reg_name} (0x{config_spec.address:04X}): 0x{value:0{config_spec.size_bits//4}X}{RESET}")
            
            # Special handling for TP_CONFIG
            if config_spec.address == RegisterAddress.TP_CONFIG:
                tp_config = TPConfig.from_int(value)
                print(tp_config.describe())
                
        except Exception as e:
            print(f"{RED}Error reading {reg_name}: {e}{RESET}")
    return config

def configure_device(interface: Daphne, reg_configs: Dict[str, RegisterConfig], selected_registers: Optional[List[str]] = None):
    """Configure registers on a DAPHNE device"""
    if selected_registers is None:
        selected_registers = list(reg_configs.keys())
    
    for reg_name, config in reg_configs.items():
        if reg_name not in selected_registers:
            continue
            
        try:
            interface.write_reg(config.address, [config.value])
            print(f"Set {reg_name}=0x{config.value:0{config.size_bits//4}X} at {config.address:04X}")
            
            # Read back for verification
            read_value = interface.read_reg(config.address, 1)[2]
            print(f"Readback {reg_name} (0x{config.address:04X}): {GREEN}0x{read_value:0{config.size_bits//4}X}{RESET}")
            
            # Special handling for TP_CONFIG
            if config.address == RegisterAddress.TP_CONFIG:
                tp_config = TPConfig.from_int(read_value)
                print(tp_config.describe())
                
        except Exception as e:
            print(f"{RED}Error configuring {reg_name}: {e}{RESET}")

def print_config_summary(config: SelfTriggerConfig, corr_thresh: int, disc_thresh: int):
    """Print configuration summary"""
    disc_clamped = clamp_discrimination_threshold(disc_thresh)
    corr_clamped = clamp_correlation_threshold(corr_thresh)
    
    # Calculate disc_14bit value properly
    if disc_clamped < 0:
        disc_14bit = (disc_clamped + (1 << 14)) & 0x3FFF
    else:
        disc_14bit = disc_clamped & 0x3FFF
    
    xcorr_val = calculate_xcorr_value(corr_thresh, disc_thresh)
    
    print(f"{GREEN}\nConfiguration Summary:{RESET}")
    print(f"corr_thresh={corr_thresh} => clamped={corr_clamped} (bits[27:0])")
    print(f"disc_thresh={disc_thresh} => clamped={disc_clamped} => disc_14bit=0x{disc_14bit:04X}")
    print(f"=> cross_correlation reg=0x{xcorr_val:010X}")
    print(f"tp_conf=0x{config.tp_config.to_int():08X}")
    print(f"compensator=0x{config.compensator:010X}")
    print(f"inverter=0x{config.inverter:010X}")
    print(f"enable_inputs=0x{config.enable_inputs:010X}")
    print(f"adhoc_cmd=0x{config.adhoc_cmd:02X}")

@click.command()
@click.option("--ip_address", "-ip", default="ALL",
              help="Last digits of the IP address (comma-separated) or 'ALL'")
@click.option("--corr_thresh", default=DEFAULT_CONFIG.xcorr_thresh, type=int,
              help="Cross-correlation threshold (28 bits). Default: 0xFFFFF")
@click.option("--disc_thresh", default=0xFFFF, type=int,
              help="Discrimination threshold (14-bit signed). Default: 0xFFFF")
@click.option("--tp_conf", default=hex(DEFAULT_TP_CONFIG.to_int()),
              help=f"32-bit Self Trigger config in hex. Default: {hex(DEFAULT_TP_CONFIG.to_int())}")
@click.option("--compensator", default=hex(DEFAULT_CONFIG.compensator),
              help=f"40-bit hex mask for AFE compensators. Default: {hex(DEFAULT_CONFIG.compensator)}")
@click.option("--inverter", default=hex(DEFAULT_CONFIG.inverter),
              help=f"40-bit hex mask for digital inverter. Default: {hex(DEFAULT_CONFIG.inverter)}")
@click.option("--enable_inputs", default=hex(DEFAULT_CONFIG.enable_inputs),
              help=f"40-bit hex mask for input enables. Default: {hex(DEFAULT_CONFIG.enable_inputs)}")
@click.option("--adhoc_cmd", default=hex(DEFAULT_CONFIG.adhoc_cmd),
              help=f"8-bit hex ad-hoc trigger command. Default: {hex(DEFAULT_CONFIG.adhoc_cmd)}")
@click.option("--registers", "-r", multiple=True,
              help="Specific registers to configure (comma-separated). Default: all")
@click.option("--read-only", is_flag=True,
              help="Read current configuration without making changes")
@click.option("--verbose", is_flag=True,
              help="Show detailed register descriptions (especially for TP_CONFIG)")
def main(ip_address: str,
         corr_thresh: int,
         disc_thresh: int,
         tp_conf: str,
         compensator: str,
         inverter: str,
         enable_inputs: str,
         adhoc_cmd: str,
         registers: List[str],
         read_only: bool,
         verbose: bool):
    """
    Configure or read the self-trigger module for DAPHNE using memory-map registers.
    
    The DEFAULT_CONFIG sets default values, which can be overridden by command-line options.
    Use --registers to select specific registers to configure (e.g., -r enable_inputs -r tp_conf).
    Use --read-only to read current configuration without making changes.
    Use --verbose for detailed register descriptions.
    """
    print(f"{GREEN}Configuring self-trigger module for selected DAPHNE endpoints.{RESET}")

    try:
        # Parse and validate IP addresses
        selected_ips = validate_ip_address(ip_address)
        
        # Convert hex strings to integers
        config = SelfTriggerConfig(
            enable_inputs=int(enable_inputs, 16),
            tp_config=TPConfig.from_int(int(tp_conf, 16)),
            compensator=int(compensator, 16),
            inverter=int(inverter, 16),
            adhoc_cmd=int(adhoc_cmd, 16),
            xcorr_thresh=corr_thresh
        )
        
        # Create register configurations
        reg_configs = create_register_configs(config, corr_thresh, disc_thresh)
        
        # If specific registers were requested, filter the configurations
        selected_registers = None
        if registers:
            selected_registers = [r.strip() for r in registers if r.strip() in reg_configs]
            if not selected_registers:
                print(f"{RED}No valid registers specified. Valid options: {list(reg_configs.keys())}{RESET}")
                return
        
        # Print configuration summary
        if not read_only:
            print_config_summary(config, corr_thresh, disc_thresh)
        
        # Configure each IP
        for ip in selected_ips:
            full_ip = f"10.73.137.{100 + ip}"
            print(f"{GREEN}\nProcessing endpoint {full_ip}{RESET}")
            
            try:
                interface = Daphne(full_ip)
                
                # Read firmware version
                fw_version = interface.read_reg(RegisterAddress.FW_VERSION, 1)[2]
                print(f"Firmware version: {GREEN}{fw_version:08X}{RESET}")
                
                if read_only:
                    # Read-only mode
                    print(f"{YELLOW}Reading current configuration{RESET}")
                    current_config = read_device_config(interface, reg_configs)
                else:
                    # Write mode
                    print(f"{YELLOW}Configuring registers{RESET}")
                    # Reset counters
                    interface.write_reg(RegisterAddress.RESET_COUNTERS, [1234])
                    # Configure registers
                    configure_device(interface, reg_configs, selected_registers)
                
                interface.close()
                
            except Exception as e:
                print(f"{RED}Error while processing IP {full_ip}: {e}{RESET}")
                
    except Exception as e:
        print(f"{RED}Configuration error: {e}{RESET}")

if __name__ == "__main__":
    main()
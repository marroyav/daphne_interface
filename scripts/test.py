import socket
import struct
import logging
import time
import re
from threading import Lock

logging.basicConfig(level=logging.INFO)

class DaphneInterface:
    def __init__(self, ip, port=2001, timeout=1.0):
        self.ip = ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(timeout)
        self.target = (ip, port)
        self.lock = Lock()

    def send_command(self, cmd):
        """Send a raw command to the hardware."""
        with self.lock:
            self.sock.sendto(cmd, self.target)
            try:
                response, _ = self.sock.recvfrom(1024)
                logging.debug(f"Received response: {response.hex()}")
                return response
            except socket.timeout:
                raise TimeoutError(f"Timeout while waiting for response from {self.ip}:{self.port}")

    def read_register(self, addr, size):
        """Read `size` 64-bit words from the register at `addr`."""
        cmd = struct.pack("BBQ", 0x00, size, addr)  # 0x00 is the read opcode
        response = self.send_command(cmd)
        if len(response) < 2 + (8 * size):
            raise ValueError(f"Incomplete response: expected {2 + (8 * size)} bytes, got {len(response)} bytes")
        return struct.unpack(f"<BB{size}Q", response)

    def write_register(self, addr, values):
        """Write a list of 64-bit words to the register at `addr`."""
        cmd = struct.pack("BBQ", 0x01, len(values), addr)  # 0x01 is the write opcode
        for value in values:
            cmd += struct.pack("Q", value)
        self.send_command(cmd)

    def close(self):
        """Close the socket connection."""
        self.sock.close()


class DaphneController:
    def __init__(self, ip):
        self.interface = DaphneInterface(ip)
        self.bias_ctrl = 0
        self.channel_confs = {}
        self.afe_confs = {}
        self.lock = Lock()

    def configure_analog_chain(self):
        """Configure the analog chain."""
        logging.info("Configuring analog chain")
        self.interface.send_command(b"CFG AFE ALL INITIAL")
        self.interface.send_command(f"WR VBIASCTRL V {self.bias_ctrl}".encode())

        for ch, conf in self.channel_confs.items():
            self.interface.send_command(f"WR TRIM CH {ch} V {conf['trim']}".encode())
            self.interface.send_command(f"WR OFFSET CH {ch} V {conf['offset']}".encode())
            self.interface.send_command(f"CFG OFFSET CH {ch} GAIN {conf['gain']}".encode())

        for afe, conf in self.afe_confs.items():
            self.interface.send_command(f"WR AFE {afe} REG 52 V {conf['reg52']}".encode())
            self.interface.send_command(f"WR AFE {afe} REG 4 V {conf['reg4']}".encode())
            self.interface.send_command(f"WR AFE {afe} REG 51 V {conf['reg51']}".encode())
            self.interface.send_command(f"WR AFE {afe} VGAIN V {conf['v_gain']}".encode())
            self.interface.send_command(f"WR BIASSET AFE {afe} V {conf['v_bias']}".encode())
        logging.info("Analog chain configured")

    def align_DDR(self):
        """Align the DDR."""
        logging.info("Aligning DDR")
        for _ in range(3):
            self.interface.write_register(0x2001, [1234])
        time.sleep(0.005)

        for afe, conf in self.afe_confs.items():
            if conf["v_gain"] > 0:
                data = self.interface.read_register(0x40000000 + (afe * 0x100000) + (8 * 0x10000), 15)
                if data[0] != 0x3F80:
                    raise RuntimeError(f"DDR alignment failed for AFE {afe}")
        logging.info("DDR alignment successful")

    def configure_trigger_mode(self, threshold, channels=[]):
        """Configure the trigger mode."""
        logging.info("Configuring trigger mode")
        if threshold > 0:
            self.interface.write_register(0x3001, [0x3])  # Enable link 0
            self.interface.write_register(0x6000, [threshold])
            mask = sum([1 << ch for ch in channels])
            self.interface.write_register(0x6001, [mask])
        else:
            self.interface.write_register(0x3001, [0xAA])
            self.interface.write_register(0x6000, [0])  # Mask everything
            for i, ch in enumerate(channels):
                reg = 0x5000 + i
                value = (ch // 8) * 10 + (ch % 8)
                self.interface.write_register(reg, [value])
        logging.info("Trigger mode configured")

    def close(self):
        """Close the connection."""
        self.interface.close()


# Example Usage
if __name__ == "__main__":
    controller = DaphneController("10.73.137.111")
    try:
        controller.configure_analog_chain()
        controller.align_DDR()
        controller.configure_trigger_mode(threshold=16383, channels=[0, 1, 2, 3])
    finally:
        controller.close()
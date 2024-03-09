"""
Libraries to talk with specific hardware in daphne
"""
from time import sleep
from . import oei
import numpy as np
import time
import unicodedata

def remove_control_characters(s):
    return "".join(ch for ch in s if unicodedata.category(ch)[0]!="C")

class Command:
    def __init__(self,ip, cmd_string, get_response=True):
        self.device = oei.OEI(ip)
        self.cmd_bytes = [ord(ch) for ch in cmd_string]
        self.cmd_bytes.append(0x0d)
        for i in range(0, len(self.cmd_bytes), 50):
            self.device.write_fifo(0x90000000, self.cmd_bytes[i*50:(i+1)*50])
        self.response = self.get_response_data() if get_response else None
        self.device.close()

    def get_response_data(self):
        response = ""
        self.more = 40
        while self.more > 0:
            response_bytes = self.device.read_fifo(0x90000000,50)
            for b in response_bytes[2:]:
                if b == 255:
                    break
                elif b in (1, 2, 3):
                    response += f"[{['START', 'RESULT', 'END'][b-1]}]"
                elif chr(b).isprintable:
                    self.more = 40
                    response = response + chr(b)
            sleep(0.005)
            self.more -= 1
        response = response + chr(0)
        return remove_control_characters(response)

class ReadCurrent:
    def __init__(self, ip, ch=0, iterations=1):
        self.current_avg = []
        for _ in range(iterations):
            try:
                response = Command(ip, f'RD CM CH {ch}').response
                self.current_avg.append(float(response.split("(mV)= -")[1][:7]))
                # print (response)
            except Exception as e:
                print(f"Error reading current: {e}")
        self.current = np.mean(self.current_avg)

class ReadVoltages:
    def __init__(self, ip):
        response = Command(ip, f'RD VM ALL').response
        self.b_vector=[float(response.split(f"VBIAS{i}=")[1][:7]) for i in range (5)]



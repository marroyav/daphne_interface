"""
Libraries to talk with specific hardware in daphne
"""
from time import sleep
from numpy import mean
import time
import unicodedata
import socket
import struct
import signal

def signal_handler(signum, frame):
    time.sleep(0.5)
    raise TimeoutError("Command execution timed out")

def timeout_handler(func):
    def wrapper(*args, **kwargs):
        signal.signal(signal.SIGALRM, signal_handler)

        while True:
            signal.alarm(1)
            try:
                result = func(*args, **kwargs)
                signal.alarm(0)
            except:
                continue
            return result
    return wrapper

class daphne(object):
    @timeout_handler
    def __init__(self,ipaddr,port=2001):
        self.sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.target = (ipaddr,port)
    @timeout_handler
    def read_reg(self,addr,size):
        cmd = struct.pack("BB",0x00,size)
        cmd += struct.pack("Q",addr)
        self.sock.sendto(cmd,self.target)
        d,a = self.sock.recvfrom(2+(8*size))
        return struct.unpack(f"<BB{size}Q",d)
    @timeout_handler
    def write_reg(self,addr,data):
        cmd = struct.pack("BB",1,len(data))
        cmd += struct.pack("Q",addr)
        for i in data:
            cmd += struct.pack("Q",i)
        self.sock.sendto(cmd,self.target)
    @timeout_handler
    def read_fifo(self,addr,size):
        cmd = struct.pack("BB",0x08,size)
        cmd += struct.pack("Q",addr)
        self.sock.sendto(cmd,self.target)
        d,a = self.sock.recvfrom(2+(8*size))
        return struct.unpack(f"<BB{size}Q",d)
    @timeout_handler
    def write_fifo(self,addr,data):
        cmd = struct.pack("BB",0x09,len(data))
        cmd += struct.pack("Q",addr)
        for i in data:
            cmd += struct.pack("Q",i)
        self.sock.sendto(cmd,self.target)
    @timeout_handler
    def close(self):
        self.sock.close()
    @timeout_handler
    def command(self, cmd_string):
        cmd_bytes = [ord(ch) for ch in cmd_string]
        cmd_bytes.append(0x0d)
        for i in range(0, len(cmd_bytes), 50):
            self.write_fifo(0x90000000, cmd_bytes[i*50:(i+1)*50])
        return self.get_response_data()

    def get_response_data(self):
        response = ""
        self.more = 40
        while self.more > 0:
            response_bytes = self.read_fifo(0x90000000,50)
            for b in response_bytes[2:]:
                if b == 255:
                    break
                elif b in (1, 2, 3):
                    response += f"[{['START', 'RESULT', 'END'][b-1]}]"
                elif chr(b).isprintable:
                    self.more = 40
                    response = response + chr(b)
            sleep(0.007)
            self.more -= 1
        response = response + chr(0)
        return self.remove_control_characters(response)

    def read_current(self, ch=0,iterations=3):
        self.current = None
        counter=0
        while self.current is None and counter<50:
            try:
                self.current = [float(self.command(f'RD CM CH {ch}').split("(mV)= ")[1][:8]) for i in range (iterations)]
                counter+=1
            except:
                if counter>=50:
                    self.close()
                else:
                    pass
        return mean(self.current)

    def read_bias(self):
        info=self.command(f'RD VM ALL')
        b_vector=[float(info.split(f"VBIAS{i}=")[1][:6]) for i in range (5)]
        return b_vector


    def remove_control_characters(self,s):
        return "".join(ch for ch in s if unicodedata.category(ch)[0]!="C")


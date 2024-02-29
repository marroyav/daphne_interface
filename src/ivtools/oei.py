"""
Operator Entry Interface. 
"""

import socket
import struct

class OEI(object):

    def __init__(self,ipaddr,port=2001):
        self.sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.target = (ipaddr,port)

    def read_reg(self,addr,size): 
        cmd = struct.pack("BB",0x00,size) 
        cmd += struct.pack("Q",addr)
        self.sock.sendto(cmd,self.target)
        d,a = self.sock.recvfrom(2+(8*size))
        return struct.unpack(f"<BB{size}Q",d) 

    def write_reg(self,addr,data): 
        cmd = struct.pack("BB",1,len(data)) 
        cmd += struct.pack("Q",addr)
        for i in data:
            cmd += struct.pack("Q",i)
        self.sock.sendto(cmd,self.target)

    def read_fifo(self,addr,size):
        cmd = struct.pack("BB",0x08,size) 
        cmd += struct.pack("Q",addr)
        self.sock.sendto(cmd,self.target)
        d,a = self.sock.recvfrom(2+(8*size))
        return struct.unpack(f"<BB{size}Q",d)

    def write_fifo(self,addr,data): 
        cmd = struct.pack("BB",0x09,len(data)) 
        cmd += struct.pack("Q",addr)
        for i in data:
            cmd += struct.pack("Q",i)
        self.sock.sendto(cmd,self.target)

    def close(self):
        self.sock.close()


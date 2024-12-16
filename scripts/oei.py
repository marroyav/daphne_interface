# rewrite for python 3 JTO

import socket
import struct

class OEI(object):

    def __init__(self,ipaddr):
        self.sock = socket.socket(socket.AF_INET,
                                  socket.SOCK_DGRAM)
        self.target = (ipaddr,2001)

    def read(self,addr,num): # read memory (addr inrem)
        cmd = b''
        cmd += struct.pack("B",0x00) # read operation
        cmd += struct.pack("B",num)  # read N words
        cmd += struct.pack("Q",addr) # starting addr
        self.sock.sendto(cmd,self.target)
        d,a = self.sock.recvfrom(2+(8*num))
        fmt = "<BB%dQ"%num
        temp = struct.unpack(fmt,d)
        return temp  # (type, seq, data(1), ... ,data(num))

    def write(self,addr,data): # write memory (addr increm)
        cmd = b''
        cmd += struct.pack("B",1)          # write operation
        cmd += struct.pack("B",len(data))  # write n words
        cmd += struct.pack("Q",addr)
        for i in data:
            cmd += struct.pack("Q",i)
        self.sock.sendto(cmd,self.target)

    def readf(self,addr,num): # read FIFO (addr no increm)
        cmd = b''
        cmd += struct.pack("B",0x08)  # read operation, no increm
        cmd += struct.pack("B",num)   # read N words
        cmd += struct.pack("Q",addr)  # starting addr
        self.sock.sendto(cmd,self.target)
        d,a = self.sock.recvfrom(2+(8*num))
        fmt = "<BB%dQ"%num
        temp = struct.unpack(fmt,d)
        return temp  # (type, seq, data(1), ... ,data(num))

    def writef(self,addr,data): # write FIFO (addr no increm)
        cmd = b''
        cmd += struct.pack("B",0x09)  # write operation, no increm
        cmd += struct.pack("B",len(data))  # write n words
        cmd += struct.pack("Q",addr)
        for i in data:
            cmd += struct.pack("Q",i)
        self.sock.sendto(cmd,self.target)

    def close(self):
        self.sock.close()

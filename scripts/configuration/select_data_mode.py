import ivtools

full_stream_ep=[]
hi_rate_self_triggr_ep=[13]
low_rate_self_triggr_ep=[]
disable=[4,5,7,9,11,12]

for i in full_stream_ep:
    thing = ivtools.interface(f"10.73.137.{100+i}")
    print (f"address= 10.73.137.{100+i}")
    thing.write_reg(0x3000,[0x002081+i*0x400000])
    print(f"parameters =  {hex(thing.read_reg(0x3000,1)[2])}")
    thing.write_reg(0x3001,[0xaa])
    print(f"data mode = {hex(thing.read_reg(0x3001,1)[2])}")
    thing.write_reg(0x6001,[0b00000000])
    print(f"channels active = {thing.read_reg(0x6001,1)[2]}")
    print(f"reg 0x5007 = {(thing.read_reg(0x5007,2))}")

    thing.close()

for i in hi_rate_self_triggr_ep:
    thing = ivtools.interface(f"10.73.137.{100+i}")
    print (f"address= 10.73.137.{100+i}")
    thing.write_reg(0x3000,[0x002081+i*0x400000])
    print(f"parameters =  {hex(thing.read_reg(0x3000,1)[2])}")
    thing.write_reg(0x3001,[0x3])
    print(f"data mode = {hex(thing.read_reg(0x3001,1)[2])}")
    thing.write_reg(0x6000,[16000])
    print(f"threshhold = {thing.read_reg(0x6000,1)[2]}")
    thing.write_reg(0x6001,[0b11111111])
    print(f"channels active = {thing.read_reg(0x6001,1)[2]}")
    #print(f"reg 0x5007 = {(thing.read_reg(0x5007,2))}")

for i in low_rate_self_triggr_ep:
    thing = ivtools.interface(f"10.73.137.{100+i}")
    print (f"address= 10.73.137.{100+i}")
    thing.write_reg(0x3000,[0x002081+i*0x400000])
    print(f"parameters =  {hex(thing.read_reg(0x3000,1)[2])}")
    thing.write_reg(0x3001,[0x3])
    print(f"data mode = {hex(thing.read_reg(0x3001,1)[2])}")
    thing.write_reg(0x6000,[30])
    print(f"threshhold = {thing.read_reg(0x6000,1)[2]}")
    thing.write_reg(0x6001,[0b11111111])
    print(f"channels active = {thing.read_reg(0x6001,1)[2]}")


for i in disable:
    thing = ivtools.interface(f"10.73.137.{100+i}")
    print (f"address= 10.73.137.{100+i}")
    thing.write_reg(0x3000,[0x002081+i*0x400000])
    print(f"parameters =  {hex(thing.read_reg(0x3000,1)[2])}")
    thing.write_reg(0x3001,[0x0])
    print(f"data mode = {hex(thing.read_reg(0x3001,1)[2])}")
    thing.write_reg(0x6001,[0b00000000])
    print(f"channels active = {thing.read_reg(0x6001,1)[2]}")

    thing.close()


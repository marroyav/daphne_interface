import ivtools

print ("DAPHNE physical scheme")
print ("ADDRESS    ",end='\t')
print ("SLOT",end='\t')
print ("REG",end='\t')
print ("MODE",)

for i in [4,5,7,9,11,12,13]:
    thing = ivtools.daphne(f"10.73.137.{100+i}")
    print(f"10.73.137.{100+i}",end='\t')
    slot = (thing.read_reg(0x3000,1)[2]>>22)
    sender = (thing.read_reg(0x3001,1)[2])
    
    print(f"{slot}",end='\t')
    print(f"{hex(sender)}",end='\t')

    if sender==0xaa:  print(f"full streaming")
    elif sender==0x3: print(f"self trigger")
    else:             print("disabled")
    
    thing.close()
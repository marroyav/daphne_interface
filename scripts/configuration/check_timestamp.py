import ivtools

for i in [4,5,7,9,11,12,13]:
    thing = ivtools.daphne(f"10.73.137.{i+100}")
    thing.write_reg(0x2000, [1234])
    print (f"time stamp in DAPHNE with ip address 10.73.137.{100+i}"  )
    a = thing.read_reg(0x40500000,4)
    for r in range (len(a)-2):
        print (a[r+2])
    thing.close()
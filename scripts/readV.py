import ivtools

for i in [4,5,7,9,11,12,13]:
    ip=f'10.73.137.{100+i}'
    k = ivtools.ReadVoltages(ip)
    print(k.b_vector)

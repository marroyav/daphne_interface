import ivtools

for i in [4,5,7,9,11,12,13]:
    daphne=ivtools.interface(f'10.73.137.{100+i}')
    k = daphne.read_bias()
    print(k)

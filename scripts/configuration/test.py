import multiprocessing

def worker(num):
    """ Worker procedure
    """
    print('Worker:', str(num))

if __name__ == '__main__':
        p1 = multiprocessing.Process(target=worker, args=(3,))
        p2 = multiprocessing.Process(target=worker, args=(10,))
        p1.start() # starting workers
        p2.start() # starting workers

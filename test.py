import math
import time
from permanent_memoization import  memoize_to_folder

@memoize_to_folder('memoization/primes')
def nth_prime(n):
    primes =  [2]
    p = 3
    while True:
        for prime in primes:
            if p % prime == 0 or prime > math.sqrt(p):
                break
        if p % prime:
            primes.append(p)
        if len(primes) >= n:
            print("The nth prime is {}".format(primes[n-1]))
            return primes[n-1]
        p += 2

def time_n(n):
    start = time.time()
    p = nth_prime(n, __recalculate=True)
    duration1 = time.time() - start
    print("Found {} in {} sec"
            .format(p, duration1))

    start = time.time()
    p = nth_prime(n)
    duration2 = time.time() - start
    print("Recalled {} in {} sec"
            .format(p, duration2))

time_n(100000)

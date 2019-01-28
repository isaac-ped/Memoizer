# Memoizer
Permanent memoization to file based on function arguments

Decorate a costly function with `@memoize_to_folder('directory')` to
automatically save the output of that function to a file,
which will be loaded if the same function is called again with the same arguments.

Also keeps track of printed statements, and will recall them on the next call
to the same function.

Attempts to name files in a human-readable format, but reverts to hashing
if the filenames grow too long.

## Use:

```python
from Memoizer import memoize_to_folder

@memoize_to_folder('primes')
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

p = nth_prime(100000)

print("Found the 100000th  prime: {}".format(p))
```

Run twice, and watch the massive speedup!


### TODO:

* Fix bug in stdout recall
* Time original and new function execution 

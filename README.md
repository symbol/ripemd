Ripemd
======

Given headache openssl devs gave to everyone, this is tiny ripemd module for python 3. Shamelessly ~~stolen~~ extracted from [pycryptodome](https://github.com/Legrandin/pycryptodome).

### Usage

Single call:
```py
from ripemd.ripemd160 import ripemd160  # import function

ripemd160(b'abc').hex() == '8eb208f7e05d987a9b044a8e98c6b087f15a0bfc'
ripemd160(b'a' * 1000000).hex() == '52783243c1697bdbe16d37f97f68f08325dc1528'
```

Update mode:
```py
from ripemd import ripemd160  # import module

h = ripemd160.new()
h.update(b'abc')
h.digest().hex() == '8eb208f7e05d987a9b044a8e98c6b087f15a0bfc'
```

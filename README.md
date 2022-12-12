# Plano

[![main](https://github.com/ssorj/plano/workflows/main/badge.svg)](https://github.com/ssorj/plano/actions?query=workflow%3Amain)

Python functions for writing shell-style system scripts.

## Installation

To install plano globally for the current user:

~~~
make install
~~~

## Example 1

`~/.local/bin/widget`:
~~~ python
#!/usr/bin/python

from plano import *

@command
def greeting(message="Howdy"):
    print(message)

if __name__ == "__main__":
    PlanoCommand(sys.modules[__name__]).main()
~~~

~~~ shell
$ widget greeting --message Hello
--> greeting
Hello
<-- greeting
OK (0s)
~~~

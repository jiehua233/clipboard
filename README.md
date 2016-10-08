# Clipboard

Share your clipboard between two computers in LAN, it supports plaintext and image(screen capture) 
and has been tested on Ubuntu and Mac.

In order to support image share, we use `pygtk` library since the `thinter` only support text.

## Setup

* Ubuntu

```
$ sudo apt-get install python-gtk2
```

* Mac

```
$ brew install pygtk
```

## Usage

    # firstly you need to know either of your ip address, just use ifconfig if you like:
    $ ifconfig 
    ......
    inet 172.16.9.23    # something like this
    ......
    # then run the clipboard tools:
    $ python clipboard.py

    # on the other computer, run:
    $ python clipboard.py 172.16.9.23

Now, you should be able to copy text or capture screen in Ubuntu and then paste in Mac.

Default it use the port `34455`, however if the port conflicts, you can easily specific another one 
by editing `SERVER_PORT` in the `clipboard.py`.

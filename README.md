# Clipboard

Share your clipboard between two computers located in the same LAN, it supports text and image(screen capture) 
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

    # firstly you need to know your ip address, just run the following command on both Ubuntu and Mac
    $ ifconfig 
    # assume ubuntu: 172.16.1.100, mac: 172.16.1.200
    # run on ubuntu
    $ python clipboard.py --remote 172.16.1.200
    # run on mac
    $ python clipboard.py --remote 172.16.1.100

Now, you should be able to copy text or capture screen in Ubuntu and then paste in Mac.

Default it use the port `34455`, however if the port conflicts, you may want to specific another one:

    $ python clipboard.py --port 45566 --remote 172.16.1.xxx:45566

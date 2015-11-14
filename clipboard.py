#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import StringIO
import argparse
import base64
import threading
import BaseHTTPServer

import gtk
import requests

""" 全局变量 """
ClipData = ''       # 剪贴板内容


def main():
    args = parse_cmdline()
    server_thread = ServerThread(args.local_port)
    server_thread.daemon = True
    server_thread.start()

    connect(args.remote_addr)

    clip_thread = ClipboardThread(args.remote_addr, args.detect_freq)
    clip_thread.daemon = True
    clip_thread.start()

    while True:
        time.sleep(1)


""" Parse the command line arguments """
def parse_cmdline():
    parser = argparse.ArgumentParser()
    parser.add_argument('--local_port', type=int, default='34567',
                        help='Specific the local server bind port, default is: 34567')
    parser.add_argument('--remote_addr', type=str, default='localhost:34567',
                        help='Specific the remote server address, e.g. 172.16.2.95:34567')
    parser.add_argument('--detect_freq', type=int, default=2,
                        help='Specific the frequency of detecting the clipboard, default is: 2(seconds)')
    args = parser.parse_args()
    return args


""" Ping the remote server """
def connect(remote_addr):
    while True:
        print 'Connecting to %s ...' % remote_addr
        try:
            r = requests.get('http://%s' % remote_addr)
            if r.status_code == 200:
                print r.text
                break
        except requests.exceptions.ConnectionError:
            print 'Connect fail !'
            time.sleep(1)


class ServerThread(threading.Thread):
    """ 通讯线程 """

    def __init__(self, port):
        threading.Thread.__init__(self)
        self.port = port

    def run(self):
        print "Staring Service on port: %s" % self.port
        server = BaseHTTPServer.HTTPServer(('', self.port), ClipboardHandler)
        server.serve_forever()


class ClipboardHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    def do_GET(self):
        self.response(200)
        self.wfile.write('pong')

    def do_POST(self):
        if self.path in ['/text', '/image']:
            self.response(200)
            self.wfile.write('done')
            self.set_clipboard()

        else:
            self.response(404)

    def set_clipboard(self):
        print 'Receiving data...'
        content = self.get_content()
        lock_set_clipdata(content)

        clipboard = Clipboard()
        if self.path == '/text':
            clipboard.set_text(content)
        elif self.path == '/image':
            clipboard.set_image(content)

    def response(self, code):
        self.send_response(code)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def get_content(self):
        length = int(self.headers.getheader('Content-length'))
        body = self.rfile.read(length)
        return body


class ClipboardThread(threading.Thread):
    """ 剪贴板监听,数据同步线程 """

    def __init__(self, remote_addr, detect_freq):
        threading.Thread.__init__(self)
        self.remote_addr = remote_addr
        self.detect_freq = detect_freq

    def run(self):
        global ClipData
        clipboard = Clipboard()
        while True:
            clip_text = clipboard.get_text()
            clip_image = clipboard.get_image()
            if clip_text is None and clip_image is None or \
                    ClipData == clip_text or ClipData == clip_image:
                time.sleep(self.detect_freq)
                continue

            if clip_text:
                if clip_text != ClipData:
                    lock_set_clipdata(clip_text)
                    self.sync_loop('text', clip_text)
            elif clip_image:
                if clip_image != ClipData:
                    lock_set_clipdata(clip_image)
                    self.sync_loop('image', clip_image)

    def sync_loop(self, mimetype, content):
        url = 'http://%s/%s' % (self.remote_addr, mimetype)
        while True:
            print 'Sending clipboard data to %s ...' % self.remote_addr
            try:
                r = requests.post(url, content)
                if r.status_code == 200:
                    print r.text
                    break
            except requests.exceptions.ConnectionError:
                print 'Send data fail !'
                time.sleep(1)


class Clipboard():
    """ 剪贴板类 """

    def __init__(self):
        self.clipboard = gtk.Clipboard()
        self.clipboard.clear()

    def get_text(self):
        content = None
        if self.clipboard.wait_is_text_available():
            content = self.clipboard.wait_for_text()

        return content

    def get_image(self):
        content = None
        if self.clipboard.wait_is_image_available():
            content = self._pixbuf2b64(self.clipboard.wait_for_image())

        return content

    def set_text(self, text):
        self.clipboard.set_text(text)
        self.clipboard.store()

    def set_image(self, b64_pixbuf):
        pixbuf = self._b642pixbuf(b64_pixbuf)
        self.clipboard.set_image(pixbuf)
        self.clipboard.store()

    def _pixbuf2b64(self, pixbuf):
        fh = StringIO.StringIO()
        pixbuf.save_to_callback(fh.write, 'png')
        return base64.b64encode(fh.getvalue())

    def _b642pixbuf(self, b64):
        pixloader = gtk.gdk.PixbufLoader('png')
        pixloader.write(base64.b64decode(b64))
        pixloader.close()
        return pixloader.get_pixbuf()


def lock_set_clipdata(content):
    global ClipData
    lock = threading.Lock()
    lock.acquire()
    ClipData = content
    lock.release()


if __name__ == "__main__":
    main()

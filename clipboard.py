#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import StringIO
import argparse
import base64
import threading
import BaseHTTPServer

try:
    import gtk
except ImportError:
    try:
        # python 2
        import Tkinter as tk
    except ImportError:
        # python 3
        import tkinter as tk

import requests


""" 全局常量 """
CLIP_NONE = 0
CLIP_TEXT = 1
CLIP_IMAGE = 2

""" 全局变量 """
ClipBoard = None    # 剪贴板对象
ClipData = ''       # 剪贴板内容


def main():
    global ClipBoard
    ClipBoard = init_clipboard()

    args = parse_cmdline()
    server_thread = ServerThread(args.local)
    server_thread.daemon = True
    server_thread.start()

    connect(args.remote)

    clip_thread = ClipboardThread(args.remote)
    clip_thread.daemon = True
    clip_thread.start()

    while True:
        time.sleep(1)


def parse_cmdline():
    """ Parse the command line arguments """
    parser = argparse.ArgumentParser()
    parser.add_argument('--local', type=str, default='0.0.0.0:34567',
                        help='Specific the local server address, e.g. 172.16.2.90:34567, default is: 0.0.0.0:34567')
    parser.add_argument('--remote', type=str, default='127.0.0.1:34567',
                        help='Specific the remote server address, e.g. 172.16.2.95:34567, default is: 127.0.0.1:34567')
    args = parser.parse_args()
    return args


def init_clipboard():
    """初始化剪贴板

    优先使用gtk，如果该库不存在则使用python内置Tkinter """
    clipboard = None
    try:
        clipboard = ClipboardGTK()
    except NameError:
        clipboard = ClipboardTK()

    return clipboard


def connect(remote):
    """ Ping the remote server """
    while True:
        print 'Connecting to %s ...' % remote
        try:
            r = requests.get('http://%s' % remote)
            if r.status_code == 200:
                print r.text
                break
        except requests.exceptions.ConnectionError:
            print 'Connect fail !'
            time.sleep(1)


def lock_set_clipdata(content):
    """ 线程中改变全局变量加锁 """
    global ClipData
    lock = threading.Lock()
    lock.acquire()
    ClipData = content
    lock.release()


class ServerThread(threading.Thread):
    """ 通讯线程 """

    def __init__(self, local):
        threading.Thread.__init__(self)
        self.local = local

    def run(self):
        print "Staring Service on %s \n" % self.local
        addr = self.local.split(':')[0]
        port = int(self.local.split(':')[1])
        server = BaseHTTPServer.HTTPServer((addr, port), ClipboardHandler)
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
        if self.path == '/text':
            mimetype = CLIP_TEXT
        elif self.path == '/image':
            mimetype = CLIP_IMAGE

        global ClipBoard
        content = self.get_content()
        ClipBoard.set_content(mimetype, content)
        lock_set_clipdata(content)

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

    def __init__(self, remote):
        threading.Thread.__init__(self)
        self.remote = remote

    def run(self):
        global ClipData, ClipBoard
        while True:
            mimetype, content = ClipBoard.get_content()
            if content is None or content == ClipData:
                time.sleep(2)
                continue

            self.sync_loop(mimetype, content)

    def sync_loop(self, mimetype, content):
        router = ''
        if mimetype == CLIP_TEXT:
            router = 'text'
        elif mimetype == CLIP_IMAGE:
            router = 'image'

        url = 'http://%s/%s' % (self.remote, router)
        # 重发计数器
        counter = 10
        while counter > 0:
            print 'Sending data to %s ...' % self.remote
            try:
                r = requests.post(url, content)
                if r.status_code == 200:
                    lock_set_clipdata(content)
                    print r.text
                    break
            except requests.exceptions.ConnectionError:
                print 'Send fail !'
                time.sleep(2)
                counter -= 1


class ClipboardTK():
    """基于Tkinter的剪贴板类

    python内置，仅支持剪贴板纯文本操作
    """
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()

    def get_content(self):
        text = self.get_text()
        if text is None:
            return CLIP_TEXT, text

        return CLIP_NONE, None

    def set_content(self, mimetype, content):
        if mimetype == CLIP_TEXT:
            self.set_text(content)

    def get_text(self):
        content = None
        try:
            content = self.root.clipboard_get()
        except tk._tkinter.TclError:
            pass

        return content

    def set_text(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)


class ClipboardGTK():
    """基于GTK的剪贴板类

    需要安装pygtk，支持剪贴板纯文本，图像的操作
    """
    def __init__(self):
        self.clipboard = gtk.Clipboard()
        self.clipboard.clear()

    def get_content(self):
        """ 获取剪贴板内容，返回 CLIP_TYPTE, content """
        text = self.get_text()
        if text is not None:
            return CLIP_TEXT, text

        image = self.get_image()
        if image is not None:
            return CLIP_IMAGE, image

        return CLIP_NONE, None

    def set_content(self, mimetype, content):
        if mimetype == CLIP_TEXT:
            self.set_text(content)
        elif mimetype == CLIP_IMAGE:
            self.set_image(content)

    def get_text(self):
        content = None
        if self.clipboard.wait_is_text_available():
            content = self.clipboard.wait_for_text()

        return content

    def get_image(self):
        content = None
        if self.clipboard.wait_is_image_available():
            pixbuf = self.clipboard.wait_for_image()
            # Mac 下测试获取截图为空
            if pixbuf is None:
                pixbuf = self.clipboard.wait_for_contents('image/tiff').get_pixbuf()

            content = self._pixbuf2b64(pixbuf)

        return content

    def set_text(self, text):
        self.clipboard.set_text(text)
        self.clipboard.store()

    def set_image(self, b64_pixbuf):
        pixbuf = self._b642pixbuf(b64_pixbuf)
        self.clipboard.set_image(pixbuf)
        self.clipboard.store()

    def _pixbuf2b64(self, pixbuf):
        """ gtk.gdk.Pixbuf对象转化为base64编码字符串 """
        fh = StringIO.StringIO()
        pixbuf.save_to_callback(fh.write, 'png')
        return base64.b64encode(fh.getvalue())

    def _b642pixbuf(self, b64):
        """ base64编码字符串转换为gtk.gdk.Pixbuf """
        pixloader = gtk.gdk.PixbufLoader('png')
        pixloader.write(base64.b64decode(b64))
        pixloader.close()
        return pixloader.get_pixbuf()


if __name__ == "__main__":
    main()

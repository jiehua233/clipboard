#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding("utf8")
import time
import StringIO
import argparse
import base64
import threading
import httplib
import BaseHTTPServer
import gtk


""" 全局常量 """
CLIP_NONE = 0
CLIP_TEXT = 1
CLIP_IMAGE = 2

SERVER_PORT = 34567

""" 全局变量 """
ClipData = ""


def main():
    # 解析命令行参数
    args = parse_cmdline()

    # 启动数据接收线程
    server_thread = ServerThread(args.local)
    server_thread.daemon = True
    server_thread.start()
    time.sleep(0.1)

    # 启动数据发送线程
    client_thread = ClientThread(args.remote)
    client_thread.daemon = True
    client_thread.start()
    time.sleep(0.1)

    # 主线程，休眠
    while True:
        time.sleep(0.1)


def parse_cmdline():
    """ Parse the command line arguments """
    parser = argparse.ArgumentParser()
    parser.add_argument('--local', type=str, default='0.0.0.0:34567',
                        help='Specific the local server address, e.g. 172.16.2.90:34567, default is: 0.0.0.0:34567')
    parser.add_argument('--remote', type=str, default='127.0.0.1:34567',
                        help='Specific the remote server address, e.g. 172.16.2.95:34567, default is: 127.0.0.1:34567')
    args = parser.parse_args()
    return args


class ClientThread(threading.Thread):
    """ 数据发送线程 """

    def __init__(self, remote):
        threading.Thread.__init__(self)
        print 'Using PYGTK...'
        if ':' not in remote:
            self.remote = '%s:%s' % (remote, SERVER_PORT)
        else:
            self.remote = remote

    def run(self):
        self.ping(self.remote)
        global ClipData
        cb = ClipboardGTK()
        content, success = None, True
        while True:
            mimetype, content = cb.get_content()
            if content is None or content == ClipData:
                time.sleep(2)
            else:
                ClipData = content
                success = False

            # 发送是否成功，不成功持续发送
            if not success:
                success = self.send(mimetype, content)

    def ping(self, remote):
        """ Ping the remote server """
        while True:
            print 'Ping %s ...' % remote
            try:
                resp = self.request(remote)
                if resp.status == 200:
                    print 'Remote(%s): %s' % (remote, resp.read())
                    break
            except Exception as e:
                print 'Ping fail: %s' % e
                time.sleep(1)

    def request(self, remote, method='GET', url='/', body=''):
        conn = httplib.HTTPConnection(remote)
        conn.request(method, url, body)
        resp = conn.getresponse()
        conn.close()
        return resp

    def send(self, mimetype, content):
        success = False
        url = '/'
        if mimetype == CLIP_TEXT:
            url = '/text'
        elif mimetype == CLIP_IMAGE:
            url = '/image'

        print 'Sending data to %s ...' % self.remote
        try:
            resp = self.request(self.remote, 'POST', '%s' % url, content)
            if resp.status == 200:
                success = True
                print 'Remote(%s): %s' % (self.remote, resp.read())
        except Exception as e:
            print 'Send fail: %s' % e

        return success


class ServerThread(threading.Thread):
    """ 数据接收线程 """

    def __init__(self, local):
        threading.Thread.__init__(self)
        self.local = local

    def run(self):
        try:
            addr_port = self.local.split(':')
            addr = addr_port[0] if addr_port[0] != '' else '0.0.0.0'
            port = int(addr_port[1]) if addr_port[1].isdigit() else SERVER_PORT
            print "Staring Service on %s" % self.local
            server = BaseHTTPServer.HTTPServer((addr, port), RequestHandler)
            server.serve_forever()
        except Exception as e:
            print "Can't bind server on %s, Error: %s" % (self.local, e)
            return


class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    def do_GET(self):
        self.response(200)
        self.wfile.write('pong')

    def do_POST(self):
        if self.path in ['/text', '/image']:
            self.response(200)
            self.wfile.write('done')

            print 'Receiving data...'
            if self.path == '/text':
                mimetype = CLIP_TEXT
            elif self.path == '/image':
                mimetype = CLIP_IMAGE

            content = self.get_body()
            global ClipData
            ClipData = content
            cb = ClipboardGTK()
            cb.set_content(mimetype, content)

        else:
            self.response(404)

    def response(self, code):
        self.send_response(code)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def get_body(self):
        length = int(self.headers.getheader('Content-length'))
        body = self.rfile.read(length)
        return body


class ClipboardGTK():
    """基于GTK的剪贴板类

    需要安装pygtk，支持剪贴板纯文本，图像的操作
    """
    def __init__(self):
        self.clipboard = gtk.Clipboard()

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

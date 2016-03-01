#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @author: jiehua233@gmail.com
#

import sys
import time
import StringIO
import argparse
import base64
import logging
import threading
import httplib
import BaseHTTPServer
import gtk


reload(sys)
sys.setdefaultencoding("utf8")


""" 全局常量 """
CLIP_NONE = 0
CLIP_TEXT = 1
CLIP_IMAGE = 2
SERVER_PORT = 34455


""" 全局变量 """
CLIPBOARD = None
CLIP_DATA = ""


def main():
    # 解析命令行参数
    args = parse_cmdline()

    # clipboard
    global CLIPBOARD
    CLIPBOARD = ClipboardGTK()

    # 启动数据接收线程
    server_thread = ServerThread(args.port)
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
    parser.add_argument('--port', type=int, default=SERVER_PORT,
                        help='Specific the local server port, default is: %d' % SERVER_PORT)
    parser.add_argument('--remote', type=str, default='127.0.0.1:%d' % SERVER_PORT,
                        help='Specific the remote server address, default is: 127.0.0.1:%d' % SERVER_PORT)
    args = parser.parse_args()
    return args


def get_logger():
    logger = logging.getLogger('clipboard')
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    ch.setLevel(logging.DEBUG)
    logger.addHandler(ch)
    return logger


logger = get_logger()

class ClientThread(threading.Thread):
    """ 数据发送线程 """

    def __init__(self, remote):
        threading.Thread.__init__(self)
        logger.info('Clipboard using PYGTK...')
        self.remote = remote if ':' in remote else '%s:%s' % (remote, SERVER_PORT)
        self.ping()

    def ping(self):
        logger.info('Connecting %s', self.remote)
        try:
            resp = self.request(self.remote)
            if resp.status == 200:
                logger.info('%s is ok: %s', self.remote, resp.read())
        except Exception as e:
            logger.error('Connect fail: %s', e)

    def run(self):
        global CLIP_DATA, CLIPBOARD
        content, success = None, True
        while True:
            mimetype, content = CLIPBOARD.get_content()
            if content is None or content == CLIP_DATA:
                time.sleep(1)
            else:
                CLIP_DATA = content
                success = False

            # 发送是否成功，不成功持续发送
            if not success:
                success = self.send(mimetype, content)

    def send(self, mimetype, content):
        success = False
        url = '/'
        if mimetype == CLIP_TEXT:
            url = '/text'
        elif mimetype == CLIP_IMAGE:
            url = '/image'
        else:
            success = True
            return

        msg = "Send %s to %s: " % (url[1:], self.remote)
        try:
            resp = self.request(self.remote, 'POST', '%s' % url, content)
            if resp.status == 200:
                success = True
                logger.info(msg + resp.read())
            else:
                logger.warn(msg + resp.status)

        except Exception as e:
            logger.error(msg + str(e))

        return success

    def request(self, remote, method='GET', url='/', body=''):
        conn = httplib.HTTPConnection(remote)
        conn.request(method, url, body)
        resp = conn.getresponse()
        conn.close()
        return resp


class ServerThread(threading.Thread):
    """ 数据接收线程 """

    def __init__(self, port):
        threading.Thread.__init__(self)
        self.port = port

    def run(self):
        try:
            logger.info("Staring server on 0.0.0.0:%s", self.port)
            server = BaseHTTPServer.HTTPServer(("0.0.0.0", self.port), RequestHandler)
            server.serve_forever()
        except Exception as e:
            logger.error("Start server fail: %s", e)


class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    def do_GET(self):
        self.response(200)
        self.wfile.write('pong')

    def do_POST(self):
        if self.path == '/text':
            mimetype = CLIP_TEXT
        elif self.path == '/image':
            mimetype = CLIP_IMAGE
        else:
            self.response(404)

        # 设置剪贴板数据
        global CLIP_DATA, CLIPBOARD
        content = self.get_body()
        CLIP_DATA = content
        CLIPBOARD.set_content(mimetype, content)
        # response
        msg = 'type:%s, length:%s' % (self.path[1:], len(content))
        logger.info("Received data %s", msg)
        self.response(200)
        self.wfile.write("Done %s" % msg)

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
        try:
            content = self.clipboard.wait_for_text() if self.clipboard.wait_is_text_available() else None
        except Exception as e:
            logger.error("get text err:", e)

        return content

    def get_image(self):
        content = None
        try:
            if self.clipboard.wait_is_image_available():
                pixbuf = self.clipboard.wait_for_image()
                # Mac 下测试获取截图为空
                if pixbuf is None:
                    pixbuf = self.clipboard.wait_for_contents('image/tiff').get_pixbuf()

                content = self._pixbuf2b64(pixbuf)
        except Exception as e:
            logger.error("get image err:", e)

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

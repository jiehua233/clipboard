#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @author: jiehua233@gmail.com
#

import os
import sys
import time
import socket
import StringIO
import base64
import logging
import threading
import httplib
import BaseHTTPServer
import gtk


reload(sys)
sys.setdefaultencoding("utf8")
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


""" global constants """
CLIP_NONE = 0
CLIP_TEXT = 1
CLIP_IMAGE = 2
SERVER_PORT = 34455


""" global variables """
REMOTE_IP = None
CLIPBOARD = None
CLIP_DATA = ""


def main():
    # clipboard
    global CLIPBOARD, REMOTE_IP
    CLIPBOARD = ClipboardGTK()

    if len(sys.argv) == 2:
        if check_ip(sys.argv[1]):
            REMOTE_IP = sys.argv[1]
        else:
            logging.error("remote ip %s is invalid", sys.argv[1])
            sys.exit(-1)
    else:
        ip = get_local_ip()
        logging.info(
            "Your server ip is %s, run the following command on your another computer:\n\n\
            python clipboard.py %s\n", ip, ip)

    # server
    server_thread = ServerThread()
    server_thread.daemon = True
    server_thread.start()
    time.sleep(0.1)

    # client
    client_thread = ClientThread()
    client_thread.daemon = True
    client_thread.start()
    time.sleep(0.1)

    # 主线程，休眠
    while True:
        time.sleep(0.1)


class ServerThread(threading.Thread):
    """ 数据接收线程 """

    def __init__(self):
        logging.info("Starting server thread...")
        threading.Thread.__init__(self)

    def run(self):
        try:
            server = BaseHTTPServer.HTTPServer(("0.0.0.0", SERVER_PORT), RequestHandler)
            logging.info("Server listen on 0.0.0.0:%s", SERVER_PORT)
            server.serve_forever()
        except Exception as e:
            logging.error("Server error: %s", e)
            os._exit(-1)


class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    def do_GET(self):
        global REMOTE_IP
        REMOTE_IP = self.client_address[0]
        logging.info("Get a remote client from %s", REMOTE_IP)
        self.response(200)

    def do_POST(self):
        global REMOTE_IP
        REMOTE_IP = self.client_address[0]
        if self.path == '/text':
            mimetype = CLIP_TEXT
        elif self.path == '/image':
            mimetype = CLIP_IMAGE
        else:
            return self.response(404)

        # 设置剪贴板数据
        global CLIP_DATA, CLIPBOARD
        CLIP_DATA = self.get_body()
        CLIPBOARD.set_content(mimetype, CLIP_DATA)
        logging.info("Receive data from %s, length: %s", self.path, len(CLIP_DATA))
        self.response(200)

    def log_message(self, format, *args):
        # disable log
        return

    def response(self, code):
        self.send_response(code)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write("done")

    def get_body(self):
        length = int(self.headers.getheader("Content-length"))
        body = self.rfile.read(length)
        return body


class ClientThread(threading.Thread):
    """ 数据发送线程 """

    def __init__(self):
        logging.info("Starting client thread...")
        threading.Thread.__init__(self)
        if REMOTE_IP:
            try:
                resp = self.request()
                logging.info("Ping server, http code: %s", resp.status)
            except Exception as e:
                logging.error("Connect error: %s", e)
                os._exit(-1)
        else:
            logging.info("Waiting for the remote client...")

    def run(self):
        global CLIP_DATA, CLIPBOARD
        content = None
        while True:
            time.sleep(1)
            mimetype, content = CLIPBOARD.get_content()
            if content is None or content == CLIP_DATA:
                continue

            CLIP_DATA = content
            self.send(mimetype, content)

    def send(self, mimetype, content):
        url = '/'
        if mimetype == CLIP_TEXT:
            url = '/text'
        elif mimetype == CLIP_IMAGE:
            url = '/image'
        else:
            return

        msg = "Send %s, result: " % url[1:]
        try:
            resp = self.request("POST", url, content)
            if resp.status == 200:
                logging.info(msg + resp.read())
            else:
                logging.warn(msg + resp.status)

        except Exception as e:
            logging.error(msg + str(e))

    def request(self, method='GET', url='/', body=''):
        assert REMOTE_IP is not None, "REMOTE_IP is None"
        remote = "%s:%s" % (REMOTE_IP, SERVER_PORT)
        conn = httplib.HTTPConnection(remote)
        conn.request(method, url, body)
        resp = conn.getresponse()
        conn.close()
        return resp


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
            logging.error("get text err: %s", e)

        return content

    def get_image(self):
        content = None
        try:
            if self.clipboard.wait_is_image_available():
                pixbuf = self.clipboard.wait_for_image()
                # Mac 下测试获取截图为空
                if pixbuf is None:
                    pixbuf = self.clipboard.wait_for_contents("image/tiff").get_pixbuf()

                content = self._pixbuf2b64(pixbuf)
        except Exception as e:
            logging.error("get image err: %s", e)

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


def check_ip(ip):
    if ip.count(".") != 3:
        return False

    for b in ip.split("."):
        if not (b.isdigit() and int(b)>= 0 and int(b) <= 255):
            return False

    return True


def get_local_ip():
    # from /etc/hosts
    for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
        if not ip.startswith("127."):
            return ip

    # socket dgram
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 53))
    ip = s.getsockname()[0]
    s.close()
    return ip


if __name__ == "__main__":
    main()

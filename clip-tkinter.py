#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding("utf8")
import time
import argparse
import threading
import httplib
import BaseHTTPServer
import Queue
import Tkinter as tk


""" 全局常量 """
CLIP_NONE = 0
CLIP_TEXT = 1
CLIP_IMAGE = 2

SERVER_PORT = 34567

""" 全局变量 """
RecvQueue = Queue.Queue(100000)    # 接收到的数据
SendQueue = Queue.Queue(100000)    # 即将发送的数据


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

    # 主线程，检测剪贴板数据
    clipboard = ClipboardTK()
    clipboard.run()


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
        self.remote = remote
        if ':' not in remote:
            self.remote = '%s:%s' % (remote, SERVER_PORT)
        else:
            self.remote = remote

    def run(self):
        self.ping(self.remote)
        global SendQueue
        content, success = None, True
        while True:
            # 阻塞进程
            try:
                mimetype, content = SendQueue.get(timeout=1)
                success = False
            except Queue.Empty:
                pass

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

            global RecvQueue
            RecvQueue.put((mimetype, self.get_body()))

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


class ClipboardTK():
    """基于Tkinter的剪贴板类

    python内置，仅支持剪贴板纯文本操作
    """
    def __init__(self):
        print 'Using Tkinter...'
        self.root = tk.Tk()
        self.root.withdraw()

    def get_content(self):
        self.root.after(30, self.get_text())
        self.root.update()
        time.sleep(0.1)
        text = self.content
        if text is not None:
            return CLIP_TEXT, text

        return CLIP_NONE, None

    def set_content(self, mimetype, content):
        if mimetype == CLIP_TEXT:
            self.set_text(content)

    def get_text(self):
        self.content = None
        try:
            self.content = self.root.clipboard_get()
        except tk._tkinter.TclError:
            pass

    def set_text(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    def run(self):
        """ Tkinter必须在主线程运行 """
        clipdata = ''
        global RecvQueue, SendQueue
        while True:
            # 是否有数据发送过来
            try:
                mimetype, content = RecvQueue.get(timeout=1)
                self.set_content(mimetype, content)
                clipdata = content
            except Queue.Empty:
                pass

            # 剪贴板数据是否发生变化
            mimetype, content = self.get_content()
            if content is not None and content != clipdata:
                SendQueue.put((mimetype, content))
                clipdata = content


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""估值区间六步决策台 · 本地网站服务

用法: python serve_dashboard.py [端口]
默认端口 8976，绑定 0.0.0.0（同局域网手机/平板可访问）。
自动跳转到最新生成的门户 HTML；调度器每日重写后刷新浏览器即可看到新数据。
"""
import http.server
import os
import socketserver
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "output")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8976
HOME = "估值雷达估值区间决策门户.html"


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=OUT, **kwargs)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.path = "/" + HOME
        return super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    if not os.path.exists(os.path.join(OUT, HOME)):
        print("门户文件不存在:", os.path.join(OUT, HOME))
        sys.exit(1)
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"估值区间六步决策台: http://localhost:{PORT}")
        print("局域网访问: http://<本机IP>:{PORT}   |   按 Ctrl+C 停止")
        httpd.serve_forever()

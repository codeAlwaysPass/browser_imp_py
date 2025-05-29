import socket
import ssl
import time
import gzip

# 全局连接池，用作连接复用
connections = {}

# 全局缓存
cache = {}

class URL:
    def __init__(self, url):
        # 处理url不合规的情况
        if url == "about:blank":
            self.scheme = "about"
            self.host = ""
            self.path = ""
            self.port = None
            self.blank = True
            return
        
        self.blank = False
        # 将传入的url拆分为协议和剩余部分
        self.scheme, url = url.split("://", 1)
        # 检查协议是否在白名单内
        assert self.scheme in ['http', 'https']
        # 为url补全路径部分
        if "/" not in url:
            url = url + "/"
        # 将剩余url拆分为主机和路径部分
        self.host, url = url.split("/", 1)
        self.path = "/" + url
        
        # 根据协议选择端口
        if self.scheme == 'http':
            self.port = 80
        elif self.scheme == 'https':
            self.port = 443
        
        # 如果主机包含端口号, 则拆分出来
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)
            
    # 读取chunked编码的body
    def read_chunked_body(self, response):
        body = b""
        while True:
            # 读取chunk size
            size_line = response.readline().decode("utf-8").strip()
            if size_line == "":
                continue
            size = int(size_line, 16)
            if size == 0:
                break
            # 根据size读取chunk的大小
            chunk = response.read(size)
            # chunk拼接
            body += chunk
            
            # 读掉CRLF
            response.read(2)
    
        return body
    
    def request(self, method = "GET", redirect_limit = 10):
        # 处理空白页情况
        if self.blank:
            return ""
        
        # 生成连接键
        key = (self.scheme, self.host, self.port)
        # 生成缓存键
        cache_key = (method, self.scheme + "://" + self.host + self.path)
        
        # 如果命中缓存，直接返回缓存内容; 清理过期缓存
        if cache_key in cache:
            entry = cache[cache_key]
            if entry["max-age"] is not None:
                if time.time() - entry["time-stamp"] < entry["max-age"]:
                    print("命中缓存")
                    return entry["body"]
                else:
                    print("缓存已过期，清理")
                    del cache[cache_key]
        
        # 复用已有的连接
        if key in connections:
            s = connections[key]
        else:
            # 浏览器通信基于底层OS的socket
            s = socket.socket(
                family=socket.AF_INET,
                type=socket.SOCK_STREAM,
                proto=socket.IPPROTO_TCP
            )
            # 如果协议是https, 则创建SSL安全套接字
            if self.scheme == 'https':
                ctx = ssl.create_default_context()
                s = ctx.wrap_socket(s, server_hostname=self.host)
            # 连接到服务器, 端口取决于协议
            s.connect((self.host, self.port))
            
            connections[key] = s
        
        # 使用宏替换符号拼接请求和主机
        # \r\n代表换行且光标回到行首，\n代表换行但光标垂直向下, 使用\r\n非常重要
        request = "GET {} HTTP/1.1\r\n".format(self.path)
        request += "Host: {}\r\n".format(self.host)
        
        # close是1.1的新产物，代表浏览器不想支持长连接，但目前主流浏览器是不使用的
        request += "Connection: keep-alive\r\n"
            
        # User-Agent需要真实一点，这代表浏览器的身份标识，不真实的User-Agent在Https的请求下可能会被拒绝或重定向至http
        request += "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36\r\n"
        
        # 在请求头中添加允许的压缩方式
        request += "Accept-Encoding: gzip\r\n"
        
        # 最后一次空行告诉浏览器请求已经发送完毕
        request += "\r\n"
        
        # 发送请求到对应域名的服务器
        s.send(request.encode('utf-8'))
        
        response = s.makefile("rb", newline="\r\n")
        
        # 读取状态行 包含协议版本、状态码、状态描述
        statusline = response.readline().decode('utf-8')
        print(statusline, end="")
        
        version, status, explanation = statusline.split(" ", 2)
        
        # 获取响应头内容
        response_headers = {}
        while True:
            line = response.readline().decode('utf-8')
            if line == "\r\n":
                break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()
        
        print(response_headers)
        
        
        # 解决重定向问题，根据响应码判断是否需要重定向
        if status.startswith("3"):
            if redirect_limit <= 0:
                raise Exception("Too many redirects")
            
            # 在响应头中提取location字段，代表重定向的地址
            localtion: str = response_headers["location"]
            
            if localtion.startswith("/"):
                localtion = self.scheme + "://" + self.host + localtion
                
            print("Redirecting to:", localtion)
            return URL(localtion).request(redirect_limit=redirect_limit - 1)
        
        # 解析缓存
        cache_control: str = response_headers.get("cache-control", "")
        cacheable = False
        max_age = None
        if "no-store" in cache_control:
            cacheable = False
        elif "max-age" in cache_control:
            try:
                parts = [p.strip() for p in cache_control.split(",")]
                for part in parts:
                    if part.startswith("max-age"):
                        max_age = int(part.split("=")[1])
                        cacheable = True
            except:
                pass
        
        # 根据响应头中是否有transfer-encoding字段来判断是否需要对chunk进行处理
        if "transfer-encoding" in response_headers:
            # chunked编码
            if response_headers["transfer-encoding"] == "chunked":
                raw_body = self.read_chunked_body(response)
            else:
                raise Exception("不支持 Transfer-Encoding")
        else:
            # 在响应头中获取可以读取的指定字节数, content-length是说明接下来的body有多少字节
            length = int(response_headers.get("content-length", 0))
            # 检验缓存，减少输出量，便于调试
            # length = 1024
            raw_body = response.read(length)
        
        # gzip解压，注意这里的顺序：假设是chunked编码，先读取chunked编码的body，再解压gzip
        if response_headers.get("content-encoding") == "gzip":
            try:
                raw_body = gzip.decompress(raw_body)
            except:
                print("GZip Error")
                pass
        
        content = raw_body.decode("utf-8", errors="replace")
        
        # 写入缓存
        if cacheable and method == "GET":
            cache[cache_key] = {
                "body": content,
                "time-stamp": time.time(),
                "max-age": max_age
            }
        
        # 长连接状态下，不可以关闭连接
        # s.close()
        
        return content
    
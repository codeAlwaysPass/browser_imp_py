import sys
import os
import urllib.parse
from url import URL

# 解析响应体的文本
def show(body: str):
    i = 0
    
    while i < len(body):
        c = body[i]
        
        # 特殊字符解析
        if body[i:].startswith("&lt;"):
            print("<", end="")
            i += 4
            continue     
        elif body[i:].startswith("&gt;"):
            print(">", end="")
            i += 4
            continue
        else:
            print(c, end="")
            # print("", end="")
            
            
        i += 1


# 加载方法
def load(url: str):
    if url.startswith("file://"):
        # 去除前缀，得到文件名
        path = url[len("file://"):]
        print(path)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        show(content)
    
    # 处理data协议
    elif url.startswith("data:"):
        try:
            _, data = url.split(",", 1)
            content = urllib.parse.unquote(data)
            show(content)
        except Exception as e:
            print(e)
    
    # 处理view-source协议
    elif url.startswith("view-source:"):
        real_url = url[len("view-source:"):]
        body = URL(real_url).request()
        show(body)

    else:
        body = URL(url).request()
        show(body)

if __name__ == "__main__":
    if (len(sys.argv)) > 1:
        if sys.argv[1].startswith("data:"):
            load(sys.argv[1])
        else:
            load(sys.argv[1])
            # 检验缓存命中，重复两次
            # load(sys.argv[1])
    
    # 浏览器启动时如果未提供url, 则加载默认文件
    else:
        default_file = os.path.join(os.path.dirname(__file__), "default.html")
        load(f"file://{default_file}")

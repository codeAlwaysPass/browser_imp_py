import tkinter
from url import URL

# 定义画布宽高
WIDTH, HEIGHT = 800, 600

class Browser:
    def __init__(self):
        # 注册一个窗口
        self.window = tkinter.Tk()
        # 注册一个画布
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT,
        )
        # 将画布放置在窗口中
        self.canvas.pack(fill="both", expand=True)
        
        # 定义初始滚动位置
        self.scroll = 0
        
        # 绑定向下的滚动事件
        self.window.bind("<Down>", self.scrolldown)
        # 绑定向上的滚动事件
        self.window.bind("<Up>", self.scrollup)
        # 绑定鼠标/触控板事件
        self.window.bind("<MouseWheel>", self.onMouseWheel)
        self.window.bind("<Button-4>", self.scrollup)
        self.window.bind("<Button-5>", self.scrolldown)
        # 绑定resize事件
        self.window.bind("<Configure>", self.onResize)
        
        # 初始化滚动步长
        self.SCROLL_STEP = 100    
        # 定义水平和垂直步长
        self.HSTEP, self.VSTEP = 13, 18
        # 定义换行步长
        self.CHANGE_LINE_STEP = 24
        
        # 备用文本方向-暂不实现
    
    # 绘制函数
    def draw(self):
        self.canvas.delete("all")
        for x, y, c in self.display_list:
            # 如果y大于滚动步长, 则不渲染
            if y > self.scroll + HEIGHT: continue
            # 如果y小于滚动步长, 则不渲染
            if y + self.VSTEP < self.scroll: continue
            
            # (y-步长) 时, 字的渲染位置会比原始位置出现偏移, 这就模拟出了滚动效果
            self.canvas.create_text(x, y - self.scroll, text=c)
            
            self.drawScrollBar()
            
    
    # 绘制滚动条   
    def drawScrollBar(self):
        content_height = self.getContentHeight()
        if content_height <= HEIGHT:
            return
        
        # 计算滚动条高度
        bar_height = HEIGHT * HEIGHT // content_height
        # 计算滚动条顶部位置
        bar_top = self.scroll * HEIGHT // content_height
        
        self.canvas.create_rectangle(
            WIDTH - 10, bar_top, WIDTH, bar_top + bar_height,
            fill="gray",
            outline=""
        )
    
    # 支持emoji
    def renderEmoji():
        print("暂时不写")
    
    def getContentHeight(self):
        if not self.display_list:
            return 0
        return self.display_list[-1][1] + self.VSTEP
    
    # 向下滚动函数
    def scrolldown(self, e):
        self.scroll = min(self.scroll + self.SCROLL_STEP, self.display_list[-1][1])
        self.draw()
    
    # 向上滚动函数
    def scrollup(self, e):
        self.scroll = max(self.scroll - self.SCROLL_STEP, 0)
        self.draw()
    
    # resize事件函数
    def onResize(self, e):
        global WIDTH, HEIGHT
        # 获取当前窗口宽高, 赋值给WIDTH, HEIGHT
        WIDTH, HEIGHT = e.width, e.height
        
        # 重新计算布局
        self.relayout()
    
    def onMouseWheel(self, e):
        if e.delta > 0:
            self.scrolldown(e)
        else:
            self.scrollup(e)
    
    # 加载url函数, 首次渲染
    def load(self, url: URL):
        
        body = url.request()
        self.text = lex(body)
        
        # 记录布局列表, 布局列表记录了每个字符的位置和文本
        self.display_list = self.layout(self.text)
        self.draw()
    
    # layout布局函数
    def layout(self, text):
        display_list = []
        cursor_x, cursor_y = self.HSTEP, self.VSTEP
        
        for c in text:
            display_list.append((cursor_x, cursor_y, c))
            
            # 更新光标位置
            cursor_x += self.HSTEP
            
            # 如果光标位置超过画布宽度，则换行
            if cursor_x > WIDTH - self.HSTEP:
                cursor_x = self.HSTEP
                cursor_y += self.VSTEP
            
            # 处理换行符
            if c == '\n' or c == '\r\n':
                cursor_x = self.HSTEP
                cursor_y += self.CHANGE_LINE_STEP
                
        return display_list
    
    def relayout(self):
        self.display_list = self.layout(self.text)
        # 布局并绘制
        self.draw()
        

# 解析出非Tag的文本 
def lex(body):
    in_tag = False
    text = ""
    
    for c in body:
        if c == '<':
            in_tag = True
            continue
        
        elif c == '>':
            in_tag = False
            continue
        
        elif not in_tag:
            text += c
            
    return text
        
if __name__ == "__main__":
    import sys
    browser = Browser()
    
    try:
        raw_url = sys.argv[1] if len(sys.argv) > 1 else "about:blank"
        url = URL(raw_url)
        browser.load(url)
    except Exception as e:
        print("Error loading url, falling back to about:blank")
        browser.load(URL("about:blank"))
    
    tkinter.mainloop()
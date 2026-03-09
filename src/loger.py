
# == 日志文件 ==

#此文件为OneBot11-小生物的日志涵数文件
#应用环境为LL-Bot v2.4.4

#如果不清楚具体作用，除配置外，请不要修改任何参数代码


#引用库
import time, os

localtion = os.path.dirname(__file__) #获取文件位置
localtion = localtion.replace("\src","")
localtion = localtion.replace("\\","/")
path = f"{localtion}/data/log" #重定向日志文件至data文件夹下

#系统时间 => 日志文件名字
current_time = time.strftime("%Y-%m-%d_%H_%M_%S", time.localtime())
loger_time = time.strftime("%Y-%m-%d", time.localtime()) #每日轮换文件


#日志写入
def log(data: str = "", needPrint=True):
    #每日轮换文件
    today = time.strftime("%Y-%m-%d", time.localtime()) 
    global current_time
    global loger_time
    if today != loger_time: 
        loger_time = time.strftime("%Y-%m-%d", time.localtime()) 
        current_time = time.strftime("%Y-%m-%d_%H_%M_%S", time.localtime())
        os.system("cls")
    #后台打印
    if needPrint: print(data)
    #文件写入
    if not os.path.exists(path):
        os.makedirs(path)
    file = open(f'{path}/{current_time}.log', 'a', encoding="utf-8")
    file.write(f"{data}\n")
    file.close()
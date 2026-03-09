
# == 库引用文件 ==

#此文件为OneBot11-小生物的库引用涵数文件
#应用环境为LL-Bot v2.4.4

#如果不清楚具体作用，除配置外，请不要修改任何参数代码


#引用库
import os

#引用对应库，失败时自动pip下载
def import_package(package, name_as = None, package_from = None, package_pip_Name = None):
    command = ""
    if package_from != None:
        command += f"from {package_from} "
    if name_as == None: 
        command += f"import {package}"
    else:
        command += f"import {package} as {name_as}"
    try:
        exec(command)
    except:
        if package_pip_Name == None: package_pip_Name = package
        os.system(f"pip install {package_pip_Name}")
    return command
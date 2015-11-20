### 剪切板共享

用于在Ubuntu和Mac下共享剪贴板，可以共享纯文本以及屏幕截图等；

### 截图支持

`clip-tkinter.py`：使用`python`内置类库`Thinter`，仅支持纯文本共享，目前性能存在比较大的问题；

`clip-pygtk.py`：支持截图共享（`推荐`），需要安装第三方类库`pygtk`，

* Ubuntu

    sudo apt-get install python-gtk2

* Mac

    brew install pygtk

### 运行

    $python clip-pygtk.py --local ip:port --remote ip:port
    #省略 port，默认为 34567
    $python clip-pygtk.py --remote ip

假设`电脑A`的内网IP为：`172.16.2.100`；`电脑B`的内网IP为：`172.16.2.200`，则

在A上运行:

    $python clip-pygtk.py --remote 172.16.2.200

在B上运行

    $python clip-pygtk.py --remote 172.16.2.100

默认绑定端口`34567`，如果出现端口冲突，可以指定其他端口：

    $python clip-pygtk.py --local :18899 --remote 172.16.2.100:18899

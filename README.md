### 剪切板共享

用于在Ubuntu和Mac下共享剪贴板，可以共享纯文本以及屏幕截图等；

### 截图支持

剪贴板操作默认使用`python`内置类库`Thinter`，仅支持纯文本共享；如果需要共享剪贴板截图，需要安装第三方类库`pygtk`:

* Ubuntu

    sudo apt-get install python-gtk2

* Mac

    brew install pygtk

### 运行

假设`电脑A`的内网IP为：`172.16.2.100`，绑定端口：`34567`；`电脑B`的内网IP为：`172.16.2.200`，绑定端口：`34568`，则

在A上运行:

    $python clipboard.py --local 172.16.2.100:34567 --remote 172.16.2.200:34568

在B上运行

    $python clipboard.py --local 172.16.2.200:34568 --remote 172.16.2.100:34567

Just enjoy it ~~~

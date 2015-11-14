### 剪切板共享

用于在Ubuntu和Mac下共享剪切板

### 安装

    pip install requests

* Ubuntu

    sudo apt-get install python-gtk2

* Mac

    brew install pygtk

### 运行

假设`电脑A`的内网IP为：`172.16.2.100`，绑定端口：`34567`；`电脑B`的内网IP为：`172.16.2.200`，绑定端口到：`34568`，则

    # 在A上运行
    $python clipboard.py --local_port 34567 --remote_addr 172.16.2.200:34568
    # 在B上运行
    $python clipboard.py --local_port 34568 --remote_addr 172.16.2.100:34567

如果需要指定检测剪贴板的频率（默认为2s），可添加`--detect_freq n`参数

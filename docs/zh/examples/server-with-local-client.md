请先安装 qrcode：
```shell
pip install qrcode
```

这段代码不仅提供 DG-Lab WebSocket 服务端服务，还生成了一个本地终端可供 App 连接。

!!! tip
    不管是本地终端 [`DGLabLocalClient`][pydglab_ws.DGLabLocalClient]
    还是 WebSocket 终端 [`DGLabWSClient`][pydglab_ws.DGLabWSClient]，
    **包含的主要方法都相同**，因此在该段代码中，终端相关的逻辑与上面的独立的 WebSocket 终端的实现基本相同。
    这种方式，省去了终端连接 WebSocket 服务端的环节，终端与 WebSocket 服务端一体，**网络延迟更低，部署更方便**。

``` py title="examples/server_with_local_client.py"
--8<-- "examples/server_with_local_client.py"
```
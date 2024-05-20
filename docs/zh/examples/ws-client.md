请先安装 qrcode：
```shell
pip install qrcode
```

当进入 [`DGLabWSServer`][pydglab_ws.DGLabWSServer] 的异步生成器时，从 WebSocket 服务端获取 `clientId` 的操作会 **自动完成**

``` py title="examples/ws_client.py"
--8<-- "examples/ws_client.py"
```
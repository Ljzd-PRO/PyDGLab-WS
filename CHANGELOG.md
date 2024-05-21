## 更新内容

### 💡 新特性

- 增加波形操作数据过长的异常 - [`PulseDataTooLong`](https://pydglab-ws.readthedocs.io/zh/stable/api/exceptions/#pydglab_ws.exceptions.PulseDataTooLong)
- 增加消息长度大于 1950 的错误码的收取 - [`RetCode.MESSAGE_TOO_LONG`](https://pydglab-ws.readthedocs.io/zh/stable/api/enums/#pydglab_ws.enums.RetCode.MESSAGE_TOO_LONG)
- 可获取波形操作数据的最大长度 - [`PULSE_DATA_MAX_LENGTH`](https://pydglab-ws.readthedocs.io/zh/stable/api/utils/#pydglab_ws.utils.PULSE_DATA_MAX_LENGTH)
- 缩短了 WebSocket 消息（JSON）长度

[//]: # (### 🪲 修复)

**Full Changelog**: https://github.com/Ljzd-PRO/PyDGLab-WS/compare/v1.0.2...v1.1.0
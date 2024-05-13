# PyDGLab-WS

一个用于创建郊狼 DG-Lab App Socket 被控的客户端和服务端的 Python 库

## 💡 特性

- 通过该库可开发 Python 程序，接入 DG-Lab App
- 完全使用异步，并发执行各项操作
- 可部署第三方终端与 Socket 服务一体的服务端，降低部署复杂度和延迟
- 使用异步生成器、迭代器等，结合语言特性
- 通过 Pydantic, 枚举 管理消息结构和常量，便于开发

## 🛫 快速开始

## 使用方法

### 安装

```bash
pip3 install pydglabws
```

### 命令

使用帮助命令或前往 [命令](commands/guide.md) 页面查看更多帮助。
  
#### ❓ 获取帮助总览
```bash
ktoolbox -h
```
  
#### ❓ 获取某个命令的帮助信息
```bash
ktoolbox download-post -h
```

#### ⬇️🖼️ 下载指定的作品
```bash
ktoolbox download-post https://kemono.su/fanbox/user/49494721/post/6608808
```
??? info "如果部分文件下载失败"
    如果部分文件下载失败，你可以尝试重新运行命令，已下载完成的文件会被 **跳过**。
  
#### ⬇️🖌️ 下载作者的所有作品
```bash
# 下载作者/画师的所有作品
ktoolbox sync-creator https://kemono.su/fanbox/user/9016

# 下载作者/画师最新的 10 个作品
ktoolbox sync-creator https://kemono.su/fanbox/user/9016 --length=10

# 下载作者/画师最新的第 11 至 15 个作品
ktoolbox sync-creator https://kemono.su/fanbox/user/9016 --offset=10 --length=5

# 下载作者/画师从 2024-1-1 到 2024-3-1 的作品
ktoolbox sync-creator https://kemono.su/fanbox/user/9016 --start-time=2024-1-1 --end-time=2024-3-1
```

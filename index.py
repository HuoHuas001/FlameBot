# -*- coding: utf-8 -*-
import botpy
from botpy import logging, BotAPI
from botpy.ext.command_util import Commands
from botpy.message import GroupMessage
import asyncio
import websockets
import uuid

from config import *
from basic import *
from websocketServer import *

_log = logging.get_logger()    #Botpy Logger
server_instance = None         #websocketServer全局变量

@Commands("添加白名单")
async def addAllowList(api: BotAPI, message: GroupMessage, params=None):
    if(not params):
        await message.reply(content=f"参数不正确，请使用 /帮助 来查看帮助")
        return True

    unique_id = uuid.uuid4()
    await message.reply(content=f"已请求添加白名单.\nXbox Id:{params}\n请管理员核对.如有错误,请输入/删除 {unique_id}")
    await server_instance.broadcast({"type":"add","xboxid":params,"uuid":str(unique_id)},message.group_openid)
    return True

@Commands("删除")
async def reCall(api: BotAPI, message: GroupMessage, params=None):
    if(not params):
        await message.reply(content=f"参数不正确，请使用 /帮助 来查看帮助")
        return True

    await message.reply(content=f"已请求删除Id为{params}的白名单.")
    await server_instance.broadcast({"type":"delete","uuid":params},message.group_openid)
    return True

@Commands("帮助")
async def help(api: BotAPI, message: GroupMessage, params=None):
    await message.reply(content='FlameHuo帮助:\n/添加白名单 {Xbox Id}\n/删除 {uuid}\n/帮助\n/查群号\n/设置名称 {昵称}\n/发信息 {消息}\n注:若XboxId有空格请打上双引号,如:"XboxId"')
    return True

@Commands("查群号")
async def queryGroup(api: BotAPI, message: GroupMessage, params=None):
    groupId = message.group_openid
    await message.reply(content=f"本群OpenId:{groupId}")
    return True

@Commands("设置名称")
async def setGroupName(api: BotAPI, message: GroupMessage, params=None):
    await update_json_data(file_path, modify_data,{
        "groupId":message.group_openid,
        "author":message.author.member_openid,
        "nick":params
    })
    await message.reply(content=f"已将您的群服互通昵称设置为{params}")
    return True
    
@Commands("发信息")
async def sendGameMsg(api: BotAPI, message: GroupMessage, params=None):
    nick = await queryName({
        "groupId":message.group_openid,
        "author":message.author.member_openid,
    })
    if nick == None:
        await message.reply(content="没有找到你的昵称数据，请使用/设置昵称 {昵称}来设置")
    else:
        await server_instance.broadcast({"type":"chat","msg":params,"nick":nick},message.group_openid)

    return True

@Commands("执行命令")
async def sendCmd(api: BotAPI, message: GroupMessage, params=None):
    unique_id = uuid.uuid4()
    await server_instance.broadcast({"type":"cmd","cmd":params,"uuid":str(unique_id)},message.group_openid)
    async def cmdReply(msg):
        ret = await message.reply(content=msg)
        _log.info(ret)
    server_instance.addCallback(str(unique_id),cmdReply)
    return True

@Commands("查白名单")
async def queryWl(api: BotAPI, message: GroupMessage, params=None):
    unique_id = uuid.uuid4()
    await server_instance.broadcast({"type":"queryList","uuid":str(unique_id)},message.group_openid)
    async def wlReply(msg):
        await message.reply(content=msg)
    server_instance.addCallback(str(unique_id),wlReply)
    return True

#BotPy主框架
class BotClient(botpy.Client):
    def postApi(self):
        if(server_instance != None):
            server_instance.botAPI(self.api)

    async def on_group_at_message_create(self, message):
        # 注册指令handler
        handlers = [
            addAllowList,
            help,
            reCall,
            queryGroup,
            setGroupName,
            sendGameMsg,
            sendCmd,
            queryWl
        ]
        for handler in handlers:
            if await handler(api=self.api, message=message):
                return
    
# 开启BotPy客户端
async def startClient():
    intents = botpy.Intents.none()
    intents.public_messages=True
    client = BotClient(intents=intents)
    client.postApi()
    await client.start(appid=APPID, secret=SECRET)

# 创建服务器实例的协程
async def create_server():
    global server_instance
    if server_instance is None:
        server_instance = WebSocketServer(_log)
    return server_instance

# 启动WebSocket服务器的函数
async def start_server(host="localhost", port=8888):
    server = await create_server()  # 获取服务器实例
    async with websockets.serve(server.handler, host, port):
            _log.info(f"[Websocket] Server started on ws://{host}:{port}")
            await asyncio.Future()  # 运行服务器直到被取消

# 主函数，用于启动WebSocket服务器
async def main():
    server_coroutine = start_server()  # 获取启动服务器的协程
    client_coroutine = startClient()  # 获取启动客户端的协程
    await asyncio.gather(server_coroutine, client_coroutine)  # 并发运行

if __name__ == '__main__':
    asyncio.run(main())
    

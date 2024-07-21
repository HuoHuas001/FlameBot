# -*- coding: utf-8 -*-
import os

import botpy
from botpy import logging, BotAPI

from botpy.ext.command_util import Commands
from botpy.message import GroupMessage
from botpy.ext.cog_yaml import read
import re
import asyncio
import websockets
import json
import uuid
import aiofiles
from config import *

_log = logging.get_logger()
file_path = "nickName.json"


#切割命令参数
def splitCommandParams(params: str):
    if not params:
        return []

    result = []
    now, in_quote = "", ""
    for word in params.split():
        if in_quote:
            in_quote += " " + word
            if word.endswith('"'):
                in_quote = in_quote.rstrip('"')
                result.append(in_quote.strip('"'))
                in_quote = ""
        else:
            if word.startswith('"') and word.endswith('"'):
                result.append(word[1:-1])
            elif word.startswith('"'):
                in_quote = word
            else:
                result.append(word)

    if in_quote:
        for word in in_quote.split():
            result.append(word)

    return [item.replace('"', '') for item in result]

#检查是否是合法的QQ
def is_valid_QQ(qqStr: str):
    qq_regex = r"^\d{5,12}$"
    # 使用正则表达式匹配
    if re.match(qq_regex, qqStr):
        return True
    else:
        return False

#Xbox ID 的合法性
def is_valid_xbox_id(xbox_id):
    # 定义Xbox ID的正则表达式规则
    pattern = r'^[a-zA-Z_][a-zA-Z0-9_ ]{2,14}[a-zA-Z0-9_]$'
    # 使用正则表达式匹配
    if re.match(pattern, xbox_id):
        return True
    else:
        return False

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

#添加玩家NickName
async def update_json_data(file_path, update_func,memberData):
    async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
        data = await file.read()
        data_dict = json.loads(data)
    updated_data = update_func(data_dict,memberData)
    async with aiofiles.open(file_path, 'w', encoding='utf-8') as file:
        await file.write(json.dumps(updated_data, indent=4, ensure_ascii=False))

def modify_data(data,memberData):
    if memberData["groupId"] not in data:
        data[memberData["groupId"]] = {}
    data[memberData["groupId"]][memberData["author"]] = memberData["nick"]
    return data

@Commands("设置名称")
async def setGroupName(api: BotAPI, message: GroupMessage, params=None):
    await update_json_data(file_path, modify_data,{
        "groupId":message.group_openid,
        "author":message.author.member_openid,
        "nick":params
    })
    await message.reply(content=f"已将您的群服互通昵称设置为{params}")
    return True


#查询玩家昵称
async def queryName(memberData):
    async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
        data = await file.read()
        data_dict = json.loads(data)
    
    if(memberData["groupId"] not in data_dict):
        return None
    
    if(memberData["author"] not in data_dict[memberData["groupId"]]):
        return None
    
    return data_dict[memberData["groupId"]][memberData["author"]]

    
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
    await server_instance.broadcast({"type":"cmd","cmd":params},message.group_openid)
    await message.reply(content="已发送命令。")
    return True

@Commands("查白名单")
async def queryWl(api: BotAPI, message: GroupMessage, params=None):
    unique_id = uuid.uuid4()
    await server_instance.broadcast({"type":"queryList","uuid":str(unique_id)},message.group_openid)
    async def wlReply(msg):
        await message.reply(content=msg)
    server_instance.addCallback(str(unique_id),wlReply)
    return True

class MyClient(botpy.Client):
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
    
async def startClient():
    intents = botpy.Intents.none()
    intents.public_messages=True
    client = MyClient(intents=intents)
    client.postApi()
    await client.start(appid=APPID, secret=SECRET)


# 定义WebSocket服务器类
class WebSocketServer:
    def __init__(self):
        self.active_connections = set()
        self.registedServer = {}
        self.botApi = None
        self.callback = {}

    async def handler(self, websocket, path):
        await self.register(websocket)
        try:
            async for message in websocket:
                await self.process_message(websocket, message)
        except websockets.exceptions.ConnectionClosedError:
            # 客户端关闭连接时不抛出异常
            pass
        finally:
            await self.unregister(websocket)

    async def register(self, websocket):
        self.active_connections.add(websocket)
        _log.info(f"[Websocket] Active connections: {len(self.active_connections)}")

    async def unregister(self, websocket):
        self.active_connections.remove(websocket)
        _log.info(f"[Websocket] Active connections: {len(self.active_connections)}")

    def botAPI(self,api):
        self.botApi = api

    def addCallback(self,id,cbfunc):
        self.callback[id] = cbfunc

    #发送Bot消息
    async def sendGroupMsg(self,group,msg):
        await self.botApi.post_group_message(group,0,msg,msg_seq=1000)

    async def process_message(self, client, message):
        try:
            data = json.loads(message)
            if not self.validate_data(data):
                await client.send(json.dumps({"type":"error","error": "Invalid data"},ensure_ascii=False))
                return

            # 处理消息
            response = {"type": "success"}
            
            if(data["type"] == "sendMsg"):
                await self.sendGroupMsg(data["group"],data["msg"])
                await client.send(json.dumps(response,ensure_ascii=False))
            elif(data["type"] == "heart"):
                await client.send(data)
            elif(data["type"] == "success"):
                pass
            elif(data["type"] == "error"):
                pass
            elif(data["type"] == "shakeHand"):
                self.registedServer[data["name"]] = client
                await client.send(json.dumps({"type":"shaked","Code":1,"Msg":""},ensure_ascii=False))
            elif(data["type"] == "queryWl"):
                if data["uuid"] in self.callback:
                    await self.callback[data["uuid"]](data["list"])
                    del self.callback[data["uuid"]]
                else:
                    _log.error("[Websocket] Callback Id不存在")
            
        except json.JSONDecodeError:
            await client.send(json.dumps({"type":"error","error": "Invalid JSON format"},ensure_ascii=False))

    #广播信息
    async def broadcast(self, message,groupId=""):
        message["groupId"] = groupId
        for connection in self.active_connections:
            try:
                await connection.send(json.dumps(message,ensure_ascii=False))
            except websockets.exceptions.ConnectionClosed as e:
                _log.error(f"Connection closed error: {e}")
                self.active_connections.remove(connection)
            

    def validate_data(self, data):
        # 这里可以添加具体的数据验证逻辑
        return "type" in data and isinstance(data["type"], str)

# 移除全局变量和线程锁
server_instance = None

# 创建服务器实例的协程
async def create_server():
    global server_instance
    if server_instance is None:
        server_instance = WebSocketServer()
    return server_instance

# 启动WebSocket服务器的函数
async def start_server(host="localhost", port=8888):
    server = await create_server()  # 获取服务器实例
    async with websockets.serve(server.handler, host, port):
            _log.info(f"[Websocket] Server started on {host}:{port}")
            await asyncio.Future()  # 运行服务器直到被取消

# 主函数，用于启动WebSocket服务器
async def main():
    server_coroutine = start_server()  # 获取启动服务器的协程
    client_coroutine = startClient()  # 获取启动客户端的协程
    await asyncio.gather(server_coroutine, client_coroutine)  # 并发运行

    

if __name__ == '__main__':
    asyncio.run(main())
    

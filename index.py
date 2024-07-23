# -*- coding: utf-8 -*-
import botpy
from botpy import logging, BotAPI
from botpy.ext.command_util import Commands
from botpy.message import GroupMessage,MessageAudit
from botpy.types.message import MarkdownPayload
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

    if(not await queryIsAdmin(message.group_openid,message.author.member_openid)):
        return True
    unique_id = uuid.uuid4()
    await message.reply(content=f"已请求添加白名单.\nXbox Id:{params}\n请管理员核对.如有错误,请输入/删除 {unique_id}")
    await server_instance.broadcast("add",{"xboxid":params,"uuid":str(unique_id)},message.group_openid)
    return True

@Commands("删除")
async def reCall(api: BotAPI, message: GroupMessage, params=None):
    if(not params):
        await message.reply(content=f"参数不正确，请使用 /帮助 来查看帮助")
        return True
    
    if(not await queryIsAdmin(message.group_openid,message.author.member_openid)):
        return True
    await message.reply(content=f"已请求删除Id为{params}的白名单.")
    await server_instance.broadcast("delete",{"uuid":params},message.group_openid)
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

@Commands("查自己")
async def queryMe(api: BotAPI, message: GroupMessage, params=None):
    authorId = message.author.member_openid
    await message.reply(content=f"你的OpenId:{authorId}")
    return True

@Commands("加管理")
async def addAdmin(api: BotAPI, message: GroupMessage, params=None):
    if(not await queryIsAdmin(message.group_openid,message.author.member_openid)):
        return True
    groupId,authorId = splitCommandParams(params)
    await addGroupAdmin(groupId,authorId)
    await message.reply(content=f"已向{groupId}的群聊中添加了管理员:{authorId}")
    return True

@Commands("查管理")
async def queryAdmin(api: BotAPI, message: GroupMessage, params=None):
    if(not await queryIsAdmin(message.group_openid,message.author.member_openid)):
        return True
    groupId,authorId = splitCommandParams(params)
    ret = await queryIsAdmin(groupId,authorId)
    if(ret):
        ret = "有"
    else:
        ret = "无"
    await message.reply(content=f"{groupId}的群聊中,管理员{authorId}{ret}权限")
    return True

@Commands("删管理")
async def delAdmin(api: BotAPI, message: GroupMessage, params=None):
    if(not await queryIsAdmin(message.group_openid,message.author.member_openid)):
        return True
    groupId,authorId = splitCommandParams(params)
    ret = await delGroupAdmin(groupId,authorId)
    if(ret):
        await message.reply(content=f"已向{groupId}的群聊中删除了管理员:{authorId}")
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
        await server_instance.broadcast("chat",{"msg":params,"nick":nick},message.group_openid)

    return True

@Commands("执行命令")
async def sendCmd(api: BotAPI, message: GroupMessage, params=None):
    aaaa = await queryIsAdmin(message.group_openid,message.author.member_openid)
    _log.info(aaaa)
    if(not aaaa):
        return True
    unique_id = str(uuid.uuid4())
    await server_instance.broadcast("cmd",{"cmd":params},message.group_openid,unique_id)
    async def cmdReply(msg):
        ret = await message.reply(content=msg,msg_seq=2)
        #_log.info(ret)
    server_instance.addCallbackFunc(unique_id,cmdReply)
    await message.reply(content="已向服务器发送命令，请等待执行.")
    return True

@Commands("查白名单")
async def queryWl(api: BotAPI, message: GroupMessage, params=None):
    if(not queryIsAdmin(message.group_openid,message.author.member_openid)):
        return True
    #api.post_group_message(msg_seq=1000)
    unique_id = str(uuid.uuid4())
    await server_instance.broadcast("queryList",{},message.group_openid,unique_id)
    async def wlReply(msg):
        await message.reply(content=msg)
    server_instance.addCallbackFunc(unique_id,wlReply)
    return True

@Commands("查在线")
async def queryOnline(api: BotAPI, message: GroupMessage, params=None):
    unique_id = str(uuid.uuid4())
    await server_instance.broadcast("queryOnline",{},message.group_openid,unique_id)
    async def onlineReply(msg):
        markdown = MarkdownPayload(
            custom_template_id="102147135_1721645887",
            params=[
                {
				    "key": "title",
				    "values": ["在线玩家列表"]
			    },
                {
				    "key": "content",
				    "values": [msg]
			    },
            ])
        try:
            await message.reply(msg_type=2,markdown=markdown)
        except errors.ServerError as e:
            rpMsg = msg.replace("\u200b","\n")
            await message.reply(content=f"在线玩家列表:\n{rpMsg}")
    server_instance.addCallbackFunc(unique_id,onlineReply)
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
            queryWl,
            queryOnline,
            queryMe,
            delAdmin,
            queryAdmin,
            addAdmin
        ]
        for handler in handlers:
            if await handler(api=self.api, message=message):
                return
    async def on_message_audit_reject(self, message: MessageAudit):
        _log.warning(f"消息：{message.message_id} 审核未通过.")
    
# 开启BotPy客户端
async def startClient():
    intents = botpy.Intents.none()
    intents.public_messages=True
    intents.message_audit=True
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
async def start_server(host="0.0.0.0", port=8765):
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
    

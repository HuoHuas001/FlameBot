# -*- coding: utf-8 -*-
import os

import botpy
from botpy import logging, BotAPI

from botpy.ext.command_util import Commands
from botpy.message import GroupMessage
from botpy.ext.cog_yaml import read
from configS import *
_log = logging.get_logger()


@Commands("添加白名单")
async def addAllowList(api: BotAPI, message: GroupMessage, params=None):
    _log.info(params)
    await message.reply(content=f"已添加白名单")
    return True

@Commands("撤销")
async def reCall(api: BotAPI, message: GroupMessage, params=None):
    _log.info(params)
    await message.reply(content=f"已撤销白名单")
    return True

@Commands("帮助")
async def help(api: BotAPI, message: GroupMessage, params=None):
    await message.reply(content='FlameHuo帮助:\n/添加白名单\n/撤销')
    return True

@Commands("查群号")
async def queryGroup(api: BotAPI, message: GroupMessage, params=None):
    groupId = "114514"
    await message.reply(content=f"本群群号:{groupId}")
    return True

@Commands("设置名称")
async def setGroupName(api: BotAPI, message: GroupMessage, params=None):
    await message.reply(content=f"已设置")
    return True

@Commands("发信息")
async def sendGameMsg(api: BotAPI, message: GroupMessage, params=None):
    await message.reply(content="你好呀，我是FlameHuo")
    return True

@Commands("查白名单")
async def queryWl(api: BotAPI, message: GroupMessage, params=None):
    await message.reply(content="现在还没有白名单")
    return True

@Commands("查在线")
async def queryOnline(api: BotAPI, message: GroupMessage, params=None):
    await message.reply(content="在线玩家：0")
    return True

class MyClient(botpy.Client):
    async def on_group_at_message_create(self, message):
        # 注册指令handler
        handlers = [
            addAllowList,
            help,
            reCall,
            queryGroup,
            setGroupName,
            sendGameMsg,
            queryWl,
            queryOnline
        ]
        for handler in handlers:
            if await handler(api=self.api, message=message):
                return

#订阅事件
intents = botpy.Intents.none()
intents.public_messages=True

client = MyClient(intents=intents)
client.run(appid=APPID, secret=SECRET)

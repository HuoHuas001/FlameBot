import json
import websockets
from botpy import errors
import uuid
from libs.basic import *

# 定义WebSocket服务器类
class WebSocketServer:
    def __init__(self,_log):
        self.active_connections = set()
        self.registedServer = {}
        self.botApi = None
        self.callback = {}
        self.logger = _log

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
        self.logger.info(f"[Websocket] Active connections: {len(self.active_connections)}")

    async def unregister(self, websocket):
        self.active_connections.remove(websocket)
        self.logger.info(f"[Websocket] Active connections: {len(self.active_connections)}")
        for i in self.registedServer:
            if(self.registedServer[i]["client"] == websocket):
                self.logger.info(f"[Websocket] Client Disconnect: {i}")
                for groupId in self.registedServer[i]["group"]:
                    await self.sendGroupMsg(groupId,f"{i} 已断开与FlameHuo的连接,请管理员检查是否存在问题")
                del self.registedServer[i]
                break
                
    #获取botApi
    def botAPI(self,api):
        self.botApi = api

    #添加Callback事件
    def addCallbackFunc(self,id,cbfunc):
        self.callback[id] = cbfunc
        return True

    #查询连接的客户端
    def queryClientList(self):
        clientList = {}
        unKnownId = 1
        for client in self.active_connections:
            flag = True
            for clientName in self.registedServer:
                if(self.registedServer[clientName]["client"] == client):
                   flag = False
                   clientList[clientName] = client
            if(flag):
                clientList[f"unknown_Client_{unKnownId}"] = client
                unKnownId += 1
        return clientList
                

    #进行回调事件
    async def callBackFunc(self,callbackId:str,args):
        if callbackId in self.callback:
            try:
                await self.callback[callbackId](args)
            except Exception as e:
                self.logger.error(f"[Websocket] {e}")
                
            del self.callback[callbackId]
            return True
        else:
            self.logger.error("[Websocket] Callback Id不存在")
            return False
        
    #命令客户端关闭连接
    async def shutDownClient(self,client,code=1000,reson=""):
        await self.sendClientMsg(client,"shutdown",{"msg":reson})
        await client.close(code,reson)
        
    #发送Bot消息
    async def sendGroupMsg(self,group,msg,client = None):
        try:
            return await self.botApi.post_group_message(group,0,msg,msg_seq=1000)
        except errors.ServerError:
            self.logger.error(f"{group} 不存在!")
            if(client != None):
                await self.shutDownClient(client,1003,f"{group} 不存在!")
            return None
        
    async def sendClientMsg(self,client,type="success",body={},unique_id = str(uuid.uuid4())):
        data = {
                "header":{
                    "type":type,
                    "id":unique_id
                },
                "body":body
            }
        await client.send(json.dumps(data,ensure_ascii=False))

    #执行内置语句
    async def websocketAdminProcess(self,client,body):
        if(body["type"] == "addGroupAdmin"):
            await addGroupAdmin(body["groupId"],body["authorId"])
            await self.sendClientMsg(client,"success",{})
        elif(body["type"] == "isGroupAdmin"):
            isGroupAdminRet = await queryIsAdmin(body["groupId"],body["authorId"])
            await self.sendClientMsg(client,"success",{"ret":isGroupAdminRet})
        elif(body["type"] == "delGroupAdmin"):
            delGroupAdminRet = await delGroupAdmin(body["groupId"],body["authorId"])
            await self.sendClientMsg(client,"success",{"ret":delGroupAdminRet})

    #消息处理
    async def process_message(self, client, message):
        try:
            data = json.loads(message)
            header = data["header"]
            body = data["body"]
            

            #Header参数
            type = header["type"]
            id = header["id"]

            if(type != "heart"):
                self.logger.info(data)
            
            if not self.validate_data(data):
                await self.sendClientMsg(client,"error",{"error": "Invalid data"})
                return
            
            # 处理消息
            if(type == "sendMsg"):
                await self.sendGroupMsg(body["group"],body["msg"],client)
                await self.sendClientMsg(client) #发送success信息

            elif(type == "heart"):
                await self.sendClientMsg(client,"heart",{})

            elif(type == "success"):
                if(id != ""):
                    await self.callBackFunc(id,body["msg"])
                else:
                    await self.sendGroupMsg(body["group"],"执行成功:\n"+body["msg"],client)

            elif(type == "error"):
                if(id != ""):
                    await self.callBackFunc(id,body["msg"])
                else:
                    await self.sendGroupMsg(body["group"],"执行失败:\n"+body["msg"],client)

            elif(type == "shakeHand"):
                if body["name"] not in self.registedServer:
                    self.registedServer[body["name"]] = {"client":client,"group":body["group"]}
                    for groupId in body["group"]:
                        await self.sendGroupMsg(groupId,f'{body["name"]} 已连接FlameHuo',client)
                        await self.sendClientMsg(client,"shaked",{"code":1,"msg":""})
                else:
                    await self.sendClientMsg(client,"shaked",{"code":2,"msg":"Duplicate client registration information"})
                    await self.shutDownClient(client,1003,"Duplicate client registration information")
                
            elif(type == "queryWl"):
                if not await self.callBackFunc(id,body["list"]):
                    self.logger.error("[Websocket] Callback Id不存在")

            elif(type == "queryOnline"):
                if not await self.callBackFunc(id,body["list"]):
                    self.logger.error("[Websocket] Callback Id不存在")

            elif(type == "websocketAdmin"):
                if(body["Adminkey"] == "flameHuo@HuoHuas001"):
                    await self.websocketAdminProcess(client,body)
                else:
                    await self.sendClientMsg(client,"error",{"msg":"AdminkeyError"})
            
        except json.JSONDecodeError:
            await self.sendClientMsg(client,"error",{"error": "Invalid JSON format"})

    #广播信息
    async def broadcast(self,type: str,message: dict,groupId="",unique_id = str(uuid.uuid4())):
        message["groupId"] = groupId
        for connection in self.active_connections:
            try:
                await self.sendClientMsg(connection,type,message,str(unique_id))
            except websockets.exceptions.ConnectionClosed as e:
                self.logger.error(f"Connection closed error: {e}")
                self.active_connections.remove(connection)

                
    def validate_data(self, data):
        # 这里可以添加具体的数据验证逻辑
        return "header" in data and "body" in data and isinstance(data["header"], dict) and isinstance(data["body"], dict)
    
if __name__ == "__main__":
    print("[Error] 请在index.py下运行")
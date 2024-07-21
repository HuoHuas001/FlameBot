import json
import websockets

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
            if(self.registedServer[i] == websocket):
                self.logger.info(f"[Websocket] Client Disconnect: {i}")
                break
        
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
                    self.logger.error("[Websocket] Callback Id不存在")
            
        except json.JSONDecodeError:
            await client.send(json.dumps({"type":"error","error": "Invalid JSON format"},ensure_ascii=False))

    #广播信息
    async def broadcast(self, message,groupId=""):
        message["groupId"] = groupId
        for connection in self.active_connections:
            try:
                await connection.send(json.dumps(message,ensure_ascii=False))
            except websockets.exceptions.ConnectionClosed as e:
                self.logger.error(f"Connection closed error: {e}")
                self.active_connections.remove(connection)
            

    def validate_data(self, data):
        # 这里可以添加具体的数据验证逻辑
        return "type" in data and isinstance(data["type"], str)
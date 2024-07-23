//LiteLoaderScript Dev Helper
/// <reference path="E:\\MCServer\\HelperLib\\src\\index.d.ts"/> 

const VERSION = "0.0.1"
const PATH = "plugins/FlameHuo/"
const CONFIGPATH = `${PATH}config.json`
const ALLOWLISTPATH = `${PATH}allowlist.json`
const BLOCKPATH = `${PATH}blockMsg.json`
const BDSALLOWLISTPATH = "allowlist.json"

logger.setTitle("FlameHuo")

/**
 * 读取文件
 * @param {string} file 
 * @returns 
 */
function readFile(file) {
    return JSON.parse(File.readFrom(file))
}

/**
 * 写入文件
 * @param {string} file 
 * @param {Object} data 
 * @returns 
 */
function writeFile(file, data) {
    return File.writeTo(file, JSON.stringify(data, null, '\t'))
}

class FWebsocketClient {
    constructor(connectLink, name, log) {
        this.name = name;
        this.log = log;
        let WSC = new WSClient();
        this.WSC = WSC;
        WSC.Open = 0;
        WSC.Closing = 1;
        WSC.Closed = 2;
        this.connectLink = connectLink;
        this.isShakeHand = false;
        this.tryConnect = false;

        //事件监听
        this.Events = {
            shaked: null,
            chat: null,
            success: null,
            add: null,
            delete: null,
            cmd: null,
            queryList: null,
            queryOnline: null,
            shutdown: null
        };

        this._InitMsgProcess();
    }

    /**
     * 连接服务器
     * @returns 
     */
    _Connect() {
        return new Promise((cBack, _cErr) => {
            this.WSC.connectAsync(this.connectLink, (bool) => {
                if (bool) {
                    logger.info(`服务端连接成功!`);
                    logger.info(`开始握手...`);
                    this._sendShakeHand();
                } else {
                    cBack(bool);
                }
            });
        });
    }

    /**
     * 重连服务器
     * @returns 
     */
    _ReConnect() {
        this._Close();
        return this._Connect();
    }

    /**
     * 断开与服务器连接
     * @returns 
     */
    _Close() {
        this.isShakeHand = false;
        if (this.WSC.status == this.WSC.Open) {
            return this.close(false);
        }
        return this.close(true);
    }

    /**
     * Websocket内置方法-设定监听消息
     */
    _InitMsgProcess() {
        let wsc = this.WSC;
        wsc.listen("onBinaryReceived", (data) => {
            logger.warn("客户端不支持Binary消息!自动断开!");
            this._Close();
        });
        wsc.listen("onError", (msg) => {
            logger.error(`WSC出现异常: ${msg}`);
            logger.info(`自动重连中...`);
            this._ReConnect();
        });
        wsc.listen("onLostConnection", (code) => {
            logger.warn(`WSC服务器连接丢失!CODE: ${code}`);
            if ([1008, 1003].indexOf(code) == -1 && this.tryConnect) {
                logger.info(`正在尝试重新连接...`);
                this.tryConnect = false;
                let reConnectCount = 0;
                let reConnect = () => {
                    reConnectCount++;
                    if (reConnectCount >= 5) {
                        logger.warn("已超过自动重连次数，请检查后输入/flamehuo reconnect重连");
                    } else {
                        this._ReConnect().then((code) => {
                            if (!code) {
                                logger.warn(`连接失败!重新尝试中...`);
                                reConnect();
                            }
                        });
                    }
                };
                reConnect();
            } else {
                logger.info(
                    `由于CODE码为预设值,所以放弃重新连接,请检查版本是否为最新!`
                );
            }
        });
        wsc.listen("onTextReceived", (msg) => {
            try {
                let json = JSON.parse(msg);
                this._processMessage(json.header, json.body);
            } catch (_) {
                logger.logger.error(_)
                logger.error(`WSC无法解析接收到的字符串!`);
                logger.info(`重新尝试连接...`);
                this._ReConnect();
            }
        });
    }

    /**
     * 向服务器发送响应
     * @param {object} msg 
     * @param {Array} groupId 
     * @param {"success"|"error"} type 
     * @param {string} uuid 
     */
    _Respone(msg, groupId, type, uuid = "") {
        this._sendMsg(type, { msg: msg, group: groupId }, uuid)
    }

    /**
     * 运行事件
     * @param {"shaked"|"chat"|"success"|"add"|"delete"|"cmd"|"queryList"|"queryOnline"|"shutdown"} type 
     * @param {string} id 
     * @param {object} body 
     */
    _runEvent(type, id, body) {
        if (this.Events[type] == null) {
            throw new Error(`事件[${type}]不存在!`);
        }
        try {
            let res = this.Events[type](id, body);
        } catch (e) {
            logger.error(`在运行事件[${type}]时遇到错误: ${e}\n${e.stack}`);
            if (type != "shutdown") {
                logger.info(`正在重新连接...`);
                this._ReConnect();
            }


        }
    }

    /**
     * 消息处理
     * @param {{"type":string,"id":string}} header 
     * @param {object} body 
     */
    _processMessage(header, body) {
        if (header.id == null) {
            logger.info(`收到特殊消息: ${body.msg}, 正在尝试重新连接...`);
            this._ReConnect();
            return;
        }
        try {
            switch (header.type) {
                case "shaked": this.onShaked(header.id, body); break;
                case "chat": this.onChat(header.id, body); break;
                //ws.listen("success")
                case "add": this.onAddAllowList(header.id, body); break;
                case "delete": this.onDelAllowList(header.id, body); break;
                case "cmd": this.onRunCmd(header.id, body); break;
                case "queryList": this.onQueryAllowList(header.id, body); break;
                case "queryOnline": this.onQueryOnline(header.id, body); break;
                case "shutdown": this.onShutDown(header.id, body); break;
            }
        } catch (e) {
            logger.error(`在处理消息是遇到错误: ${e.stack}`);
            logger.error(`此错误具有不可容错性!请检查插件是否为最新!`);
            logger.info(`正在断开连接...`);
            this._Close();
        }
    }

    /**
     * 握手成功
     * @param {string} id 
     * @param {object} body 
     */
    onShaked(id, body) {
        if (body.code == 1) {
            logger.info(`握手完成!`);
            this.continueHeart = 0;
            this.isShakeHand = true;
            this.tryConnect = true;
        } else {
            logger.error(`握手失败!原因: ${body.msg}`);
        }
    }

    /**
     * 聊天信息
     * @param {string} id 
     * @param {object} body 
     */
    onChat(id, body) {
        let config = readFile(CONFIGPATH)
        let chatMsg = config.chatFormat.group
            .replace("{nick}", body.nick)
            .replace("{msg}", body.msg);
        if (config.recvGroupId.indexOf(body.groupId) != -1) {
            sendGroupMsg2Game(chatMsg)
        }
    }

    /**
     * 添加白名单请求
     * @param {string} id 
     * @param {object} body 
     */
    onAddAllowList(id, body) {
        let allowlist = readFile(ALLOWLISTPATH);
        allowlist[body.uuid] = body.xboxid
        let outputAdd = mc.runcmdEx(`allowlist add ${body.xboxid}`)
        if (writeFile(ALLOWLISTPATH, allowlist)) {
            this._Success(outputAdd.output, group)
        }
    }

    /**
     * 删除白名单请求
     * @param {string} id 
     * @param {object} body 
     */
    onDelAllowList(id, body) {
        let allowlist = readFile(ALLOWLISTPATH);
        if (body.uuid in Object.keys(allowlist)) {
            let outputDel = mc.runcmdEx(`allowlist remove ${allowlist[body.uuid]}`);
            delete allowlist[body.uuid];
            if (writeFile(ALLOWLISTPATH, allowlist)) {
                this._Respone(outputDel.output, group, "success")
            }
        } else {
            this._Respone("UUID不存在", group, "error")
        }
    }

    /**
     * 执行命令请求
     * @param {string} id 
     * @param {object} body 
     */
    onRunCmd(id, body) {
        let outputCmd = mc.runcmdEx(body.cmd);
        if (outputCmd.success) {
            this._Respone(outputCmd.output,body.groupId,"success", id)
        } else {
            this._Respone(outputCmd.output, body.groupId,"error", id)
        }
    }

    /**
     * 查询白名单请求
     * @param {string} id 
     * @param {object} body 
     */
    onQueryAllowList(id, body) {
        let wl = readFile(BDSALLOWLISTPATH)
        let BDSAllowlist = eval(wl);
        let allowlistNameString = "服内白名单如下:\n"
        for (let i = 0; i < BDSAllowlist.length; i++) {
            allowlistNameString += BDSAllowlist[i]["name"];
            if (i < BDSAllowlist.length - 1) {
                allowlistNameString += "\n"
            }
        }
        this._sendMsg("queryWl", { "list": allowlistNameString }, id)
    }

    /**
     * 查询在线列表请求
     * @param {string} id 
     * @param {object} body 
     */
    onQueryOnline(id, body) {
        let config = readFile(CONFIGPATH)
        let onlineNameString = ""
        let online = mc.getOnlinePlayers();
        for (let i = 0; i < online.length; i++) {
            let simulated = ""
            if (online[i].isSimulatedPlayer() && config.addSimulatedPlayerTip) {
                simulated = "(假人)"
            }
            onlineNameString += online[i].name + simulated;
            if (i < online.length - 1) {
                onlineNameString += "\n"
            }
        }
        this._sendMsg("queryOnline", { "list": onlineNameString }, id)
    }

    /**
     * 服务端断开连接
     * @param {string} id 
     * @param {object} body 
     */
    onShutDown(id, body) {
        this.tryConnect = false
        logger.error(`服务端命令断开连接 原因:${body.msg}`);
        logger.error(`此错误具有不可容错性!请检查插件配置文件!`);
        logger.info(`正在断开连接...`);
        this._Close();
    }

    /**
     * 监听事件
     * @param {"shaked"|"chat"|"success"|"add"|"delete"|"cmd"|"queryList"|"queryOnline"|"shutdown"} event 
     * @param {(id: string, body: object)=>{}} func 
     * @returns 
     */
    listen(event, func) {
        if (this.Events[event] == null) {
            this.Events[event] = func;
        } else {
            throw new Error(`重复监听事件${event}`)
        }

        return true;
    }

    /**
     * 发送消息
     * @param {"shaked"|"chat"|"success"|"add"|"delete"|"cmd"|"queryList"|"queryOnline"|"shutdown"} type 
     * @param {object} body 
     * @param {string} uuid 
     * @returns 
     */
    _sendMsg(type, body, uuid = system.randomGuid()) {
        if (this.WSC.status != 0 && this.isShakeHand) {
            cb(null);
            return;
        }
        let response = {
            "header": {
                "type": type,
                "id": uuid
            },
            "body": body
        }
        let jsonStr = JSON.stringify(response);
        this.WSC.send(jsonStr);
    }

    /**
     * 向服务端握手
     */
    _sendShakeHand() {
        let config = readFile(CONFIGPATH)
        this._sendMsg(
            "shakeHand",
            { name: this.name, group: config.sendGroupId }
        );
    }

    /**
     * 关闭客户端连接
     * @param {boolean} bool 
     * @returns 
     */
    close(bool = false) {
        this.isShakeHand = false;
        if (!bool) {
            this.WSC.close();
        }
        return true;
    }
}

/**
 * 查询玩家是否屏蔽群消息
 * @param {string} plXuid 
 * @returns 
 */
function queryBlock(plXuid) {
    let block = readFile(BLOCKPATH)
    return Object.keys(block).indexOf(plXuid) == -1 || block[plXuid]
}

/**
 * 为没有屏蔽群消息的玩家发送消息
 * @param {string} msg 
 */
function sendGroupMsg2Game(msg) {

    let online = mc.getOnlinePlayers();
    for (let i = 0; i < online.length; i++) {
        let player = online[i]
        if (queryBlock(player.xuid)) {
            player.tell(msg)
        }
    }
}

/**
 * 屏蔽开关Gui
 * @param {Player} pl 
 */
function blockGui(pl) {
    let fm = mc.newCustomForm();
    fm.setTitle("群消息设置")
    let block = readFile(BLOCKPATH)
    fm.addSwitch("是否接收群消息", queryBlock(pl.xuid));
    pl.sendForm(fm, (pl, da) => {
        block[pl.xuid] = da[0];
        if (writeFile(BLOCKPATH, block)) {
            pl.tell("设置成功")
        }
    })
}


/**
 * 初始化WebSocket服务
 */
function initWebsocketServer() {
    let config = readFile(CONFIGPATH)
    let ws = new FWebsocketClient(config.wsUrl, config.serverName, logger,)
    logger.info("正在连接FlameHuo服务端...")
    ws._Connect().then((status) => {
        if (status) {
            logger.info("FlameHuo服务端连接成功.")
        }
    })

    mc.listen("onChat", (pl, msg) => {
        let config = readFile(CONFIGPATH)
        let fmtStr = config.chatFormat.game
            .replace("{name}", pl.name)
            .replace("{msg}", msg)
        for (let i = 0; i < config.sendGroupId.length; i++) {
            let group = config.sendGroupId[i];
            ws._sendMsg("sendMsg", { "group": group, "msg": fmtStr })
        }
    })
    return ws;
}

/**
 * 注册命令
 * @param {FWebsocketClient} ws 
 */
function regCommand(ws) {
    const cmd = mc.newCommand("flamehuo", "FlameHuo管理", PermType.Any);
    //cmd.setEnum("HomeAction", ["add", "del", "go"]);
    cmd.setEnum("Gui", ["gui", "reconnect"]);
    //cmd.mandatory("action", ParamType.Enum, "HomeAction", 1);
    cmd.mandatory("gui", ParamType.Enum, "Gui", 1);
    //cmd.mandatory("name", ParamType.RawText);
    //cmd.overload(["HomeAction", "name"]);
    cmd.overload(["Gui"]);
    cmd.overload([]);


    cmd.setCallback((_cmd, _ori, out, res) => {
        let homeName = res.name;
        let type = res.gui || "gui"
        if (_ori.player == null && type == "gui") {
            out.error("此命令无法在非玩家终端执行!");
            return;
        }
        let pl = _ori.player;
        switch (type) {
            case "gui":
                blockGui(pl)
                break;
            case "reconnect":
                if (_ori.player == null || _ori.player.permLevel > 0) {
                    if (ws.WSC.status == ws.WSC.Closed) {
                        ws._Connect()
                    } else {
                        out.error("Websocket 处于连接状态，无须重连")
                        return;
                    }
                } else {
                    out.error("权限不足.")
                    return;
                }
                break;
        }
    });
    cmd.setup();
}

/**
 * 初始化插件
 */
function initPlugin() {
    logger.info("FlameHuo 配套插件 v" + VERSION + "已加载。 作者:HuoHuas001")
    ll.registerPlugin(
        "FlameHuo",
        "FlameHuo adapted to LeviLamina",
        VERSION,
        { "Author": "HuoHuas001" }
    );
    mc.listen("onServerStarted", () => {
        let ws = initWebsocketServer()
        regCommand(ws)
    })

}

initPlugin()

//LiteLoaderScript Dev Helper
/// <reference path="E:\\MCServer\\HelperLib\\src\\index.d.ts"/> 

const VERSION = "0.0.1"
const CONFIGPATH = "plugins/FlameHuo/config.json"
const ALLOWLISTPATH = "plugins/FlameHuo/allowlist.json"
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

        this._InitMsgProcess();
    }
    _Connect() {
        return new Promise((cBack, _cErr) => {
            this.WSC.connectAsync(this.connectLink, (bool) => {
                if (bool) {
                    this.log.info(`服务端连接成功!`);
                    this.log.info(`开始握手...`);
                    this._sendShakeHand();
                } else {
                    cBack(bool);
                }
            });
        });
    }
    _ReConnect() {
        this._Close();
        return this._Connect("Server");
    }
    _Close() {
        this.isShakeHand = false;
        if (this.WSC.status == this.WSC.Open) {
            return this.close(false);
        }
        return this.close(true);
    }
    _InitMsgProcess() {
        let wsc = this.WSC;
        wsc.listen("onBinaryReceived", (data) => {
            this.log.warn("客户端不支持Binary消息!自动断开!");
            this._Close();
        });
        wsc.listen("onError", (msg) => {
            this.log.error(`WSC出现异常: ${msg}`);
            this.log.info(`自动重连中...`);
            this._ReConnect();
        });
        wsc.listen("onLostConnection", (code) => {
            this.log.warn(`WSC服务器连接丢失!CODE: ${code}`);
            if ([1008, 1003].indexOf(code) == -1) {
                this.log.info(`正在尝试重新连接...`);
                this.tryConnect = false;
                let reConnectCount = 0;
                let reConnect = () => {
                    reConnectCount++;
                    if (reConnectCount >= 5) {
                        this.log.warn("已超过自动重连次数，请检查后输入/reconnect重连");
                    } else {
                        this._ReConnect().then((code) => {
                            if (!code) {
                                this.log.warn(`连接失败!重新尝试中...`);
                                reConnect();
                            }
                        });
                    }
                };
                reConnect();
            } else {
                this.log.info(
                    `由于CODE码为预设值,所以放弃重新连接,请检查版本是否为最新!`
                );
            }
        });
        wsc.listen("onTextReceived", (msg) => {
            try {
                let json = JSON.parse(msg);
                this._processMessage(json);
            } catch (_) {
                this.log.logger.error(_)
                this.log.error(`WSC无法解析接收到的字符串!`);
                this.log.info(`重新尝试连接...`);
                this._ReConnect();
            }
        });
    }

    _Success(msg, groupId) {
        this._sendMsg("success", { msg: msg, group: groupId })
    }

    _Error(msg, groupId) {
        this._sendMsg("error", { msg: msg, group: groupId })
    }

    _processMessage(data) {
        try {

            let type = data.type;
            let group = data.groupId

            let config = readFile(CONFIGPATH)
            let allowlist = readFile(ALLOWLISTPATH);

            switch (type) {
                case "shaked": {
                    if (data.Code == 1) {
                        this.log.info(`握手完成!`);
                        this.continueHeart = 0;
                        this.isShakeHand = true;
                        this.tryConnect = true;
                    } else {
                        this.log.error(`握手失败!原因: ${data.Msg}`);
                    }
                    break;
                }
                case "chat":
                    mc.broadcast(
                        config.chatFormat.group
                            .replace("{nick}", data["nick"])
                            .replace("{msg}", data["msg"])
                    )
                    //this._Success()
                    break
                case "success":
                    break
                case "add":
                    allowlist[data["uuid"]] = data["xboxid"]
                    let outputAdd = mc.runcmdEx(`allowlist add ${data["xboxid"]}`)
                    if (writeFile(ALLOWLISTPATH, allowlist)) {
                        this._Success(outputAdd.output, group)
                    }
                    break
                case "delete":
                    if (data["uuid"] in Object.keys(allowlist)) {
                        let outputDel = mc.runcmdEx(`allowlist remove ${allowlist[data["uuid"]]}`);
                        delete allowlist[data["uuid"]];
                        if (writeFile(ALLOWLISTPATH, allowlist)) {
                            this._Success(outputDel.output, group)
                        }
                    } else {
                        this._Error("UUID不存在", group)
                    }
                    break
                case "cmd":
                    let outputCmd = mc.runcmdEx(data["cmd"]);
                    if (outputCmd.success) {
                        this._Success(outputCmd.output, group)
                    } else {
                        this._Error(outputCmd.output, group)
                    }

                    break
                case "queryList":
                    let wl = readFile(BDSALLOWLISTPATH)
                    let BDSAllowlist = eval(wl);
                    let nameString = "服内白名单如下:\n"
                    for (let i = 0; i < BDSAllowlist.length; i++) {
                        nameString += BDSAllowlist[i]["name"];
                        if (i < BDSAllowlist.length - 1) {
                            nameString += "\n"
                        }
                    }
                    this._sendMsg("queryWl", { "list": nameString, "uuid": data.uuid })

            }
        } catch (e) {
            this.log.error(`在处理消息是遇到错误: ${e.stack}`);
            this.log.error(`此错误具有不可容错性!请检查插件是否为最新!`);
            this.log.info(`正在断开连接...`);
            this._Close();
        }
    }

    _sendMsg(type, body) {
        if (this.WSC.status != 0 && this.isShakeHand) {
            cb(null);
            return;
        }
        body["type"] = type;
        let jsonStr = JSON.stringify(body);
        this.WSC.send(jsonStr);
    }

    _sendShakeHand() {
        this._sendMsg(
            "shakeHand",
            { name: this.name }
        );
    }

    close(bool = false) {
        if (!bool) {
            this.WSC.close();
        }
        return true;
    }
}


function initWebsocketServer() {
    let config = readFile(CONFIGPATH)
    let ws = new FWebsocketClient(config.wsUrl, config.serverName, logger,)
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
}

function initPlugin() {
    logger.info("FlameHuo 配套插件 v" + VERSION + "已加载。 作者:HuoHuas001")
    ll.registerPlugin(
        /* name */
        "FlameHuo",
        /* introduction */
        "FlameHuo adapted to LeviLamina",
        /* version */
        VERSION,
        /* otherInformation */
        {
            "Author": "HuoHuas001"
        }
    );
    mc.listen("onServerStarted", initWebsocketServer)
}

initPlugin()

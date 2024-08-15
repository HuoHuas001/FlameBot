import aiofiles
import json
import re
file_path = "nickName.json"
admin_path = "adminList.json"

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


#查询管理员
async def queryIsAdmin(groupId,authorId):
    async with aiofiles.open(admin_path, 'r', encoding='utf-8') as file:
        data = await file.read()
        data_dict = json.loads(data)
    if(groupId not in data_dict):
        return False
    if(authorId not in data_dict[groupId]):
        return False
    return True

#添加群组管理员
async def addGroupAdmin(groupId,authorId):
    async with aiofiles.open(admin_path, 'r', encoding='utf-8') as file:
        data = await file.read()
        data_dict = json.loads(data)
    if groupId not in data_dict:
        data_dict[groupId] = []
    if authorId in data_dict[groupId]:
        return True
    data_dict[groupId].append(authorId)
    async with aiofiles.open(admin_path, 'w', encoding='utf-8') as file:
        await file.write(json.dumps(data_dict, indent=4, ensure_ascii=False))
    return True

#删除群组管理员
async def delGroupAdmin(groupId,authorId):
    async with aiofiles.open(admin_path, 'r', encoding='utf-8') as file:
        data = await file.read()
        data_dict = json.loads(data)
    if groupId not in data_dict:
        return True
    data_dict[groupId] = list(filter(lambda x: x == authorId, data_dict[groupId]))
    async with aiofiles.open(admin_path, 'w', encoding='utf-8') as file:
        await file.write(json.dumps(data_dict, indent=4, ensure_ascii=False))
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

#查询是否是符合数字
def isNumber(data:str):
    if(data.isdigit() and int(data) >= 0):
        return True
    return False
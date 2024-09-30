import os
from plugins.plugin_iKnowWxAPI.rsa_crypto import RsaCode, load_pubkey_file
from aiohttp import web
from common.log import logger


# 修改全局配置文件 config.json 中关于AI方面的配置
async def handle_update_ai_setting(request):
    logger.warn("通过POST方式修改AI配置(handle_update_config)")
    data = await request.json()

    keys = {"character_desc"}
    if not keys.issubset(data):
        return _resp_error("参数不完整")
    logger.info("_rsa_verify:{}".format(data))
    # 验证签名
    if not _rsa_verify(data["msg"], data["sign"], data["user"]):
        logger.error("handle_update_ai_setting 签名验证失败")
        return web.HTTPBadRequest(text="数据包验证失败")

    return web.json_response(
        {
            "actual_user_id": "to_user_id",
            "actual_user_nickname": "to_user_nickname",
            **data,
        }
    )

_pubkeys = {}
# 根据用户名从配置中读取公钥
def get_pubkey(user):
    global _pubkeys
    if len(user) < 1:
        return ""
    if user in _pubkeys:
        return _pubkeys[user]

    path = os.path.dirname(__file__)
    pubkeyFile = os.path.join(path, user + "_pubkey.pem")
    # _pubkeys[user] = _config.get(user + "_pubkey")
    _pubkeys[user] = load_pubkey_file(pubkeyFile)
    return _pubkeys[user]


# 验证签名
def _rsa_verify(msg, sign, user):
    return RsaCode().verify(get_pubkey(user), msg, sign)


def _resp_ok(message="ok"):
    resp = {"error": 0, "message": message}
    return web.json_response(resp)


def _resp_error(message, error=404):
    resp = {"error": error, "message": message}
    return web.json_response(resp, status=error)

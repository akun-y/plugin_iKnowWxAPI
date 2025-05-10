import time
from bridge.bridge import Bridge
from common.log import logger
from aiohttp import web

from config import conf, load_config
from plugins.plugin_comm.api.api_groupx import ApiGroupx
from plugins.plugin_iKnowWxAPI.comm import _resp_error, _rsa_verify


# 修改全局配置文件 config.json 中关于AI方面的配置
async def handle_update_ai_setting(request):
    logger.warn("通过POST方式修改AI配置(handle_update_config)")
    data = await request.json()

    keys = {"character_desc", "mode_name", "agent"}
    if not keys.issubset(data):
        err_msg = "handle_update_ai_setting 参数不完整"
        logger.error(err_msg)
        return _resp_error(err_msg)
    
    # 验证签名
    debug = conf().get("debug") == True
    if not debug:
        logger.info("_rsa_verify:{}".format(data))
        if not _rsa_verify(data["character_desc"], data["sign"], data["user"]):
            err_msg = "handle_update_ai_setting 签名验证失败"
            logger.error(err_msg)
            return web.HTTPBadRequest(text=err_msg)
    desc = conf().get("character_desc")

    load_config()
    conf()["character_desc"] = data["character_desc"]
    bot = Bridge().get_bot("chat")
    bot.sessions.clear_all_session()
    desc = conf().get("character_desc")
    return web.json_response(
        {
            "actual_user_id": "to_user_id",
            "actual_user_nickname": "to_user_nickname",
            **data,
        }
    )


def thread_refresh_ai_config():
    time.sleep(12)
    logger.warn("刷新AI配置")
    groupx = ApiGroupx()
    while True:
        if groupx.is_login():
            res = groupx.get_ai_setting()
            if res and res["code"] == 200:
                logger.info(f"获取AI配置信息成功:\n agent:{res['data']['agent']} \n modelName:{res['data']['modelName']}")
                desc = res["data"]["description"]
                if desc:
                    desc = conf()["character_desc"] = desc
                    bot = Bridge().get_bot("chat")
                    bot.sessions.clear_all_session()
                    Bridge().reset_bot()
                    logger.warn(f"======> AI配置更新成功,共{len(desc)}字符....\n{desc[0:96]}...")
            else:
                logger.error(f"======>获取AI配置失败 {res}")
            break
        else:
            logger.warn("======>[iKnowWxAPI] 等待groupx登录成功...")
            groupx.post_login()
            time.sleep(12)

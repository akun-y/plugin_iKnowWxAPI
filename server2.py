import asyncio
import os
import time

import aiofiles
import aiohttp
import arrow
from aiohttp import web

from bridge.reply import Reply, ReplyType
from common.log import logger
from lib import itchat
from plugins.plugin_iKnowWxAPI.find_plugins_func import PluginsFuncProc
from plugins.plugin_iKnowWxAPI.message_proc import MessageProc
from plugins.plugin_iKnowWxAPI.rsa_crypto import RsaCode

_pubkeys = {}


async def handle(request):
    current_time = arrow.now().format("HH:mm:ss")
    return web.Response(text="iKnow Model API Server {}".format(current_time))


# 根据用户名从配置中读取公钥


def get_pubkey(user):
    global _pubkeys
    if len(user) < 1:
        return ""
    if user in _pubkeys:
        return _pubkeys[user]

    _pubkeys[user] = _config.get(user + "_pubkey")
    return _pubkeys[user]


# 验证签名


def _rsa_verify(msg, sign, user):
    return RsaCode().verify(get_pubkey(user), msg, sign)


def _resp_ok(message="ok"):
    resp = {"error": 0, "message": message}
    return web.json_response(resp)


def _resp_error(message, error=400):
    resp = {"error": error, "message": message}
    return web.json_response(resp, status=error)


# url 支持图片,视频,文件等
def _get_real_to_user_id(to_user_nickname, to_user_id, end):
    try:
        friend = itchat.search_friends(userName=to_user_id)
        if friend:
            return friend.UserName, friend.NickName

        if "@@" in to_user_id:
            friends = itchat.search_chatrooms(name=to_user_nickname)
        else:
            friends = itchat.search_friends(name=to_user_nickname)
        if friends and len(friends) > 0:
            if len(friends) > 1:
                logger.error("找到多个用户,请检查昵称是否唯一")
                return None, None
            f = friends[0]
            logger.warn(
                f"通过腾讯服务器重新获取用户,原用户:{to_user_nickname}-{to_user_id}"
            )
            logger.warn(f"====>找到新用户:{f.get('UserName')}")
            return f.get("UserName"), f.get("NickName")
        elif not end:
            itchat.get_friends(update=True)
            return _get_real_to_user_id(to_user_nickname, to_user_id, True)
    except Exception as e:
        logger.error("_get_real_to_user_id 获取用户发生意外 to_user_id,{}".format(e))
    logger.error(
        "_get_real_to_user_id 获取用户失败 to_user_id,{},to_user_nickname,{}".format(
            to_user_id, to_user_nickname
        )
    )
    return to_user_id


async def handle_send_url(request):
    data = await request.json()
    keys = {"type", "user", "sign", "msg", "filename", "to_user_id"}

    if not keys.issubset(data):
        return _resp_error("参数不完整")
    # 验证签名
    if not _rsa_verify(data["msg"], data["sign"], data["user"]):
        logger.error("handle_send_msg 签名验证失败")
        return _resp_error("签名验证失败")
    file_name = data.get("filename")

    to_user_id, to_user_nickname = _get_real_to_user_id(
        data.get("to_user_nickname", None), data.get("to_user_id", None), False
    )
    url = data["msg"]
    if url.startswith("http"):
        if handle_message_process.send_wx_url(
            data.get("type", "IMAGE_URL"), url, to_user_id, file_name
        ):
            return _resp_ok("文件发送成功")
    return _resp_error("发送失败,缺少文件链接")


# 支持通过POST form-data方式上传文件


async def handle_file(request):
    data = await request.post()

    keys = {"user", "sign", "msg", "to_user_id", "file"}
    if not keys.issubset(data):
        return _resp_error("参数不完整")
    # 验证签名
    if not _rsa_verify(data["msg"], data["sign"], data["user"]):
        logger.error("handle_send_msg 签名验证失败")
        return _resp_error("签名验证失败")

    to_user_id, to_user_nickname = _get_real_to_user_id(
        data["to_user_nickname"], data["to_user_id"], False
    )
    upload_file = data["file"]
    if upload_file and upload_file.filename:  # 检查是否上传了文件
        content_type = upload_file.content_type  # 获取上传文件的Content-Type
        ext_name = upload_file.filename.split(".")[-1]
        if content_type.startswith("video/"):
            handle_message_process.send_wx_video(
                to_user_id, upload_file.file.file, ext_name
            )
            return _resp_ok("视频上传成功")
        elif content_type.startswith("image/"):
            handle_message_process.send_wx_img_file(
                to_user_id, upload_file.file.file, ext_name
            )
            return _resp_ok("图片上传成功")
        else:
            return _resp_error("不支持的文件格式")
    else:
        return _resp_error("没有上传文件")


# 支持通过POST json方式发送请求
async def handle_send_msg(request):
    logger.warn("通过POST方式发送消息(LISTEN)")
    logger.info("handle_send_msg:{}".format(request))
    data = await request.json()

    keys = {"user", "msg", "to_user_id", "to_user_nickname"}
    if not keys.issubset(data):
        return _resp_error("参数不完整")
    logger.info("_rsa_verify:{}".format(data))
    # 验证签名
    if not _rsa_verify(data["msg"], data["sign"], data["user"]):
        logger.error("handle_send_msg 签名验证失败")
        return web.HTTPBadRequest(text="数据包验证失败")

    to_user_id, to_user_nickname = _get_real_to_user_id(
        data["to_user_nickname"], data["to_user_id"], False
    )

    msg_type = data["type"].upper()
    if msg_type == "IMAGE":
        logger.info("send image:{} - {}".format(to_user_id, len(data["msg"])))
        handle_message_process.send_wx_img_base64(data["msg"], to_user_id)
    else:
        logger.info("send text:{}-{}".format(data["to_user_id"], data["msg"]))
        handle_message_process.send_wx_text(data["msg"], to_user_id)

    return web.json_response(
        {"actual_user_id": to_user_id, "actual_user_nickname": to_user_nickname, **data}
    )


async def handle_send_plugins(request):
    logger.info("handle_send_plugins:{}".format(request))
    data = await request.json()

    keys = {"user", "msg", "to_user_id", "to_user_nickname"}
    if not keys.issubset(data):
        return _resp_error("参数不完整")
    logger.info("_rsa_verify:{}".format(data))
    # 验证签名
    if not _rsa_verify(data["msg"], data["sign"], data["user"]):
        logger.error("handle_send_msg 签名验证失败")
        return web.HTTPBadRequest(text="数据包验证失败")

    to_user_id, to_user_nickname = _get_real_to_user_id(
        data["to_user_nickname"], data["to_user_id"], False
    )

    # handle_message_process.send_wx_img_base64(data["msg"], to_user_id)

    proc = PluginsFuncProc(_config)
    # proc.runTask(True, data["msg"])
    proc.runTask(to_user_id, True, data["msg"])

    return web.json_response(
        {"actual_user_id": to_user_id, "actual_user_nickname": to_user_nickname, **data}
    )


async def handle(request):
    return web.Response(text="Hello, World!")


async def init():
    pass


async def setup():
    app = web.Application()

    app.router.add_get("/", handle)

    app.router.add_get("/wx", handle)
    app.router.add_post("/send", handle_send_msg)
    app.router.add_post("/send/file", handle_file)
    app.router.add_post("/send/url", handle_send_url)
    app.router.add_post("/send/plugins", handle_send_plugins)

    server_fs = []
    single = web.AppRunner(app)
    await single.setup()
    server_fs.append(web.TCPSite(single, port=9092).start())

    double = web.AppRunner(app)
    await double.setup()
    server_fs.append(web.TCPSite(double, host="localhost", port=9093).start())

    return asyncio.ensure_future(asyncio.gather(*server_fs))


def start_aiohttp():
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    srv = loop.run_until_complete(setup())
    logger.info(f"server runing on... {srv}")
    loop.run_forever()


def server_run2(config, channel):
    global handle_message_process, _config
    # 延迟5秒，让初始化任务执行完
    time.sleep(5)

    _config = config
    handle_message_process = MessageProc(channel)

    logger.warn("=====>server_run:{}".format(config["port"]))

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init())

    while True:
        start_aiohttp()
        logger.error("=====>server_run:{}".format(config["port"]))
        time.sleep(25)
    # while True:
    #     time.sleep(1.1)

    # handle_message_process = MessageProc(channel)
    # logging.info("server_run2:", config['port'])
    # web.run_app(app, host='0.0.0.0', port=config['port'])

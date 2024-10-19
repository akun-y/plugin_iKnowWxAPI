import asyncio
import os
import time

import arrow
from aiohttp import web

from bridge.reply import Reply, ReplyType
from common.log import logger

from plugins.plugin_iKnowWxAPI.find_plugins_func import PluginsFuncProc
from plugins.plugin_iKnowWxAPI.invite_user import handle_invite_user_to_group
from plugins.plugin_iKnowWxAPI.message_proc import MessageProc
from plugins.plugin_iKnowWxAPI.rsa_crypto import RsaCode, load_pubkey_file
from plugins.plugin_iKnowWxAPI.update_ai_setting import handle_update_ai_setting
from plugins.plugin_iKnowWxAPI.comm import _resp_error, _resp_ok, _rsa_verify


async def handle(request):
    current_time = arrow.now().format("HH:mm:ss")
    return web.Response(text="iKnow Model API Server {}".format(current_time))


async def handle_send_url(request):
    data = await request.json()
    keys = {"type", "user", "sign", "msg", "to_user_id"}

    if not keys.issubset(data):
        logger.error("handle_send_url 缺少参数 {}".format(data))
        return _resp_error("参数不完整")
    # 验证签名
    if not _rsa_verify(data["msg"], data["sign"], data["user"]):
        logger.error("handle_send_url 签名验证失败")
        return _resp_error("签名验证失败")
    file_name = data.get("filename", "")

    to_user_id = data["to_user_id"]
    to_user_nickname = data["to_user_nickname"]
    url = data["msg"]
    if url.startswith("http"):
        if handle_message_process.send_wx_url(
            data.get("type", "IMAGE_URL"), url, to_user_id, file_name
        ):
            logger.info("handle_send_url 发送成功 {}".format(url))
            return web.json_response(
                {
                    "actual_user_id": to_user_id,
                    "actual_user_nickname": to_user_nickname,
                    **data,
                }
            )
    logger.error("handle_send_url 链接格式错误 {}".format(url))
    return _resp_error("发送失败,缺少文件链接")


# 支持通过POST form-data方式上传文件


async def handle_file(request):
    data = await request.post()

    keys = {"user", "sign", "msg", "to_user_id", "file"}
    if not keys.issubset(data):
        return _resp_error("参数不完整")
    # 验证签名
    if not _rsa_verify(data["msg"], data["sign"], data["user"]):
        logger.error("handle_file 签名验证失败")
        return _resp_error("签名验证失败")

    to_user_id = data.get("to_user_id")
    to_user_nickname = data.get("to_user_nickname")

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
    logger.warn("通过POST方式发送消息(handle_send_msg)")
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

    to_user_id = data["to_user_id"]
    to_user_nickname = data["to_user_nickname"]

    msg_type = data["type"].upper()
    if msg_type == "IMAGE":
        logger.info("send image:{} - {}".format(to_user_id, len(data["msg"])))
        handle_message_process.send_wx_img_base64(data["msg"], to_user_id)
    elif msg_type == "WX_LINK":
        logger.info("send text:{}-{}".format(data["msg"], to_user_id))
        handle_message_process.send_wx_url("微信链接", data["msg"], to_user_id)
    else:
        logger.info("send text:{}-{}".format(data["to_user_id"], data["msg"]))
        handle_message_process.send_wx_text(data["msg"], to_user_id)

    return web.json_response(
        {"actual_user_id": to_user_id, "actual_user_nickname": to_user_nickname, **data}
    )


# 发送消息给多个群
async def handle_send_msg_groups(request):
    logger.warn("通过POST方式发送消息(handle_send_msg_groups)")
    logger.info("handle_send_msg_groups:{}".format(request))
    data = await request.json()

    keys = {"user", "groupObjectIds", "msg"}
    if not keys.issubset(data):
        logger.error("handle_send_msg_groups 缺少参数 {}".format(data))
        return _resp_error("参数不完整")
    logger.info("_rsa_verify:{}".format(data))
    # 验证签名
    msgData = data["msg"]
    if not _rsa_verify(
        msgData["type"] + msgData["content"], data["sign"], data["user"]
    ):
        logger.error("handle_send_msg_groups 签名验证失败")
        return web.HTTPBadRequest(text="数据包验证失败")

    goupsIds = data["groupObjectIds"]
    for groupId in goupsIds:
        msg_type = data["type"].upper()

        if msg_type == "WX_LINK":
            logger.info("send text:{}-{}".format(data["msg"], groupId))
            handle_message_process.send_wx_url("微信链接", msgData["content"], groupId)
        elif msg_type == "IMAGE_URL":
            logger.info("send image:{} - {}".format(groupId, len(data["msg"])))
            # type, url, to_user_id, fil
            handle_message_process.send_wx_url("图片", msgData["content"], groupId)
        elif msg_type == "VIDEO_URL":
            logger.info("send video:{} - {}".format(groupId, len(data["msg"])))
            handle_message_process.send_wx_url("视频", msgData["content"], groupId)

        elif msg_type == "IMAGE":
            logger.info("send image:{} - {}".format(groupId, len(data["msg"])))
            handle_message_process.send_wx_img_base64(data["msg"], groupId)
        else:
            logger.info("send text:{}-{}".format(data["msg"], groupId))
            handle_message_process.send_wx_text(msgData["content"], groupId)

    return web.json_response(
        {"actual_user_id": goupsIds, "actual_user_nickname": "to_user_nickname", **data}
    )


async def handle_send_plugins(request):
    logger.info("handle_send_plugins:{}".format(request))
    data = await request.json()

    keys = {"user", "msg", "to_user_id", "to_user_nickname"}
    if not keys.issubset(data):
        return _resp_error("参数不完整")
    logger.info("_rsa_verify:{}".format(data))
    # 验证签名
    # if not _rsa_verify(data["msg"], data["sign"], data["user"]):
    #     logger.error("handle_send_plugins 签名验证失败")
    #     return web.HTTPBadRequest(text="数据包验证失败")

    to_user_id = data.get("to_user_id")
    to_user_nickname = data.get("to_user_nickname")
    from_user_id = data.get("from_user_id")
    from_user_nickname = data.get("from_user_nickname")
    actual_user_id = data.get("actual_user_id") or from_user_id
    actual_user_nickname = data.get("actual_user_nickname") or from_user_nickname

    content_data = {        
        **data,
        "isgroup": True,
        "msg": data["msg"],
    }

    proc = PluginsFuncProc(_config)
    # proc.runTask(True, data["msg"])
    proc.runTask(to_user_id, isGroup=True, text=data["msg"],other_dict=content_data)

    return web.json_response(
        {"actual_user_id": actual_user_id, "actual_user_nickname": actual_user_nickname, **data}
    )


async def handle(request):
    return web.Response(text="Hello, World!")


async def init():
    logger.info("server_run2 init")
    return


async def setup():
    global handle_message_process
    app = web.Application()

    app.router.add_get("/", handle)

    app.router.add_get("/wx", handle)
    app.router.add_post("/send", handle_send_msg)
    app.router.add_post("/send/groups", handle_send_msg_groups)
    app.router.add_post("/send/file", handle_file)
    app.router.add_post("/send/url", handle_send_url)
    app.router.add_post("/send/plugins", handle_send_plugins)

    app.router.add_post("/update/ai/setting", handle_update_ai_setting)
    app.router.add_post("/invite/user/to/group", handle_invite_user_to_group_with_process)

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


def listen_server(config, channel, handlers_msg):
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


async def handle_invite_user_to_group_with_process(request):
    return await handle_invite_user_to_group(request, handle_message_process)

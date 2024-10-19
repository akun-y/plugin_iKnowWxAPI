from bridge.reply import Reply, ReplyType
from bridge.context import Context, ContextType
from channel.chat_message import ChatMessage
from common.log import logger
from aiohttp import web


async def handle_invite_user_to_group(request, handlers_msg):
    logger.info("handle_invite_user_to_group")
    data = await request.json()
    user_wxid = data.get("userWxid")
    group_id = data.get("groupWxid")
    content = data.get("content",'')
    is_group = data.get("isGroup", False)
    
    
    # 创建字典
    content_dict = {
        "content": content,
    }
    # 添加必要key
    content_dict["receiver"] = user_wxid
    content_dict["session_id"] = user_wxid
    content_dict["isgroup"] = is_group

    content_dict["msg"] = ChatMessage(content_dict)

    context = Context(ContextType.TEXT, content, content_dict)

    content = group_id
    ret = handlers_msg.send_use_custom(content, ReplyType.InviteRoom, context)
    return web.json_response({"ret": ret, "data": data})

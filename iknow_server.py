# encoding:utf-8

import threading
import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from channel.chat_message import ChatMessage
import logging
from plugins import *
from plugins.plugin_iKnowWxAPI.server2 import server_run2


@plugins.register(
    name="iKnowWxAPI",
    desire_priority=900,
    hidden=True,
    desc="iKnowModel的微信信息处理服务API",
    version="0.63",
    author="akun.yunqi",
)

class iKnowServerAPI(Plugin):
    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context

        self.config = super().load_config()
        if not self.config:
            # 未加载到配置，使用模板中的配置
            self.config = self._load_config_template()
        if self.config:
            self.port = self.config.get("port")

        self.channel = None
        
        self._start_listen_task(self.channel)
        
        logger.info(f"[iKnowWxAPI] inited, config={self.config}")
    
    def _start_listen_task(self,channel):
        # 创建子线程
        t = threading.Thread(target=server_run2,kwargs={
            'config':self.config,
            'channel': channel,})
        t.setDaemon(True)
        t.start()

    def on_handle_context(self, e_context: EventContext):
        if self.channel is None:
            self.channel = e_context["channel"]
            logging.debug(f"本次的channel为：{self.channel}")
            
        if e_context["context"].type not in [
            ContextType.TEXT,
            ContextType.JOIN_GROUP,
            ContextType.PATPAT,
        ]:
            return

        if e_context["context"].type == ContextType.JOIN_GROUP:
            e_context["context"].type = ContextType.TEXT
            msg: ChatMessage = e_context["context"]["msg"]
            e_context["context"].content = f'请你随机使用一种风格说一句问候语来欢迎新用户"{msg.actual_user_nickname}"加入群聊。'
            e_context.action = EventAction.BREAK  # 事件结束，进入默认处理逻辑
            return

        if e_context["context"].type == ContextType.PATPAT:
            e_context["context"].type = ContextType.TEXT
            msg: ChatMessage = e_context["context"]["msg"]
            e_context["context"].content = f"请你随机使用一种风格介绍你自己，并告诉用户输入#help可以查看帮助信息。"
            e_context.action = EventAction.BREAK  # 事件结束，进入默认处理逻辑
            return

        content = e_context["context"].content
        logger.debug("[Hello] on_handle_context. content: %s" % content)
        if content == "Hello":
            reply = Reply()
            reply.type = ReplyType.TEXT
            msg: ChatMessage = e_context["context"]["msg"]
            if e_context["context"]["isgroup"]:
                reply.content = f"Hello, {msg.actual_user_nickname} from {msg.from_user_nickname}"
            else:
                reply.content = f"Hello, {msg.from_user_nickname}"
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑

        if content == "Hi":
            reply = Reply()
            reply.type = ReplyType.TEXT
            reply.content = "Hi"
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK  # 事件结束，进入默认处理逻辑，一般会覆写reply

        if content == "End":
            # 如果是文本消息"End"，将请求转换成"IMAGE_CREATE"，并将content设置为"The World"
            e_context["context"].type = ContextType.IMAGE_CREATE
            content = "The World"
            e_context.action = EventAction.CONTINUE  # 事件继续，交付给下个插件或默认逻辑

    def get_help_text(self, **kwargs):
        help_text = "处理来自用户的消息,发送服务端用户响应消息"
        return help_text

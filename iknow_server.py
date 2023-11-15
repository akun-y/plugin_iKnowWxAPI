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
            
    def get_help_text(self, **kwargs):
        help_text = "处理来自用户的消息,发送服务端用户响应消息"
        return help_text

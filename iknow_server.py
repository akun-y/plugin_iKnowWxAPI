# encoding:utf-8

import threading
import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from channel.chat_message import ChatMessage

from plugins import *
from plugins.plugin_iKnowWxAPI.listen_server import listen_server
from plugins.plugin_iKnowWxAPI.sync_contracts_rooms import SyncContractsRooms
from plugins.plugin_iKnowWxAPI.update_ai_setting import thread_refresh_ai_config


@plugins.register(
    name="iKnowWxAPI",
    desire_priority=900,
    hidden=False,
    desc="iKnowModel的微信信息处理服务API",
    version="0.63",
    author="akun.yunqi",
)
class iKnowServerAPI(Plugin):
    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        self.path = os.path.dirname(__file__)
        self.config = super().load_config()
        if not self.config:
            # 未加载到配置，使用模板中的配置
            self.config = self._load_config_template()
        if self.config:
            self.port = self.config.get("port")

        self.channel = None

        self._start_listen_task(self.channel)
        self._start_ai_setting_refresh_task()
        
        logger.info(f"======>[iKnowWxAPI] inited")

    #启动监听服务,默认监听9092,用于发送微信消息
    def _start_listen_task(self, channel):
        # 创建子线程
        t = threading.Thread(
            target=listen_server,
            kwargs={
                "config": self.config,
                "channel": channel,
            },
        )
        t.setDaemon(True)
        t.start()
    #启动更新ai 配置线程,配置信息来自groupx服务器,更新后退出
    def _start_ai_setting_refresh_task(self):
        # 创建子线程
        t = threading.Thread(
            target=thread_refresh_ai_config,
           
        )
        #t.setDaemon(True)
        t.start()
        
    def on_handle_context(self, e_context: EventContext):
        pass

    def get_help_text(self, **kwargs):
        help_text = "处理来自用户的消息,发送服务端用户响应消息"
        return help_text

    def post_contacts_to_groupx(self, rooms, contracts):
        if not self.config.get('sync_contracts'):
            logger.warn("======>[iKnowWxAPI] 通讯录同步功能未开启")
            return
        SyncContractsRooms(rooms, contracts).postWxInfo2Groupx()
        pass

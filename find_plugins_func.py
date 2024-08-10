# encoding:utf-8
import plugins
from bridge.context import ContextType, Context
from bridge.reply import Reply, ReplyType
from channel.chat_message import ChatMessage
import logging
from plugins import *
import re
import arrow
from bridge.bridge import Bridge
import config as RobotConfig
import requests
import io
import time
import gc
from channel import channel_factory


# 通过输入指令，确定是否有插件能够处理该指令，如有则调用并将调用结果返回。
class PluginsFuncProc(object):
    def __init__(self,_config):
        super().__init__()
        self.conf = _config
        self.channel = None

    # 使用默认的回复
    def replay_use_default(self, reply_message, e_context: EventContext):
        # 回复内容
        reply = Reply()
        reply.type = ReplyType.TEXT
        reply.content = reply_message
        e_context["reply"] = reply
        e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑

    # 使用自定义回复
    def replay_use_custom(
        self,
        reply_text: str,
        replyType: ReplyType,
        context: Context,
        retry_cnt=0,
    ):
        try:
            reply = Reply()
            reply.type = replyType
            reply.content = reply_text
            channel_name = RobotConfig.conf().get("channel_type", "wx")
            channel = channel_factory.create_channel(channel_name)
            channel.send(reply, context)

            # 释放
            channel = None
            gc.collect()

        except Exception as e:
            if retry_cnt < 2:
                time.sleep(3 + 3 * retry_cnt)
                self.replay_use_custom(reply_text, replyType, context, retry_cnt + 1)

    # 执行定时task
    def runTask(self, to_user_id, isGroup: bool, text: str):
        # 事件内容
        eventStr = text
        # 发送的用户ID
        other_user_id = to_user_id
        # 是否群聊
        isGroup = True

        logger.info("触发了定时任务：{} , 任务详情：{}".format("taskId", eventStr))

        # 去除多余字符串
        orgin_string = eventStr.replace("ChatMessage:", "")
        # 使用正则表达式匹配键值对
        pattern = r"(\w+)\s*=\s*([^,]+)"
        matches = re.findall(pattern, orgin_string)
        # 创建字典
        content_dict = {match[0]: match[1] for match in matches}
        # 替换源消息中的指令
        content_dict["content"] = eventStr
        # 添加必要key
        content_dict["receiver"] = other_user_id
        content_dict["session_id"] = other_user_id
        content_dict["isgroup"] = isGroup
        msg: ChatMessage = ChatMessage(content_dict)
        # 信息映射
        for key, value in content_dict.items():
            if hasattr(msg, key):
                setattr(msg, key, value)
        # 处理message的is_group
        msg.is_group = isGroup
        content_dict["msg"] = msg
        context = Context(ContextType.TEXT, eventStr, content_dict)

        # 处理GPT
        event_content = eventStr
        key_word = "GPT"
        isGPT = event_content.startswith(key_word)

        # GPT处理
        # if isGPT:
        #     index = event_content.find(key_word)
        #     #内容体
        #     event_content = event_content[:index] + event_content[index+len(key_word):]
        #     event_content = event_content.strip()
        #     #替换源消息中的指令
        #     content_dict["content"] = event_content
        #     msg.content = event_content
        #     context.__setitem__("content",event_content)

        #     content = context.content.strip()
        #     imgPrefix = RobotConfig.conf().get("image_create_prefix")
        #     img_match_prefix = self.check_prefix(content, imgPrefix)
        #     if img_match_prefix:
        #         content = content.replace(img_match_prefix, "", 1)
        #         context.type = ContextType.IMAGE_CREATE

        #     #获取回复信息
        #     replay :Reply = Bridge().fetch_reply_content(content, context)
        #     self.replay_use_custom(model,replay.content,replay.type, context)
        #     return

        # 变量
        e_context = None
        # 是否开启了所有回复路由
        is_open_route_everyReply = self.conf.get("is_open_route_everyReply", True)
        if is_open_route_everyReply:
            try:
                # 检测插件是否会消费该消息
                e_context = PluginManager().emit_event(
                    EventContext(
                        Event.ON_HANDLE_CONTEXT,
                        {"channel": self.channel, "context": context, "reply": Reply()},
                    )
                )
            except Exception as e:
                print(f"开启了所有回复均路由，但是消息路由插件异常！后续会继续查询是否开启拓展功能。错误信息：{e}")

        # 查看配置中是否开启拓展功能
        is_open_extension_function = self.conf.get("is_open_extension_function", True)
        # 需要拓展功能 & 未被路由消费
        route_replyType = None
        isFindExFuc = False
        if e_context:
            route_replyType = e_context["reply"].type
        if is_open_extension_function and route_replyType is None:
            # 事件字符串
            event_content = eventStr
            # 支持的功能
            funcArray = self.conf.get("extension_function", [])
            for item in funcArray:
                key_word = item["key_word"]
                func_command_prefix = item["func_command_prefix"]
                # 匹配到了拓展功能
                isFindExFuc = False
                if event_content.startswith(key_word):
                    index = event_content.find(key_word)
                    insertStr = func_command_prefix + key_word
                    # 内容体
                    event_content = (
                        event_content[:index]
                        + insertStr
                        + event_content[index + len(key_word) :]
                    )
                    event_content = event_content.strip()
                    isFindExFuc = True
                    break

            # 找到了拓展功能
            if isFindExFuc:
                # 替换源消息中的指令
                content_dict["content"] = event_content
                msg.content = event_content
                context.__setitem__("content", event_content)

                try:
                    # 检测插件是否会消费该消息
                    e_context = PluginManager().emit_event(
                        EventContext(
                            Event.ON_HANDLE_CONTEXT,
                            {
                                "channel": self.channel,
                                "context": context,
                                "reply": Reply(),
                            },
                        )
                    )
                except Exception as e:
                    print(f"路由插件异常！将使用原消息回复。错误信息：{e}")

        # 回复处理
        reply_text = ""
        replyType = None
        # 插件消息
        if e_context:
            reply = e_context["reply"]
            if reply and reply.type:
                reply_text = reply.content
                replyType = reply.type

        # 原消息
        if reply_text is None or replyType is None:
            reply_text = eventStr
            replyType = ReplyType.TEXT

        # 消息回复
        self.replay_use_custom(reply_text, replyType, context)

    # 检查前缀是否匹配
    def check_prefix(self, content, prefix_list):
        if not prefix_list:
            return None
        for prefix in prefix_list:
            if content.startswith(prefix):
                return prefix
        return None

    # 自定义排序函数，将字符串解析为 arrow 对象，并按时间进行排序
    def custom_sort(self, time):
        # cron - 排列最后
        if time.startswith("cron"):
            return arrow.get("23:59:59", "HH:mm:ss")

        # 普通时间
        return arrow.get(time, "HH:mm:ss")

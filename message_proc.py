import base64
import os
from hashlib import md5
import hashlib
import uuid
from bridge.context import ContextType, Context
from bridge.reply import Reply, ReplyType
from channel.chat_message import ChatMessage
import logging
from plugins import *
from bridge.bridge import Bridge
import config as RobotConfig
import requests
import time
import gc
from common.log import logger
from channel import channel_factory


class MessageProc(object):
    def __init__(self, channel):
        super().__init__()
        # 保存定时任务回调
        self.channel = channel

        curdir = os.path.dirname(__file__)
        self.saveFolder = os.path.join(curdir, "saved")
        if not os.path.exists(self.saveFolder):
            os.makedirs(self.saveFolder)

    def send_wx_text(self, content, to_user_id):
        # 创建字典
        content_dict = {
            "content": "eventStr",
        }
        # 添加必要key
        content_dict["receiver"] = to_user_id
        content_dict["session_id"] = to_user_id
        content_dict["isgroup"] = False

        content_dict["msg"] = ChatMessage(content_dict)

        context = Context(ContextType.TEXT, "eventStr", content_dict)

        self.send_use_custom(content, ReplyType.TEXT, context)
       # itchat.set_pinned(to_user_id, True)

    def _normalize_url_type(self, media_type):
        """将前端历史 type 值归一化为 send_wx_url 识别的中文类型。"""
        if not media_type:
            return "图片"
        media_type = str(media_type).strip()
        aliases = {
            "image_url": "图片",
            "imageurl": "图片",
            "image": "图片",
            "video_url": "视频",
            "videourl": "视频",
            "video": "视频",
            "file": "文件",
            "wx_link": "微信链接",
            "wxlink": "微信链接",
        }
        return aliases.get(media_type.lower(), media_type)

    def _build_url_context(self, url, to_user_id):
        content_dict = {
            "content": url,
            "receiver": to_user_id,
            "session_id": to_user_id,
            "isgroup": False,
        }
        content_dict["msg"] = ChatMessage(content_dict)
        return content_dict

    def _send_image_url(self, url, to_user_id):
        """优先下载后发本地图片；失败时回退旧的 IMAGE_URL 通道。"""
        try:
            ext_name = self._guess_ext_from_url(url, "jpg")
            file_path = self.save_url_to_local(url, str(uuid.uuid4()), ext_name)
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                return self._send_local_media(
                    to_user_id, file_path, ReplyType.IMAGE, ContextType.IMAGE, url
                )
        except Exception as e:
            logger.warn(f"[WX] 下载图片失败，回退 IMAGE_URL: {e}")

        content_dict = self._build_url_context(url, to_user_id)
        context = Context(ContextType.IMAGE, url, content_dict)
        return self.send_use_custom(url, ReplyType.IMAGE_URL, context)

    def _send_video_url(self, url, to_user_id):
        """优先下载后发本地视频；失败时回退旧的 VIDEO_URL 通道。"""
        try:
            ext_name = self._guess_ext_from_url(url, "mp4")
            file_path = self.save_url_to_local(url, str(uuid.uuid4()), ext_name)
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                return self._send_local_media(
                    to_user_id, file_path, ReplyType.VIDEO, ContextType.VIDEO, url
                )
        except Exception as e:
            logger.warn(f"[WX] 下载视频失败，回退 VIDEO_URL: {e}")

        content_dict = self._build_url_context(url, to_user_id)
        context = Context(ContextType.VIDEO, url, content_dict)
        return self.send_use_custom(url, ReplyType.VIDEO_URL, context)

    def _guess_ext_from_url(self, url, default="jpg"):
        path = url.split("?", 1)[0]
        ext_name = os.path.splitext(path)[1].lstrip(".").lower()
        if ext_name in ("jpg", "jpeg", "png", "gif", "webp", "bmp"):
            return "jpg" if ext_name == "jpeg" else ext_name
        return default

    def send_wx_url(self, type, url, to_user_id, file_name="x"):
        type = self._normalize_url_type(type)
        keys = {"图片", "视频", "文件", "月图片", "公开月图片", "微信链接"}

        if type not in keys:
            logger.error(f"不支持的URL类型{type},支持类型为: {keys}")
            return False

        if type in ["图片", "月图片", "公开月图片"]:
            return self._send_image_url(url, to_user_id)
        if type == "微信链接":
            content_dict = self._build_url_context(url, to_user_id)
            context = Context(ContextType.MP_LINK, url, content_dict)
            return self.send_use_custom(url, ReplyType.LINK, context)
        if type == "视频":
            return self._send_video_url(url, to_user_id)
        if type == "文件":
            ext_name = os.path.splitext(file_name)[1]
            if len(ext_name) > 1:
                ext_name = ext_name[1:]
            if not ext_name:
                ext_name = self._guess_ext_from_url(url, "bin")

            save_name = file_name or "x"
            file_path = self.save_url_to_local(url, save_name, ext_name)
            content_dict = self._build_url_context(url, to_user_id)
            context = Context(ContextType.FILE, file_name, content_dict)
            return self.send_use_custom(file_path, ReplyType.FILE, context)
        return False

    # 保存二进制数据为文件,如jpg,mp4等
    def save_metadata_to_file(self, binary_data, ext_name):
        file_hash = md5(binary_data).hexdigest()
        file_name = os.path.join(self.saveFolder, f"{file_hash}.{ext_name}")

        if not os.path.exists(file_name):
            with open(file_name, "wb") as image_file:
                image_file.write(binary_data)
                logger.info(f"文件保存为{file_name}")
        else:
            logging.info("文件已经存在:" + file_name)
        return file_name

    def save_file_to_local(self, file, ext_name):
        uuid_str = uuid.uuid4()
        md5_hash = hashlib.md5()
        tmp_file = os.path.join(self.saveFolder, f"{uuid_str}.{ext_name}")
        with open(tmp_file, "wb") as f:
            while True:
                chunk = file.read(4096)
                if not chunk:
                    break
                f.write(chunk)
                md5_hash.update(chunk)
        file_hash = md5_hash.hexdigest()
        file_name = os.path.join(self.saveFolder, f"{file_hash}.{ext_name}")
        if os.path.exists(file_name):
            os.remove(tmp_file)
        else:
            os.rename(tmp_file, file_name)
        return file_name

    def save_url_to_local(self, url, file_name, ext_name=""):
        tmp_file = os.path.join(self.saveFolder, file_name + "." + ext_name)
        with open(tmp_file, "wb") as f:
            logger.info(f"[WX] start download file, url={url}")
            file_res = requests.get(url, stream=True)
            size = 0
            for block in file_res.iter_content(1024):
                size += len(block)
                f.write(block)

        return tmp_file

    def _send_local_media(
        self, to_user_id, file_path, reply_type, context_type, context_content=None
    ):
        context_content = context_content or file_path
        content_dict = {
            "content": context_content,
            "receiver": to_user_id,
            "session_id": to_user_id,
            "isgroup": False,
        }
        content_dict["msg"] = ChatMessage(content_dict)
        context = Context(context_type, context_content, content_dict)
        return self.send_use_custom(file_path, reply_type, context)

    def send_wx_img_file(self, to_user_id, file, ext_name):
        file_path = self.save_file_to_local(file, ext_name)
        return self._send_local_media(
            to_user_id, file_path, ReplyType.IMAGE, ContextType.IMAGE
        )

    def send_wx_img_base64(self, content, to_user_id):
        header, _, image_data = content.partition(",")
        if not image_data:
            image_data = content
        image_binary = base64.b64decode(image_data)
        ext_name = "jpg"
        if header.startswith("data:image/"):
            mime = header.split(";")[0].split("/")[-1].lower()
            if mime == "png":
                ext_name = "png"
            elif mime in ("jpeg", "jpg"):
                ext_name = "jpg"
            elif mime in ("gif", "webp"):
                ext_name = mime
        file_path = self.save_metadata_to_file(image_binary, ext_name)
        return self._send_local_media(
            to_user_id, file_path, ReplyType.IMAGE, ContextType.IMAGE
        )

    def send_wx_video(self, to_user_id, file, ext_name):
        file_path = self.save_file_to_local(file, ext_name)
        return self._send_local_media(
            to_user_id, file_path, ReplyType.VIDEO, ContextType.VIDEO
        )

    def send_wx_file_local(self, to_user_id, file, ext_name, display_name="file"):
        if isinstance(file, str):
            file_path = file
        else:
            file_path = self.save_file_to_local(file, ext_name)
        return self._send_local_media(
            to_user_id,
            file_path,
            ReplyType.FILE,
            ContextType.FILE,
            display_name,
        )

    # 使用默认的回复,仅支持文本
    def send_use_default(self, reply_message, e_context: EventContext):
        # 回复内容
        reply = Reply()
        reply.type = ReplyType.TEXT
        reply.content = reply_message
        e_context["reply"] = reply
        e_context.action = (
            EventAction.BREAK_PASS
        )  # 事件结束，并跳过处理context的默认逻辑

    # 使用自定义回复
    def send_use_custom(
        self, reply_text: str, replyType: ReplyType, context: Context, retry_cnt=0
    ):
        try:
            reply = Reply(replyType, reply_text)
            channel_name = RobotConfig.conf().get("channel_type", "wx")
            channel = channel_factory.create_channel(channel_name)
            channel.send(reply, context)

            # 释放
            channel = None
            gc.collect()
            return True
        except Exception as e:
            logger.error(e)
            if retry_cnt < 2:
                logger.warn("重试发送 send_use_custom")
                time.sleep(3 + 3 * retry_cnt)
                self.send_use_custom(reply_text, replyType, context, retry_cnt + 1)
            return False

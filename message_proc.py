
import base64
from hashlib import md5
import hashlib
import uuid
import plugins
from bridge.context import ContextType, Context
from bridge.reply import Reply, ReplyType
from channel.chat_message import ChatMessage
import logging
from plugins import *
from lib import itchat
from lib.itchat.content import *
import re
import arrow
from bridge.bridge import Bridge
import config as RobotConfig
import requests
import io
import time
import gc
from common.log import logger
from channel import channel_factory


class MessageProc(object):
    def __init__(self, channel):
        super().__init__()
        #保存定时任务回调
        self.channel = channel

        curdir = os.path.dirname(__file__)
        self.saveFolder = os.path.join(curdir, 'saved')
        if not os.path.exists(self.saveFolder):
                os.makedirs(self.saveFolder)

    def send_wx_text(self, content, to_user_id):
        # 创建字典
        content_dict = {
            'content': 'eventStr',
        }
        #添加必要key
        content_dict["receiver"] = to_user_id
        content_dict["session_id"] = to_user_id
        content_dict["isgroup"] = False

        content_dict["msg"] = ChatMessage(content_dict)

        context = Context(ContextType.TEXT, 'eventStr', content_dict)

        self.send_use_custom(content, ReplyType.TEXT, context)
        itchat.set_pinned(to_user_id, True)
    def send_wx_url(self, type, url, to_user_id,file_name=''):
        keys = {'图片', '视频', '文件'}

        if not type in keys:
            logger.error(f'不支持的URL类型{type},支持类型为: {keys}')
            return False

        # 创建字典
        content_dict = {'content': url}
        #添加必要key
        content_dict["receiver"] = to_user_id
        content_dict["session_id"] = to_user_id
        content_dict["isgroup"] = False

        content_dict["msg"] = ChatMessage(content_dict)
        
        itchat.set_pinned(to_user_id, True)
        
        if(type == "图片"):
            context = Context(ContextType.IMAGE, url, content_dict)
            return self.send_use_custom(url, ReplyType.IMAGE_URL, context)
        elif type == '视频':
            context = Context(ContextType.VIDEO, url, content_dict)
            return self.send_use_custom(url, ReplyType.VIDEO_URL, context)
        elif type == '文件':
            ext_name = os.path.splitext(file_name)[1]
            if(len(ext_name) > 1): ext_name = ext_name[1:]
            
            file_path = self.save_url_to_local(url, file_name,ext_name)
            context = Context(ContextType.FILE, file_name, content_dict)
            
            return self.send_use_custom(file_path, ReplyType.FILE, context)
        return False
    #保存二进制数据为文件,如jpg,mp4等
    def save_metadata_to_file(self, binary_data, ext_name):
        file_hash = md5(binary_data).hexdigest()
        file_name = os.path.join(self.saveFolder, f'{file_hash}.{ext_name}')

        if not os.path.exists(file_name):
            with open(file_name, "wb") as image_file:
                image_file.write(binary_data)
                logger.info(f"文件保存为{file_name}")
        else:
            logging.info('文件已经存在:'+file_name)
        return file_name
    def save_file_to_local(self, file, ext_name):
        uuid_str = uuid.uuid4()
        md5_hash = hashlib.md5()
        tmp_file = os.path.join(self.saveFolder, f'{uuid_str}.{ext_name}')
        with open(tmp_file, 'wb') as f:
            while True:
                chunk = file.read(4096)
                if not chunk:
                    break
                f.write(chunk)
                md5_hash.update(chunk)
        file_hash=md5_hash.hexdigest()
        file_name = os.path.join(self.saveFolder, f'{file_hash}.{ext_name}')
        if os.path.exists(file_name):
            os.remove(tmp_file)
        else:
            os.rename(tmp_file, file_name)
        return file_name
    def save_url_to_local(self, url, file_name,ext_name):
        tmp_file = os.path.join(self.saveFolder, file_name)
        with open(tmp_file, 'wb') as f:
            logger.info(f"[WX] start download file, url={url}")
            file_res = requests.get(url, stream=True)
            size = 0
            for block in file_res.iter_content(1024):
                size += len(block)
                f.write(block)
                
        return tmp_file

    def send_wx_img_file(self, to_user_id, file, ext_name):
        file_name = self.save_file_to_local(file, ext_name)
        itchat.send_image(file_name, to_user_id)
    def send_wx_img_base64(self, content, to_user_id):
        # 获取图片数据部分（去除"data:image/png;base64,"这部分）
        image_data = content.split(",")[1]
        image_binary = base64.b64decode(image_data)
        file_name = self.save_metadata_to_file(image_binary, "jpg")

        itchat.send_image(file_name, to_user_id)

    def send_wx_video(self, to_user_id, file, ext_name):
        file_name = self.save_file_to_local(file, ext_name)
        itchat.send_video(file_name, to_user_id)

    #使用默认的回复,仅支持文本
    def send_use_default(self, reply_message, e_context: EventContext):
        #回复内容
        reply = Reply()
        reply.type = ReplyType.TEXT
        reply.content = reply_message
        e_context["reply"] = reply
        e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑

    #使用自定义回复
    def send_use_custom(self, reply_text: str, replyType: ReplyType, context : Context, retry_cnt=0):
        try:
            reply = Reply()
            reply.type = replyType
            reply.content = reply_text
            channel_name = RobotConfig.conf().get("channel_type", "wx")
            channel = channel_factory.create_channel(channel_name)
            channel.send(reply, context)

            #释放
            channel = None
            gc.collect()
            return True
        except Exception as e:
            if retry_cnt < 2:
                time.sleep(3 + 3 * retry_cnt)
                #self.replay_use_custom(model, reply_text, replyType, context,retry_cnt + 1)
            return False

import time
import aiofiles
import aiohttp
import asyncio
from aiohttp import web
import arrow
from common.log import logger

from plugins.plugin_iKnowWxAPI.message_proc import MessageProc
from plugins.plugin_iKnowWxAPI.rsa_crypto import RsaCode

handle_message_process = None
_config = None
_pubkeys = {}
async def handle(request):
    current_time = arrow.now().format('HH:mm:ss')
    return web.Response(text="iKnow Model API Server {}".format(current_time))

#根据用户名从配置中读取公钥
def get_pubkey(user):
    global _pubkeys
    if (len(user) < 1):
        return ""
    if user in _pubkeys:
        return _pubkeys[user]
    
    _pubkeys[user] = _config.get(user+"_pubkey")
    return _pubkeys[user]
#验证签名
def _rsa_verify(msg, sign, user):
    return RsaCode().verify(get_pubkey(user),msg,sign)
def _resp_ok(message="ok"):
    resp = {
        'error':0,
        'message':message
    }
    return web.json_response(resp)
def _resp_error(message,error=400):
    resp = {
        'error':error,
        'message':message
    }
    return web.json_response(resp,status=error)
#支持通过POST form-data方式上传文件
async def handle_file(request):
    data = await request.post() 
    
    keys = {'user','sign','msg','to_user_id', 'file'}
    if not keys.issubset(data):
        return _resp_error('参数不完整')
    #验证签名
    if not _rsa_verify(data['msg'], data['sign'], data['user']):
        logger.error('handle_send_msg 签名验证失败')
        return _resp_error('签名验证失败')

    to_user_id = data['to_user_id']
    upload_file = data['file']    
    if upload_file and upload_file.filename:  # 检查是否上传了文件
        content_type = upload_file.content_type  # 获取上传文件的Content-Type
        ext_name = upload_file.filename.split('.')[-1]
        if content_type.startswith('video/'):            
            handle_message_process.send_wx_video(to_user_id,upload_file.file.file,ext_name)     
            return _resp_ok("视频上传成功")
        elif content_type.startswith('image/'):
            handle_message_process.send_wx_img_file(to_user_id,upload_file.file.file,ext_name)     
            return _resp_ok("图片上传成功")
        else:
            return _resp_error('不支持的文件格式')
    else:
        return _resp_error('没有上传文件')

#支持通过POST json方式发送请求
async def handle_send_msg(request):
    data =await request.json()
    
    keys = {'user', 'msg', 'to_user_id'}
    if not keys.issubset(data):
        return _resp_error('参数不完整')

    #验证签名
    if not _rsa_verify(data['msg'], data['sign'], data['user']):
        logger.error('handle_send_msg 签名验证失败')
        return web.HTTPBadRequest(text='数据包验证失败')
    
    type = data['type'].upper()
    if type == 'IMAGE':
        logger.info("send image:", data['to_user_id'],len(data['msg']))
        handle_message_process.send_wx_img_base64(data['msg'],data['to_user_id'])     
    else:
        logger.info("send text:", data['to_user_id'],data['msg'])
        handle_message_process.send_wx_text(data['msg'],data['to_user_id'])
    
    return web.json_response(data)

app = web.Application(client_max_size=1024*1024*20)

app.router.add_get('/', handle)
app.router.add_get('/wx', handle)
app.router.add_post('/send', handle_send_msg)
app.router.add_post('/send/file', handle_file)


def server_run2(config,channel):
    global handle_message_process,_config
    #延迟5秒，让初始化任务执行完
    time.sleep(5)
        
    _config = config
    handle_message_process = MessageProc(channel)
    logger.info("server_run2:", config['port'])
    web.run_app(app, host='0.0.0.0', port=config['port'])



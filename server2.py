import time
import aiofiles
import aiohttp
import asyncio
from aiohttp import web
import arrow

from plugins.plugin_iKnowWxAPI.message_proc import MessageProc

handle_message_process = None

async def handle(request):
    current_time = arrow.now().format('HH:mm:ss')
    return web.Response(text="iKnow Model API Server {}".format(current_time))

#支持通过POST form-data方式上传文件
async def handle_file(request):
    data = await request.post() 
    
    keys = {'to_user_id', 'file'}
    if not keys.issubset(data):
        return web.Response(text='参数不完整', status=400)
    
    to_user_id = data['to_user_id']
    upload_file = data['file']    
    if upload_file and upload_file.filename:  # 检查是否上传了文件
        content_type = upload_file.content_type  # 获取上传文件的Content-Type
        ext_name = upload_file.filename.split('.')[-1]
        if content_type.startswith('video/'):            
            handle_message_process.send_wx_video(to_user_id,upload_file.file.file,ext_name)     
            return web.Response(text='视频上传成功')
        elif content_type.startswith('image/'):
            handle_message_process.send_wx_img_file(to_user_id,upload_file.file.file,ext_name)     
            return web.Response(text='图片上传成功')
        else:
            return web.Response(text='只接受视频文件', status=400)
    else:
        return web.Response(text='未上传文件', status=400)

#支持通过POST json方式发送请求
async def handle_send_msg(request):
    data =await request.json()   
    
    type = data['type'].upper()
    if type == 'IMAGE':
        print("send image:", data['to_user_id'],len(data['msg']))
        handle_message_process.send_wx_img_base64(data['msg'],data['to_user_id'])     
    else:
        print("send text:", data['to_user_id'],data['msg'])
        handle_message_process.send_wx_text(data['msg'],data['to_user_id'])
    
    return web.json_response(data)

app = web.Application(client_max_size=1024*1024*20)

app.router.add_get('/', handle)
app.router.add_get('/wx', handle)
app.router.add_post('/send', handle_send_msg)
app.router.add_post('/send/file', handle_file)


def server_run2(port,channel):
    global handle_message_process
    #延迟5秒，让初始化任务执行完
    time.sleep(5)
        
    handle_message_process = MessageProc(channel)
    #port = 9092
    print("server_run2:", port)
    web.run_app(app, host='0.0.0.0', port=port)



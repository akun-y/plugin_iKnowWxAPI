# 目的
在iKow-on-wechat,chatgpt-on-wechat项目中，作为插件，用于接收来自指定服务器的消息发送请求

# 试用场景
目前是在个人,群,微信公众号下面使用过。

# 使用步骤
1 进入管理员模式:
```
#auth password
```
如果没设置管理员密码，启动程序时会在输出信息中提示临时密码，否则设置 config.json 中Godcmd下 password
2 安装插件
```
#installp https://github.com/akun-y/plugin_iKnowWxAPI.git

* 注意:缺少模块是,可手动安装,如:
pip install numpy -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

```
3 查看插件安装结果
```
#scanp
```
4 启动插件
```
#enablep iKnowWxAPI
```
5 停止插件
```
#disablep iKnowWxAPI
```
6 卸载插件
```
#uninstallp iKnowWxAPI
```


# 验证结果

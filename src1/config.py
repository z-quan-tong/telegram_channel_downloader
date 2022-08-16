import os

# your telegram api id
api_id = int(os.getenv('api_id')  )
# your telegram api hash
api_hash = os.getenv('api_hash')
# your bot_token
bot_token = os.getenv('bot_token')
# your chat id
admin_id = int(os.getenv('admin_id'))
# file save path
save_path = os.getenv('save_path')

# 同时下载数量
max_num = int(os.getenv('max_num'))
# filter file name/文件名过滤
filter_list = os.getenv('filter_list')
if len(filter_list) > 0:
    filter_list = filter_list.split(",")
else:
    filter_list = []
# filter chat id /过滤某些频道不下载
blacklist = os.getenv('blacklist')

def f(s):
    return int(s) 
if len(blacklist) > 0:
    blacklist = [int(x) for x in blacklist.split(",")]
else:
    blacklist = []

# 监控所有你加入的频道，收到的新消息如果包含媒体都会下载，默认关闭; 1/0 => True/False
download_all_chat = os.getenv('download_all_chat')
# 过滤文件后缀，可以填jpg、avi、mkv、rar等。
filter_file_name = os.getenv('filter_file_name')
if len(filter_file_name) > 0:
    filter_file_name = filter_file_name.split(",")
else:
    filter_file_name = []
# 自行替换代理设置，如果不需要代理，请删除括号内容
# proxy = ("socks5", '127.0.0.1', 4444) 
# mac 用docker启动时，host: docker.for.mac.host.internal
proxy = os.getenv('proxy')
if len(proxy) > 0:
    proxy = tuple(proxy.split(","))
else:
    proxy = ()


size_min = 80 * 1024 * 1024
size_max = 500 * 1024 * 1024

duration_min = 300
duration_max = 1800
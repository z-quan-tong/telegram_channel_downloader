# !/usr/bin/env python3
import difflib
import os
import re
import time
import asyncio
import asyncio.subprocess
import logging
from turtle import tilt
from xmlrpc.client import boolean

from telethon import TelegramClient, events, errors
from telethon.tl.types import MessageMediaWebPage, PeerChannel

# ***********************************************************************************#
# your telegram api id
api_id = os.getenv('api_id')  
# your telegram api hash
api_hash = os.getenv('api_hash')
# your bot_token
bot_token = os.getenv('bot_token')
# your chat id
admin_id = os.getenv('admin_id')
# file save path
save_path = os.getenv('save_path')
# set upload file to google drive; 1/0 => True/False 
upload_file_set = int(os.getenv('upload_file_set'))

# google teamdrive id 如果使用OD，删除''内的内容即可。
drive_id = os.getenv('drive_id')
# rclone drive name
drive_name = os.getenv('drive_name')
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

# ***********************************************************************************#

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.WARNING)
logger = logging.getLogger(__name__)
queue = asyncio.Queue()


# 文件夹/文件名称处理
def validate_title(title):
    # r_str = r"[\/\\\:\*\?\"\<\>\|\n]"  # '/ \ : * ? " < > |'
    r_str = r'[^\:\-\w\u4e00\u9F5A\.]'
    # 替换为下划线
    new_title = re.sub(r_str, "_", title) 

    p = re.compile(r'[_]{1,}')
    # 连续多个下划线合并为一个
    new_title = re.sub(p,'_', new_title)

    p = re.compile(r'[\.]{1,}')
    # 连续多个点合并为一个
    new_title = re.sub(p,'.', new_title)
    return new_title
def get_file_name(message):
    file_name = 0
    if message.document:
        try:
            if type(message.media) == MessageMediaWebPage:
                return file_name
            if message.media.document.mime_type == "image/webp":
                return file_name
            if message.media.document.mime_type == "application/x-tgsticker":
                return file_name
            for i in message.document.attributes:
                try:
                    file_name = i.file_name
                except:
                    continue
            if file_name == '':
                file_name = f'{message.id}-{caption}.{message.document.mime_type.split("/")[-1]}'
            else:
                # 如果文件名中已经包含了标题，则过滤标题
                if get_equal_rate(caption, file_name) > 0.6:
                    caption = ""
                file_name = f'{message.id}-{caption}{file_name}'
        except:
            file_name = 0
    elif message.photo:
        file_name = f'{message.id}-{caption}{message.photo.id}.jpg'
    else:
        return file_name
    
    # ************
    if message.document:
        try:
            if type(message.media) == MessageMediaWebPage:
                return file_name
            if message.media.document.mime_type == "image/webp":
                file_name = f'{message.media.document.id}.webp'
            if message.media.document.mime_type == "application/x-tgsticker":
                file_name = f'{message.media.document.id}.tgs'
            for i in message.document.attributes:
                try:
                    file_name = i.file_name
                except:
                    continue
            if file_name == '':
                file_name = f'{message.id}-{caption}.{message.document.mime_type.split("/")[-1]}'
            else:
                # 如果文件名中已经包含了标题，则过滤标题
                if get_equal_rate(caption, file_name) > 0.6:
                    caption = ""
                file_name = f'{message.id}-{caption}{file_name}'
        except:
            print(message.media)
    elif message.photo:
        file_name = f'{message.id}-{caption}{message.photo.id}.jpg'
    else:
        return file_name
    return file_name

# 获取相册标题
async def get_group_caption(message):
    group_caption = ""
    entity = await client.get_entity(message.to_id)
    async for msg in client.iter_messages(entity=entity, reverse=True, offset_id=message.id - 9, limit=10):
        if msg.grouped_id == message.grouped_id:
            if msg.text != "":
                group_caption = msg.text
                return group_caption
    return group_caption


# 获取本地时间
def get_local_time():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


# 判断相似率
def get_equal_rate(str1, str2):
    return difflib.SequenceMatcher(None, str1, str2).quick_ratio()


# 返回文件大小
def bytes_to_string(byte_count):
    suffix_index = 0
    while byte_count >= 1024:
        byte_count /= 1024
        suffix_index += 1

    return '{:.2f}{}'.format(
        byte_count, [' bytes', 'KB', 'MB', 'GB', 'TB'][suffix_index]
    )


async def worker(name):
    while True:
        queue_item = await queue.get()
        message = queue_item[0]
        chat_title = queue_item[1]
        entity = queue_item[2]
        file_name = queue_item[3]
        for filter_file in filter_file_name:
            if file_name.endswith(filter_file):
                return
        dirname = validate_title(f'{chat_title}_{entity.id}_')
        datetime_dir_name = message.date.strftime("%Y_%m")
        file_save_path = os.path.join(save_path, dirname, datetime_dir_name)
        if not os.path.exists(file_save_path):
            os.makedirs(file_save_path)
        # 判断文件是否在本地存在
        if file_name in os.listdir(file_save_path):
            os.remove(os.path.join(file_save_path, file_name))
        print(f"{get_local_time()} 开始下载： {chat_title}-{file_name}")

        try:
            loop = asyncio.get_event_loop()
            task = loop.create_task(client.download_media(
                message, os.path.join(file_save_path, file_name)))
            await asyncio.wait_for(task, timeout=3600)
            if upload_file_set:
                proc = await asyncio.create_subprocess_exec('fclone',
                                                            'move',
                                                            os.path.join(
                                                                file_save_path, file_name),
                                                            f"{drive_name}:{{{drive_id}}}/{dirname}/{datetime_dir_name}",
                                                            '--ignore-existing',
                                                            stdout=asyncio.subprocess.DEVNULL)
                await proc.wait()
                if proc.returncode == 0:
                    print(f"{get_local_time()} - {file_name} 下载并上传完成")
        except (errors.rpc_errors_re.FileReferenceExpiredError, asyncio.TimeoutError):
            logging.warning(f'{get_local_time()} - {file_name} 出现异常，重新尝试下载！')
            async for new_message in client.iter_messages(entity=entity, offset_id=message.id - 1, reverse=True,
                                                          limit=1):
                await queue.put((new_message, chat_title, entity, file_name))
        except Exception as e:
            print(f"{get_local_time()} - {file_name} {e.__class__} {e}")
            await bot.send_message(admin_id, f'{e.__class__}!\n\n{e}\n\n{file_name}')
        finally:
            queue.task_done()
            # 无论是否上传成功都删除文件。
            if upload_file_set:
                try:
                    os.remove(os.path.join(file_save_path, file_name))
                except:
                    pass


@events.register(events.NewMessage(pattern='/start', from_users=admin_id))
async def handler(update):
    text = update.message.text.split(' ')
    msg = '参数错误，请按照参考格式输入:\n\n' \
          '1.普通群组\n' \
          '<i>/start https://t.me/fkdhlg 0 </i>\n\n' \
          '2.私密群组(频道) 链接为随便复制一条群组消息链接\n' \
          '<i>/start https://t.me/12000000/1 0 </i>\n\n' \
          'Tips:如果不输入offset_id，默认从第一条开始下载'
    if len(text) == 1:
        await bot.send_message(admin_id, msg, parse_mode='HTML')
        return
    elif len(text) == 2:
        chat_id = text[1]
        offset_id = 0
        try:
            entity = await client.get_entity(chat_id)
            chat_title = entity.title
            await update.reply(f'开始从 {chat_title} 的第 {0} 条消息下载')
        except ValueError:
            channel_id = text[1].split('/')[4]
            entity = await client.get_entity(PeerChannel(int(channel_id)))
            chat_title = entity.title
            await update.reply(f'开始从 {chat_title} 的第 {0} 条消息下载')
        except Exception as e:
            await update.reply('chat输入错误，请输入频道或群组的链接\n\n'
                               f'错误类型：{e.__class__}'
                               f'异常消息：{e}')
            return
    elif len(text) == 3:
        chat_id = text[1]
        offset_id = int(text[2])
        try:
            entity = await client.get_entity(chat_id)
            chat_title = entity.title
            await update.reply(f'开始从 {chat_title} 的第 {offset_id} 条消息下载')
        except ValueError:
            channel_id = text[1].split('/')[4]
            entity = await client.get_entity(PeerChannel(int(channel_id)))
            chat_title = entity.title
            await update.reply(f'开始从 {chat_title} 的第 {offset_id} 条消息下载')
        except Exception as e:
            await update.reply('chat输入错误，请输入频道或群组的链接\n\n'
                               f'错误类型：{type(e).__class__}'
                               f'异常消息：{e}')
            return
    else:
        await bot.send_message(admin_id, msg, parse_mode='HTML')
        return
    if chat_title:
        print(f'{get_local_time()} - 开始下载：{chat_title}({entity.id}) - {offset_id}')
        last_msg_id = 0
        async for message in client.iter_messages(entity, offset_id=offset_id, reverse=True, limit=None):
            if message.media:
                # 如果是一组媒体
                caption = await get_group_caption(message) if (
                        message.grouped_id and message.text == "") else message.text
                # 过滤文件名称中的广告等词语
                if len(filter_list) and caption != "":
                    for filter_keyword in filter_list:
                        caption = caption.replace(filter_keyword, "")
                # 如果文件文件名不是空字符串，则进行过滤和截取，避免文件名过长导致的错误
                caption = "" if caption == "" else f'{validate_title(caption)} - '[
                                                   :50]
                file_name = ''
                # 如果是文件
                # *******************************************************************
                if message.document:
                    if type(message.media) == MessageMediaWebPage:
                        continue
                    if message.media.document.mime_type == "image/webp":
                        continue
                    if message.media.document.mime_type == "application/x-tgsticker":
                        continue
                    for i in message.document.attributes:
                        try:
                            file_name = i.file_name
                        except:
                            continue
                    if file_name == '':
                        file_name = f'{message.id}-{caption}.{message.document.mime_type.split("/")[-1]}'
                    else:
                        # 如果文件名中已经包含了标题，则过滤标题
                        if get_equal_rate(caption, file_name) > 0.6:
                            caption = ""
                        file_name = f'{message.id}-{caption}{file_name}'
                elif message.photo:
                    file_name = f'{message.id}-{caption}{message.photo.id}.jpg'
                else:
                    continue
                # *******************************************************************
                await queue.put((message, chat_title, entity, file_name))
                last_msg_id = message.id
        await bot.send_message(admin_id, f'{chat_title} all message added to task queue, last message is：{last_msg_id}')


@events.register(events.NewMessage())
async def all_chat_download(update):
    message = update.message
    if message.media:
        chat_id = update.message.to_id
        entity = await client.get_entity(chat_id)
        if entity.id in blacklist:
            return
        chat_title = entity.title
        # 如果是一组媒体
        caption = await get_group_caption(message) if (
                message.grouped_id and message.text == "") else message.text
        if caption != "":
            for fw in filter_list:
                caption = caption.replace(fw, '')
        # 如果文件文件名不是空字符串，则进行过滤和截取，避免文件名过长导致的错误
        caption = "" if caption == "" else f'{validate_title(caption)}-'[:50]
        file_name = ''
        # 如果是文件
        # *******************************************************************
        if message.document:
            try:
                if type(message.media) == MessageMediaWebPage:
                    return
                if message.media.document.mime_type == "image/webp":
                    file_name = f'{message.media.document.id}.webp'
                if message.media.document.mime_type == "application/x-tgsticker":
                    file_name = f'{message.media.document.id}.tgs'
                for i in message.document.attributes:
                    try:
                        file_name = i.file_name
                    except:
                        continue
                if file_name == '':
                    file_name = f'{message.id}-{caption}.{message.document.mime_type.split("/")[-1]}'
                else:
                    # 如果文件名中已经包含了标题，则过滤标题
                    if get_equal_rate(caption, file_name) > 0.6:
                        caption = ""
                    file_name = f'{message.id}-{caption}{file_name}'
            except:
                print(message.media)
        elif message.photo:
            file_name = f'{message.id}-{caption}{message.photo.id}.jpg'
        else:
            return
        # *******************************************************************
        # 过滤文件名称中的广告等词语
        for filter_keyword in filter_list:
            file_name = file_name.replace(filter_keyword, "")
        print(chat_title, file_name)
        await queue.put((message, chat_title, entity, file_name))


if __name__ == '__main__':
    print("proxy", proxy)

    bot = TelegramClient('telegram_channel_downloader_bot',
                         api_id, api_hash, proxy=proxy).start(bot_token=str(bot_token))
    bot.add_event_handler(handler)

    client = TelegramClient(
        'telegram_channel_downloader', api_id, api_hash, proxy=proxy).start()
    if download_all_chat:
        client.add_event_handler(all_chat_download)

    tasks = []
    try:
        for i in range(max_num):
            loop = asyncio.get_event_loop()
            task = loop.create_task(worker(f'worker-{i}'))
            tasks.append(task)
        print('Successfully started (Press Ctrl+C to stop)')
        client.run_until_disconnected()
    finally:
        for task in tasks:
            task.cancel()
        client.disconnect()
        print('Stopped!')


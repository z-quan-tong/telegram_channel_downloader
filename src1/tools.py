import difflib
import re
import time
import logging

from telethon.tl.types import MessageMediaWebPage, DocumentAttributeVideo, MessageMediaDocument

import config


# 文件夹/文件名称处理
def validate_title(title):
    # r_str = r"[\/\\\:\*\?\"\<\>\|\n]"  # '/ \ : * ? " < > |'
    r_str = r'[^\-\w\u4e00\u9F5A]'
    # 替换为下划线
    new_title = re.sub(r_str, "_", title) 
    new_title = re.sub(r_str, "_", new_title) 

    p = re.compile(r'[_]{1,}')
    # 连续多个下划线合并为一个
    new_title = re.sub(p,'_', new_title)

    p = re.compile(r'\s{1,}')
    # 连续多个空白符
    new_title = re.sub(p,'_', new_title)

    p = re.compile(r'[\.]{1,}')
    # 连续多个点合并为一个
    new_title = re.sub(p,'.', new_title)

    return new_title


async def get_file_name(ctx, message):
    # 如果是一组媒体
    caption = await get_group_caption(ctx, message) if (
            message.grouped_id and message.text == "") else message.text
    # 过滤文件名称中的广告等词语
    if len(config.filter_list) and caption != "":
        for filter_keyword in config.filter_list:
            caption = caption.replace(filter_keyword, "")

    if len(validate_title(caption)) > 40:
        return ""
    # 如果文件文件名不是空字符串，则进行过滤和截取，避免文件名过长导致的错误
    caption = "" if caption == "" else f'{validate_title(caption)} - '[:50]
    # *******************************************************************
    # 如果是文件
    file_name = format_file_name(message, caption)
    return file_name


def format_file_name(message, caption):
    file_name = ''
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
async def get_group_caption(ctx, message):
    group_caption = ""
    entity = await ctx.client.get_entity(message.to_id)
    async for msg in ctx.client.iter_messages(entity=entity, reverse=True, offset_id=message.id - 9, limit=10):
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

# 选择合适的文件
def check_media(media):
    return 1
# def check_media(media):
#     flag = 1

#     if not isinstance(media, MessageMediaDocument):
#         return 0

#     size = media.document.size

#     if size < config.size_min or size > config.size_max:
#         flag = 0

#     for att in media.document.attributes:
#         if isinstance(att, DocumentAttributeVideo):
#             dur = att.duration
#             if dur > config.duration_max or dur < config.duration_min:
#                 flag = 0

#     if media.document.mime_type != 'video/mp4':
#         flag = 0

#     print("checkresult", flag)
#     return flag

# 从chat中获取历史消息
async def load_message_from_chat(ctx, entity, offset_id):
    chat_title = entity.title
    print(f'{get_local_time()} - 开始下载：{chat_title}({entity.id}) - {offset_id}')
    async for message in ctx.client.iter_messages(entity, offset_id=offset_id, reverse=True, limit=None):
        if message.media and check_media(message.media):
            file_name = await get_file_name(ctx, message)

            print(chat_title, file_name)
            if file_name == '':
                continue
            # *******************************************************************
            await ctx.queue.put((message, chat_title, entity, file_name))
    await ctx.bot.send_message(config.admin_id, f'{chat_title} all message added to task queue, last message is：{message.id}')

# 保存下载进度，避免重复下载
async def save_download_process():
    print(1)

# logger
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.WARNING)
logger = logging.getLogger(__name__)
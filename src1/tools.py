import difflib
import re
import time

from telethon.tl.types import MessageMediaWebPage


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

def get_file_name(message, caption):
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
async def get_group_caption(message, client):
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

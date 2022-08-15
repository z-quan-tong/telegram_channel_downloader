# !/usr/bin/env python3
import os
import asyncio
import asyncio.subprocess
import logging
from turtle import tilt

from telethon import TelegramClient, events, errors
from telethon.tl.types import PeerChannel, User

import config, tools


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.WARNING)
logger = logging.getLogger(__name__)
queue = asyncio.Queue()


async def worker(name):
    while True:
        queue_item = await queue.get()
        message = queue_item[0]
        chat_title = queue_item[1]
        entity = queue_item[2]
        file_name = queue_item[3]
        for filter_file in config.filter_file_name:
            if file_name.endswith(filter_file):
                return
        dirname =tools.validate_title(f'{chat_title}_{entity.id}_')
        datetime_dir_name = message.date.strftime("%Y_%m")
        file_save_path = os.path.join(config.save_path, dirname, datetime_dir_name)
        if not os.path.exists(file_save_path):
            os.makedirs(file_save_path)
        # 判断文件是否在本地存在
        if file_name in os.listdir(file_save_path):
            os.remove(os.path.join(file_save_path, file_name))
        print(f"{tools.get_local_time()} 开始下载： {chat_title}-{file_name}")

        try:
            loop = asyncio.get_event_loop()
            task = loop.create_task(client.download_media(
                message, os.path.join(file_save_path, file_name)))
            await asyncio.wait_for(task, timeout=3600)
        except (errors.rpc_errors_re.FileReferenceExpiredError, asyncio.TimeoutError):
            logging.warning(f'{tools.get_local_time()} - {file_name} 出现异常，重新尝试下载！')
            async for new_message in client.iter_messages(entity=entity, offset_id=message.id - 1, reverse=True,
                                                          limit=1):
                await queue.put((new_message, chat_title, entity, file_name))
        except Exception as e:
            print(f"{tools.get_local_time()} - {file_name} {e.__class__} {e}")
            await bot.send_message(config.admin_id, f'{e.__class__}!\n\n{e}\n\n{file_name}')
        finally:
            queue.task_done()



@events.register(events.NewMessage(pattern='/start', from_users=config.admin_id))
async def handler(update):
    text = update.message.text.split(' ')
    msg = '参数错误，请按照参考格式输入:\n\n' \
          '1.普通群组\n' \
          '<i>/start https://t.me/fkdhlg 0 </i>\n\n' \
          '2.私密群组(频道) 链接为随便复制一条群组消息链接\n' \
          '<i>/start https://t.me/12000000/1 0 </i>\n\n' \
          'Tips:如果不输入offset_id，默认从第一条开始下载'
    if len(text) == 1:
        await bot.send_message(config.admin_id, msg, parse_mode='HTML')
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
        await bot.send_message(config.admin_id, msg, parse_mode='HTML')
        return
    if chat_title:
        print(f'{tools.get_local_time()} - 开始下载：{chat_title}({entity.id}) - {offset_id}')
        last_msg_id = 0
        async for message in client.iter_messages(entity, offset_id=offset_id, reverse=True, limit=None):
            if message.media:
                # 如果是一组媒体
                caption = await tools.get_group_caption(message, client) if (
                        message.grouped_id and message.text == "") else message.text
                # 过滤文件名称中的广告等词语
                if len(config.filter_list) and caption != "":
                    for filter_keyword in config.filter_list:
                        caption = caption.replace(filter_keyword, "")
                # 如果文件文件名不是空字符串，则进行过滤和截取，避免文件名过长导致的错误
                caption = "" if caption == "" else f'{tools.validate_title(caption)} - '[:50]
                file_name = ''

                # *******************************************************************
                # 如果是文件
                file_name = tools.get_file_name(message, caption)

                print(chat_title, file_name)
                if file_name == '':
                    continue
                # *******************************************************************
                await queue.put((message, chat_title, entity, file_name))
                last_msg_id = message.id
        await bot.send_message(config.admin_id, f'{chat_title} all message added to task queue, last message is：{last_msg_id}')


@events.register(events.NewMessage())
async def all_chat_download(update):
    message = update.message
    if message.media:
        chat_id = update.message.to_id
        entity = await client.get_entity(chat_id)
        if entity.id in config.blacklist:
            return
        if type(entity) == User:
            # 发给单独某个人的; 不处理
            chat_title = entity.username
            return
        else:
            chat_title = entity.title

        
        # 如果是一组媒体
        caption = await tools.get_group_caption(message,client) if (
                message.grouped_id and message.text == "") else message.text
        if caption != "":
            for fw in config.filter_list:
                caption = caption.replace(fw, '')
        # 如果文件文件名不是空字符串，则进行过滤和截取，避免文件名过长导致的错误
        caption = "" if caption == "" else f'{tools.validate_title(caption)}-'[:50]

        # *******************************************************************
        # 如果是文件
        file_name = tools.get_file_name(message, caption)

        if file_name == '':
            return
        # *******************************************************************
        # 过滤文件名称中的广告等词语
        for filter_keyword in config.filter_list:
            file_name = file_name.replace(filter_keyword, "")
        print(chat_title, file_name)
        await queue.put((message, chat_title, entity, file_name))


if __name__ == '__main__':
    bot = TelegramClient('telegram_channel_downloader_bot',
                         config.api_id, config.api_hash, proxy=config.proxy).start(bot_token=str(config.bot_token))
    bot.add_event_handler(handler)

    client = TelegramClient(
        'telegram_channel_downloader', config.api_id, config.api_hash, proxy=config.proxy).start()
    if config.download_all_chat:
        client.add_event_handler(all_chat_download)

    tasks = []
    try:
        for i in range(config.max_num):
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


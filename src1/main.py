# !/usr/bin/env python3
import asyncio
import asyncio.subprocess
from pydoc import cli
from turtle import tilt

from telethon import TelegramClient, events
from telethon.tl.types import PeerChannel, User

import config, tools, worker

queue = asyncio.Queue()


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

    ctx = {
        client: client,
        bot: bot,
        queue: queue
    }

    try:
        for i in range(config.max_num):
            loop = asyncio.get_event_loop()
            task = loop.create_task(worker.worker(f'worker-{i}', ctx))
            tasks.append(task)
        print('Successfully started (Press Ctrl+C to stop)')
        client.run_until_disconnected()
    finally:
        for task in tasks:
            task.cancel()
        client.disconnect()
        print('Stopped!')


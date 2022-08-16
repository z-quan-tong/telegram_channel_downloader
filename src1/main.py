# !/usr/bin/env python3
import asyncio
import asyncio.subprocess
from pydoc import cli
from turtle import tilt

from telethon import TelegramClient, events
from telethon.tl.types import PeerChannel, User, DocumentAttributeVideo

import config, tools, worker

class Context:
    def __init__(self, client, bot, queue):
        self.client = client
        self.bot = bot
        self.queue = queue


queue = asyncio.Queue()

bot = TelegramClient(
    'tg_bot', config.api_id, config.api_hash, 
    proxy=config.proxy).start(bot_token=str(config.bot_token))

client = TelegramClient(
    'tg_client', config.api_id, config.api_hash, proxy=config.proxy).start()


ctx = Context(client, bot, queue)

# @events.register(events.NewMessage(pattern='/start', from_users=config.admin_id))
@events.register(events.NewMessage(pattern='/start'))
async def handler(update):
    text = update.message.text.split(' ')
    
    # 只处理自己发送的下载请求
    if config.admin_id != update.message.peer_id.user_id:
        return

    print("************************************************")
    
    msg = '参数错误，请按照参考格式输入:\n\n' \
          '1.普通群组\n' \
          '<i>/start https://t.me/fkdhlg 0 </i>\n\n' \
          '2.私密群组(频道) 链接为随便复制一条群组消息链接\n' \
          '<i>/start https://t.me/12000000/1 0 </i>\n\n' \
          'Tips:如果不输入offset_id，默认从第一条开始下载'

    if len(text) == 3:
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
        await tools.load_message_from_chat(ctx, entity, offset_id)


@events.register(events.NewMessage())
async def all_chat_download(update):

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

    message = update.message
    if message.media and tools.check_media(message.media):
        file_name = await tools.get_file_name(ctx, message)

        print(chat_title, file_name)
        if file_name == '':
            return

        await queue.put((message, chat_title, entity, file_name))


if __name__ == '__main__':


    bot.add_event_handler(handler)



    if config.download_all_chat:
        client.add_event_handler(all_chat_download)

    tasks = []


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


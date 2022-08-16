# !/usr/bin/env python3
import asyncio
import asyncio.subprocess
import datetime
from html import entities

from http import client
from pydoc import cli
from turtle import tilt

from telethon import TelegramClient, events
from telethon.tl.types import PeerChannel, User, MessageMediaDocument, DocumentAttributeVideo
from telethon.tl.functions.messages import GetHistoryRequest

import config, tools, worker

queue = asyncio.Queue()

api_id = config.api_id
api_hash = config.api_hash

client = TelegramClient('tg_client',config.api_id, config.api_hash, proxy=config.proxy).start()



async def get_entity_data(entity_id, limit):
    entity = await client.get_entity(entity_id)
    today = datetime.datetime.today()
    # y = today - datetime.timedelta(days=1)
    # offset_date=None,
    posts = await client(GetHistoryRequest(
                   peer=entity,
                   limit=limit,
                   offset_date=None,
                   offset_id=0,
                   max_id=0,
                   min_id=0,
                   add_offset=0,
                   hash=0))

    return posts.messages


async def main():
    # Getting information about yourself
    me = await client.get_me()
    print(me.username)

    # You can print all the dialogs/conversations that you are part of:
    # async for dialog in client.iter_dialogs():
    #     print(dialog.name, 'has ID', dialog)

    # You can send messages to yourself...
    # await client.send_message('me', 'Hello, myself!')
    # ...to some chat ID
    # await client.send_message(-100123456, 'Hello, group!')
    # ************************************************

    entity = await client.get_entity('https://t.me/suzhilangqun')

    print(entity.stringify())

    # ************************************************
    # messages = await get_entity_data('https://t.me/suzhilangqun', 20)
    # for message in messages:
    #     # print(message.id, message.stringify())
    #     print("id", message.id)

    #     print("message", message.message) # len

    #     media = message.media
    #     if media and isinstance(media, MessageMediaDocument):
    #         print("size", media.document.size) # 100 < size/(1024 * 1024) < 500
    #         print("mime_type", media.document.mime_type) # video/mp4
            # for att in media.document.attributes:
            #     if isinstance(att, DocumentAttributeVideo):
            #         print("duration", att.duration) # 300 < duration < 1800
    # ************************************************

    # You can print the message history of any chat:
    # async for message in client.iter_messages('me'):
    #     print(message.id, message.text)

        # You can download media from messages, too!
        # The method will return the path where the file was saved.
        # if message.photo:
        #     path = await message.download_media()
        #     print('File saved to', path)  # printed after download is done
    # --------------

with client:
    client.loop.run_until_complete(main())


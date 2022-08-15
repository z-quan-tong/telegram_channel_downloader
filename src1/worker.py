import os
import asyncio
from telethon import errors

import config, tools


async def worker(name, ctx):
    while True:
        print("before 开始下载")
        queue_item = await ctx.queue.get()
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
            task = loop.create_task(ctx.client.download_media(
                message, os.path.join(file_save_path, file_name)))
            await asyncio.wait_for(task, timeout=3600)
        except (errors.rpc_errors_re.FileReferenceExpiredError, asyncio.TimeoutError):
            tools.logging.warning(f'{tools.get_local_time()} - {file_name} 出现异常，重新尝试下载！')
            async for new_message in ctx.client.iter_messages(entity=entity, offset_id=message.id - 1, reverse=True,
                                                          limit=1):
                await ctx.queue.put((new_message, chat_title, entity, file_name))
        except Exception as e:
            print(f"{tools.get_local_time()} - {file_name} {e.__class__} {e}")
            await ctx.bot.send_message(config.admin_id, f'{e.__class__}!\n\n{e}\n\n{file_name}')
        finally:
            ctx.queue.task_done()


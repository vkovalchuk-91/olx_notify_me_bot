import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, List

import injector
import instaloader
from aiogram import html
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from app.insta.db_sqlite_insta_impl import InstaSQLiteDatabase
from app.injector_config import InstaDBModule

# Loading variables from the .env file
load_dotenv()
INSTA_LOGIN = os.getenv("INSTA_LOGIN")
INSTA_PASSWORD = os.getenv("INSTA_PASSWORD")

db = injector.Injector([InstaDBModule]).get(InstaSQLiteDatabase)
L = instaloader.Instaloader()
L.login(INSTA_LOGIN, INSTA_PASSWORD)


async def check_new_insta_content_and_measure_spent_time():
    parsing_start_time = datetime.now()

    await check_new_insta_content()

    parsing_time = datetime.now() - parsing_start_time
    minutes = parsing_time.total_seconds() // 60
    seconds = parsing_time.total_seconds() % 60
    print(f"Час Перевірки інстаграму: {int(minutes)} хвилин {int(seconds)} секунд")


async def check_new_insta_content():
    story_content_type_id, post_content_type_id, photo_media_type_id, video_media_type_id = await get_type_ids()
    print(photo_media_type_id)
    usernames = ['yulia.or.julia','_a_a_p_95']

    for username in usernames:
        if not await db.is_user_registered(username):
            user_id = await db.register_new_user(username)
        else:
            user_id = await db.get_user_id_by_username(username)

        content = await get_parsed_content(
            username,
            user_id,
            story_content_type_id,
            post_content_type_id,
            photo_media_type_id,
            video_media_type_id
        )
        # for content_item in content:
        #     if not await db.is_content_item_exist(
        #         content_item['content_type_id'],
        #         content_item['media_type_id'],
        #         content_item['user_id'],
        #         content_item['date_local'],
        #     ):
        #         await db.save_new_content(
        #             content_item['content_type_id'],
        #             content_item['media_type_id'],
        #             content_item['user_id'],
        #             content_item['date_local'],
        #             content_item['url']
        #         )
        #         print(f"{html.bold("Додано новий інстаграм контент!")}\n"
        #                    f"{html.bold("Хто додав: ")}{content_item['username']}\n"
        #                    f"{html.bold("Коли додав: ")}{content_item['date_local']}\n"
        #                    f"{html.bold("URL: ")}{content_item['url']}")
        #         print()


async def get_parsed_content(
        username: str,
        user_id: int,
        story_content_type_id: int,
        post_content_type_id: int,
        photo_media_type_id: int,
        video_media_type_id: int
) -> List[Dict]:
    parsed_content = []

    # profile = instaloader.Profile.from_username(L.context, username)

    # for post in profile.get_posts():
    #     for node in post.get_sidecar_nodes():
    #         if node.is_video:
    #             content_item = {
    #                 'content_type_id': post_content_type_id,
    #                 'media_type_id': video_media_type_id,
    #                 'username': username,
    #                 'user_id': user_id,
    #                 'date_local': post.date_local,
    #                 'url': node.video_url
    #             }
    #             parsed_content.append(content_item)
    #         else:
    #             content_item = {
    #                 'content_type_id': post_content_type_id,
    #                 'media_type_id': photo_media_type_id,
    #                 'username': username,
    #                 'user_id': user_id,
    #                 'date_local': post.date_local,
    #                 'url': node.display_url
    #             }
    #             parsed_content.append(content_item)

    # for story in L.get_stories(userids=[profile.userid]):
    #     for item in story.get_items():
    #         if item.is_video:
    #             content_item = {
    #                 'content_type_id': story_content_type_id,
    #                 'media_type_id': video_media_type_id,
    #                 'username': username,
    #                 'user_id': user_id,
    #                 'date_local': item.date_local,
    #                 'url': item.video_url
    #             }
    #             parsed_content.append(content_item)
    #         else:
    #             content_item = {
    #                 'content_type_id': story_content_type_id,
    #                 'media_type_id': photo_media_type_id,
    #                 'username': username,
    #                 'user_id': user_id,
    #                 'date_local': item.date_local,
    #                 'url': item.url
    #             }
    #             parsed_content.append(content_item)
    # return parsed_content


async def get_type_ids():
    story_content_type_id = await db.get_content_type_id("Story")
    post_content_type_id = await db.get_content_type_id("Post")
    photo_media_type_id = await db.get_media_type_id("Photo")
    video_media_type_id = await db.get_media_type_id("Video")
    return story_content_type_id, post_content_type_id, photo_media_type_id, video_media_type_id


async def send_message_to_user_with_new_found_content_item(bot, content_item, insta_receiver_telegram_id):
    logging.info(f"New instagram content item sent to '{insta_receiver_telegram_id}': {content_item['url']}")
    await bot.send_message(insta_receiver_telegram_id,
                           f"{html.bold("Додано новий інстаграм контент!")}\n"
                           f"{html.bold("Хто додав: ")}{content_item['username']}\n"
                           f"{html.bold("Коли додав: ")}{content_item['date_local']}\n"
                           f"{html.bold("URL: ")}{content_item['url']}",
                           parse_mode=ParseMode.HTML)


async def test():
    await check_new_insta_content_and_measure_spent_time()

if __name__ == '__main__':
    asyncio.run(test())
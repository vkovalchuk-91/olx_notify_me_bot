from typing import Dict, List

from scrapers.insta_parser_anonyig_com import extract_filename_from_url
from scrapers.insta_parser_anonyig_com import get_parsed_content as get_anonyig_content


async def get_parsed_content(
    username: str,
    user_id: int,
    story_content_type_id: int,
    post_content_type_id: int,
    photo_media_type_id: int,
    video_media_type_id: int,
) -> List[Dict]:
    parsed_content = await get_anonyig_content(username, user_id)
    for item in parsed_content:
        item['content_type_id'] = story_content_type_id if item['content_type'] == 'Story' else post_content_type_id
        item['media_type_id'] = video_media_type_id if item['media_type'] == 'Video' else photo_media_type_id
    return parsed_content

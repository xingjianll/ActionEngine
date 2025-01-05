from __future__ import annotations

import os
import random
from typing import Annotated

from bilibili_api import Credential, search, comment, video
from bilibili_api.comment import CommentResourceType, OrderType
from cohere import Client
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict

from action_engine.action import Action
from action_engine.engine import Engine
from action_engine.param_functions import Tag, Deps
from inspect import cleandoc as I

from action_engine.types import Id
from demo.memory import Fifo

load_dotenv()
SESSDATA = os.getenv("SESSDATA")
BILI_JCT = os.getenv("BILI_JCT")
BUVID3 = os.getenv("BUVID3")


class Base(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    credential: Credential
    co: Client
    prompt: str = "You are browsing Bilibili, A Chinese video sharing platform."
    memory: Fifo


def action_selector(actions: list[Action]) -> Action:
    print([action.name for action in actions])
    rand = random.randint(0, len(actions) - 1)
    return actions[rand]


engine = Engine(
    base_state_type=Base,
    base_action_selector=action_selector,
)


@engine.action()
async def browse_videos(
    base: Base,
) -> tuple[
    Annotated[str | Id, Tag("video_id", cascade=True)],
    Annotated[str | Id, Tag("video_title")],
    Annotated[str | Id, Tag("video_description")]
]:
    prompt = I(
        f"""
        {base.prompt}
        Here are your past actions {base.memory.prompt()} Generate a keyword phrase for videos you want to watch.
        Be creative and avoid repeating. Respond with a maximum of three words in Chinese.
        """
    )
    response = base.co.chat(temperature=1, message=prompt).text
    res = await search.search_by_type(
        response,
        search_type=search.SearchObjectType.VIDEO,
        order_type=search.OrderUser.FANS,
        order_sort=0,
    )
    base.memory.add(f"searched for {response} while browsing video")

    top_10 = []
    for i in range(10):
        video = res["result"][i]
        top_10.append(f"{i + 1} {video['title']}, {video['play']} plays")
    top_10_str = "\n".join(top_10)

    prompt = I(
        f"""
        {base.prompt}
        Here are your past actions {base.memory.prompt()}
        Here are 10 videos: {top_10_str}, return the number that represents the video 
        you want to see the most. If you don't want to watch any of these videos, respond with -1.
        """
    )
    response = base.co.chat(temperature=1, message=prompt).text
    if response == "-1":
        return Id(), Id(), Id()
    video = res["result"][int(response)]
    base.memory.add(f"finds {video['title']} while browsing videos")
    return video["bvid"], video["title"], video["description"]


@engine.action()
async def read_comments(
    base:              Base,
    video_id:          Annotated[str, Deps(["comment_id"])],
    video_title:       str,
    video_description: str
) -> Annotated[str, Tag("comment_id")]:
    c = await comment.get_comments(
            oid=video.Video(bvid=video_id).get_aid(),
            type_=CommentResourceType.VIDEO,
            order=OrderType.LIKE,
            credential=base.credential,
        )
    top_10 = []
    for i in range(min(5, c["page"]["count"])):
        cmt = c["replies"][i]
        top_10.append(f"{i + 1} {cmt['member']['uname']}: {cmt['content']['message']}")
    top_10_str = "\n".join(top_10)

    prompt = I(
        f"""
        {base.prompt}
        You are browsing a video called {video_title}, the description is {video_description}. 
        Here are 10 comments: {top_10_str}, return the number that represents the comment you want to reply most. 
        Give a number and nothing else.
        """
    )
    response = base.co.chat(temperature=1, message=prompt).text
    cmt = c["replies"][int(response)]
    base.memory.add(
        f"finds comment: {cmt['content']['message']} while browsing {video_title}"
    )

    print("read_comments")
    return "comment_id1"


@engine.action()
async def post_comment(base: Base, video_id: str) -> None:
    print("post_comment")
    return

@engine.action()
async def reply_to_comment(base: Base, comment_id: str) -> None:
    print("post_comment")
    return

if __name__ == "__main__":
    ...

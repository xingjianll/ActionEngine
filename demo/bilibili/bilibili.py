from __future__ import annotations

import os
import random
import time
from typing import Annotated

import requests
from bilibili_api import Credential, search, comment, dynamic
from bilibili_api.comment import CommentResourceType, OrderType, Comment
from bilibili_api.dynamic import BuildDynamic
from bilibili_api.video import Video
from cohere import Client
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict

from action_engine.action import Action
from action_engine.engine import Engine
from action_engine.param_functions import Tag, Deps
from inspect import cleandoc as I

from demo.bilibili.memory import Fifo

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


class TargetComment(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    cmt: Comment
    user_name: str
    content: str

def action_selector(actions: list[Action]) -> Action:
    print([action.name for action in actions])
    rand = random.randint(0, len(actions) - 1)
    time.sleep(5)
    return actions[rand]


engine = Engine(
    base_state_type=Base,
    base_action_selector=action_selector,
)


@engine.action()
async def browse_videos(
    base: Base,
) -> Annotated[Video | None, Tag("vid", cascade=True)]:
    print("browse videos")
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
        vid = res["result"][i]
        top_10.append(f"{i + 1} {vid['title']}, {vid['play']} plays")
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
        return None
    vid = res["result"][int(response)]
    base.memory.add(f"finds {(await Video(bvid=vid['bvid']).get_info()).get('title')} while browsing videos")
    return Video(bvid=vid['bvid'], credential=base.credential)


@engine.action()
async def read_comments(
    base:  Base,
    vid: Annotated[Video, Deps(["cmt"])],
) -> Annotated[TargetComment, Tag("cmt")]:
    print("read_comments")

    c = await comment.get_comments(
        oid=vid.get_aid(),
        type_=CommentResourceType.VIDEO,
        order=OrderType.LIKE,
        credential=base.credential,
    )
    top_10 = []
    for i in range(min(c["page"]["count"], 10)):
        cmt = c["replies"][i]
        top_10.append(f"{i + 1} {cmt['member']['uname']}: {cmt['content']['message']}")
    top_10_str = "\n".join(top_10)

    prompt = I(
        f"""
        {base.prompt}
        You are browsing a video {(await vid.get_info()).get('title')}. 
        Here are 10 comments: {top_10_str}, return the number that represents the comment you want to reply most. 
        Give a number and nothing else.
        """
    )
    response = base.co.chat(temperature=1, message=prompt).text
    cmt = c["replies"][int(response)]
    base.memory.add(
        f"finds comment: {cmt['content']['message']} while browsing {(await vid.get_info()).get('title')}"
    )

    return TargetComment(
        cmt=Comment(
            oid=vid.get_aid(),
            type_=CommentResourceType.VIDEO,
            rpid=cmt["rpid"],
            credential=base.credential
        ),
        user_name=cmt["member"]["uname"],
        content=cmt["content"]["message"]
    )


@engine.action()
async def post_comment(base: Base, vid: Video) -> None:
    print("post_comment")

    cid = await vid.get_cid(0)
    subtitles = (await vid.get_subtitle(cid))["subtitles"]
    concatenated_subtitle = ''
    if len(subtitles) > 0:
        subtitle_url = subtitles[0].get("subtitle_url")
        if subtitle_url is not None and subtitle_url != "":
            res = requests.get(url="https://" + subtitle_url[2:]).json()
            concatenated_subtitle = "".join(item["content"] for item in res["body"])

    prompt = I(
        f"""
        {base.prompt}
        You are browsing a video {(await vid.get_info()).get('title')}.
        Here is the video's tags {await vid.get_tags()}.
        Here is the video's summary {(await vid.get_ai_conclusion(page_index=0))}.
        Here is the video's script {concatenated_subtitle}.
        Return your comment to this video in Chinese.
        """
    )

    response = base.co.chat(temperature=1, message=prompt).text
    footnote = (
        f"\n I am a bot, and this action was performed automatically. Please contact {os.environ.get('name', '')}"
        f" if you have any questions or concerns."
    )
    await comment.send_comment(
        text=f"{response} {footnote}",
        oid=vid.get_aid(),
        type_=CommentResourceType.VIDEO,
        credential=base.credential,
    )
    base.memory.add(f"commented {response} to {(await vid.get_info()).get('title')}")
    d = BuildDynamic.empty().add_text(
        f"reply to https://www.bilibili.com/video/{vid.get_bvid()} \n"
        + f"{response} {footnote}"
    )
    await dynamic.send_dynamic(d, credential=base.credential)

@engine.action()
async def reply_to_comment(base: Base, cmt: TargetComment, vid: Video) -> None:
    print("reply_to_comment")
    prompt = I(
        f"""
        {base.prompt}
        You are replying to a comment by {cmt.user_name}.
        Here is the comment: {cmt.content}.
        Return your reply to this comment in Chinese.
        """
    )
    response = base.co.chat(temperature=1, message=prompt).text
    footnote = (
        f"\n I am a bot, and this action was performed automatically. Please contact {os.environ.get('name', '')}"
        f" if you have any questions or concerns."
    )
    await comment.send_comment(
        text=f"{response} {footnote}",
        oid=cmt.cmt.get_oid(),
        type_=cmt.cmt.get_type(),
        credential=base.credential,
        root=cmt.cmt.get_rpid(),
    )
    base.memory.add(f"replied {response} to {cmt.content} by {cmt.user_name}")

    d = BuildDynamic.empty().add_text(
        f"reply to {cmt.user_name} in https://www.bilibili.com/video/{vid.get_bvid()} \n"
        + f"{response} {footnote}"
    )
    await dynamic.send_dynamic(d, credential=base.credential)

if __name__ == "__main__":
    memory = Fifo()
    co = Client(os.environ.get("COHERE_API_KEY"))
    credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT, buvid3=BUVID3)
    base = Base(credential=credential, co=co, memory=memory)

    print(engine.display())
    engine.run(base)

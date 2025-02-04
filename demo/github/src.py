import os
from typing import Annotated

from cohere import Client
from dotenv import load_dotenv
from github import Github, Auth
from github.Repository import Repository
from pydantic import BaseModel, ConfigDict

from action_engine.action import Action
from action_engine.engine import Engine
from action_engine.param_functions import Tag
from action_engine.utils import indexed_str

load_dotenv()

class Base(BaseModel):
    g: Github
    model_config = ConfigDict(arbitrary_types_allowed=True)
    history: list[str]
    llm: Client
    summary: str = ""

def action_selector(base: Base, actions: list[Action]) -> Action:
    target = "Goal: browse github repositories, for each repo, get three issues. When you are done, generate a summary. \n"
    postfix = "Pick your next action based on the past actions, give the index and nothing else.\n"
    query = target + indexed_str("Past actions", base.history) + indexed_str("Possible actions", actions) + postfix
    response = base.llm.chat(message=query).text
    return actions[int(response)]

engine = Engine(
    base_state_type=Base,
    base_action_selector=action_selector,
)

@engine.action()
def browse_repo(base: Base) -> Annotated[Repository, Tag("repo")]:
    message = indexed_str("Your Past Actions", base.history) + "Give me a keyword about ai and nothing else:"
    query = base.llm.chat(message=message).text
    repo = base.g.search_repositories(query=query).get_page(0)[0]
    base.history.append(f"Browsing repository {repo.name}: {repo.description}")
    return repo

@engine.action()
def get_issue(base: Base, repo: Repository) -> None:
    issues = repo.get_issues().get_page(0)[:10]
    history = indexed_str("Your Past Actions", base.history)
    postfix = "Your response should be a number and nothing else."
    response = base.llm.chat(message=history + "Now, pick a new issue:" + indexed_str("Issues", issues) + postfix).text
    base.history.append(f"Retrieved issue: {issues[int(response)].title}")

@engine.action(terminal=True)
def summarize(base: Base) -> None:
    base.summary = base.llm.chat(message="Generate a summary of the repos and issues:" + "\n".join(base.history)).text

if __name__ == "__main__":
    base = Base(
        history=[],
        llm=Client(os.environ.get("COHERE_API_KEY")),
        g=Github(auth=Auth.Token(os.environ["GITHUB_TOKEN"]))
    )
    engine.run(base)
    print(base.summary)

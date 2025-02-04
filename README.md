<div align= "center">
    <h4>Light-weight, fully-typed tool call orchestration framework for agentic workflows.</h4>
</div>

> Docs: https://xingjianll.github.io/ActionEngine/ (Work in progress)

Install with pip:

```shell

  pip install action-engine

```

## Key Features
* **Easy to use** - Minimalistic interfaces inspired by FastAPI and Typer
* **Type Safety** - Designed to be fully compatible with type checkers such as mypy
* **Zero LLM wrapper** - Pick your favorite LLM package such as `openai` `liteLLM` `aisuite` and use it directly with ActionEngine
- **State Management**: Engine manages the global state, ensuring only the right variables are passed to the actions when calling
- **Tool Filtering**: Tools that are not compatible with the current state are automatically filtered out

## How Does Action Engine Work?

### Motivation
Agent frameworks we have today are designed to use APIs where the arguments can be inferred by a LLM using its in-weight knowledge:
```python
from duckduckgo_search import DDGS

results = DDGS().text( # Search using the DuckDuckGo API
    "python programming", # This can be inferred by an LLM! 
    max_results=5
)
```
However, they are less suitable with APIs where an LLM's in-weight knowledge is not enough:
```python
from pyyoutube import Client
client = Client(...)
client.channels.list( # Get youtube channel info
    channel_id="UC_x5XG1OV2P6uZZ5FSM9Ttw" # This cannot be inferred by an LLM!
)
```

Usually, the second type of APIs are a part of a larger system of APIs where the non-inferrable apis are dependent on some directly inferrable apis:
```python
from bilibili_api import search, comment
from bilibili_api.video import Video

vid = await search.search_by_type(
    "cute cate videos" # This can be inferred by an LLM!
)["result"][i]

comment.send_comment( 
    text=f"I like this video!",
    oid=Video(bvid=vid["bvid"]).get_aid() # This value depends on the previous API call!
)
```

ActionEngine is designed to handle such complex, interdependent APIs for agentic workflows. It does this by 1. automatically **filter out actions** that are not compatible with the current state 2. automatically **fills the input arguments** when the next action is chosen.    

Only two things are required to use Action Engine:
1. A selector that selects the agent's next action
2. A set of actions that the agent can perform


### Example: Github Issue Summary Bot
```python
import cohere
# other imports omitted for brevity

class Base(BaseModel):
    g: Github
    model_config = ConfigDict(arbitrary_types_allowed=True)
    history: list[str]
    llm: cohere.Client
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

```

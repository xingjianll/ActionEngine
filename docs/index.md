# ActionEngine Documentation

ActionEngine is a tool-call orchestration framework for agentic workflows. Specifically, it is designed for agents that interact with a set of complex, interdependent API endpoints.(1)
{ .annotate }

1.  Wrapper libraries for popular websites such as [PyGithub](https://github.com/PyGithub/PyGithub), [python-youtube](https://github.com/sns-sdks/python-youtube) etc. are examples of such sets of API endpoints.

## Key Features
* **Easy to use** - Minimalistic interfaces inspired by FastAPI and Typer
* **Type Safety** - Designed to be fully compatible with type checkers such as mypy
* **Zero LLM wrapper** - Pick your favorite LLM package such as `openai` `liteLLM` `aisuite` and use it directly with ActionEngine

## Installation

=== "uv"

    ```shell
    uv add action-engine
    ```

=== "pip"

    ```shell
    pip install action-engine
    ```

## Example: Github Summary Bot
    
```python

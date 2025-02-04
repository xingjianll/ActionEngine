from typing import Any


def indexed_str(name: str, items: list[Any]) -> str:
    return f"{name}: \n" + "\n".join([f"{i}: {str(action)}" for i, action in enumerate(items)]) + "\n"
from abc import ABC


class Displayable(ABC):
    def get_name(self) -> str:
        raise NotImplementedError

    def get_info(self) -> list[str]:
        raise NotImplementedError

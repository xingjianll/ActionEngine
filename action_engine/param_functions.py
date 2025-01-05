from pydantic import BaseModel


class TagMetaData(BaseModel):
    name: str
    cascade: bool


class DepsMetaData(BaseModel):
    deps: list[str]


def Tag(name: str, *, cascade: bool = False) -> TagMetaData:
    return TagMetaData(name=name, cascade=cascade)


def Deps(deps: list[str]) -> DepsMetaData:
    return DepsMetaData(deps=deps)

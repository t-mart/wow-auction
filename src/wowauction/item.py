from attrs import frozen


@frozen
class Item:
    id_: str
    name: str
    quality: int
    rank: None | int
    major: int
    minor: int
    patch: int
    build: int

# nft.py
import datetime as _dt
from typing import List, Dict


class NFT:
    def __init__(
        self,
        name: str,
        description: str,
        image: str,
        dna: str,
        edition: int,
        attributes: List[Dict],
    ):
        self.name = name
        self.description = description
        self.image = image
        self.dna = dna
        self.edition = edition
        self.date = int(_dt.datetime.now().timestamp() * 1000)
        self.attributes = attributes
        self.owner = None  # NFT 소유자 추가

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "image": self.image,
            "dna": self.dna,
            "edition": self.edition,
            "date": self.date,
            "attributes": self.attributes,
            "owner": self.owner,
        }

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            name=data["name"],
            description=data["description"],
            image=data["image"],
            dna=data["dna"],
            edition=data["edition"],
            attributes=data["attributes"],
        )

# models.py
from typing import List, Optional
from pydantic import BaseModel, Field
import datetime as _dt


class Attribute(BaseModel):
    trait_type: str
    value: str


class NFTModel(BaseModel):
    name: str
    description: str
    image: str
    dna: str
    edition: int
    date: int
    attributes: List[Attribute]
    compiler: str


class TransactionModel(BaseModel):
    sender: str
    receiver: str
    nft: Optional[NFTModel] = None
    price: float
    timestamp: Optional[str] = Field(default_factory=lambda: str(_dt.datetime.now()))


class BlockModel(BaseModel):
    index: int
    timestamp: str
    transactions: List[TransactionModel]
    proof: int
    previous_hash: str


class BlockchainModel(BaseModel):
    chain: List[BlockModel]
    length: int


class MineBlockResponse(BaseModel):
    message: str
    block: BlockModel


class NFTDetailModel(BaseModel):
    nft: NFTModel
    owner: str
    last_block_index: int


class NodeRegisterModel(BaseModel):
    node_address: str
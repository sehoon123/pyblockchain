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
    edition: Optional[int] = None  # Made optional
    date: int
    attributes: Optional[List[Attribute]] = None  # Made optional
    compiler: Optional[str] = None  # Made optional


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


class MineBlockRequestModel(BaseModel):
    miner_address: str


class NFTDetailModel(BaseModel):
    nft: NFTModel
    owner: str
    last_block_index: int


class NodeRegisterModel(BaseModel):
    node_address: str


class PostModel(BaseModel):
    id: int
    user_id: int
    item_name: Optional[str] = None
    expected_price: Optional[float] = None
    created_date: Optional[str] = None
    updated_date: Optional[str] = None
    dna: Optional[str] = None
    img_url: Optional[str] = None
    is_sold: Optional[bool] = None
    description: Optional[str] = None
    sold_price: Optional[float] = None

    class Config:
        orm_mode = True  # Allows compatibility with SQLAlchemy models


class NFTWithOwnerAndPriceModel(BaseModel):
    nft: NFTModel
    owner: Optional[str] = None
    price: Optional[float] = None
    post: Optional[PostModel] = None

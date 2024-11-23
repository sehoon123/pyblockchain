# main.py
import fastapi as _fastapi
from fastapi import HTTPException
from typing import List, Optional
from models import (
    NFTModel,
    NFTDetailModel,
    TransactionModel,
    BlockModel,
    BlockchainModel,
    MineBlockResponse,
)
from blockchain import Blockchain, Transaction, NFT

# Initialize the blockchain
blockchain = Blockchain()
app = _fastapi.FastAPI(title="NFT Blockchain API", version="1.0.0")

def get_current_owner(dna: str) -> Optional[str]:
    """
    Retrieve the current owner of the NFT based on its DNA.
    """
    owner = None
    for block in blockchain.chain:
        for tx in block["transactions"]:
            nft_data = tx.get("nft")
            if nft_data and nft_data.get("dna") == dna:
                owner = tx["receiver"]
    return owner

@app.post("/create_transaction", response_model=TransactionModel)
def create_transaction(transaction: TransactionModel):
    """
    Create a new NFT transaction and add it to the list of pending transactions.
    """
    try:
        # If the transaction involves an NFT, verify ownership
        if transaction.nft:
            current_owner = get_current_owner(transaction.nft.dna)
            if current_owner and current_owner != transaction.sender:
                raise ValueError(f"Sender {transaction.sender} is not the current owner of the NFT.")
            elif not current_owner and transaction.sender != "SYSTEM":
                raise ValueError("NFT does not exist. Only 'SYSTEM' can create NFTs.")

        # Convert TransactionModel to internal Transaction object
        nft = None
        if transaction.nft:
            nft = NFT(
                name=transaction.nft.name,
                description=transaction.nft.description,
                image=transaction.nft.image,
                dna=transaction.nft.dna,
                edition=transaction.nft.edition,
                date=transaction.nft.date,
                attributes=[attr.dict() for attr in transaction.nft.attributes],
                compiler=transaction.nft.compiler,
            )
        tx = Transaction(
            sender=transaction.sender,
            receiver=transaction.receiver,
            nft=nft,
            price=transaction.price,
            timestamp=transaction.timestamp,
        )
        index = blockchain.create_transaction(tx)
        return transaction
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@app.post("/mine_block", response_model=MineBlockResponse)
def mine_block(miner_address: str):
    """
    Mine a new block by adding all pending transactions to the blockchain.
    """
    if not blockchain.is_chain_valid():
        raise HTTPException(status_code=400, detail="Invalid blockchain")

    try:
        block = blockchain.mine_block(miner_address)
        # Convert block dict to BlockModel
        block_model = BlockModel(
            index=block["index"],
            timestamp=block["timestamp"],
            transactions=[
                TransactionModel(
                    sender=tx["sender"],
                    receiver=tx["receiver"],
                    nft=NFTModel(**tx["nft"]) if tx["nft"] else None,
                    price=tx["price"],
                    timestamp=tx["timestamp"],
                )
                for tx in block["transactions"]
            ],
            proof=block["proof"],
            previous_hash=block["previous_hash"],
        )
        return MineBlockResponse(message="Block mined successfully", block=block_model)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/blockchain", response_model=BlockchainModel)
def get_blockchain():
    """
    Retrieve the entire blockchain.
    """
    if not blockchain.is_chain_valid():
        raise HTTPException(status_code=400, detail="Invalid blockchain")

    chain_data = []
    for block in blockchain.chain:
        transactions = []
        for tx in block["transactions"]:
            if tx["nft"]:
                nft = NFTModel(**tx["nft"])
            else:
                nft = None
            transaction = TransactionModel(
                sender=tx["sender"],
                receiver=tx["receiver"],
                nft=nft,
                price=tx["price"],
                timestamp=tx["timestamp"],
            )
            transactions.append(transaction)
        block_model = BlockModel(
            index=block["index"],
            timestamp=block["timestamp"],
            transactions=transactions,
            proof=block["proof"],
            previous_hash=block["previous_hash"],
        )
        chain_data.append(block_model)
    return BlockchainModel(chain=chain_data, length=len(chain_data))


@app.get("/validate", response_model=bool)
def is_blockchain_valid():
    """
    Validate the integrity of the blockchain.
    """
    return blockchain.is_chain_valid()


@app.get("/previous_block", response_model=BlockModel)
def get_previous_block():
    """
    Get the most recent block in the blockchain.
    """
    if not blockchain.is_chain_valid():
        raise HTTPException(status_code=400, detail="Invalid blockchain")

    previous_block = blockchain.get_previous_block()
    transactions = []
    for tx in previous_block["transactions"]:
        if tx["nft"]:
            nft = NFTModel(**tx["nft"])
        else:
            nft = None
        transaction = TransactionModel(
            sender=tx["sender"],
            receiver=tx["receiver"],
            nft=nft,
            price=tx["price"],
            timestamp=tx["timestamp"],
        )
        transactions.append(transaction)

    block_model = BlockModel(
        index=previous_block["index"],
        timestamp=previous_block["timestamp"],
        transactions=transactions,
        proof=previous_block["proof"],
        previous_hash=previous_block["previous_hash"],
    )
    return block_model


@app.get("/nfts", response_model=List[NFTModel])
def get_all_nfts():
    """
    Retrieve all NFTs in the blockchain.
    """
    nfts = []
    for block in blockchain.chain:
        for tx in block["transactions"]:
            nft_data = tx.get("nft")
            if nft_data:
                nft = NFTModel(**nft_data)
                nfts.append(nft)
    return nfts


@app.get("/nft/{dna}", response_model=NFTDetailModel)
def get_nft_by_dna(dna: str):
    """
    Retrieve a specific NFT by its DNA along with the current owner.
    """
    nft_found = None
    owner = None

    # Iterate over the blockchain in chronological order
    for block in blockchain.chain:
        for tx in block["transactions"]:
            nft_data = tx.get("nft")
            if nft_data and nft_data.get("dna") == dna:
                nft_found = NFTModel(**nft_data)
                owner = tx["receiver"]  # The receiver is the current owner

    if nft_found and owner:
        return NFTDetailModel(nft=nft_found, owner=owner)

    raise HTTPException(status_code=404, detail="NFT not found")


@app.get("/transactions", response_model=List[TransactionModel])
def get_all_transactions():
    """
    Retrieve all transactions in the blockchain.
    """
    transactions = []
    for block in blockchain.chain:
        for tx in block["transactions"]:
            if tx["nft"]:
                nft = NFTModel(**tx["nft"])
            else:
                nft = None
            transaction = TransactionModel(
                sender=tx["sender"],
                receiver=tx["receiver"],
                nft=nft,
                price=tx["price"],
                timestamp=tx["timestamp"],
            )
            transactions.append(transaction)
    return transactions

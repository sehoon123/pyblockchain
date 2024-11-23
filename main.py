import boto3
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
from botocore.exceptions import NoCredentialsError
from fastapi.middleware.cors import CORSMiddleware
from botocore.client import Config
from dotenv import load_dotenv
import os

load_dotenv()

# Initialize the blockchain
blockchain = Blockchain()
app = _fastapi.FastAPI(title="NFT Blockchain API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

AWS_REGION = os.getenv("AWS_REGION")
AWS_ACCESS_KEY_ID=os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY=os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET_NAME=os.getenv("S3_BUCKET_NAME")

s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

ENDPOINTURL = s3_client.meta.endpoint_url

s3_client = boto3.client(
    's3', 
    endpoint_url=ENDPOINTURL,
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

@app.get("/generate_presigned_url")
def generate_presigned_url(
    file_name: str = _fastapi.Query(..., description="업로드할 파일 이름"),
    content_type: str = _fastapi.Query("application/octet-stream", description="파일의 Content-Type (기본값: application/octet-stream)")
):
    """
    Generate a pre-signed URL for S3 file upload.
    """
    try:
        file_key = f"nft_images/{file_name}"  # S3 내 파일 경로
        presigned_url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": S3_BUCKET_NAME,
                "Key": file_key,
                "ContentType": content_type,  # Content-Type 설정
            },
            ExpiresIn=3600,  # URL 유효 기간 (초 단위, 3600초 = 1시간)
            HttpMethod="PUT",
        )

        return {
            "url": presigned_url,
            "file_key": file_key,
        }
    except NoCredentialsError:
        raise HTTPException(status_code=500, detail="AWS credentials not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    Retrieve all unique NFTs in the blockchain.
    """
    unique_nfts = {}
    for block in blockchain.chain:
        for tx in block["transactions"]:
            nft_data = tx.get("nft")
            if nft_data:
                # Use a unique identifier like 'dna' to filter duplicates
                nft_key = nft_data.get("dna")
                if nft_key and nft_key not in unique_nfts:
                    unique_nfts[nft_key] = NFTModel(**nft_data)
    return list(unique_nfts.values())


@app.get("/nft/{dna}", response_model=NFTDetailModel)
def get_nft_by_dna(dna: str):
    """
    Retrieve a specific NFT by its DNA along with the current owner.
    """
    print(f"Searching for DNA: {dna}")
    nft_found = None
    owner = None
    last_block_index = None

    # Iterate over the blockchain in chronological order
    for block in blockchain.chain:
        print(f"Inspecting block: {block['index']}")
        for tx in block["transactions"]:
            nft_data = tx.get("nft")
            if nft_data:
                print(f"Found NFT with DNA: {nft_data.get('dna')}")
            if nft_data and nft_data.get("dna") == dna:
                nft_found = NFTModel(**nft_data)
                owner = tx["receiver"]  # The receiver is the current owner
                last_block_index = block["index"]

    if nft_found and owner:
        print(f"NFT found: {nft_found}")
        return NFTDetailModel(nft=nft_found, owner=owner, last_block_index=last_block_index)

    print("NFT not found")
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

# blockchain_route.py
import os
from typing import List, Optional
import requests
import boto3
from botocore.exceptions import NoCredentialsError
from database.connection import get_session
from fastapi import APIRouter, HTTPException, Query, Request, Depends, status
from sqlmodel import text
from dotenv import load_dotenv
from models.blockchain import Blockchain, Transaction, NFT
from models.blockchain_util import (
    MineBlockRequestModel,
    NFTModel,
    NFTDetailModel,
    NodeRegisterModel,
    TransactionModel,
    BlockModel,
    BlockchainModel,
    MineBlockResponse,
    NFTWithOwnerAndPriceModel,
)
from utils.security import verify_request_signature, send_signed_request  # Added

# Load environment variables
load_dotenv()

# Initialize the blockchain
blockchain = Blockchain()

# Initialize S3 client
AWS_REGION = os.getenv("AWS_REGION")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

ENDPOINTURL = s3_client.meta.endpoint_url

s3_client = boto3.client(
    "s3",
    endpoint_url=ENDPOINTURL,
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/heif",
    "image/apng",
    "image/avif",
    "image/gif",
    "image/webp",
}


# Dependencies
async def verify_signature_dependency(request: Request):
    from main import SECRET_KEY  # Import the secret key

    await verify_request_signature(request, SECRET_KEY)


router = APIRouter()


@router.get("/databases", status_code=status.HTTP_201_CREATED)
async def show_databases(session=Depends(get_session)) -> dict:
    try:
        result = session.execute(text("SHOW DATABASES"))
        databases = [row[0] for row in result.fetchall()]
        return {"databases": databases}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/generate_presigned_url")
def generate_presigned_url(
    file_name: str = Query(..., description="Name of the file to upload"),
    content_type: str = Query(
        "application/octet-stream",
        description="Content-Type of the file (default: application/octet-stream)",
    ),
):
    """
    Generate a pre-signed URL for S3 file upload.
    """

    # Verify content type
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported Content-Type. Allowed types: {', '.join(ALLOWED_IMAGE_TYPES)}",
        )

    try:
        file_key = f"nft_images/{file_name}"  # S3 file path
        presigned_url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": S3_BUCKET_NAME,
                "Key": file_key,
                "ContentType": content_type,  # Set Content-Type
                "Metadata": {
                    "x-amz-meta-max-size": "10485760",  # 10MB limit
                },
            },
            ExpiresIn=300,  # URL expiration time in seconds (3600s = 1 hour)
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


@router.post(
    "/create_transaction",
    response_model=TransactionModel,
    dependencies=[Depends(verify_signature_dependency)],
)
def create_transaction(transaction: TransactionModel):
    """
    Internal endpoint to add a new NFT transaction to the list of pending transactions.
    This endpoint is used by /broadcast_transaction to propagate transactions.
    """
    try:
        # If the transaction involves an NFT, verify ownership
        if transaction.nft:
            current_owner = get_current_owner(transaction.nft.dna)
            if current_owner and current_owner != transaction.sender:
                raise ValueError(
                    f"Sender {transaction.sender} is not the current owner of the NFT."
                )
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
                edition=transaction.nft.edition,  # Now optional
                date=transaction.nft.date,
                attributes=[attr.dict() for attr in transaction.nft.attributes]
                if transaction.nft.attributes
                else None,
                compiler=transaction.nft.compiler,  # Now optional
            )
        tx = Transaction(
            sender=transaction.sender,
            receiver=transaction.receiver,
            nft=nft,
            price=transaction.price,
            timestamp=transaction.timestamp,
        )
        index = blockchain.create_transaction(tx)
        # Save blockchain after creating transaction
        blockchain.save_to_file()
        return transaction
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/broadcast_transaction",
    dependencies=[Depends(verify_signature_dependency)],
)
def broadcast_transaction(transaction: TransactionModel):
    """
    Broadcast a transaction to other nodes in the network.
    """
    # Validate and create the transaction on the current node
    try:
        create_transaction(transaction)  # Internal validation occurs here
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

    # Broadcast the transaction to other nodes
    broadcast_errors = []
    from main import SECRET_KEY  # SECRET_KEY 가져오기

    for node in blockchain.nodes:
        try:
            # 서명된 요청 보내기
            response = send_signed_request(
                f"{node}/api/create_transaction", transaction.dict(), SECRET_KEY
            )
            if response.status_code != 200:
                broadcast_errors.append(
                    f"Failed to broadcast to {node}: {response.text}"
                )
        except requests.exceptions.RequestException as e:
            broadcast_errors.append(f"Failed to broadcast to {node}: {e}")

    if broadcast_errors:
        return {
            "message": "Transaction broadcasted with some errors.",
            "errors": broadcast_errors,
        }

    return {"message": "Transaction broadcasted successfully."}


@router.post(
    "/mine_block",
    response_model=MineBlockResponse,
    dependencies=[Depends(verify_signature_dependency)],
)
def mine_block(request: MineBlockRequestModel):
    """
    Mine a new block by adding all pending transactions to the blockchain.
    """
    miner_address = request.miner_address

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
                    nft=NFTModel(**tx["nft"]) if tx.get("nft") else None,
                    price=tx["price"],
                    timestamp=tx["timestamp"],
                )
                for tx in block["transactions"]
            ],
            proof=block["proof"],
            previous_hash=block["previous_hash"],
        )
        # Broadcast the new block to other nodes
        from main import SECRET_KEY  # Import the secret key

        for node in blockchain.nodes:
            print(f"Broadcasting block to node: {node}")
            try:
                response = send_signed_request(
                    f"{node}/api/receive_block",
                    block_model.dict(),
                    SECRET_KEY,
                )
                if response.status_code != 200:
                    print(f"Failed to broadcast block to {node}: {response.text}")
            except requests.exceptions.RequestException as e:
                print(f"Error broadcasting block to {node}: {e}")
        # Synchronize the chain after mining
        blockchain.replace_chain()  # Replace the chain if needed
        return MineBlockResponse(
            message="Block mined and broadcasted successfully", block=block_model
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/blockchain", response_model=BlockchainModel)
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


@router.get("/validate", response_model=bool)
def is_blockchain_valid():
    """
    Validate the integrity of the blockchain.
    """
    return blockchain.is_chain_valid()


@router.get("/previous_block", response_model=BlockModel)
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


@router.get("/nfts", response_model=List[NFTWithOwnerAndPriceModel])
def get_all_nfts():
    """
    Retrieve all unique NFTs in the blockchain along with their current owners and prices.
    """
    unique_nfts = {}
    nfts_with_details = []

    # First, collect all unique NFTs by their DNA
    for block in blockchain.chain:
        for tx in block["transactions"]:
            nft_data = tx.get("nft")
            if nft_data:
                dna = nft_data.get("dna")
                if dna and dna not in unique_nfts:
                    unique_nfts[dna] = NFTModel(**nft_data)

    # Now, for each unique NFT, find the current owner and current price
    for dna, nft in unique_nfts.items():
        owner = get_current_owner(dna)
        current_price = None

        # Iterate over the blockchain in reverse to find the latest transaction with a price
        for block in reversed(blockchain.chain):
            for tx in reversed(block["transactions"]):
                if tx.get("nft") and tx["nft"].get("dna") == dna:
                    if tx.get("price") is not None:
                        current_price = tx["price"]
                        break
            if current_price is not None:
                break

        nfts_with_details.append(
            NFTWithOwnerAndPriceModel(nft=nft, owner=owner, price=current_price)
        )

    return nfts_with_details


@router.get("/nft/{dna}", response_model=NFTDetailModel)
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
        return NFTDetailModel(
            nft=nft_found, owner=owner, last_block_index=last_block_index
        )

    print("NFT not found")
    raise HTTPException(status_code=404, detail="NFT not found")


@router.get("/transactions", response_model=List[TransactionModel])
def get_confirmed_transactions():
    """
    Retrieve all confirmed transactions that are included in the blockchain.
    """
    transactions = []
    try:
        for block in blockchain.chain:
            for tx in block["transactions"]:
                transaction = TransactionModel(
                    sender=tx["sender"],
                    receiver=tx["receiver"],
                    nft=tx["nft"],
                    price=tx["price"],
                    timestamp=tx["timestamp"],
                )
                transactions.append(transaction)
        return transactions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending_transactions", response_model=List[TransactionModel])
def get_pending_transactions():
    """
    Retrieve all pending transactions that are awaiting inclusion in a block.
    """
    try:
        pending_txs = [
            TransactionModel(
                sender=tx.sender,
                receiver=tx.receiver,
                nft=tx.nft.to_dict() if tx.nft else None,
                price=tx.price,
                timestamp=tx.timestamp,
            )
            for tx in blockchain.pending_transactions
        ]
        return pending_txs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# New block retrieval endpoint
@router.get("/block", response_model=BlockModel)
def get_block(
    index: Optional[int] = Query(None, description="Index of the block to retrieve"),
    hash: Optional[str] = Query(None, description="Hash of the block to retrieve"),
):
    """
    Retrieve a specific block by its index or hash.
    """
    if index is None and hash is None:
        raise HTTPException(
            status_code=400, detail="Either 'index' or 'hash' must be provided."
        )

    block = None

    if index is not None:
        block = blockchain.get_block_by_index(index)
        if not block:
            raise HTTPException(
                status_code=404, detail=f"Block with index {index} not found."
            )
    elif hash is not None:
        block = blockchain.get_block_by_hash(hash)
        if not block:
            raise HTTPException(
                status_code=404, detail=f"Block with hash {hash} not found."
            )

    # Convert block dict to BlockModel
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
    return block_model


# Node registration endpoint
@router.post(
    "/register_node",
    dependencies=[Depends(verify_signature_dependency)],
)
def register_node(node: NodeRegisterModel):
    """
    Register a new node in the network and propagate it to all existing nodes.
    """
    node_address = node.node_address

    if not node_address:
        raise HTTPException(status_code=400, detail="Invalid node address")

    # Prevent registering the current node
    current_host = os.getenv("HOST", "localhost")
    current_port = os.getenv("PORT", "8000")
    current_node = f"http://{current_host}:{current_port}"
    if node_address == current_node:
        raise HTTPException(status_code=400, detail="Cannot register the current node.")

    # Register the node (idempotent operation)
    already_exists = node_address in blockchain.nodes
    blockchain.register_node(node_address)
    if not already_exists:
        print(f"Node {node_address} registered successfully.")
    else:
        print(f"Node {node_address} is already registered.")

    response = {
        "message": "New node has been added"
        if not already_exists
        else "Node already exists",
        "total_nodes": list(blockchain.nodes),
    }

    # Broadcast the new node to all existing nodes except itself
    from main import SECRET_KEY  # Import the

    for existing_node in blockchain.nodes:
        if existing_node != node_address and existing_node != current_node:
            try:
                print(f"Broadcasting new node to {existing_node}")
                send_signed_request(
                    f"{existing_node}/api/register_node",
                    {"node_address": node_address},
                    SECRET_KEY,
                )
            except requests.exceptions.RequestException as e:
                print(f"Failed to broadcast to {existing_node}: {e}")

    return response


# Get nodes endpoint
@router.get("/get_nodes", response_model=List[str])
def get_nodes():
    """
    Retrieve the list of all nodes in the network.
    """
    return list(blockchain.nodes)


# Chain replacement endpoint
@router.get("/replace_chain")
def replace_chain():
    """
    Compare and replace the chain with the longest one in the network.
    """
    is_replaced = blockchain.replace_chain()
    if is_replaced:
        response = {
            "message": "The chain was replaced by the longest one.",
            "new_chain": blockchain.chain,
        }
    else:
        response = {
            "message": "Current chain is already the longest.",
            "chain": blockchain.chain,
        }
    return response


# Block broadcast endpoint
@router.post(
    "/broadcast_block",
    dependencies=[Depends(verify_signature_dependency)],
)
def broadcast_block(block: BlockModel):
    """
    Broadcast a new block to other nodes in the network.
    """
    # Validate and add the block to the chain before broadcasting
    added = blockchain.add_block(block.dict())
    if not added:
        raise HTTPException(status_code=400, detail="Invalid block")
    # Send the block to other nodes
    from main import SECRET_KEY  # Import the secret key

    for node in blockchain.nodes:
        try:
            response = send_signed_request(
                f"{node}/api/receive_block",
                block.dict(),
                SECRET_KEY,
            )
        except requests.exceptions.RequestException:
            continue
    return {"message": "Block broadcasted successfully."}


# Block reception endpoint
@router.post(
    "/receive_block",
    dependencies=[Depends(verify_signature_dependency)],
)
def receive_block(block: BlockModel):
    """
    Receive a block from another node and add it to the chain.
    """
    try:
        block_data = block.dict()
        added = blockchain.add_block(block_data)
        if not added:
            # If the block was not added, check if the received chain is longer
            replaced = blockchain.replace_chain()
            if replaced:
                return {
                    "message": "Chain was replaced with the longest one after receiving block."
                }
            else:
                raise HTTPException(
                    status_code=400, detail="Invalid block and chain not replaced."
                )
        return {"message": "Block added successfully."}
    except KeyError as ke:
        raise HTTPException(status_code=400, detail=f"Missing key in block data: {ke}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

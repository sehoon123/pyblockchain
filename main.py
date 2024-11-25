# main.py
import fastapi
from fastapi.middleware.cors import CORSMiddleware
from blockchain_route import router as blockchain_router
import asyncio
import os
import requests
import httpx

app = fastapi.FastAPI(title="NFT Blockchain API", version="0.2.1")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include the blockchain router
app.include_router(blockchain_router, prefix="/api", tags=["Blockchain"])

# Optionally, you can add a root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to the NFT Blockchain API"}

# Background task for periodic chain replacement
async def periodic_replace_chain():
    while True:
        await asyncio.sleep(60)  # Execute every 60 seconds
        try:
            from blockchain_route import blockchain
            replaced = blockchain.replace_chain()
            if replaced:
                print("Chain was replaced with the longest one.")
            else:
                print("Chain is already the longest.")
        except Exception as e:
            print(f"Error during replace_chain: {e}")

# Background task for mining blocks periodically
async def periodic_mine_block():
    await asyncio.sleep(60)  # 초기 지연 시간 (필요에 따라 조정 가능)
    while True:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:8000/api/mine_block",
                    json={"miner_address": "main server"},
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json"
                    },
                    timeout=10  # 요청 타임아웃 설정 (초 단위)
                )
                if response.status_code == 200:
                    print("자동 블록 채굴 성공:", response.json())
                else:
                    print(f"자동 블록 채굴 실패: {response.status_code}, {response.text}")
        except Exception as e:
            print(f"자동 블록 채굴 중 오류 발생: {e}")
        
        await asyncio.sleep(60)  # 다음 실행까지 대기 시간

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(periodic_replace_chain())
    asyncio.create_task(periodic_mine_block())

    # Automatic node registration if not the bootstrap node
    host = os.getenv("HOST", "localhost")
    port = os.getenv("PORT", "8000")
    node_address = f"http://{host}:{port}"

    bootstrap_node = os.getenv("BOOTSTRAP_NODE", node_address)  # If not set, self is bootstrap

    if node_address != bootstrap_node:
        try:
            # Register with the bootstrap node
            print(f"Registering with bootstrap node at {bootstrap_node}")
            response = requests.post(
                f"{bootstrap_node}/api/register_node",
                json={"node_address": node_address}
            )
            if response.status_code == 200:
                print("Successfully registered with the bootstrap node.")
            else:
                print(f"Failed to register with bootstrap node: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error registering with bootstrap node: {e}")

        try:
            # Retrieve the list of nodes from the bootstrap node
            print(f"Retrieving node list from bootstrap node at {bootstrap_node}")
            response = requests.get(f"{bootstrap_node}/api/get_nodes")
            if response.status_code == 200:
                nodes = response.json()
                print(f"Discovered nodes: {nodes}")
                for node in nodes:
                    if node != node_address:
                        try:
                            print(f"Registering with node: {node}")
                            requests.post(
                                f"{node}/api/register_node",
                                json={"node_address": node_address}
                            )
                        except requests.exceptions.RequestException as e:
                            print(f"Failed to register with node {node}: {e}")
            else:
                print(f"Failed to retrieve node list: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error retrieving node list: {e}")

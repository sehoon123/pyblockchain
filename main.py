import fastapi
from fastapi.middleware.cors import CORSMiddleware
from blockchain_route import router as blockchain_router
import asyncio


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
        await asyncio.sleep(60)  # 60초마다 실행
        try:
            from blockchain_route import blockchain
            replaced = blockchain.replace_chain()
            if replaced:
                print("Chain was replaced with the longest one.")
            else:
                print("Chain is already the longest.")
        except Exception as e:
            print(f"Error during replace_chain: {e}")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(periodic_replace_chain())
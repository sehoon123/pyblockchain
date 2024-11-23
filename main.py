import fastapi
from fastapi.middleware.cors import CORSMiddleware
from blockchain_route import router as blockchain_router


app = fastapi.FastAPI(title="NFT Blockchain API", version="0.2.0")

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

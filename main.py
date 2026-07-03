from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import create_db_and_tables
from routers import accounts, auth, categories, investments, stats, transactions


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="Finance API",
    description="Personal finance API: accounts, transactions, investments and net worth.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(categories.router)
app.include_router(transactions.router)
app.include_router(investments.router)
app.include_router(stats.router)


@app.get("/", tags=["health"])
def health_check():
    return {"status": "ok", "service": "finance-api"}


# Serve the frontend at /app (http://localhost:8000/app/)
frontend_dir = Path(__file__).parent / "frontend"
if frontend_dir.is_dir():
    app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")

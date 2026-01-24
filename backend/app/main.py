from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.endpoints import files, dictionaries
from app.core.config import settings
from app.core.database import init_db, engine
from app.core import seed
from sqlmodel import Session

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()
    with Session(engine) as session:
        seed.seed_data(session)

# Mount API routers
app.include_router(dictionaries.router, prefix=f"{settings.API_V1_STR}", tags=["dictionaries"])
app.include_router(files.router, prefix=f"{settings.API_V1_STR}", tags=["files"])

# Optional: Mount storage for static access if needed (or handle via API)

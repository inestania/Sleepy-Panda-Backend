from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.common.config import settings
from backend.common.database import Base, engine
from backend.services.auth import router as auth_router
from backend.services.feedback import router as feedback_router
from backend.services.prediction import router as prediction_router
from backend.services.sleep import router as sleep_router
from backend.services.users import router as users_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.project_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(prediction_router)
app.include_router(sleep_router)
app.include_router(feedback_router)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}

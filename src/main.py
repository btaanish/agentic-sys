from fastapi import FastAPI

from src.api.routes import router

app = FastAPI(title="Deep Research Agent System")
app.include_router(router)

# app/main.py

from fastapi import FastAPI
from app.api.routes import router as api_router

app = FastAPI(title="Calendar Booking Assistant")

# Register API routes
app.include_router(api_router, prefix="/api")

@app.get("/")
def home():
    return {"message": "🎉 Calendar Booking API is working! Visit /docs to try it."}


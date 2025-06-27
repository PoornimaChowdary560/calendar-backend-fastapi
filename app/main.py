# app/main.py

from fastapi import FastAPI
from app.api.routes import router as api_router
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://calendar-booking-frontend-6fb5d4y3unjuja6hh2wowe.streamlit.app/"],  # In production, specify frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app = FastAPI(title="Calendar Booking Assistant")

# Register API routes
app.include_router(api_router, prefix="/api")

@app.get("/")
def home():
    return {"message": "🎉 Calendar Booking API is working! Visit /docs to try it."}


# app/main.py

from fastapi import FastAPI
from app.api.routes import router as api_router
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(title="Calendar Booking Assistant")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://calendar-booking-frontend-7kbexjx3aan9qg22ejfpux.streamlit.app/"],  # In production, specify frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Register API routes
app.include_router(api_router, prefix="/api")

@app.get("/")
def home():
    return {"message": "🎉 Calendar Booking API is working! Visit /docs to try it."}


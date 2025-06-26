# app/api/routes.py

from fastapi import APIRouter, Request
from pydantic import BaseModel
from app.services.calendar_utils import create_event, get_upcoming_events, find_first_free_slot
from app.services.agent import handle_message
from app.schemas.message import ChatRequest

from typing import Optional

router = APIRouter()

class BookingRequest(BaseModel):
    summary: str
    date: str        # Format: YYYY-MM-DD
    start_time: str  # Format: HH:MM (24-hour)
    end_time: str    # Format: HH:MM (24-hour)

@router.get("/check")
async def check_events():
    # Assume fixed time for now — replace with your logic if needed
    #return {"available_time": "3 PM tomorrow"}
    slot = find_first_free_slot()
    if slot:
        return {"available_time": slot}
    return {"available_time": "No free slot tomorrow at 3 PM"}



@router.post("/book")
async def book_event_time(data: dict):
    time = data.get("time", "3 PM tomorrow")

    from datetime import datetime, timedelta
    india = pytz.timezone('Asia/Kolkata')
    tomorrow = datetime.now(india) + timedelta(days=1)
    
    # Extract hour from time string like "10 AM tomorrow"
    hour_map = {
        "9": "09:00", "10": "10:00", "11": "11:00",
        "12": "12:00", "1": "13:00", "2": "14:00", "3": "15:00",
        "4": "16:00", "5": "17:00"
    }

    time_parts = time.split()
    hour = hour_map.get(time_parts[0].replace("AM", "").replace("PM", ""), "15:00")

    date = tomorrow.strftime("%Y-%m-%d")
    start_time = hour
    end_time = f"{int(hour[:2]) + 1:02}:00"  # Add 1 hour

    create_event("Meeting", date, start_time, end_time)
    return {"message": f"✅ Meeting booked at {time}."}



class ChatRequest(BaseModel):
    message: str
    memory: Optional[dict] = {}

@router.post("/chat")
async def chat_with_agent(request: ChatRequest):
    state = handle_message(request.message, request.memory or {})
    return {
        "response": state.get("result", "Something went wrong."),
        "memory": state.get("memory", {})
    }


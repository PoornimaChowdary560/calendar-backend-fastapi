from __future__ import print_function
from datetime import datetime, timedelta, time
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from googleapiclient.discovery import build
import pytz
from fastapi import HTTPException
SCOPES = ['https://www.googleapis.com/auth/calendar']

# OAuth client config using environment variables
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/callback")

# Used in login flow (auth URL, callback, token exchange)
def get_google_auth_flow():
    return Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uris": [REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

# Production-ready service builder with injected token



def get_calendar_service(user_email: str):
    token_path = f"tokens/{user_email}.json"

    if not os.path.exists(token_path):
        raise HTTPException(status_code=401, detail="❌ No token found. Please login via /api/login")

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, "w") as token_file:
                token_file.write(creds.to_json())
        else:
            raise HTTPException(status_code=401, detail="❌ Token expired or invalid. Please re-authenticate via /api/login")

    return build('calendar', 'v3', credentials=creds)


def get_upcoming_events(for_date: datetime.date, user_email: str):
    service = get_calendar_service(user_token_file)
    india = pytz.timezone("Asia/Kolkata")

    start_dt = india.localize(datetime.combine(for_date, time.min))
    end_dt = india.localize(datetime.combine(for_date + timedelta(days=1), time.min))

    events_result = service.events().list(
        calendarId='primary',
        timeMin=start_dt.isoformat(),
        timeMax=end_dt.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    return events_result.get('items', [])

def create_event(summary, start_date, start_time, end_time, user_email: str):
    service = get_calendar_service(user_token_file)
    event = {
        'summary': summary,
        'start': {
            'dateTime': f'{start_date}T{start_time}:00',
            'timeZone': 'Asia/Kolkata',
        },
        'end': {
            'dateTime': f'{start_date}T{end_time}:00',
            'timeZone': 'Asia/Kolkata',
        },
    }
    event = service.events().insert(calendarId='primary', body=event).execute()
    print(f"✅ Event created: {event.get('htmlLink')}")

def find_first_free_slot(for_date: datetime.date, user_token_file=None):
    events = get_upcoming_events(for_date, user_token_file)
    india = pytz.timezone('Asia/Kolkata')

    booked_times = []
    for event in events:
        start_str = event['start'].get('dateTime', '')
        if start_str:
            booked = datetime.fromisoformat(start_str.replace('Z', '+00:00')).astimezone(india)
            booked_times.append(booked)

    for hour in range(9, 18):
        naive_slot = datetime.combine(for_date, time(hour=hour))
        aware_slot = india.localize(naive_slot)

        slot_taken = any(
            abs((booked - aware_slot).total_seconds()) < 30 * 60
            for booked in booked_times
        )

        if not slot_taken:
            return aware_slot.strftime('%I:%M %p on %B %d')

    return None

def is_slot_booked(date: str, hour: int, minute: int = 0, user_token_file=None) -> bool:
    service = get_calendar_service(user_token_file)
    india = pytz.timezone("Asia/Kolkata")

    start_dt = india.localize(datetime.strptime(f"{date} {hour:02}:{minute:02}", "%Y-%m-%d %H:%M"))
    end_dt = start_dt + timedelta(hours=1)

    events_result = service.events().list(
        calendarId='primary',
        timeMin=start_dt.isoformat(),
        timeMax=end_dt.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    return len(events_result.get('items', [])) > 0

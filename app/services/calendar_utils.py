from __future__ import print_function
from datetime import datetime, timedelta, time
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pytz

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    creds = None
    token_path = 'credentials/token.json'
    creds_path = 'credentials/credentials.json'

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)


def get_upcoming_events(for_date: datetime.date):
    service = get_calendar_service()
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


def create_event(summary, start_date, start_time, end_time):
    service = get_calendar_service()
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


def find_first_free_slot(for_date: datetime.date):
    events = get_upcoming_events(for_date)
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


def is_slot_booked(date: str, hour: int, minute: int = 0) -> bool:
    service = get_calendar_service()
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


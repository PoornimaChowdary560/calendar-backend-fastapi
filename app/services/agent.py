import os
from dotenv import load_dotenv
from langchain_community.chat_models import ChatOpenAI
from langgraph.graph import StateGraph, END
from app.services.calendar_utils import (
    get_upcoming_events,
    create_event,
    is_slot_booked,
    find_first_free_slot,
)
import dateparser
from dateparser.search import search_dates
from dateutil.relativedelta import relativedelta, TH, FR, WE, TU, MO, SA, SU
from datetime import datetime, timedelta, time
import pytz
import re

load_dotenv()
llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo")

india = pytz.timezone("Asia/Kolkata")

# Extract time range like "between 2 and 4 PM"
def extract_time_range(msg):
    match = re.search(r'between (\d{1,2})(?::(\d{2}))?\s?(am|pm)?\s?and\s?(\d{1,2})(?::(\d{2}))?\s?(am|pm)?', msg)
    if match:
        def parse(hour, minute, period):
            hour = int(hour)
            minute = int(minute or 0)
            if period == "pm" and hour != 12:
                hour += 12
            elif period == "am" and hour == 12:
                hour = 0
            return hour, minute

        start_hour, start_min = parse(match.group(1), match.group(2), match.group(3))
        end_hour, end_min = parse(match.group(4), match.group(5), match.group(6))
        return start_hour, start_min, end_hour, end_min
    return None

# Smart date interpretation
# Smart date interpretation
def interpret(state):
    msg = state["input"].lower()
    now = datetime.now(india)
    parsed_datetime = None

    # Manual handling for relative keywords
    special_day = None
    if "day after tomorrow" in msg:
        special_day = now + timedelta(days=2)
    elif "tomorrow" in msg:
        special_day = now + timedelta(days=1)
    elif "today" in msg:
        special_day = now
    elif "next week" in msg:
        special_day = now + timedelta(weeks=1)
    elif "next monday" in msg:
        special_day = now + relativedelta(weekday=MO(+1))
    elif "next tuesday" in msg:
        special_day = now + relativedelta(weekday=TU(+1))
    elif "next wednesday" in msg:
        special_day = now + relativedelta(weekday=WE(+1))
    elif "next thursday" in msg:
        special_day = now + relativedelta(weekday=TH(+1))
    elif "next friday" in msg:
        special_day = now + relativedelta(weekday=FR(+1))
    elif "next saturday" in msg:
        special_day = now + relativedelta(weekday=SA(+1))
    elif "next sunday" in msg:
        special_day = now + relativedelta(weekday=SU(+1))

    # ✅ Custom parsing for numeric dates like 5-9-2025 or 05/09/2025
    # ✅ Custom parsing for numeric dates like 5-9-2025 or 05/09/2025
    # ✅ Custom parsing for numeric dates like 5-9-2025 or 05/09/2025
    numeric_date_match = re.search(r'\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b', msg)
    if numeric_date_match:
        day, month, year = map(int, numeric_date_match.groups())
        try:
            parsed_datetime = india.localize(datetime(year, month, day))

            # ⏰ Extract specific time like "11am", "2:30 pm", etc.
            # ✅ Improved time regex: works for "12am", "2:30pm", "2 pm", etc.
            time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', msg.replace(" ", ""))

            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2) or 0)
                period = time_match.group(3).lower()

                if period == "pm" and hour != 12:
                    hour += 12
                elif period == "am" and hour == 12:
                    hour = 0

                parsed_datetime = parsed_datetime.replace(hour=hour, minute=minute)
            else:
                # 🔁 Only fallback if time not given at all
                parsed_datetime = parsed_datetime.replace(hour=9, minute=0)
        except ValueError:
            parsed_datetime = None  # fallback to dateparser



    # Use dateparser if not already parsed
    if not parsed_datetime:
        if special_day:
            parsed_datetime = dateparser.parse(
                msg,
                settings={
                    "TIMEZONE": "Asia/Kolkata",
                    "RETURN_AS_TIMEZONE_AWARE": True,
                    "PREFER_DATES_FROM": "future",
                    "RELATIVE_BASE": special_day,
                    "DATE_ORDER": "DMY"
                }
            )
        else:
            parsed_datetime = dateparser.parse(
                msg,
                settings={
                    "TIMEZONE": "Asia/Kolkata",
                    "RETURN_AS_TIMEZONE_AWARE": True,
                    "PREFER_DATES_FROM": "future",
                    "DATE_ORDER": "DMY"
                }
            )

    # Fallback to search_dates if still not parsed
    if not parsed_datetime:
        found = search_dates(
            msg,
            settings={
                "TIMEZONE": "Asia/Kolkata",
                "RETURN_AS_TIMEZONE_AWARE": True,
                "PREFER_DATES_FROM": "future",
                "DATE_ORDER": "DMY"
            }
        )
        if found:
            parsed_datetime = found[0][1]

    # Default time if missing
    # 🕒 Handle vague time keywords and override wrong default times
    if parsed_datetime:
        original_msg = msg.lower()
        current_time = now.strftime("%H:%M")
        parsed_time = parsed_datetime.strftime("%H:%M")

        # If time wasn't explicitly mentioned or looks wrongly inherited from current time
        if (
            parsed_time == current_time or
            parsed_datetime.time() == datetime.min.time()
        ):
            if "afternoon" in original_msg:
                parsed_datetime = parsed_datetime.replace(hour=14, minute=0)
            elif "evening" in original_msg:
                parsed_datetime = parsed_datetime.replace(hour=18, minute=0)
            elif "night" in original_msg:
                parsed_datetime = parsed_datetime.replace(hour=20, minute=0)
            elif "morning" in original_msg:
                parsed_datetime = parsed_datetime.replace(hour=9, minute=0)
            else:
                parsed_datetime = parsed_datetime.replace(hour=9, minute=0)  # default fallback


    # Normalize to IST
    if parsed_datetime and not parsed_datetime.tzinfo:
        parsed_datetime = india.localize(parsed_datetime)
    elif parsed_datetime:
        parsed_datetime = parsed_datetime.astimezone(india)

    # Extract time range
    time_range = extract_time_range(msg)

    # Intent
    if parsed_datetime:
        state["intent"] = "book" if "book" in msg or "schedule" in msg else "check"
        state["parsed_datetime"] = parsed_datetime
        state["time_range"] = time_range
    elif "check" in msg or "free" in msg or "available" in msg:
        state["intent"] = "check"
    elif "book" in msg or "schedule" in msg:
        state["intent"] = "book"
    else:
        state["intent"] = "unknown"

    return state

# Action handler
def take_action(state):
    intent = state["intent"]
    memory = state.get("memory", {})
    parsed_dt = state.get("parsed_datetime")
    
    if intent == "check":
        if not parsed_dt:
            return {"result": "❌ Please specify a date like 'Check availability tomorrow'.", "memory": memory}

        date = parsed_dt.astimezone(india).date()
        events = get_upcoming_events(for_date=date)

        booked_hours = [
            datetime.fromisoformat(e["start"]["dateTime"].replace('Z', '+00:00')).astimezone(india).hour
            for e in events if "dateTime" in e["start"]
        ]

        free_slots = []
        for hour in range(9, 18):
            if hour not in booked_hours:
                time_str = datetime.strptime(f"{hour}:00", "%H:%M").strftime("%I %p").lstrip("0")
                free_slots.append(f"{time_str} on {date.strftime('%b %d')}")
            if len(free_slots) == 3:
                break

        memory["last_checked_time"] = free_slots[0] if free_slots else None

        return {
            "result": f"Available slots: {', '.join(free_slots)}" if free_slots else "No free slots found.",
            "memory": memory
        }

    if intent == "book":
        try:
            time_range = state.get("time_range")
            if time_range and parsed_dt:
                start_hour, start_minute, end_hour, end_minute = time_range
                date = parsed_dt.astimezone(india).date()
                for hour in range(start_hour, end_hour):
                    for minute in [0, 30]:
                        if hour == start_hour and minute < start_minute:
                            continue
                        if hour == end_hour and minute > end_minute:
                            continue
                        if is_slot_booked(date.strftime("%Y-%m-%d"), hour, minute):
                            continue
                        start_time = f"{hour:02}:{minute:02}"
                        end_dt = datetime.combine(date, time(hour, minute)) + timedelta(hours=1)
                        end_time = end_dt.strftime("%H:%M")
                        create_event("Meeting", date.strftime("%Y-%m-%d"), start_time, end_time)
                        return {
                            "result": f"✅ Meeting booked for {datetime.combine(date, time(hour, minute)).strftime('%I:%M %p')} on {date.strftime('%b %d')}",
                            "memory": memory
                        }

                return {"result": "❌ No free slot found in specified range.", "memory": memory}

            if not parsed_dt:
                today = datetime.now(india).date() + timedelta(days=1)
                suggestion = find_first_free_slot(today)
                return {"result": f"❌ Please specify a time. Suggested: {suggestion}", "memory": memory}

            local_dt = parsed_dt.astimezone(india)
            start_date = local_dt.date().strftime("%Y-%m-%d")
            hour = local_dt.hour
            minute = local_dt.minute

            if is_slot_booked(start_date, hour, minute):
                return {
                    "result": f"❌ Slot at {local_dt.strftime('%I:%M %p')} is already booked.",
                    "memory": memory
                }

            start_time = f"{hour:02}:{minute:02}"
            end_dt = local_dt + timedelta(hours=1)
            end_time = f"{end_dt.hour:02}:{end_dt.minute:02}"

            create_event("Meeting", start_date, start_time, end_time)

            return {
                "result": f"✅ Meeting booked for {local_dt.strftime('%I:%M %p')} on {local_dt.strftime('%b %d')}",
                "memory": memory
            }

        except Exception as e:
            return {"result": f"❌ Error booking: {str(e)}", "memory": memory}

    return {"result": "❌ I didn’t understand. Try again with a proper instruction.", "memory": memory}

# LangGraph setup
def build_agent():
    builder = StateGraph(dict)
    builder.add_node("Interpret", interpret)
    builder.add_node("Action", take_action)
    builder.set_entry_point("Interpret")
    builder.add_edge("Interpret", "Action")
    builder.add_edge("Action", END)
    return builder.compile()

agent = build_agent()

def handle_message(user_input: str, memory: dict = None) -> dict:
    if memory is None:
        memory = {}
    return agent.invoke({"input": user_input, "memory": memory})

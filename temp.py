# streamlit_event_app.py
# Event Organizer + AI Description Generator with Tone Options

import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, date, time
import json
import os
import base64
import dspy
from dotenv import load_dotenv
load_dotenv()

# -----------------------------
# DSPy LLM Configuration
# -----------------------------
llm = dspy.LM(
    model="gemini/gemini-2.0-flash",
    api_key=os.environ["GOOGLE_API_KEY"]
)
dspy.settings.configure(lm=llm)

# -----------------------------
# Config
# -----------------------------
ADMIN_CREDENTIALS = {"admin": "adminpass"}
USERS = {"user": "userpass"}
EVENTS_FILE = "events.json"
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

st.set_page_config(page_title="Event Organizer", layout="wide")

# -----------------------------
# Utility Functions
# -----------------------------
def load_events():
    if os.path.exists(EVENTS_FILE):
        try:
            with open(EVENTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_events(events):
    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2, default=str)

def image_to_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
            mime = "image/png"
            if file_path.lower().endswith((".jpg", ".jpeg")):
                mime = "image/jpeg"
            return f"data:{mime};base64,{encoded}"
    except:
        return ""

def ensure_session():
    if "events" not in st.session_state:
        st.session_state.events = load_events()
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "role" not in st.session_state:
        st.session_state.role = None
    if "username" not in st.session_state:
        st.session_state.username = ""
    if "ai" not in st.session_state:
        st.session_state.ai = {"description": ""}

ensure_session()

# -----------------------------
# Authentication
# -----------------------------
st.title("🎫 KnoWhere – Event Organizer")

with st.expander("Login (Admin/User)", expanded=True):
    col1, col2 = st.columns([1, 2])
    with col1:
        role = st.radio("Login as:", ["Guest", "User", "Admin"], index=0)
    with col2:
        if role == "Guest":
            if st.button("Continue as Guest"):
                st.session_state.logged_in = True
                st.session_state.role = "guest"
                st.session_state.username = "Guest"
                st.success("Continuing as Guest")

        else:
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")

            if st.button("Login"):
                if role == "Admin":
                    if username in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[username] == password:
                        st.session_state.logged_in = True
                        st.session_state.role = "admin"
                        st.session_state.username = username
                        st.success("Logged in as Admin")
                    else:
                        st.error("Invalid admin credentials")

                elif role == "User":
                    if username:
                        st.session_state.logged_in = True
                        st.session_state.role = "user"
                        st.session_state.username = username
                        st.success(f"Logged in as {username}")
                    else:
                        st.error("Invalid user credentials")

if not st.session_state.logged_in:
    st.info("Please login first.")
    st.stop()

# -----------------------------
# ADMIN PANEL — AI DESCRIPTION ONLY
# -----------------------------
if st.session_state.role == "admin":

    st.header("🛠 Admin Panel — Add Event")
    st.subheader("✨ AI Description Generator")

    # ---- Tone Selector ----
    tone = st.selectbox(
        "Select Description Tone",
        [
            "Professional",
            "Casual",
            "Marketing / Promotional",
            "Formal",
            "Friendly",
            "Academic",
            "Short & Crisp",
            "Inspirational",
        ],
        index=0,
    )

    # ---- Extra context ----
    user_context = st.text_area(
        "Additional context for the description (optional):",
        placeholder="Example: highlight benefits, keynote speaker details, audience type..."
    )

    # ---- AI Button (outside form) ----
    if st.button("✨ Generate Description with AI"):
        prompt = f"""
        Write a {tone.lower()} 4–6 sentence event description.

        Context:
        {user_context}

        Make it engaging, clear, and suitable for an event listing.
        """

        try:
            st.session_state.ai["description"] = llm(prompt)
            st.success("AI Description Generated!")
        except Exception as e:
            st.error(f"AI Error: {e}")

    # -----------------------------
    # EVENT FORM
    # -----------------------------
    st.markdown("### 📝 Event Form")

    with st.form("add_event_form"):
        col1, col2 = st.columns(2)

        with col1:
            title = st.text_input("Event Title")
            category = st.selectbox(
                "Category",
                ["Conference", "Workshop", "Meetup", "Concert", "Other"]
            )
            date_val = st.date_input("Event Date", value=date.today())

        with col2:
            time_val = st.time_input("Event Time", value=time(18, 0))
            location = st.text_input("Location")
            price = st.number_input("Price (INR)", min_value=0.0, value=0.0)

        organizer = st.text_input("Organizer", value=st.session_state.username)

        description = st.text_area(
            "Event Description",
            value=st.session_state.ai.get("description", "")
        )

        img = st.file_uploader("Upload Event Image (optional)", type=["jpg", "jpeg", "png"])

        submitted = st.form_submit_button("Add Event")

        if submitted:
            event_id = int(datetime.now().timestamp() * 1000)

            img_data_url = ""
            if img:
                ext = os.path.splitext(img.name)[1]
                img_path = os.path.join(UPLOAD_DIR, f"{event_id}{ext}")
                with open(img_path, "wb") as f:
                    f.write(img.getbuffer())
                img_data_url = image_to_base64(img_path)

            event = {
                "id": event_id,
                "title": title,
                "category": category,
                "date": date_val.isoformat(),
                "time": time_val.strftime("%H:%M"),
                "location": location,
                "price": float(price),
                "organizer": organizer,
                "description": description,
                "image": img_data_url,
            }

            st.session_state.events.append(event)
            save_events(st.session_state.events)
            st.success("Event added successfully!")

    st.markdown("---")

# -----------------------------
# BROWSE EVENTS
# -----------------------------
st.header("Browse Events")

all_events = st.session_state.events
st.sidebar.header("Filters")

q = st.sidebar.text_input("Search")
categories = sorted(list({e.get("category", "") for e in all_events}))
cat_filter = st.sidebar.selectbox("Category", ["All"] + categories)

locations = sorted(list({e.get("location", "") for e in all_events}))
loc_filter = st.sidebar.selectbox("Location", ["All"] + locations)

min_price = 0
max_price = max([e["price"] for e in all_events]) if all_events else 100
price_range = st.sidebar.slider("Price Range", min_price, int(max_price) + 50, (min_price, int(max_price)))

filtered = []
for e in all_events:
    if q and q.lower() not in e["title"].lower():
        continue
    if cat_filter != "All" and e["category"] != cat_filter:
        continue
    if loc_filter != "All" and e["location"] != loc_filter:
        continue
    if not (price_range[0] <= e["price"] <= price_range[1]):
        continue
    filtered.append(e)

def render_event_cards(events_list):
    if not events_list:
        st.info("No events found.")
        return

    html = """
    <style>
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }
    .card { border-radius: 12px; padding: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.12); background: white; }
    .title { font-size:18px; font-weight:600; margin-bottom:6px; }
    .meta { font-size:13px; color:#555; margin-bottom:8px; }
    .desc { font-size:14px; color:#333; margin-bottom:8px; }
    img { width:100%; height:160px; object-fit:contain; border-radius:8px; margin-bottom:8px; }
    </style>
    <div class="grid">
    """
    for e in events_list:
        img_html = f"<img src='{e['image']}'/>" if e.get("image") else ""
        card = f"""
        <div class="card">
            {img_html}
            <div class="title">{e['title']}</div>
            <div class="meta">{e['category']} · {e['location']} · {e['date']} {e['time']}</div>
            <div class="desc">{e['description']}</div>
        </div>
        """
        html += card

    html += "</div>"
    components.html(html, height=600, scrolling=True)

render_event_cards(filtered)

# -----------------------------
# ADMIN TOOLS
# -----------------------------
if st.session_state.role == "admin":
    st.markdown("---")
    st.subheader("Admin Tools")

    if st.button("Export events JSON"):
        save_events(st.session_state.events)
        with open(EVENTS_FILE, "rb") as f:
            st.download_button("Download events.json", f, file_name="events.json")

    if st.button("Clear all events"):
        st.session_state.events = []
        save_events([])
        st.success("All events cleared!")

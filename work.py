# streamlit_event_app.py

import streamlit as st
import streamlit.components.v1 as components  # kept in case you want custom HTML later
from datetime import datetime, date, time, timedelta
import json, os, base64

# -----------------------------
# CONFIG
# -----------------------------
ADMIN_CREDENTIALS = {"admin": "adminpass"}
USERS = {"user": "userpass"}  # not strictly used for auth check, but kept

EVENTS_FILE = "events.json"
UPLOAD_DIR = "uploads"
CHAT_DIR = "chat"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CHAT_DIR, exist_ok=True)

st.set_page_config(page_title="Event Organizer", layout="wide")

# Global CSS (for status badge blink)
st.markdown(
    """
    <style>
    .blink { animation: blinkAnim 1s infinite; }
    @keyframes blinkAnim { 50% { opacity: .2 } }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# HELPERS
# -----------------------------
def load_events():
    if not os.path.exists(EVENTS_FILE):
        return []
    try:
        return json.load(open(EVENTS_FILE, "r"))
    except:
        return []


def save_events(events):
    json.dump(events, open(EVENTS_FILE, "w"), indent=2)


def img64(path):
    try:
        b = open(path, "rb").read()
        enc = base64.b64encode(b).decode()
        mime = "image/png"
        if path.lower().endswith(".jpg") or path.lower().endswith(".jpeg"):
            mime = "image/jpeg"
        return f"data:{mime};base64,{enc}"
    except:
        return ""


def chat_file(event_id):
    return os.path.join(CHAT_DIR, f"{event_id}.json")


def load_chat(event_id):
    fp = chat_file(event_id)
    if not os.path.exists(fp):
        return []
    try:
        return json.load(open(fp, "r"))
    except:
        return []


def save_chat(event_id, messages):
    json.dump(messages, open(chat_file(event_id), "w"), indent=2)


# -----------------------------
# SESSION
# -----------------------------
if "events" not in st.session_state:
    st.session_state.events = load_events()
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None
if "username" not in st.session_state:
    st.session_state.username = None
if "page" not in st.session_state:
    st.session_state.page = "list"  # "list" or "event_page"
if "selected_event" not in st.session_state:
    st.session_state.selected_event = None
if "joined_events" not in st.session_state:
    st.session_state.joined_events = {}  # event_id -> bool


# -----------------------------
# STATUS + END TIME
# -----------------------------
def compute_status(e):
    try:
        start = datetime.combine(
            date.fromisoformat(e["date"]),
            datetime.strptime(e["time"], "%H:%M").time(),
        )
    except:
        return "past"
    hrs = float(e.get("hours", 0))
    end = start + timedelta(hours=hrs)
    now = datetime.now()
    if now > end:
        return "past"
    if now >= start:
        return "live"
    if start.date() == now.date():
        return "soon"
    return "upcoming"


def status_badge(s):
    if s == "past":
        return "<div class='status-badge' style='background:#ffd6d6;color:#8b0000;position:absolute;top:6px;right:6px;padding:4px 8px;border-radius:6px;font-size:12px;font-weight:700;'>PAST</div>"
    if s == "live":
        return "<div class='status-badge blink' style='background:#b7ffba;color:#035c00;position:absolute;top:6px;right:6px;padding:4px 8px;border-radius:6px;font-size:12px;font-weight:700;'>LIVE</div>"
    if s == "soon":
        return "<div class='status-badge' style='background:#dce8ff;color:#00347a;position:absolute;top:6px;right:6px;padding:4px 8px;border-radius:6px;font-size:12px;font-weight:700;'>STARTING SOON</div>"
    return "<div class='status-badge' style='background:#e6e3ff;color:#2a2275;position:absolute;top:6px;right:6px;padding:4px 8px;border-radius:6px;font-size:12px;font-weight:700;'>UPCOMING</div>"


# -----------------------------
# LOGIN UI
# -----------------------------
st.title("🎫 KnoWhere")

with st.expander("Login (Admin/User)", expanded=True):

    role = st.radio("Login as:", ["Guest", "User", "Admin"], index=0)

    if role == "Guest":
        if st.button("Continue as Guest"):
            st.session_state.logged_in = True
            st.session_state.role = "guest"
            st.session_state.username = "Guest"
            st.success("Continuing as Guest")
    else:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")

        if st.button("Login"):

            if role == "Admin":
                if u in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[u] == p:
                    st.session_state.logged_in = True
                    st.session_state.role = "admin"
                    st.session_state.username = u
                    st.success("Logged in as Admin")
                else:
                    st.error("Invalid admin credentials")

            elif role == "User":
                # Simple demo: accept any username/password as "user"
                st.session_state.logged_in = True
                st.session_state.role = "user"
                st.session_state.username = u
                st.success(f"Logged in as {u}")

if not st.session_state.logged_in:
    st.stop()


# -----------------------------
# ADMIN PANEL
# -----------------------------
if st.session_state.role == "admin":

    st.header("Admin Panel — Add Event")

    with st.form("add"):

        c1, c2 = st.columns(2)

        with c1:
            t = st.text_input("Event Title")
            cat = st.selectbox(
                "Category",
                ["Conference", "Workshop", "Meetup", "Concert", "Other"],
            )
            d = st.date_input("Date", value=date.today())
            tm = st.time_input("Time", value=time(18, 0))
            loc = st.text_input("Location")

        with c2:
            price = st.number_input("Price", min_value=0.0, step=50.0)
            cap = st.number_input("Capacity", min_value=1)
            hours = st.number_input(
                "How many hours event will run?", min_value=1.0, step=1.0
            )
            img = st.file_uploader("Image", type=["png", "jpg", "jpeg"])

        desc = st.text_area("Description")

        submit = st.form_submit_button("Add Event")

        if submit:
            eid = int(datetime.now().timestamp() * 1000)
            encoded = ""

            if img:
                ext = os.path.splitext(img.name)[1]
                pth = os.path.join(UPLOAD_DIR, f"{eid}{ext}")
                with open(pth, "wb") as f:
                    f.write(img.getbuffer())
                encoded = img64(pth)

            st.session_state.events.append(
                {
                    "id": eid,
                    "title": t,
                    "category": cat,
                    "date": d.isoformat(),
                    "time": tm.strftime("%H:%M"),
                    "location": loc,
                    "price": float(price),
                    "capacity": int(cap),
                    "hours": float(hours),
                    "description": desc,
                    "image": encoded,
                }
            )

            save_events(st.session_state.events)
            st.success("Event added successfully")


# -----------------------------
# FILTER SIDEBAR + STATUS FILTER
# -----------------------------
all_events = st.session_state.events
st.header("Browse Events")

st.sidebar.header("Filters")

q = st.sidebar.text_input("Search")

categories = sorted(list({e.get("category", "") for e in all_events})) if all_events else []
cat_filter = st.sidebar.selectbox("Category", ["All"] + categories)

locations = sorted(list({e.get("location", "") for e in all_events})) if all_events else []
loc_filter = st.sidebar.selectbox("Location", ["All"] + locations)

status_opts = ["live", "soon", "upcoming", "past"]
status_filter = st.sidebar.multiselect("Status", status_opts)

min_price = 0
max_price = max([e["price"] for e in all_events]) if all_events else 100
price_range = st.sidebar.slider(
    "Price Range", min_price, int(max_price) + 50, (min_price, int(max_price))
)

filtered = []
for e in all_events:
    s = compute_status(e)
    if q and q.lower() not in e["title"].lower():
        continue
    if cat_filter != "All" and e["category"] != cat_filter:
        continue
    if loc_filter != "All" and e["location"] != loc_filter:
        continue
    if status_filter and s not in status_filter:
        continue
    if not (price_range[0] <= e["price"] <= price_range[1]):
        continue
    filtered.append(e)

# reorder
filtered.sort(
    key=lambda x: ({"live": 0, "soon": 1, "upcoming": 2, "past": 3}.get(compute_status(x), 9))
)


# -----------------------------
# RENDER CARDS (with "View Event" buttons)
# -----------------------------
def render(events):
    if not events:
        st.info("No events match your filters.")
        return

    def card_html(e):
        s = compute_status(e)
        img_html = (
            f'<img src="{e["image"]}" '
            f'style="width:100%;height:170px;object-fit:contain;'
            f'border-radius:8px;margin-bottom:8px;" />'
            if e.get("image")
            else ""
        )
        return f"""
        <div style="border-radius:12px;padding:12px;background:white; color:black;
                    box-shadow:0 2px 6px rgba(0,0,0,0.15);position:relative;">
            {status_badge(s)}
            {img_html}
            <b>{e['title']}</b><br>
            {e['category']}<br>
            {e['location']}<br>
            {e['date']} {e['time']}<br>
            <b>{'Free' if e['price']==0 else '₹'+str(int(e['price']))}</b>
        </div>
        """

    # Show cards in rows of 3 using columns
    for i in range(0, len(events), 3):
        row = events[i : i + 3]
        cols = st.columns(len(row))
        for e, col in zip(row, cols):
            with col:
                st.markdown(card_html(e), unsafe_allow_html=True)
                if st.button("View Event", key=f"view_{e['id']}"):
                    st.session_state.page = "event_page"
                    st.session_state.selected_event = e["id"]
                    st.rerun()


render(filtered)


# -----------------------------
# EVENT PAGE + CHAT
# -----------------------------
if st.session_state.page == "event_page" and st.session_state.selected_event is not None:
    eid = st.session_state.selected_event
    event = next((e for e in all_events if e["id"] == eid), None)

    st.markdown("---")
    if not event:
        st.error("Event not found.")
    else:
        # Back button
        if st.button("⬅ Back to Events"):
            st.session_state.page = "list"
            st.session_state.selected_event = None
            st.rerun()

        st.subheader("Event Details")
        cols_top = st.columns([2, 1])

        with cols_top[0]:
            st.markdown(f"### {event['title']}")
            st.write(f"📍 **Location:** {event['location']}")
            st.write(f"📂 **Category:** {event['category']}")
            st.write(f"🕒 **Date & Time:** {event['date']} {event['time']}")
            st.write(
                f"💰 **Price:** {'Free' if event['price'] == 0 else '₹' + str(int(event['price']))}"
            )
            st.write(f"⏱ **Duration:** {event.get('hours', 0)} hours")
            st.write(f"👥 **Capacity:** {event.get('capacity', 0)}")
            st.write("----")
            st.markdown("#### Description")
            st.write(event.get("description") or "_No description provided._")

        with cols_top[1]:
            if event.get("image"):
                st.image(event["image"], use_container_width=True, caption="Event Image")

        st.write("----")
        st.subheader("💬 Event Chat Room")

        # Guests can view but not chat
        messages = load_chat(eid)

        # Show existing messages (last 100)
        if messages:
            for msg in messages[-100:]:
                st.markdown(
                    f"""
                    <div style="background:black;padding:8px;border-radius:6px;margin-bottom:5px; color:white;">
                        <b>{msg['user']}</b>: {msg['text']}<br/>
                        <span style="color:gray;font-size:11px;">{msg['time']}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("No messages yet. Be the first to say hi 👋")

        # Chat input logic
        if st.session_state.role not in ["user", "admin"]:
            # Guest or unknown
            st.warning("Only registered Users/Admins can participate in the chat. Login as User to join.")
        else:
            # Join gate – only those who click join can chat
            joined = st.session_state.joined_events.get(eid, False)
            if not joined:
                if st.button("✅ Join this Event Chat"):
                    st.session_state.joined_events[eid] = True
                    st.rerun()
                st.info("Join this event to participate in the chat.")
            else:
                st.success("You have joined this event. You can chat below.")

                new_msg = st.text_input(
                    "Type your message...", key=f"chat_input_{eid}"
                )
                if st.button("Send", key=f"send_{eid}"):
                    if new_msg.strip():
                        messages.append(
                            {
                                "user": st.session_state.get("username", "User"),
                                "text": new_msg.strip(),
                                "time": datetime.now().strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),
                            }
                        )
                        save_chat(eid, messages)
                        st.rerun()
                    else:
                        st.warning("Message cannot be empty.")

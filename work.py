# streamlit_event_app.py

import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, date, time, timedelta
import json, os, base64

# -----------------------------
# CONFIG
# -----------------------------
ADMIN_CREDENTIALS = {"admin": "adminpass"}
USERS = {"user": "userpass"}

EVENTS_FILE="events.json"
UPLOAD_DIR="uploads"
os.makedirs(UPLOAD_DIR,exist_ok=True)

st.set_page_config(page_title="Event Organizer",layout="wide")

# -----------------------------
# HELPERS
# -----------------------------
def load_events():
    if not os.path.exists(EVENTS_FILE): return []
    try:
        return json.load(open(EVENTS_FILE,"r"))
    except:
        return []

def save_events(events):
    json.dump(events,open(EVENTS_FILE,"w"),indent=2)

def img64(path):
    try:
        b=open(path,"rb").read()
        enc=base64.b64encode(b).decode()
        mime="image/png"
        if path.lower().endswith(".jpg") or path.lower().endswith(".jpeg"):
            mime="image/jpeg"
        return f"data:{mime};base64,{enc}"
    except:
        return ""

# -----------------------------
# SESSION
# -----------------------------
if "events" not in st.session_state:
    st.session_state.events = load_events()
if "logged_in" not in st.session_state:
    st.session_state.logged_in=False
if "role" not in st.session_state:
    st.session_state.role=None


# -----------------------------
# STATUS + END TIME
# -----------------------------
def compute_status(e):
    try:
        start = datetime.combine(date.fromisoformat(e["date"]), datetime.strptime(e["time"],"%H:%M").time())
    except:
        return "past"
    hrs = float(e.get("hours",0))
    end = start + timedelta(hours=hrs)
    now=datetime.now()
    if now > end: return "past"
    if now >= start: return "live"
    if start.date()==now.date(): return "soon"
    return "upcoming"


def status_badge(s):
    if s=="past": return "<div class='status-badge' style='background:#ffd6d6;color:#8b0000;'>PAST</div>"
    if s=="live": return "<div class='status-badge blink' style='background:#b7ffba;color:#035c00;'>LIVE</div>"
    if s=="soon": return "<div class='status-badge' style='background:#dce8ff;color:#00347a;'>STARTING SOON</div>"
    return "<div class='status-badge' style='background:#e6e3ff;color:#2a2275;'>UPCOMING</div>"


# -----------------------------
# LOGIN UI
# -----------------------------
st.title("🎫 KnoWhere")

with st.expander("Login (Admin/User)", expanded=True):

    role = st.radio("Login as:",["Guest","User","Admin"],index=0)

    if role=="Guest":
        if st.button("Continue as Guest"):
            st.session_state.logged_in=True
            st.session_state.role="guest"
            st.success("Continuing as Guest")

    else:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")

        if st.button("Login"):

            if role=="Admin":
                if u in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[u]==p:
                    st.session_state.logged_in=True
                    st.session_state.role="admin"
                    st.success("Logged in as Admin")
                else: st.error("Invalid admin credentials")

            elif role=="User":
                st.session_state.logged_in=True
                st.session_state.role="user"
                st.success(f"Logged in as {u}")

if not st.session_state.logged_in:
    st.stop()


# -----------------------------
# ADMIN PANEL
# -----------------------------
if st.session_state.role=="admin":
    
    st.header("Admin Panel — Add Event")

    with st.form("add"):

        c1,c2=st.columns(2)

        with c1:
            t=st.text_input("Event Title")
            cat=st.selectbox("Category",["Conference","Workshop","Meetup","Concert","Other"])
            d=st.date_input("Date",value=date.today())
            tm=st.time_input("Time",value=time(18))
            loc=st.text_input("Location")

        with c2:
            price=st.number_input("Price",min_value=0.0,step=50.0)
            cap=st.number_input("Capacity",min_value=1)
            hours=st.number_input("How many hours event will run?",min_value=1.0,step=1.0)
            img=st.file_uploader("Image",type=["png","jpg","jpeg"])

        desc=st.text_area("Description")

        submit=st.form_submit_button("Add Event")

        if submit:
            eid=int(datetime.now().timestamp()*1000)
            encoded=""

            if img:
                ext=os.path.splitext(img.name)[1]
                pth=os.path.join(UPLOAD_DIR,f"{eid}{ext}")
                open(pth,"wb").write(img.getbuffer())
                encoded=img64(pth)

            st.session_state.events.append({
                "id":eid,
                "title":t,
                "category":cat,
                "date":d.isoformat(),
                "time":tm.strftime("%H:%M"),
                "location":loc,
                "price":float(price),
                "capacity":int(cap),
                "hours":float(hours),
                "description":desc,
                "image":encoded
            })

            save_events(st.session_state.events)
            st.success("Event added successfully")


# -----------------------------
# FILTER SIDEBAR + STATUS FILTER
# -----------------------------
all_events = st.session_state.events
st.header("Browse Events")

st.sidebar.header("Filters")

q = st.sidebar.text_input("Search")

categories = sorted(list({e.get("category", "") for e in all_events}))
cat_filter = st.sidebar.selectbox("Category", ["All"] + categories)

locations = sorted(list({e.get("location", "") for e in all_events}))
loc_filter = st.sidebar.selectbox("Location", ["All"] + locations)

# NEW STATUS FILTER
status_opts=["live","soon","upcoming","past"]
status_filter = st.sidebar.multiselect("Status",status_opts)

min_price = 0
max_price = max([e["price"] for e in all_events]) if all_events else 100
price_range = st.sidebar.slider("Price Range", min_price, int(max_price) + 50, (min_price, int(max_price)))

filtered=[]
for e in all_events:
    s=compute_status(e)
    if q and q.lower() not in e["title"].lower(): continue
    if cat_filter != "All" and e["category"] != cat_filter: continue
    if loc_filter != "All" and e["location"] != loc_filter: continue
    if status_filter and s not in status_filter: continue
    if not(price_range[0] <= e["price"] <= price_range[1]): continue
    filtered.append(e)

# reorder
filtered.sort(key=lambda x:({"live":0,"soon":1,"upcoming":2,"past":3}.get(compute_status(x),9)))


# -----------------------------
# RENDER CARDS
# -----------------------------
def render(events):

    html="""
    <style>
    .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px;}
    .card{border-radius:12px;padding:12px;background:white;box-shadow:0 2px 6px rgba(0,0,0,0.15);position:relative;}
    img{width:100%;height:170px;object-fit:contain;border-radius:8px;margin-bottom:8px;}
    .status-badge{position:absolute;top:6px;right:6px;padding:4px 8px;border-radius:6px;font-size:12px;font-weight:700;}
    .blink{animation:blinkAnim 1s infinite;}
    @keyframes blinkAnim{50%{opacity:.2}}
    </style>
    <div class='grid'>
    """

    for e in events:
        s=compute_status(e)
        html += f"""
        <div class='card'>
            {status_badge(s)}
            {'<img src="'+e['image']+'"/>' if e['image'] else ''}
            <b>{e['title']}</b><br>
            {e['category']}<br>
            {e['location']}<br>
            {e['date']} {e['time']}</br>
            <b>{'Free' if e['price']==0 else '₹'+str(int(e['price']))}</b>
        </div>
        """

    html+="</div>"

    components.html(html,height=650,scrolling=True)

render(filtered)
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from database import init_db, get_connection
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta

init_db()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth config
SECRET_KEY = "changethiskey"  # change this to something random!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Models
class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class Task(BaseModel):
    id: Optional[int] = None
    title: str
    description: Optional[str] = None
    deadline: Optional[str] = None
    priority: Optional[int] = 0
    completed: Optional[bool] = False

# Helper functions
def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        userid: int = payload.get("userid")
        if userid is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return userid
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Auth endpoints
@app.post("/register")
def register(user: UserRegister):
    conn = get_connection()
    existing = conn.execute(
        "SELECT * FROM users WHERE username = ? OR email = ?",
        (user.username, user.email)
    ).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Username or email already taken")
    hashed = hash_password(user.password)
    conn.execute(
        "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
        (user.username, user.email, hashed)
    )
    conn.commit()
    conn.close()
    return {"message": "User created successfully"}

@app.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = get_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (form_data.username,)
    ).fetchone()
    conn.close()
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    token = create_access_token({"userid": user["userid"]})
    return {"access_token": token, "token_type": "bearer"}

# Task endpoints (now protected with login)
@app.post("/tasks", response_model=Task)
def create_task(task: Task, userid: int = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO todo (userid, name, description, deadline, priority, completed) VALUES (?, ?, ?, ?, ?, ?)",
        (userid, task.title, task.description, task.deadline, task.priority, task.completed)
    )
    conn.commit()
    task.id = cursor.lastrowid
    conn.close()
    return task

@app.get("/tasks")
def get_tasks(userid: int = Depends(get_current_user)):
    conn = get_connection()
    tasks = conn.execute(
        "SELECT * FROM todo WHERE userid = ?", (userid,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in tasks]

@app.get("/tasks/{task_id}")
def get_task(task_id: int, userid: int = Depends(get_current_user)):
    conn = get_connection()
    task = conn.execute(
        "SELECT * FROM todo WHERE todoid = ? AND userid = ?", (task_id, userid)
    ).fetchone()
    conn.close()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return dict(task)

@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, userid: int = Depends(get_current_user)):
    conn = get_connection()
    result = conn.execute(
        "DELETE FROM todo WHERE todoid = ? AND userid = ?", (task_id, userid)
    )
    conn.commit()
    conn.close()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Task not found")

@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, task: Task, userid: int = Depends(get_current_user)):
    conn = get_connection()
    result = conn.execute(
        "UPDATE todo SET name = ?, description = ?, deadline = ?, priority = ?, completed = ? WHERE todoid = ? AND userid = ?",
        (task.title, task.description, task.deadline, task.priority, task.completed, task_id, userid)
    )
    conn.commit()
    conn.close()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    task.id = task_id
    return task

class Event(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    start_time: str
    end_time: Optional[str] = None
    event_type: Optional[str] = "personal"

@app.post("/events")
def create_event(event: Event, userid: int = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO calendar (userid, name, description, start_time, end_time, event_type) VALUES (?, ?, ?, ?, ?, ?)",
        (userid, event.name, event.description, event.start_time, event.end_time, event.event_type)
    )
    conn.commit()
    event.id = cursor.lastrowid
    conn.close()
    return event

@app.get("/events")
def get_events(userid: int = Depends(get_current_user)):
    conn = get_connection()
    events = conn.execute(
        "SELECT * FROM calendar WHERE userid = ?", (userid,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in events]

@app.get("/events/{event_id}")
def get_event(event_id: int, userid: int = Depends(get_current_user)):
    conn = get_connection()
    event = conn.execute(
        "SELECT * FROM calendar WHERE eventid = ? AND userid = ?", (event_id, userid)
    ).fetchone()
    conn.close()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return dict(event)

@app.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: int, userid: int = Depends(get_current_user)):
    conn = get_connection()
    result = conn.execute(
        "DELETE FROM calendar WHERE eventid = ? AND userid = ?", (event_id, userid)
    )
    conn.commit()
    conn.close()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Event not found")

@app.put("/events/{event_id}")
def update_event(event_id: int, event: Event, userid: int = Depends(get_current_user)):
    conn = get_connection()
    result = conn.execute(
        "UPDATE calendar SET name = ?, description = ?, start_time = ?, end_time = ?, event_type = ? WHERE eventid = ? AND userid = ?",
        (event.name, event.description, event.start_time, event.end_time, event.event_type, event_id, userid)
    )
    conn.commit()
    conn.close()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    event.id = event_id
    return event
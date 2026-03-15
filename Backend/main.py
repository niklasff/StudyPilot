from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from database import init_db, get_connection

init_db()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Task(BaseModel):
    id: Optional[int] = None
    title: str
    description: Optional[str] = None
    deadline: Optional[str] = None

@app.post("/tasks", response_model=Task)
def create_task(task: Task):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO todo (name, description, deadline) VALUES (?, ?, ?)",
        (task.title, task.description, task.deadline)
    )
    conn.commit()
    task.id = cursor.lastrowid
    conn.close()
    return task

@app.get("/tasks")
def get_tasks():
    conn = get_connection()
    tasks = conn.execute("SELECT * FROM todo").fetchall()
    conn.close()
    return [dict(row) for row in tasks]

@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    conn = get_connection()
    task = conn.execute("SELECT * FROM todo WHERE todoid = ?", (task_id,)).fetchone()
    conn.close()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return dict(task)

@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int):
    conn = get_connection()
    result = conn.execute("DELETE FROM todo WHERE todoid = ?", (task_id,))
    conn.commit()
    conn.close()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Task not found")

@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, task: Task):
    conn = get_connection()
    result = conn.execute(
        "UPDATE todo SET name = ?, description = ?, deadline = ? WHERE todoid = ?",
        (task.title, task.description, task.deadline, task_id)
    )
    conn.commit()
    conn.close()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    task.id = task_id
    return task
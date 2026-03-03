
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# "Tietokanta" muistissa
# - tasks: listaa kaikki Task-oliot
# - next_id: juokseva tunniste uusille tehtäville
tasks: List["Task"] = []
next_id = 1

class Task(BaseModel):
    """
    Pydantic-malli, joka kuvaa yksittäisen tehtävän (task).
    - id: asetetaan automaattisesti luontivaiheessa
    - title: tehtävän otsikko
    - deadline: määräpäivä (tässä pidetään stringinä; voisi olla myös date)
    """
    id: Optional[int] = None     # annetaan automaattisesti
    title: str
    deadline: str

@app.post("/tasks", response_model=Task)
def create_task(task: Task):
    """
    Luo uuden tehtävän.
    - Ottaa vastaan JSON-runkoon muotoillun Taskin (ilman id:tä).
    - Asettaa automaattisen id:n ja tallettaa listaan.
    - Palauttaa luodun tehtävän (näkyy Swaggerissa ja frontissa).
    """
    global next_id
    task.id = next_id           # annetaan juokseva tunniste
    next_id += 1
    tasks.append(task)          # talletetaan "muistissa olevaan tietokantaan"
    return task                 # FastAPI muuntaa tämän JSONiksi automaattisesti

@app.get("/tasks", response_model=List[Task])
def get_tasks():
    """
    Palauttaa kaikki tehtävät listana.
    Frontend kutsuu tätä päivittääkseen näkymän.
    """
    return tasks

@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int):
    
    #Poistaa tehtävän id:n perusteella.
    #Jos löytyy: poistetaan ja palautetaan 204 No Content (ei vastausrunkkoa).
    #Jos ei löydy: nostetaan 404-virhe.
    
    for idx, t in enumerate(tasks):
        if t.id == task_id:
            tasks.pop(idx)
            return               # 204 No Content
    # Tähän päädytään vain, jos tehtävää ei löytynyt
    raise HTTPException(status_code=404, detail="Task not found")

# Vinkit: 
# - Aktivoi venv PowerShellissa: .\venv\Scripts\Activate.ps1
# - Käynnistä palvelin: uvicorn main:app --reload
# - Testaa: http://127.0.0.1:8000/docs

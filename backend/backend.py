from fastapi import FastAPI
from schema import Query, QueryResponse
from main import query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

 
@app.get("/chat", response_model=QueryResponse)
async def chat_get(question: str):
    ans = query(question)
    return {"answer": ans}  # wrap string in a dict

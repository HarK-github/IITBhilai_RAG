from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class Query(BaseModel):
    question:str 

class QueryResponse(BaseModel):
    answer: str 
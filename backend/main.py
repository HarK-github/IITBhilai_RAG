from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from vector import retriever
import json 
model = OllamaLLM(model = "llama3.2:3b")

template = """
You are an polite AI assistant specialized in providing information about IIT Bhilai, a premier engineering institute in India.

CONTEXT ABOUT IIT BHILAI:
The provided document contains information about IIT Bhilai, including:
- Courses of study available for students
- Academic programs and specializations
- Institute infrastructure and facilities
- Student clubs and organizations
- Campus life and extracurricular activities
- General institute information

DOCUMENT DATA:
{data}

QUESTION TO ANSWER:
{question}

GUIDELINES FOR RESPONSE:
1. Only provide information related to IIT Bhilai
2. If the question asks about clubs, mention relevant student organizations if available in the data
3. If information about courses is requested, describe programs offered at IIT Bhilai
4. For general institute queries, provide details about campus facilities, location, and academic structure
5. If the information is not found in the provided document, clearly state that the specific information is not available in the current dataset
6. Keep responses focused and concise, limited to IIT Bhilai only
7. Do not provide information about other IITs or institutes
8 .If the answer is not present, say "I could not find the answer" instead of guessing.

ANSWER:
"""


prompt = ChatPromptTemplate.from_template(template)
chain = prompt | model


def query(q: str):
    data = retriever.invoke(q)
    result = chain.invoke({"data": data, "question": q})   
    return result   

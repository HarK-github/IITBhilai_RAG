import os
import certifi
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ---------------------
# Load PDFs
# ---------------------
pdf_folder = "./"
pdf_files = [os.path.join(pdf_folder, f) for f in os.listdir(pdf_folder) if f.endswith(".pdf")]

all_docs = []
for file_path in pdf_files:
    loader = PyPDFLoader(file_path)
    docs = loader.load()
    all_docs.extend(docs)

# ---------------------
# Load web page
# ---------------------
wloader = WebBaseLoader(
    "https://www.iitbhilai.ac.in/",
    requests_kwargs={"verify": False}  
) 
all_docs.extend(wloader.load())

all_docs.extend(wloader.load())

# ---------------------
# Split documents into chunks
# ---------------------
def split_documents(documents: list[Document]):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=80,
        length_function=len,
        is_separator_regex=False
    )
    return text_splitter.split_documents(documents)

all_docs = split_documents(all_docs)

# ---------------------
# Create embeddings and Chroma vector store
# ---------------------
embedding = OllamaEmbeddings(model="mxbai-embed-large")

db_loc = "./chroma_langchain_db"
add_doc = not os.path.exists(db_loc)

vector_store = Chroma(
    collection_name="pdf_documents",
    persist_directory=db_loc,
    embedding_function=embedding
)

if add_doc:
    ids = [f"doc_{i}" for i in range(len(all_docs))]
    vector_store.add_documents(documents=all_docs, ids=ids)

retriever = vector_store.as_retriever(search_kwargs={"k": 10})

import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from pydantic import BaseModel
from contextlib import asynccontextmanager

# Langchain Imports
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.tools.retriever import create_retriever_tool
from langchain_community.tools.tavily_search import TavilySearchResults

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Allow CORS for frontend (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- GLOBAL VARIABLES ---
agent_executor = None
supabase: Client = None

# --- APPLICATION LIFESPAN (runs at startup) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent_executor, supabase

    # 1. Initialize Supabase client
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    supabase = create_client(supabase_url, supabase_key)
    print("Supabase client initialized.")

    # 2. Initialize the LLM
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    print("LLM initialized.")

    # 3. Load documents from the /docs directory
    loader = PyPDFDirectoryLoader("docs/")
    docs = loader.load()
    print(f"Loaded {len(docs)} PDF documents.")

    # 4. Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)
    print(f"Split documents into {len(splits)} chunks.")

    # 5. Create embeddings and vector store (FAISS)
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(documents=splits, embedding=embeddings)
    print("FAISS vector store created.")

    # 6. Create a retriever tool for the documents
    retriever = vectorstore.as_retriever()
    retriever_tool = create_retriever_tool(
        retriever,
        "financial_document_search",
        "Search for information about financial planning, client data, and investment strategies. Use this tool to answer questions about financial reports and client-specific information found in the documents.",
    )
    print("Retriever tool created.")

    # 7. Create the Tavily web search tool
    tavily_tool = TavilySearchResults(max_results=3)
    tavily_tool.name = "web_search"
    tavily_tool.description = "Search the public web for financial news, market data, and general economic information. Use this for topics not covered in the local financial documents."
    print("Tavily tool created.")

    # 8. Define the tool list for the agent
    tools = [retriever_tool, tavily_tool]

    # 9. Create the Agent Prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful financial assistant. Your goal is to provide accurate information to financial advisors based on the provided documents and web search. When asked about a client, first use the financial_document_search tool to find their information."),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # 10. Create the Agent
    agent = create_openai_functions_agent(llm, tools, prompt)
    print("Agent created.")

    # 11. Create the Agent Executor
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    print("Agent Executor created. Backend is ready.")

    yield

    # --- Code to run on shutdown (if any) ---

# --- API SETUP ---
class ChatRequest(BaseModel):
    message: str

class ProposalRequest(BaseModel):
    name: str
    age: int
    income: float
    risk_tolerance: str
    financial_goals: str

@app.get("/")
def read_root():
    return {"message": "Welcome to the Financial Proposal Generator API"}

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    if not agent_executor:
        return {"error": "Agent not initialized. Please check server logs."}
    response = await agent_executor.ainvoke({"input": request.message})
    return {"response": response["output"]}

@app.post("/api/proposal")
async def proposal_endpoint(request: ProposalRequest):
    # Simple template for demonstration; replace with LLM/agent logic as needed
    proposal = (
        f"Proposal for {request.name} (Age: {request.age}):\n"
        f"Income: ${request.income}\n"
        f"Risk Tolerance: {request.risk_tolerance}\n"
        f"Financial Goals: {request.financial_goals}\n"
        "Recommended portfolio: ... (LLM/agent output here)"
    )
    return {"proposal": proposal}

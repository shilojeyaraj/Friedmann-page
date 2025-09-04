import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager

# Supabase will be imported conditionally when needed
SUPABASE_AVAILABLE = False
create_client = None
Client = None

# Google Gemini Import
import google.generativeai as genai

# Load environment variables (with error handling)
try:
    load_dotenv()
except Exception as e:
    print(f"Warning: Could not load .env file: {e}")
    print("Continuing without .env file...")

app = FastAPI(title="Financial Assistant API", version="1.0.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
gemini_model = None
supabase = None

# --- PYDANTIC MODELS ---
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    citations: Optional[List[Dict[str, str]]] = []

class ChatRequest(BaseModel):
    chat: Dict[str, List[ChatMessage]]
    conversation_id: Optional[str] = None

class ClientData(BaseModel):
    name: str
    age: Optional[int] = None
    income: Optional[float] = None
    risk_tolerance: Optional[str] = None
    financial_goals: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = {}

class StreamedMessage(BaseModel):
    type: str = "message"
    message: ChatMessage

class StreamedLoading(BaseModel):
    type: str = "loading"
    indicator: Dict[str, str]

class StreamedDone(BaseModel):
    type: str = "done"

class StreamedError(BaseModel):
    type: str = "error"
    indicator: Dict[str, str]

class FinancialReport(BaseModel):
    id: str
    client_name: str
    report_content: str
    created_at: str
    conversation_id: str

class ReportRequest(BaseModel):
    client_name: str
    conversation_id: str
    report_type: str = "comprehensive"

# --- DATABASE OPERATIONS ---
async def save_conversation(conversation_id: str, messages: List[ChatMessage]):
    """Save conversation to Supabase"""
    if not SUPABASE_AVAILABLE or not supabase:
        print("Database not available - skipping conversation save")
        return None
        
    try:
        conversation_data = {
            "id": conversation_id,
            "messages": [msg.dict() for msg in messages],
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("conversations").upsert(conversation_data).execute()
        return result
    except Exception as e:
        print(f"Error saving conversation: {e}")
        return None

async def save_client_data(client_data: ClientData, conversation_id: str):
    """Save client data extracted from conversation"""
    if not SUPABASE_AVAILABLE or not supabase:
        print("Database not available - skipping client data save")
        return None
        
    try:
        data = client_data.dict()
        data["conversation_id"] = conversation_id
        data["created_at"] = datetime.utcnow().isoformat()
        data["updated_at"] = datetime.utcnow().isoformat()
        
        result = supabase.table("clients").upsert(data).execute()
        return result
    except Exception as e:
        print(f"Error saving client data: {e}")
        return None

async def get_client_data(client_name: str) -> Optional[Dict]:
    """Retrieve client data by name"""
    if not SUPABASE_AVAILABLE or not supabase:
        print("Database not available - returning None for client data")
        return None
        
    try:
        result = supabase.table("clients").select("*").ilike("name", f"%{client_name}%").execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"Error retrieving client data: {e}")
        return None

async def save_financial_report(report: FinancialReport):
    """Save financial report to database"""
    if not SUPABASE_AVAILABLE or not supabase:
        print("Database not available - skipping report save")
        return None
        
    try:
        report_data = report.dict()
        result = supabase.table("financial_reports").upsert(report_data).execute()
        return result
    except Exception as e:
        print(f"Error saving financial report: {e}")
        return None

async def get_financial_report(report_id: str) -> Optional[Dict]:
    """Retrieve financial report by ID"""
    if not SUPABASE_AVAILABLE or not supabase:
        print("Database not available - returning None for report")
        return None
        
    try:
        result = supabase.table("financial_reports").select("*").eq("id", report_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"Error retrieving financial report: {e}")
        return None

# --- HELPER FUNCTIONS ---
async def get_gemini_response(messages: List[Dict[str, str]], system_prompt: str = None) -> str:
    """Get response from Google Gemini API"""
    try:
        if not gemini_model:
            return "Gemini model not initialized. Please check your API key."
        
        # Prepare the conversation for Gemini
        conversation_text = ""
        
        if system_prompt:
            conversation_text += f"System: {system_prompt}\n\n"
        
        # Add conversation history
        for msg in messages:
            role = "Human" if msg["role"] == "user" else "Assistant"
            conversation_text += f"{role}: {msg['content']}\n\n"
        
        # Generate response using Gemini
        response = gemini_model.generate_content(conversation_text)
        
        return response.text
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return f"I apologize, but I encountered an error processing your request: {str(e)}"

# --- APPLICATION LIFESPAN ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global gemini_model, supabase
    
    # Initialize Google Gemini
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        print("⚠️ GOOGLE_API_KEY not found in environment variables")
        gemini_model = None
    else:
        try:
            genai.configure(api_key=google_api_key)
            gemini_model = genai.GenerativeModel('gemini-1.5-flash')
            print("✅ Google Gemini client initialized")
        except Exception as e:
            print(f"⚠️ Error initializing Gemini: {e}")
            gemini_model = None
    
    # Initialize Supabase (optional - can work without it)
    global SUPABASE_AVAILABLE, create_client, Client
    try:
        from supabase import create_client, Client
        SUPABASE_AVAILABLE = True
        print("✅ Supabase library loaded")
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        if supabase_url and supabase_key:
            try:
                supabase = create_client(supabase_url, supabase_key)
                print("✅ Supabase client initialized")
                # Create database tables if they don't exist
                await create_database_tables()
            except Exception as e:
                print(f"⚠️ Error initializing Supabase: {e}")
                supabase = None
        else:
            print("⚠️ Supabase credentials not found - running without database")
            supabase = None
    except ImportError as e:
        print(f"⚠️ Supabase not available: {e}")
        print("Running without database features")
        SUPABASE_AVAILABLE = False
        supabase = None
    except Exception as e:
        print(f"⚠️ Error loading Supabase: {e}")
        SUPABASE_AVAILABLE = False
        supabase = None
    
    print("✅ Financial Assistant ready")
    
    yield
    
    # Cleanup (if needed)
    print("🔄 Shutting down...")

async def create_database_tables():
    """Create necessary database tables"""
    if not SUPABASE_AVAILABLE or not supabase:
        print("Database not available - skipping table creation")
        return
        
    try:
        # Create conversations table
        conversations_table = """
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            messages JSONB NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
        
        # Create clients table
        clients_table = """
        CREATE TABLE IF NOT EXISTS clients (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER,
            income DECIMAL(12,2),
            risk_tolerance TEXT,
            financial_goals TEXT,
            additional_info JSONB,
            conversation_id TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
        
        # Create financial reports table
        reports_table = """
        CREATE TABLE IF NOT EXISTS financial_reports (
            id TEXT PRIMARY KEY,
            client_name TEXT NOT NULL,
            report_content TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            conversation_id TEXT
        );
        """
        
        print("✅ Database tables ready")
        
    except Exception as e:
        print(f"⚠️ Database table creation error: {e}")

# --- STREAMING UTILITIES ---
async def stream_response(content: str, citations: List[Dict] = None):
    """Stream response in the format expected by the frontend"""
    citations = citations or []
    
    # Stream loading indicator
    loading_data = StreamedLoading(indicator={"status": "Generating response", "icon": "thinking"})
    yield f"{json.dumps(loading_data.dict())}\n"
    
    # Stream the actual message
    message_data = StreamedMessage(message=ChatMessage(role="assistant", content=content, citations=citations))
    yield f"{json.dumps(message_data.dict())}\n"
    
    # Stream done indicator
    done_data = StreamedDone()
    yield f"{json.dumps(done_data.dict())}\n"

# --- API ENDPOINTS ---
app.lifespan = lifespan

@app.get("/")
def read_root():
    return {"message": "Financial Assistant API Ready", "version": "1.0.0"}

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest, background_tasks: BackgroundTasks):
    """Main chat endpoint that matches the frontend expectations"""
    if not gemini_model:
        raise HTTPException(status_code=500, detail="Gemini model not initialized")
    
    try:
        messages = request.chat.get("messages", [])
        if not messages:
            raise HTTPException(status_code=400, detail="No messages provided")
        
        # Get the latest user message
        latest_message = messages[-1]
        user_input = latest_message.content
        
        # Generate conversation ID if not provided
        conversation_id = request.conversation_id or str(uuid.uuid4())
        
        # Convert messages to OpenAI format
        chat_history = []
        for msg in messages[:-1]:  # Exclude the latest message
            chat_history.append({"role": msg.role, "content": msg.content})
        
        # Define streaming function
        async def generate_stream():
            try:
                # Stream loading indicators
                yield f"{json.dumps({'type': 'loading', 'indicator': {'status': 'Analyzing your request...', 'icon': 'thinking'}})}\n"
                
                # System prompt for financial assistant
                system_prompt = """You are a sophisticated financial assistant with expertise in:

FINANCIAL PLANNING:
- Investment strategies and portfolio management
- Retirement planning and 401(k) optimization
- Tax planning and optimization strategies
- Insurance needs analysis
- Estate planning basics
- Debt management and consolidation
- Budgeting and cash flow management

CLIENT INTERACTION:
- Ask clarifying questions to gather complete financial information
- Provide personalized, actionable advice based on client's situation
- Explain complex financial concepts in simple terms
- Always consider risk tolerance and time horizon
- Maintain client confidentiality and professionalism

RESPONSE STYLE:
- Be comprehensive but concise
- Provide specific, actionable recommendations
- Include relevant examples when helpful
- Ask follow-up questions to gather missing information
- Always prioritize client's best interests

When users request financial plans or reports, gather all necessary information and create comprehensive, professional recommendations."""

                # Get Gemini response
                response_content = await get_gemini_response(chat_history, system_prompt)
                
                # Extract client data in background if detected
                if any(keyword in user_input.lower() for keyword in ["client", "customer", "age", "income", "risk tolerance", "goals"]):
                    background_tasks.add_task(extract_and_save_client_data, user_input, conversation_id)
                
                # Stream the response
                citations = []  # No citations needed for direct OpenAI responses
                async for chunk in stream_response(response_content, citations):
                    yield chunk
                
                # Save conversation in background if database is available
                if SUPABASE_AVAILABLE and supabase:
                    all_messages = messages + [ChatMessage(role="assistant", content=response_content, citations=citations)]
                    background_tasks.add_task(save_conversation, conversation_id, all_messages)
                
            except Exception as e:
                print(f"Error in generate_stream: {e}")
                error_data = StreamedError(indicator={"status": f"Error: {str(e)}", "icon": "error"})
                yield f"{json.dumps(error_data.dict())}\n"
        
        return StreamingResponse(generate_stream(), media_type="text/plain")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@app.post("/api/clients")
async def create_client(client_data: ClientData):
    """Create or update client data"""
    try:
        conversation_id = str(uuid.uuid4())
        result = await save_client_data(client_data, conversation_id)
        
        if result:
            return {"message": "Client data saved successfully", "client_id": result.data[0]["id"]}
        else:
            raise HTTPException(status_code=500, detail="Failed to save client data")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating client: {str(e)}")

@app.get("/api/clients/{client_name}")
async def get_client(client_name: str):
    """Get client data by name"""
    try:
        client_data = await get_client_data(client_name)
        
        if client_data:
            return {"client": client_data}
        else:
            raise HTTPException(status_code=404, detail="Client not found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving client: {str(e)}")

@app.post("/api/generate-report")
async def generate_financial_report(request: ReportRequest):
    """Generate a comprehensive financial report for a client"""
    if not gemini_model:
        raise HTTPException(status_code=500, detail="Gemini model not initialized")
    
    try:
        # Get client data if available
        client_data = None
        if SUPABASE_AVAILABLE and supabase:
            client_data = await get_client_data(request.client_name)
        
        # Create a comprehensive prompt for report generation
        report_prompt = f"""
        Generate a comprehensive financial report for {request.client_name}.
        
        Client Information:
        {client_data if client_data else "No specific client data available - create a general comprehensive financial plan template"}
        
        Report Type: {request.report_type}
        
        Please create a detailed financial plan including:
        1. Executive Summary
        2. Current Financial Situation Analysis
        3. Risk Assessment and Tolerance Evaluation
        4. Investment Strategy and Portfolio Recommendations
        5. Retirement Planning and Timeline
        6. Tax Optimization Strategies
        7. Insurance Needs Analysis
        8. Estate Planning Considerations
        9. Debt Management Strategy
        10. Action Items and Implementation Timeline
        11. Monitoring and Review Schedule
        
        Make this report professional, comprehensive, and actionable. Include specific recommendations, percentages, and timelines where appropriate. Use clear headings and formatting for easy reading.
        """
        
        # Generate the report using Gemini directly
        messages = [{"role": "user", "content": report_prompt}]
        response_content = await get_gemini_response(messages)
        
        # Create report object
        report_id = str(uuid.uuid4())
        report = FinancialReport(
            id=report_id,
            client_name=request.client_name,
            report_content=response_content,
            created_at=datetime.utcnow().isoformat(),
            conversation_id=request.conversation_id
        )
        
        # Save the report if database is available
        if SUPABASE_AVAILABLE and supabase:
            await save_financial_report(report)
        
        # Return the report with a URL
        report_url = f"/api/reports/{report_id}"
        
        return {
            "message": "Financial report generated successfully",
            "report_id": report_id,
            "report_url": report_url,
            "client_name": request.client_name
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")

@app.get("/api/reports/{report_id}")
async def get_financial_report_endpoint(report_id: str):
    """Get a financial report by ID"""
    try:
        if SUPABASE_AVAILABLE and supabase:
            report = await get_financial_report(report_id)
            if report:
                return {"report": report}
            else:
                raise HTTPException(status_code=404, detail="Report not found")
        else:
            # If no database, return a message indicating reports are not persisted
            raise HTTPException(status_code=404, detail="Report not found - database not configured")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving report: {str(e)}")

# --- BACKGROUND TASKS ---
async def extract_and_save_client_data(message: str, conversation_id: str):
    """Background task to extract and save client data from messages"""
    try:
        if not SUPABASE_AVAILABLE or not supabase:
            print("Database not available - skipping client data extraction")
            return
            
        # This is where you'd implement NLP to extract client information
        # For now, this is a placeholder that logs the attempt
        print(f"Extracting client data from message: {message[:100]}...")
        
        # You could use Gemini to extract structured data:
        # extraction_prompt = "Extract client information from this message: {message}"
        # extracted_data = await get_gemini_response([{"role": "user", "content": extraction_prompt}])
        
        # For demonstration, we'll just log it
        print(f"Client data extraction completed for conversation: {conversation_id}")
        
    except Exception as e:
        print(f"Error in background client data extraction: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
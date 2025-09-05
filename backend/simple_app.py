import os
import json
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import openai
from dotenv import load_dotenv

# LangChain imports
from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.schema import HumanMessage, AIMessage
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import ConversationChain
from langchain.prompts import PromptTemplate

# Supabase integration
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("⚠️ Supabase not available - install with: pip install supabase")

# Email service imports
import secrets
import string
from email_service import email_service

# Load environment variables
try:
    load_dotenv()
    print("✅ Environment variables loaded")
except Exception as e:
    print(f"⚠️ Could not load .env file: {e}")

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001"])

# Initialize SocketIO for real-time communication
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001"])  # Enable CORS for frontend ports

# Initialize OpenAI
openai_model = None
openai_api_key = os.getenv("OPENAI_API_KEY")

if openai_api_key and openai_api_key != "your_openai_api_key_here":
    try:
        openai.api_key = openai_api_key
        openai_model = "gpt-4o-mini"
        print("✅ OpenAI initialized successfully")
    except Exception as e:
        print(f"⚠️ Error initializing OpenAI: {e}")
        openai_model = None
else:
    print("⚠️ OPENAI_API_KEY not found or not set properly")
    print(f"Current key: {openai_api_key[:10] + '...' if openai_api_key else 'None'}")

# Initialize Supabase
supabase = None
if SUPABASE_AVAILABLE:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if supabase_url and supabase_key:
        try:
            supabase = create_client(supabase_url, supabase_key)
            print("✅ Supabase initialized successfully")
        except Exception as e:
            print(f"⚠️ Error initializing Supabase: {e}")
            supabase = None
    else:
        print("⚠️ SUPABASE_URL or SUPABASE_KEY not found in environment variables")
else:
    print("⚠️ Supabase not available - using in-memory storage only")

# In-memory storage for reports (simple solution)
reports = {}

# Store conversation preferences for report customization
conversation_preferences = {}

# Store report format templates
report_templates = {
    "default": {
        "sections": [
            "EXECUTIVE SUMMARY",
            "FINANCIAL HEALTH ASSESSMENT", 
            "RECOMMENDED INVESTMENT STRATEGY",
            "RISK ANALYSIS",
            "RETIREMENT PLANNING",
            "TAX OPTIMIZATION OPPORTUNITIES",
            "ACTION ITEMS AND NEXT STEPS"
        ],
        "order": [1, 2, 3, 4, 5, 6, 7]
    },
    "retirement_focused": {
        "sections": [
            "RETIREMENT PLANNING",
            "EXECUTIVE SUMMARY",
            "FINANCIAL HEALTH ASSESSMENT",
            "RECOMMENDED INVESTMENT STRATEGY", 
            "TAX OPTIMIZATION OPPORTUNITIES",
            "RISK ANALYSIS",
            "ACTION ITEMS AND NEXT STEPS"
        ],
        "order": [1, 2, 3, 4, 5, 6, 7]
    },
    "tax_focused": {
        "sections": [
            "TAX OPTIMIZATION OPPORTUNITIES",
            "EXECUTIVE SUMMARY",
            "FINANCIAL HEALTH ASSESSMENT",
            "RECOMMENDED INVESTMENT STRATEGY",
            "RETIREMENT PLANNING",
            "RISK ANALYSIS", 
            "ACTION ITEMS AND NEXT STEPS"
        ],
        "order": [1, 2, 3, 4, 5, 6, 7]
    }
}

# Store conversation history for each session
conversation_history = {}

# Store active WebSocket connections
active_connections = {}

# LangChain Memory System
class ConversationMemoryManager:
    def __init__(self):
        # Initialize embeddings for vector storage using OpenAI
        try:
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=os.getenv('OPENAI_API_KEY')
            )
            self.vectorstore = Chroma(
                collection_name="conversation_history",
                embedding_function=self.embeddings,
                persist_directory="./chroma_db"
            )
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            print("✅ LangChain vector storage initialized with Google Gemini embeddings")
        except Exception as e:
            print(f"⚠️ LangChain vector storage not available: {e}")
            self.vectorstore = None
            self.embeddings = None
        
        # In-memory conversation storage
        self.conversation_memories = {}
        self.conversation_summaries = {}
    
    def get_or_create_memory(self, conversation_id):
        """Get or create a conversation memory for a specific conversation"""
        if conversation_id not in self.conversation_memories:
            self.conversation_memories[conversation_id] = ConversationBufferMemory(
                return_messages=True,
                memory_key="chat_history"
            )
        return self.conversation_memories[conversation_id]
    
    def add_message(self, conversation_id, role, message):
        """Add a single message to the conversation memory"""
        print(f"💾 Adding message to memory - conversation_id: {conversation_id}, role: {role}, message: {message[:50]}...")
        memory = self.get_or_create_memory(conversation_id)
        
        if role == "user":
            # For user messages, we need to store them temporarily until we get the AI response
            if not hasattr(self, 'pending_user_messages'):
                self.pending_user_messages = {}
            self.pending_user_messages[conversation_id] = message
            print(f"💾 Stored user message temporarily for conversation {conversation_id}")
        elif role == "assistant":
            # For assistant messages, we can now save the context with the pending user message
            if hasattr(self, 'pending_user_messages') and conversation_id in self.pending_user_messages:
                user_message = self.pending_user_messages[conversation_id]
                memory.save_context(
                    {"input": user_message},
                    {"output": message}
                )
                print(f"💾 Saved conversation context for {conversation_id}: user='{user_message[:30]}...', assistant='{message[:30]}...'")
                del self.pending_user_messages[conversation_id]
            else:
                print(f"⚠️ No pending user message found for conversation {conversation_id}")
        
        # Also store in vector database if available
        if self.vectorstore:
            try:
                # Create a combined message for vector storage
                combined_text = f"Human: {human_message}\nAI: {ai_message}"
                chunks = self.text_splitter.split_text(combined_text)
                
                # Add metadata
                metadatas = [{
                    "conversation_id": conversation_id,
                    "timestamp": datetime.now().isoformat(),
                    "type": "conversation"
                }] * len(chunks)
                
                self.vectorstore.add_texts(
                    texts=chunks,
                    metadatas=metadatas
                )
            except Exception as e:
                print(f"⚠️ Error adding to vector store: {e}")
    
    def get_conversation_history(self, conversation_id, limit=10):
        """Get recent conversation history"""
        memory = self.get_or_create_memory(conversation_id)
        return memory.chat_memory.messages[-limit:] if memory.chat_memory.messages else []
    
    def search_conversations(self, query, conversation_id=None, limit=5):
        """Search through conversation history using semantic search"""
        if not self.vectorstore:
            return []
        
        try:
            # Filter by conversation_id if provided
            filter_dict = {"conversation_id": conversation_id} if conversation_id else None
            
            results = self.vectorstore.similarity_search(
                query=query,
                k=limit,
                filter=filter_dict
            )
            return results
        except Exception as e:
            print(f"⚠️ Error searching conversations: {e}")
            return []
    
    def get_conversation_summary(self, conversation_id):
        """Get or create a summary of the conversation"""
        if conversation_id not in self.conversation_summaries:
            messages = self.get_conversation_history(conversation_id)
            if messages:
                # Create a simple summary from recent messages
                recent_messages = messages[-6:]  # Last 6 messages
                summary_parts = []
                for msg in recent_messages:
                    if hasattr(msg, 'content'):
                        summary_parts.append(f"{type(msg).__name__}: {msg.content[:100]}...")
                
                self.conversation_summaries[conversation_id] = "\n".join(summary_parts)
            else:
                self.conversation_summaries[conversation_id] = "No conversation history yet."
        
        return self.conversation_summaries[conversation_id]

# Initialize the memory manager
memory_manager = ConversationMemoryManager()

# =============================================
# AUTHENTICATION HELPER FUNCTIONS
# =============================================

def generate_passcode(length=6):
    """Generate a secure passcode"""
    return ''.join(secrets.choice(string.digits) for _ in range(length))

def send_passcode_email(email, passcode):
    """Send passcode via email using the email service"""
    return email_service.send_passcode_email(email, passcode)

def is_client_authorized(email):
    """Check if email is in the authorized clients list"""
    if not supabase:
        print("⚠️ Supabase not available")
        return False
    
    try:
        result = supabase.table('clients').select('*').eq('email', email).eq('is_active', True).execute()
        return len(result.data) > 0
    except Exception as e:
        print(f"❌ Error checking client authorization: {e}")
        return False

def store_auth_token(email, token, expires_at, ip_address=None, user_agent=None):
    """Store authorization token in database"""
    if not supabase:
        return False
    
    try:
        result = supabase.table('authorization_tokens').insert({
            'email': email,
            'token': token,
            'expires_at': expires_at.isoformat(),
            'ip_address': ip_address,
            'user_agent': user_agent
        }).execute()
        return True
    except Exception as e:
        print(f"❌ Error storing auth token: {e}")
        return False

def verify_auth_token(email, token):
    """Verify authorization token"""
    if not supabase:
        return False
    
    try:
        from datetime import datetime
        now = datetime.now()
        
        result = supabase.table('authorization_tokens').select('*').eq('email', email).eq('token', token).eq('used', False).execute()
        
        if not result.data:
            return False
        
        token_data = result.data[0]
        expires_at = datetime.fromisoformat(token_data['expires_at'].replace('Z', '+00:00'))
        
        if now > expires_at:
            return False
        
        # Mark token as used
        supabase.table('authorization_tokens').update({'used': True}).eq('id', token_data['id']).execute()
        
        return True
    except Exception as e:
        print(f"❌ Error verifying auth token: {e}")
        return False

def create_client_session(email):
    """Create a new client session"""
    if not supabase:
        return None
    
    try:
        from datetime import datetime, timedelta
        import secrets
        
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=24)  # 24 hour session
        
        result = supabase.table('client_sessions').insert({
            'email': email,
            'session_token': session_token,
            'expires_at': expires_at.isoformat()
        }).execute()
        
        return session_token
    except Exception as e:
        print(f"❌ Error creating client session: {e}")
        return None

def verify_client_session(session_token):
    """Verify client session token"""
    if not supabase:
        return None
    
    try:
        from datetime import datetime
        
        result = supabase.table('client_sessions').select('*').eq('session_token', session_token).execute()
        
        if not result.data:
            return None
        
        session_data = result.data[0]
        expires_at = datetime.fromisoformat(session_data['expires_at'].replace('Z', '+00:00'))
        
        if datetime.now() > expires_at:
            return None
        
        # Update last accessed time
        supabase.table('client_sessions').update({'last_accessed': datetime.now().isoformat()}).eq('id', session_data['id']).execute()
        
        return session_data['email']
    except Exception as e:
        print(f"❌ Error verifying client session: {e}")
        return None

def generate_financial_data_from_conversation(conversation_id, client_name):
    """Generate financial data based on conversation history instead of hardcoded values"""
    try:
        print(f"🔍 Generating financial data for conversation: {conversation_id}, client: {client_name}")
        
        # Get conversation history
        history = memory_manager.get_conversation_history(conversation_id)
        print(f"📚 Retrieved conversation history: {len(history) if history else 0} messages")
        if history:
            print(f"📚 First message type: {type(history[0])}")
            print(f"📚 First message content: {history[0]}")
        else:
            print("📚 No conversation history found in memory manager")
        
        # Extract financial information from conversation
        financial_info = {
            "assets": {"rrsp": 0, "tfsa": 0, "investments": 0, "realEstate": 0, "totalAssets": 0},
            "liabilities": {"mortgage": 0, "carLoan": 0, "creditCards": 0, "totalLiabilities": 0},
            "netWorth": 0,
            "goals": {"shortTerm": [], "mediumTerm": [], "longTerm": []}
        }
        
        # If no conversation history, return empty data
        if not history:
            print("⚠️ No conversation history found, returning empty financial data")
            return financial_info
        
        # Analyze conversation for financial mentions
        conversation_text = ""
        for msg in history:
            if hasattr(msg, 'content'):
                conversation_text += msg.content + " "
            elif hasattr(msg, 'text'):
                conversation_text += msg.text + " "
            else:
                # Handle different message types
                conversation_text += str(msg) + " "
        
        print(f"🔍 Conversation text extracted: {conversation_text[:200]}...")
        
        # Use AI to extract financial data from conversation
        extraction_prompt = f"""
        Analyze the following conversation between a financial advisor and {client_name} and extract any mentioned financial information.
        
        Conversation: {conversation_text}
        
        Please extract and return ONLY the financial data mentioned in the conversation in this JSON format:
        {{
            "assets": {{
                "rrsp": 0,
                "tfsa": 0, 
                "investments": 0,
                "realEstate": 0,
                "totalAssets": 0
            }},
            "liabilities": {{
                "mortgage": 0,
                "carLoan": 0,
                "creditCards": 0,
                "totalLiabilities": 0
            }},
            "netWorth": 0,
            "goals": {{
                "shortTerm": [],
                "mediumTerm": [],
                "longTerm": []
            }}
        }}
        
        Rules:
        - Only include financial data that was explicitly mentioned in the conversation
        - If no specific amounts were mentioned, use 0
        - For goals, only include goals that were specifically discussed
        - Return ONLY the JSON, no other text
        """
        
        try:
            extracted_data = get_openai_response(extraction_prompt)
            # Try to parse the JSON response
            import re
            json_match = re.search(r'\{.*\}', extracted_data, re.DOTALL)
            if json_match:
                financial_info = json.loads(json_match.group())
        except Exception as e:
            print(f"⚠️ Error extracting financial data: {e}")
            # Return empty data if extraction fails
        
        return financial_info
        
    except Exception as e:
        print(f"⚠️ Error generating financial data: {e}")
        # Return empty financial data structure
        return {
            "assets": {"rrsp": 0, "tfsa": 0, "investments": 0, "realEstate": 0, "totalAssets": 0},
            "liabilities": {"mortgage": 0, "carLoan": 0, "creditCards": 0, "totalLiabilities": 0},
            "netWorth": 0,
            "goals": {"shortTerm": [], "mediumTerm": [], "longTerm": []}
        }

def detect_report_template(user_preference):
    """Detect which report template to use based on user preference"""
    if not user_preference:
        return "default"
    
    preference_lower = user_preference.lower()
    
    if any(keyword in preference_lower for keyword in ['retirement', 'retire', 'pension', 'rrsp', 'tfsa']):
        return "retirement_focused"
    elif any(keyword in preference_lower for keyword in ['tax', 'taxation', 'deduction', 'credit']):
        return "tax_focused"
    else:
        return "default"

def generate_custom_report_prompt(client_name, template_name, user_preference="", conversation_id=""):
    """Generate a customized report prompt based on the selected template and conversation history"""
    template = report_templates[template_name]
    
    # Get conversation context
    conversation_context = ""
    if conversation_id:
        history = memory_manager.get_conversation_history(conversation_id)
        if history:
            conversation_text = " ".join([msg.content for msg in history if hasattr(msg, 'content')])
            conversation_context = f"""
    
    **Conversation Context:**
    Based on the following conversation with {client_name}:
    {conversation_text[:2000]}...
    """
    
    # Build the report structure based on template
    report_structure = f"""
    ## Comprehensive Financial Report for {client_name}

    **Prepared for:** {client_name}
    **Prepared by:** Financial Assistant AI
    **Date:** {datetime.now().strftime('%B %d, %Y')}{conversation_context}
    """
    
    # Add sections in the template order
    for i, section in enumerate(template["sections"], 1):
        report_structure += f"\n\n## {i}. {section}"
        
        # Add specific content based on section
        if section == "EXECUTIVE SUMMARY":
            report_structure += "\nProvide a high-level overview of the client's financial situation, key recommendations, and priority actions."
        elif section == "FINANCIAL HEALTH ASSESSMENT":
            report_structure += "\n- **Assets:** Comprehensive breakdown of all assets\n- **Liabilities:** Detailed analysis of debts and obligations\n- **Net Worth:** Current net worth calculation and analysis\n- **Income:** Income analysis and stability assessment\n- **Expenses:** Expense breakdown and optimization opportunities\n- **Debt-to-Income Ratio:** Current DTI and recommendations\n- **Emergency Fund:** Assessment and recommendations\n- **Savings Rate:** Current savings rate and improvement strategies"
        elif section == "RECOMMENDED INVESTMENT STRATEGY":
            report_structure += "\n- **Asset Allocation:** Recommended portfolio allocation\n- **Investment Vehicles:** Specific investment recommendations\n- **Diversification:** Diversification strategy and benefits\n- **Rebalancing:** Rebalancing schedule and approach\n- **Tax-Advantaged Accounts:** Optimization of retirement accounts"
        elif section == "RISK ANALYSIS":
            report_structure += "\n- **Market Risk:** Assessment and mitigation strategies\n- **Inflation Risk:** Protection strategies\n- **Interest Rate Risk:** Impact analysis and recommendations\n- **Credit Risk:** Credit health assessment\n- **Liquidity Risk:** Liquidity needs and management"
        elif section == "RETIREMENT PLANNING":
            report_structure += "\n- **Retirement Goals:** Target retirement age and income needs\n- **Retirement Accounts:** RRSP and TFSA contribution strategies\n- **Pension Integration:** CPP and OAS optimization\n- **Withdrawal Strategy:** Tax-efficient retirement income planning"
        elif section == "TAX OPTIMIZATION OPPORTUNITIES":
            report_structure += "\n- **Tax-Advantaged Accounts:** RRSP, TFSA, RESP optimization strategies\n- **Tax-Loss Harvesting:** Opportunities and strategies\n- **Income Splitting:** Family tax optimization techniques\n- **Estate Planning:** Tax-efficient wealth transfer strategies"
        elif section == "ACTION ITEMS AND NEXT STEPS":
            report_structure += "\n- **Immediate Actions:** Steps to take in the next 30 days\n- **Short-term Actions:** 3-6 month implementation plan\n- **Long-term Actions:** 1-3 year strategic initiatives\n- **Monitoring:** Regular review schedule and key metrics"
    
    # Add customization instruction if user has preferences
    if user_preference:
        report_structure += f"""

    IMPORTANT: The user has requested the following customization for this report:
    "{user_preference}"
    
    Please restructure and customize the report based on this preference. This may include:
    - Reordering sections to prioritize the user's areas of interest
    - Emphasizing specific topics mentioned in their preference
    - Adjusting the content focus to match their needs
    - Making the report more relevant to their specific request
    """
    
    return f"""
    Create a comprehensive financial report for {client_name}. This should be a professional, detailed financial analysis report.

    Format the report with the following structure:

    {report_structure}

    IMPORTANT INSTRUCTIONS:
    - ONLY use financial information that was explicitly mentioned in the conversation above
    - Do NOT include any hardcoded or example financial data
    - If no specific financial information was discussed, indicate that in the report
    - Base all recommendations on the actual conversation content
    - Do not make up or assume any financial details not mentioned

    This report is for informational purposes only and does not constitute financial, investment, or tax advice. Please consult with qualified professionals before making financial decisions.

    Make this report specific, actionable, and professional. Use clear formatting with bullet points and specific recommendations based ONLY on the conversation content.
    """

# Database helper functions
def save_client_to_db(client_data):
    """Save client data to Supabase database"""
    if not supabase:
        # Generate a mock client ID for testing
        mock_client = {
            "id": str(uuid.uuid4()),
            "name": client_data.get("name", "Unknown"),
            "email": client_data.get("email", "unknown@example.com"),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        return {"success": True, "data": [mock_client]}
    
    try:
        result = supabase.table('clients').insert(client_data).execute()
        return {"success": True, "data": result.data}
    except Exception as e:
        print(f"Error saving client: {e}")
        return {"success": False, "error": str(e)}

def get_clients_from_db():
    """Get all clients from Supabase database"""
    if not supabase:
        return {"success": True, "data": []}  # Return empty list when Supabase is not available
    
    try:
        result = supabase.table('clients').select('*').execute()
        return {"success": True, "data": result.data}
    except Exception as e:
        print(f"Error fetching clients: {e}")
        return {"success": False, "error": str(e)}

def save_message_to_db(message_data):
    """Save chat message to Supabase database"""
    if not supabase:
        return {"success": True, "data": [message_data]}  # Return success for testing
    
    try:
        result = supabase.table('messages').insert(message_data).execute()
        return {"success": True, "data": result.data}
    except Exception as e:
        print(f"Error saving message: {e}")
        return {"success": False, "error": str(e)}

def get_messages_from_db(client_id):
    """Get all messages for a specific client from Supabase database"""
    if not supabase:
        return {"success": True, "data": []}  # Return empty list for testing
    
    try:
        result = supabase.table('messages').select('*').eq('client_id', client_id).order('created_at').execute()
        return {"success": True, "data": result.data}
    except Exception as e:
        print(f"Error fetching messages: {e}")
        return {"success": False, "error": str(e)}

def get_openai_response(message, system_prompt=None):
    """Get response from OpenAI API"""
    if not openai_model:
        return "I apologize, but I'm not properly configured. Please check the API key setup."
    
    try:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})
            
        response = openai.chat.completions.create(
            model=openai_model,
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        return f"I encountered an error processing your request: {str(e)}"

@app.route('/')
def home():
    return jsonify({
        "message": "Financial Assistant API Ready",
        "version": "1.0.0",
        "openai_status": "ready" if openai_model else "not_configured",
        "supabase_status": "ready" if supabase else "not_configured"
    })

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files from frontend"""
    frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'src')
    return send_from_directory(frontend_path, filename)

@app.route('/api/clients', methods=['GET'])
def get_clients():
    """Get all clients"""
    try:
        result = get_clients_from_db()
        if result["success"]:
            return jsonify({
                "success": True,
                "clients": result["data"]
            })
        else:
            return jsonify({
                "success": False,
                "error": result["error"]
            }), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/clients', methods=['POST'])
def create_client():
    """Create a new client"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'email']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    "success": False,
                    "error": f"Missing required field: {field}"
                }), 400
        
        # Create client data
        client_data = {
            "id": str(uuid.uuid4()),
            "name": data['name'],
            "email": data['email'],
            "phone": data.get('phone', ''),
            "age": data.get('age', None),
            "income": data.get('income', None),
            "occupation": data.get('occupation', ''),
            "goals": data.get('goals', ''),
            "notes": data.get('notes', ''),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Save to database
        result = save_client_to_db(client_data)
        if result["success"]:
            return jsonify({
                "success": True,
                "client": result["data"][0] if result["data"] else client_data
            })
        else:
            return jsonify({
                "success": False,
                "error": result["error"]
            }), 500
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/clients/<client_id>/messages', methods=['GET'])
def get_client_messages(client_id):
    """Get all messages for a specific client"""
    try:
        result = get_messages_from_db(client_id)
        if result["success"]:
            return jsonify({
                "success": True,
                "messages": result["data"]
            })
        else:
            return jsonify({
                "success": False,
                "error": result["error"]
            }), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        print(f"📨 Received chat request from {request.remote_addr}")
        data = request.get_json()
        print(f"📝 Request data: {data}")
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        message = data.get('message', '')
        client_id = data.get('client_id', None)
        conversation_id = data.get('conversation_id', str(uuid.uuid4()))
        
        if not message:
            return jsonify({"error": "No message provided"}), 400
        
        print(f"💬 Processing message: {message[:50]}...")
        
        # Store user message in LangChain memory manager
        memory_manager.add_message(conversation_id, "user", message)
        
        # Save user message to database if client_id is provided
        if client_id and supabase:
            user_message_data = {
                "id": str(uuid.uuid4()),
                "client_id": client_id,
                "role": "user",
                "content": message,
                "created_at": datetime.now().isoformat()
            }
            save_message_to_db(user_message_data)
        
        # Check if user is asking for report generation or restructuring
        report_keywords = ['generate report', 'create report', 'financial report', 'make a report', 'report generation']
        restructure_keywords = ['restructure report', 'reorganize report', 'change report', 'modify report', 'customize report', 'focus on', 'prioritize', 'emphasize']
        message_lower = message.lower()
        
        # Check for report restructuring requests
        if any(keyword in message_lower for keyword in restructure_keywords):
            # Store the restructuring preference in the conversation
            conversation_preferences[conversation_id] = message
            response = f"""I understand you'd like to customize the report structure! 

Your preference: **"{message}"**

I've noted your request to restructure the report. When you click the **"📊 Generate Report"** button, the report will be customized based on your preferences:

✅ **Customized section order** based on your priorities
✅ **Focused content** emphasizing your areas of interest
✅ **Tailored recommendations** for your specific needs
✅ **Professional formatting** with your preferred structure

Your restructuring preference has been saved for this conversation. Click the Generate Report button when you're ready to create your customized report!"""
        
        elif any(keyword in message_lower for keyword in report_keywords):
            response = """I'd be happy to help you generate a comprehensive financial report! 

To create your personalized financial report, please click the **"📊 Generate Report"** button in the header above. This will:

✅ Generate a detailed financial analysis
✅ Create a professional report with actionable recommendations  
✅ Provide you with a direct link to view and download the report
✅ Include sections on financial health, investment strategy, risk analysis, and more

The report will be tailored to your specific financial situation and goals. Once generated, you'll receive a link that you can bookmark or share with your financial advisor.

Is there anything specific you'd like me to help you with regarding your financial planning while we prepare your report?"""
        else:
            # Financial assistant system prompt
            system_prompt = """You are a professional financial advisor assistant. Help users with:
            - Financial planning and budgeting
            - Investment advice and portfolio management
            - Retirement planning
            - Tax optimization strategies
            - Risk assessment and insurance needs
            - Debt management and consolidation
            
            Provide clear, actionable advice based on best practices. Always recommend consulting with a qualified financial advisor for major decisions."""
            
            response = get_openai_response(message, system_prompt)
        
        # Store assistant response in LangChain memory manager
        memory_manager.add_message(conversation_id, "assistant", response)
        
        # Save assistant response to database if client_id is provided
        if client_id and supabase:
            assistant_message_data = {
                "id": str(uuid.uuid4()),
                "client_id": client_id,
                "role": "assistant",
                "content": response,
                "created_at": datetime.now().isoformat()
            }
            save_message_to_db(assistant_message_data)
        
        print(f"✅ Generated response: {response[:50]}...")
        
        # Return in the format the frontend expects
        return jsonify({
            "type": "message",
            "message": {
                "content": response,
                "citations": []
            }
        })
        
    except Exception as e:
        print(f"❌ Error in chat endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate-report', methods=['POST'])
def generate_report():
    try:
        data = request.get_json()
        client_name = data.get('client_name', 'Unknown Client')
        conversation_id = data.get('conversation_id', str(uuid.uuid4()))
        
        # Generate financial data based on conversation history
        financial_data = generate_financial_data_from_conversation(conversation_id, client_name)
        
        # Check for user preferences in this conversation
        user_preference = conversation_preferences.get(conversation_id, "")
        
        # Detect which template to use based on user preference
        template_name = detect_report_template(user_preference)
        print(f"📋 Using template: {template_name} for conversation {conversation_id}")
        
        # Generate a comprehensive financial report using template system
        report_prompt = generate_custom_report_prompt(client_name, template_name, user_preference, conversation_id)

        
        report_content = get_openai_response(report_prompt)
        
        # Create report ID and store it
        report_id = str(uuid.uuid4())
        reports[report_id] = {
            "id": report_id,
            "client_name": client_name,
            "content": report_content,
            "financial_data": financial_data,
            "created_at": datetime.now().isoformat(),
            "conversation_id": conversation_id,
            "user_preference": user_preference
        }
        
        # Generate URL for accessing the report (HTML view)
        report_url = f"http://localhost:8000/reports/{report_id}"
        
        return jsonify({
            "success": True,
            "report_id": report_id,
            "report_url": report_url,
            "message": f"Financial report generated successfully for {client_name}"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/financial-data/<conversation_id>', methods=['GET'])
def get_financial_data(conversation_id):
    """Get financial data extracted from conversation for charts and tables"""
    try:
        client_name = request.args.get('client_name', 'Unknown Client')
        
        # Generate financial data based on conversation history
        financial_data = generate_financial_data_from_conversation(conversation_id, client_name)
        
        return jsonify({
            "success": True,
            "financial_data": financial_data,
            "conversation_id": conversation_id,
            "client_name": client_name
        })
        
    except Exception as e:
        print(f"❌ Error getting financial data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/search-conversations', methods=['POST'])
def search_conversations():
    """Search through conversation history using semantic search"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        conversation_id = data.get('conversation_id')
        limit = data.get('limit', 5)
        
        if not query:
            return jsonify({'error': 'Query cannot be empty'}), 400
        
        # Search using LangChain vector store
        results = memory_manager.search_conversations(query, conversation_id, limit)
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                'content': result.page_content,
                'metadata': result.metadata,
                'score': getattr(result, 'score', None)
            })
        
        return jsonify({
            'results': formatted_results,
            'query': query,
            'total_found': len(formatted_results)
        })
        
    except Exception as e:
        print(f"❌ Error searching conversations: {e}")
        return jsonify({'error': 'Error searching conversations'}), 500

@app.route('/api/conversation-summary/<conversation_id>')
def get_conversation_summary(conversation_id):
    """Get a summary of a conversation"""
    try:
        summary = memory_manager.get_conversation_summary(conversation_id)
        history = memory_manager.get_conversation_history(conversation_id)
        
        return jsonify({
            'conversation_id': conversation_id,
            'summary': summary,
            'message_count': len(history),
            'last_updated': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ Error getting conversation summary: {e}")
        return jsonify({'error': 'Error getting conversation summary'}), 500

# =============================================
# AUTHENTICATION API ENDPOINTS
# =============================================

@app.route('/api/auth/request-access', methods=['POST'])
def request_access():
    """Request access by submitting email address"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({"error": "Email is required"}), 400
        
        # Check if email is authorized
        if not is_client_authorized(email):
            return jsonify({
                "success": False,
                "error": "Email not authorized. Please contact your financial advisor."
            }), 403
        
        # Generate passcode
        passcode = generate_passcode()
        
        # Set expiration (15 minutes from now)
        from datetime import datetime, timedelta
        expires_at = datetime.now() + timedelta(minutes=15)
        
        # Store token in database
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent')
        
        if not store_auth_token(email, passcode, expires_at, ip_address, user_agent):
            return jsonify({"error": "Failed to store authorization token"}), 500
        
        # Send email
        if not send_passcode_email(email, passcode):
            return jsonify({"error": "Failed to send passcode email"}), 500
        
        return jsonify({
            "success": True,
            "message": "Passcode sent to your email",
            "email": email
        })
        
    except Exception as e:
        print(f"❌ Error in request access: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/verify-token', methods=['POST'])
def verify_token():
    """Verify passcode and create session"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        token = data.get('token', '').strip()
        
        if not email or not token:
            return jsonify({"error": "Email and token are required"}), 400
        
        # Verify token
        if not verify_auth_token(email, token):
            return jsonify({
                "success": False,
                "error": "Invalid or expired passcode"
            }), 401
        
        # Create session
        session_token = create_client_session(email)
        if not session_token:
            return jsonify({"error": "Failed to create session"}), 500
        
        return jsonify({
            "success": True,
            "message": "Access granted",
            "session_token": session_token,
            "email": email
        })
        
    except Exception as e:
        print(f"❌ Error in verify token: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/validate-session', methods=['GET'])
def validate_session():
    """Validate current session"""
    try:
        session_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not session_token:
            return jsonify({"authenticated": False}), 401
        
        email = verify_client_session(session_token)
        if not email:
            return jsonify({"authenticated": False}), 401
        
        return jsonify({
            "authenticated": True,
            "email": email
        })
        
    except Exception as e:
        print(f"❌ Error in validate session: {e}")
        return jsonify({"authenticated": False}), 401

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout and clear session"""
    try:
        session_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if session_token and supabase:
            # Delete session from database
            supabase.table('client_sessions').delete().eq('session_token', session_token).execute()
        
        return jsonify({
            "success": True,
            "message": "Logged out successfully"
        })
        
    except Exception as e:
        print(f"❌ Error in logout: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/reports/<report_id>')
def get_report(report_id):
    try:
        if report_id not in reports:
            return jsonify({"error": "Report not found"}), 404
        
        report = reports[report_id]
        return jsonify({
            "success": True,
            "report": report
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/reports/<report_id>')
def view_report(report_id):
    try:
        if report_id not in reports:
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Report Not Found</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                    .error {{ color: #dc2626; }}
                </style>
            </head>
            <body>
                <h1 class="error">Report Not Found</h1>
                <p>The requested report could not be found.</p>
            </body>
            </html>
            """, 404
        
        report = reports[report_id]
        print(f"🔍 view_report: Retrieved report for {report_id}")
        print(f"🔍 view_report: Report keys: {list(report.keys())}")
        print(f"🔍 view_report: Financial data type: {type(report.get('financial_data', 'Not found'))}")
        
        # Format the report content for HTML display
        formatted_content = format_report_html(report['content'])
        
        # Generate charts HTML if financial data exists
        charts_html = ""
        if 'financial_data' in report:
            print(f"🔍 view_report: Calling generate_charts_html with: {report['financial_data']}")
            charts_html = generate_charts_html(report['financial_data'])
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Financial Report - {report['client_name']}</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <link rel="stylesheet" href="/static/styles/report.css">
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.6;
                    color: #374151;
                    background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
                    padding: 20px;
                    min-height: 100vh;
                }}
                
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                }}
                
                .header {{
                    background: white;
                    padding: 40px;
                    text-align: left;
                    border-bottom: 1px solid #e5e7eb;
                }}
                
                .header h1 {{
                    font-size: 2.5rem;
                    font-weight: 700;
                    color: #1e40af;
                    margin-bottom: 20px;
                }}
                
                .header p {{
                    font-size: 1rem;
                    color: #4b5563;
                    margin: 5px 0;
                }}
                
                .content {{
                    background: white;
                    border-radius: 0 0 16px 16px;
                    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
                    overflow: hidden;
                }}
                
                .report-sections {{
                    display: flex;
                    flex-direction: column;
                    gap: 20px;
                    padding: 40px;
                    max-width: 1000px;
                    margin: 0 auto;
                }}
                
                .section-card {{
                    background: white;
                    border-radius: 8px;
                    padding: 30px;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                    border: 1px solid #e5e7eb;
                }}
                
                .section-title {{
                    font-size: 1.5rem;
                    font-weight: 700;
                    color: #1f2937;
                    margin-bottom: 20px;
                    padding-bottom: 10px;
                    border-bottom: 1px solid #e5e7eb;
                }}
                
                .section-content {{
                    color: #4b5563;
                    line-height: 1.7;
                    font-size: 1rem;
                }}
                
                .section-content h3 {{
                    color: #1f2937;
                    font-size: 1.25rem;
                    font-weight: 600;
                    margin: 20px 0 10px 0;
                }}
                
                .section-content strong {{
                    color: #1f2937;
                    font-weight: 600;
                }}
                
                .section-content ul {{
                    margin: 10px 0;
                    padding-left: 20px;
                }}
                
                .section-content li {{
                    margin: 4px 0;
                    color: #4b5563;
                }}
                
                .section-content p {{
                    margin: 15px 0;
                    color: #4b5563;
                }}
                
                .charts-section {{
                    margin: 2rem 0;
                    padding: 2rem;
                    background: #f8fafc;
                    border-radius: 0.5rem;
                    border: 1px solid #e2e8f0;
                }}
                
                .chart-container {{
                    background: white;
                    padding: 1.5rem;
                    margin: 1rem 0;
                    border-radius: 0.5rem;
                    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
                }}
                
                .chart-title {{
                    font-size: 1.25rem;
                    font-weight: 600;
                    color: #1e40af;
                    margin-bottom: 1rem;
                }}
                
                .chart-canvas {{
                    max-height: 400px;
                }}
                
                .financial-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 1rem 0;
                    background: white;
                    border-radius: 0.5rem;
                    overflow: hidden;
                    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
                }}
                
                .financial-table th {{
                    background: #1e40af;
                    color: white;
                    padding: 0.75rem;
                    text-align: left;
                    font-weight: 600;
                }}
                
                .financial-table td {{
                    padding: 0.75rem;
                    border-bottom: 1px solid #e5e7eb;
                }}
                
                .financial-table tr:nth-child(even) {{
                    background: #f8fafc;
                }}
                
                .footer {{
                    background: #f3f4f6;
                    padding: 1.5rem 2rem;
                    border-top: 1px solid #e5e7eb;
                    font-size: 0.875rem;
                    color: #6b7280;
                }}
                
                .footer .info {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                
                .print-btn {{
                    background: #1e40af;
                    color: white;
                    border: none;
                    padding: 0.5rem 1rem;
                    border-radius: 0.375rem;
                    cursor: pointer;
                    font-size: 0.875rem;
                    margin-bottom: 1rem;
                }}
                
                .print-btn:hover {{
                    background: #1d4ed8;
                }}
                
                @media (max-width: 768px) {{
                    .report-sections {{
                        grid-template-columns: 1fr;
                        padding: 20px;
                    }}
                    
                    .header h1 {{
                        font-size: 2rem;
                    }}
                    
                    .section-card {{
                        padding: 20px;
                    }}
                }}
                
                @media print {{
                    body {{ background: white; }}
                    .container {{ box-shadow: none; }}
                    .print-btn {{ display: none; }}
                    .footer {{ display: none; }}
                    .charts-section {{ break-inside: avoid; }}
                    .section-card {{
                        break-inside: avoid;
                        box-shadow: none;
                        border: 1px solid #e5e7eb;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Financial Report</h1>
                    <p>Prepared for: {report['client_name']}</p>
                    <p>Generated: {datetime.fromisoformat(report['created_at']).strftime('%B %d, %Y at %I:%M %p')}</p>
                </div>
                
                <div class="content">
                    <button class="print-btn" onclick="window.print()">🖨️ Print Report</button>
                    
                    <!-- Comprehensive Report First -->
                    <div class="report-sections">
                        {format_report_sections(report['content'])}
                    </div>
                    
                    <!-- Charts and Tables After Report -->
                    {charts_html}
                </div>
                
                <div class="footer">
                    <div class="info">
                        <div>
                            <p><strong>Report ID:</strong> {report['id']}</p>
                            <p><strong>Conversation ID:</strong> {report['conversation_id']}</p>
                        </div>
                        <div style="text-align: right;">
                            <p>Generated by Financial Assistant AI</p>
                            <p style="font-size: 0.75rem; margin-top: 0.25rem;">
                                This report is for informational purposes only and does not constitute financial advice.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_content
        
    except Exception as e:
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                .error {{ color: #dc2626; }}
            </style>
        </head>
        <body>
            <h1 class="error">Error Loading Report</h1>
            <p>An error occurred while loading the report: {str(e)}</p>
        </body>
        </html>
        """, 500

def generate_charts_html(financial_data):
    """Generate HTML for charts and tables"""
    try:
        print(f"🔍 generate_charts_html received data type: {type(financial_data)}")
        print(f"🔍 generate_charts_html received data: {financial_data}")
        
        # Check if financial_data is a string (JSON) and parse it
        if isinstance(financial_data, str):
            import json
            financial_data = json.loads(financial_data)
            print(f"🔍 Parsed JSON data: {financial_data}")
        
        # Ensure we have the required structure
        if not isinstance(financial_data, dict):
            print(f"❌ financial_data is not a dictionary: {type(financial_data)}")
            return "<div class='error'>Error: Invalid financial data format</div>"
        
        assets = financial_data.get('assets', {})
        liabilities = financial_data.get('liabilities', {})
        goals = financial_data.get('goals', {})
        
        print(f"🔍 Extracted assets: {assets}")
        print(f"🔍 Extracted liabilities: {liabilities}")
        print(f"🔍 Extracted goals: {goals}")
        
    except Exception as e:
        print(f"❌ Error in generate_charts_html: {e}")
        return f"<div class='error'>Error generating charts: {str(e)}</div>"
    
    # Section header for charts and tables
    charts_header = """
    <div class="charts-section">
        <div class="section-header">
            <h2>📊 Financial Data Visualization</h2>
            <p>Charts, tables, and visual representations of your financial information</p>
        </div>
    """
    
    # Assets and Liabilities Table
    assets_table = f"""
    <div class="chart-container">
        <div class="chart-title">Assets & Liabilities Summary</div>
        <table class="financial-table">
            <thead>
                <tr>
                    <th>Category</th>
                    <th>Type</th>
                    <th>Amount</th>
                </tr>
            </thead>
            <tbody>
                <tr><td rowspan="4" style="background: #f0f9ff; font-weight: 600;">Assets</td><td>RRSP</td><td>${assets['rrsp']:,}</td></tr>
                <tr><td>TFSA</td><td>${assets['tfsa']:,}</td></tr>
                <tr><td>Investment Account</td><td>${assets['investments']:,}</td></tr>
                <tr><td>Real Estate</td><td>${assets['realEstate']:,}</td></tr>
                <tr><td colspan="2" style="font-weight: 600; background: #f0f9ff;">Total Assets</td><td style="font-weight: 600;">${assets['totalAssets']:,}</td></tr>
                <tr><td rowspan="3" style="background: #fef2f2; font-weight: 600;">Liabilities</td><td>Mortgage</td><td>${liabilities['mortgage']:,}</td></tr>
                <tr><td>Car Loan</td><td>${liabilities['carLoan']:,}</td></tr>
                <tr><td>Credit Cards</td><td>${liabilities['creditCards']:,}</td></tr>
                <tr><td colspan="2" style="font-weight: 600; background: #fef2f2;">Total Liabilities</td><td style="font-weight: 600;">${liabilities['totalLiabilities']:,}</td></tr>
                <tr><td colspan="2" style="font-weight: 600; background: #f0fdf4; color: #166534;">Net Worth</td><td style="font-weight: 600; color: #166534;">${financial_data['netWorth']:,}</td></tr>
            </tbody>
        </table>
    </div>
    """
    
    # Goals Progress Table
    goals_table = f"""
    <div class="chart-container">
        <div class="chart-title">Financial Goals Progress</div>
        <table class="financial-table">
            <thead>
                <tr>
                    <th>Goal</th>
                    <th>Target Amount</th>
                    <th>Progress</th>
                    <th>Current Value</th>
                    <th>Remaining</th>
                </tr>
            </thead>
            <tbody>
    """
    
    # Add short-term goals
    for goal in goals['shortTerm']:
        current = (goal['amount'] * goal['progress']) / 100
        remaining = goal['amount'] - current
        goals_table += f"""
                <tr>
                    <td>{goal['goal']} <span style="background: #3b82f6; color: white; padding: 2px 6px; border-radius: 12px; font-size: 0.75rem;">Short-term</span></td>
                    <td>${goal['amount']:,}</td>
                    <td>{goal['progress']}%</td>
                    <td>${current:,.0f}</td>
                    <td>${remaining:,.0f}</td>
                </tr>
        """
    
    # Add medium-term goals
    for goal in goals['mediumTerm']:
        current = (goal['amount'] * goal['progress']) / 100
        remaining = goal['amount'] - current
        goals_table += f"""
                <tr>
                    <td>{goal['goal']} <span style="background: #6b7280; color: white; padding: 2px 6px; border-radius: 12px; font-size: 0.75rem;">Medium-term</span></td>
                    <td>${goal['amount']:,}</td>
                    <td>{goal['progress']}%</td>
                    <td>${current:,.0f}</td>
                    <td>${remaining:,.0f}</td>
                </tr>
        """
    
    # Add long-term goals
    for goal in goals['longTerm']:
        current = (goal['amount'] * goal['progress']) / 100
        remaining = goal['amount'] - current
        goals_table += f"""
                <tr>
                    <td>{goal['goal']} <span style="background: #10b981; color: white; padding: 2px 6px; border-radius: 12px; font-size: 0.75rem;">Long-term</span></td>
                    <td>${goal['amount']:,}</td>
                    <td>{goal['progress']}%</td>
                    <td>${current:,.0f}</td>
                    <td>${remaining:,.0f}</td>
                </tr>
        """
    
    goals_table += """
            </tbody>
        </table>
    </div>
    """
    
    # Chart.js Charts
    charts_js = f"""
    <div class="chart-container">
        <div class="chart-title">Account Balances</div>
        <canvas id="accountsChart" class="chart-canvas"></canvas>
    </div>
    
    <div class="chart-container">
        <div class="chart-title">Net Worth Breakdown</div>
        <canvas id="netWorthChart" class="chart-canvas"></canvas>
    </div>
    
    <script>
        // Accounts Chart
        const accountsCtx = document.getElementById('accountsChart').getContext('2d');
        new Chart(accountsCtx, {{
            type: 'bar',
            data: {{
                labels: ['RRSP', 'TFSA', 'Investment Account'],
                datasets: [{{
                    label: 'Account Balance',
                    data: [{assets['rrsp']}, {assets['tfsa']}, {assets['investments']}],
                    backgroundColor: ['#3b82f6', '#10b981', '#f59e0b'],
                    borderColor: ['#2563eb', '#059669', '#d97706'],
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        display: false
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            callback: function(value) {{
                                return '$' + (value / 1000) + 'K';
                            }}
                        }}
                    }}
                }}
            }}
        }});
        
        // Net Worth Chart
        const netWorthCtx = document.getElementById('netWorthChart').getContext('2d');
        new Chart(netWorthCtx, {{
            type: 'doughnut',
            data: {{
                labels: ['Assets', 'Liabilities', 'Net Worth'],
                datasets: [{{
                    data: [{assets['totalAssets']}, {liabilities['totalLiabilities']}, {financial_data['netWorth']}],
                    backgroundColor: ['#10b981', '#ef4444', '#3b82f6'],
                    borderColor: ['#059669', '#dc2626', '#2563eb'],
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'bottom'
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                return context.label + ': $' + context.parsed.toLocaleString();
                            }}
                        }}
                    }}
                }}
            }}
        }});
    </script>
    """
    
    return f"""
    {charts_header}
        {assets_table}
        {goals_table}
        {charts_js}
    </div>
    """

def format_report_html(content):
    """Format the report content for HTML display"""
    # Convert markdown-like formatting to HTML
    formatted = content
    
    # Convert headers properly
    lines = formatted.split('\n')
    html_lines = []
    in_list = False
    
    for line in lines:
        line = line.strip()
        
        # Handle headers
        if line.startswith('## '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            header_text = line[3:].strip()
            html_lines.append(f'<h2>{header_text}</h2>')
        elif line.startswith('### '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            header_text = line[4:].strip()
            html_lines.append(f'<h3>{header_text}</h3>')
        elif line.startswith('- ') or line.startswith('* '):
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            # Remove the bullet point and convert to list item
            content = line[2:].strip()
            html_lines.append(f'<li>{content}</li>')
        else:
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            if line:
                # Convert bold text
                line = line.replace('**', '<strong>').replace('**', '</strong>')
                html_lines.append(f'<p>{line}</p>')
    
    if in_list:
        html_lines.append('</ul>')
    
    return '\n'.join(html_lines)

def format_report_sections(content):
    """Format the report content into clean section cards"""
    # Define section colors (alternating)
    section_colors = [
        "#3b82f6",  # Blue
        "#10b981",  # Green  
        "#f59e0b",  # Yellow
        "#ef4444",  # Red
        "#8b5cf6",  # Purple
        "#06b6d4",  # Cyan
        "#84cc16",  # Lime
        "#f97316"   # Orange
    ]
    
    # Split content by markdown headers (##)
    sections = content.split('## ')
    section_cards = []
    
    for i, section in enumerate(sections):
        if not section.strip():
            continue
            
        # Extract section title and content
        lines = section.split('\n', 1)
        if len(lines) >= 2:
            title = lines[0].strip()
            content_text = lines[1].strip()
        else:
            # If no clear title, use the whole section
            title = f"Section {i+1}"
            content_text = section.strip()
        
        # Skip if no meaningful content
        if not content_text or content_text.strip() == '':
            continue
        
        # Get color for this section
        color = section_colors[i % len(section_colors)]
        
        # Convert markdown to HTML
        content_text = content_text.replace('**', '<strong>').replace('**', '</strong>')
        content_text = content_text.replace('*', '<em>').replace('*', '</em>')
        
        # Handle bullet points
        content_text = content_text.replace('\n- ', '\n<li>').replace('\n* ', '\n<li>')
        content_text = content_text.replace('\n\n', '<br><br>')
        content_text = content_text.replace('\n', '<br>')
        
        # Wrap list items in ul tags
        if '<li>' in content_text:
            content_text = content_text.replace('<li>', '<ul><li>').replace('</li>', '</li></ul>')
            content_text = content_text.replace('</ul><ul>', '')
        
        # Create clean section card
        card_html = f'''
        <div class="section-card" style="border-top: 4px solid {color};">
            <h2 class="section-title">{title}</h2>
            <div class="section-content">
                {content_text}
            </div>
        </div>
        '''
        
        section_cards.append(card_html)
    
    return '\n'.join(section_cards)

@app.route('/api/reports')
def list_reports():
    try:
        report_list = []
        for report_id, report in reports.items():
            report_list.append({
                "id": report_id,
                "client_name": report["client_name"],
                "created_at": report["created_at"],
                "url": f"http://localhost:8000/reports/{report_id}"
            })
        
        return jsonify({
            "success": True,
            "reports": report_list
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"🔌 Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to Financial Assistant'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"🔌 Client disconnected: {request.sid}")
    # Clean up connection data
    if request.sid in active_connections:
        del active_connections[request.sid]

@socketio.on('join_conversation')
def handle_join_conversation(data):
    """Handle client joining a conversation"""
    conversation_id = data.get('conversation_id')
    client_name = data.get('client_name', 'Anonymous')
    
    print(f"👤 {client_name} joined conversation: {conversation_id}")
    
    # Store connection info
    active_connections[request.sid] = {
        'conversation_id': conversation_id,
        'client_name': client_name,
        'connected_at': datetime.now().isoformat()
    }
    
    # Join the conversation room
    join_room(conversation_id)
    
    # Send conversation history if available
    if conversation_id in conversation_history:
        emit('conversation_history', {
            'history': conversation_history[conversation_id],
            'preferences': conversation_preferences.get(conversation_id, "")
        })
    else:
        # Initialize empty conversation
        conversation_history[conversation_id] = []
        emit('conversation_initialized', {'conversation_id': conversation_id})

@socketio.on('send_message')
def handle_message(data):
    """Handle incoming chat messages via WebSocket"""
    try:
        message = data.get('message', '')
        conversation_id = data.get('conversation_id')
        client_name = data.get('client_name', 'Anonymous')
        
        if not message or not conversation_id:
            emit('error', {'message': 'Missing message or conversation_id'})
            return
        
        print(f"💬 WebSocket message from {client_name}: {message[:50]}...")
        
        # Add user message to conversation history
        user_message = {
            'role': 'user',
            'content': message,
            'timestamp': datetime.now().isoformat(),
            'client_name': client_name
        }
        
        if conversation_id not in conversation_history:
            conversation_history[conversation_id] = []
        
        conversation_history[conversation_id].append(user_message)
        
        # Check for report restructuring requests
        restructure_keywords = ['restructure report', 'reorganize report', 'change report', 'modify report', 'customize report', 'focus on', 'prioritize', 'emphasize']
        message_lower = message.lower()
        
        if any(keyword in message_lower for keyword in restructure_keywords):
            # Store the restructuring preference
            conversation_preferences[conversation_id] = message
            response = f"""I understand you'd like to customize the report structure! 

Your preference: **"{message}"**

I've noted your request to restructure the report. When you click the **"📊 Generate Report"** button, the report will be customized based on your preferences:

✅ **Customized section order** based on your priorities
✅ **Focused content** emphasizing your areas of interest
✅ **Tailored recommendations** for your specific needs
✅ **Professional formatting** with your preferred structure

Your restructuring preference has been saved for this conversation. Click the Generate Report button when you're ready to create your customized report!"""
        else:
            # Get conversation history for context using LangChain
            history = memory_manager.get_conversation_history(conversation_id)
            
            # Build context from recent conversation
            context = ""
            if history:
                context = "\n".join([
                    f"{'User' if isinstance(msg, HumanMessage) else 'Assistant'}: {msg.content}"
                    for msg in history[-6:]  # Last 6 messages for context
                ])
            
            # Generate AI response with conversation context
            system_prompt = """You are a professional financial advisor assistant. Help users with:
            - Financial planning and budgeting
            - Investment advice and portfolio management
            - Retirement planning
            - Tax optimization strategies
            - Risk assessment and management
            - Debt management and elimination
            - Insurance planning
            - Estate planning basics
            
            Provide clear, actionable advice while maintaining a professional tone. Always recommend consulting with qualified professionals for complex financial decisions."""
            
            # Create enhanced prompt with conversation context
            if context:
                full_prompt = f"{system_prompt}\n\nPrevious conversation context:\n{context}\n\nCurrent user message: {message}"
            else:
                full_prompt = f"{system_prompt}\n\nUser message: {message}"
            
            response = get_openai_response(full_prompt)
        
        # Add assistant response to conversation history
        assistant_message = {
            'role': 'assistant',
            'content': response,
            'timestamp': datetime.now().isoformat()
        }
        
        conversation_history[conversation_id].append(assistant_message)
        
        # Add to LangChain memory for persistent storage and semantic search
        memory_manager.add_message(conversation_id, "user", message)
        memory_manager.add_message(conversation_id, "assistant", response)
        
        # Emit response to the conversation room
        emit('message_response', {
            'message': response,
            'conversation_id': conversation_id,
            'timestamp': datetime.now().isoformat()
        }, room=conversation_id)
        
        # Emit updated conversation history
        emit('conversation_updated', {
            'history': conversation_history[conversation_id],
            'preferences': conversation_preferences.get(conversation_id, "")
        }, room=conversation_id)
        
    except Exception as e:
        print(f"❌ Error in WebSocket message handler: {e}")
        emit('error', {'message': f'Error processing message: {str(e)}'})

@socketio.on('generate_report')
def handle_generate_report(data):
    """Handle report generation via WebSocket"""
    try:
        client_name = data.get('client_name', 'Unknown Client')
        conversation_id = data.get('conversation_id')
        
        if not conversation_id:
            emit('error', {'message': 'Missing conversation_id'})
            return
        
        print(f"📊 Generating report for {client_name} in conversation {conversation_id}")
        
        # Emit report generation started
        emit('report_generation_started', {
            'message': 'Generating your personalized financial report...',
            'conversation_id': conversation_id
        }, room=conversation_id)
        
        # Get user preference for this conversation
        user_preference = conversation_preferences.get(conversation_id, "")
        
        # Detect which template to use based on user preference
        template_name = detect_report_template(user_preference)
        print(f"📋 Using template: {template_name} for conversation {conversation_id}")
        
        # Generate financial data based on conversation history
        financial_data = generate_financial_data_from_conversation(conversation_id, client_name)
        
        # Generate customized report prompt using template system
        report_prompt = generate_custom_report_prompt(client_name, template_name, user_preference, conversation_id)
        
        # Generate report content
        report_content = get_openai_response(report_prompt)
        
        # Create report ID and store it
        report_id = str(uuid.uuid4())
        reports[report_id] = {
            "id": report_id,
            "client_name": client_name,
            "content": report_content,
            "financial_data": financial_data,
            "created_at": datetime.now().isoformat(),
            "conversation_id": conversation_id,
            "user_preference": user_preference
        }
        
        # Generate URL for accessing the report
        report_url = f"http://localhost:8000/reports/{report_id}"
        
        # Emit report generation completed
        emit('report_generated', {
            'success': True,
            'report_id': report_id,
            'report_url': report_url,
            'message': f'Financial report generated successfully for {client_name}',
            'conversation_id': conversation_id
        }, room=conversation_id)
        
        # Add report generation to conversation history
        report_message = {
            'role': 'assistant',
            'content': f'📊 **Financial Report Generated Successfully!**\n\n**Client:** {client_name}\n**Report ID:** {report_id}\n\n**Report URL:** {report_url}\n\n*Copy the URL above and paste it in a new tab to view your professional financial report.*',
            'timestamp': datetime.now().isoformat(),
            'type': 'report_generation'
        }
        
        conversation_history[conversation_id].append(report_message)
        
        # Emit updated conversation history
        emit('conversation_updated', {
            'history': conversation_history[conversation_id],
            'preferences': conversation_preferences.get(conversation_id, "")
        }, room=conversation_id)
        
    except Exception as e:
        print(f"❌ Error in WebSocket report generation: {e}")
        emit('error', {'message': f'Error generating report: {str(e)}'}, room=conversation_id)

if __name__ == '__main__':
    print("🚀 Starting Financial Assistant API with WebSocket support...")
    print(f"🔑 API Key Status: {'✅ Configured' if openai_model else '❌ Not configured'}")
    print("🌐 Server starting on http://localhost:8000")
    print("🔌 WebSocket support enabled")
    socketio.run(app, host='0.0.0.0', port=8000, debug=True)

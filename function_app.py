import json
import logging
import azure.functions as func
from typing import List, Dict, Any
from datetime import datetime

app = func.FunctionApp()

# Fun sample data - Pokemon themed!
SAMPLE_DATA = [
    {
        "id": "pikachu-basics",
        "title": "Pikachu - The Electric Mouse Pokemon",
        "text": "Pikachu is an Electric-type Pokemon and the mascot of the Pokemon franchise. It evolves from Pichu and can evolve into Raichu. Known for its Thunderbolt attack and adorable appearance. Height: 0.4m, Weight: 6.0kg.",
        "url": "https://pokemon.com/pikachu",
        "metadata": {"type": "Electric", "number": "025", "generation": "1"}
    },
    {
        "id": "azure-functions-intro",
        "title": "Introduction to Azure Functions",
        "text": "Azure Functions is a serverless compute service that lets you run event-triggered code without managing infrastructure. Perfect for APIs, webhooks, and scheduled tasks. Supports multiple languages including Python, JavaScript, and C#.",
        "url": "https://docs.microsoft.com/azure/azure-functions",
        "metadata": {"category": "cloud", "service": "compute", "type": "serverless"}
    },
    {
        "id": "charizard-facts",
        "title": "Charizard - The Flame Pokemon",
        "text": "Charizard is a dual Fire/Flying-type Pokemon. It's the final evolution of Charmander. Its fire is hot enough to melt boulders. Popular in competitive battles. Height: 1.7m, Weight: 90.5kg.",
        "url": "https://pokemon.com/charizard",
        "metadata": {"type": "Fire/Flying", "number": "006", "generation": "1"}
    },
    {
        "id": "python-basics",
        "title": "Python Programming Fundamentals",
        "text": "Python is a high-level, interpreted programming language known for its simplicity and readability. Great for beginners and professionals alike. Used in web development, data science, AI, and automation.",
        "url": "https://python.org",
        "metadata": {"category": "programming", "difficulty": "beginner", "type": "language"}
    },
    {
        "id": "mcp-protocol",
        "title": "Understanding Model Context Protocol",
        "text": "MCP (Model Context Protocol) is an open standard for connecting AI assistants to external tools and data sources. It enables LLMs to access real-time information and perform actions through a standardized interface.",
        "url": "https://modelcontextprotocol.io",
        "metadata": {"category": "AI", "type": "protocol", "year": "2024"}
    }
]

# MCP SSE endpoint
@app.route(route="api/mcp/sse", methods=["GET", "POST", "OPTIONS"])
async def mcp_sse_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """MCP SSE endpoint for ChatGPT"""
    
    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, x-functions-key"
    }
    
    if req.method == "OPTIONS":
        return func.HttpResponse("", headers=headers, status_code=200)
    
    def generate_sse():
        # Connection message
        yield f"event: message\ndata: {json.dumps({'type': 'connection', 'status': 'connected'})}\n\n"
        
        # Tool definitions
        tools_message = {
            "type": "tools",
            "tools": [
                {
                    "name": "search",
                    "description": "Search for Pokemon, programming topics, or Azure information. Use keywords to find relevant content.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search keywords (e.g., 'pikachu', 'python', 'azure functions')"
                            }
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "fetch",
                    "description": "Get complete details about a specific topic by its ID",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "string",
                                "description": "Document ID from search results"
                            }
                        },
                        "required": ["id"]
                    }
                }
            ]
        }
        yield f"event: message\ndata: {json.dumps(tools_message)}\n\n"
    
    return func.HttpResponse(
        "".join(generate_sse()),
        headers=headers,
        status_code=200
    )

# Tool execution endpoint
@app.route(route="api/mcp/tools/{tool_name}", methods=["POST", "OPTIONS"])
async def execute_tool(req: func.HttpRequest) -> func.HttpResponse:
    """Execute MCP tools"""
    
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, x-functions-key"
    }
    
    if req.method == "OPTIONS":
        return func.HttpResponse("", headers=headers, status_code=200)
    
    tool_name = req.route_params.get('tool_name')
    
    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid request body"}),
            headers=headers,
            status_code=400
        )
    
    if tool_name == "search":
        query = req_body.get("query", "").lower()
        results = []
        
        # Search through our data
        for doc in SAMPLE_DATA:
            searchable = f"{doc['title']} {doc['text']} {json.dumps(doc.get('metadata', {}))}".lower()
            if any(word in searchable for word in query.split()):
                results.append({
                    "id": doc["id"],
                    "title": doc["title"],
                    "text": doc["text"][:200] + "..." if len(doc["text"]) > 200 else doc["text"],
                    "url": doc.get("url", "")
                })
        
        response = {
            "content": [{
                "type": "text",
                "text": json.dumps({"results": results})
            }]
        }
        
        return func.HttpResponse(
            json.dumps(response),
            headers=headers,
            status_code=200
        )
    
    elif tool_name == "fetch":
        doc_id = req_body.get("id")
        doc = next((d for d in SAMPLE_DATA if d["id"] == doc_id), None)
        
        if doc:
            result = {
                "id": doc["id"],
                "title": doc["title"],
                "text": doc["text"],
                "url": doc.get("url", ""),
                "metadata": doc.get("metadata", {})
            }
        else:
            result = {"error": f"Document '{doc_id}' not found"}
        
        response = {
            "content": [{
                "type": "text",
                "text": json.dumps(result)
            }],
            "isError": "error" in result
        }
        
        return func.HttpResponse(
            json.dumps(response),
            headers=headers,
            status_code=200
        )
    
    else:
        return func.HttpResponse(
            json.dumps({"error": f"Unknown tool: {tool_name}"}),
            headers=headers,
            status_code=404
        )

# Health check
@app.route(route="api/health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({
            "status": "healthy",
            "service": "MCP Server for ChatGPT",
            "timestamp": datetime.utcnow().isoformat()
        }),
        mimetype="application/json",
        status_code=200
    )

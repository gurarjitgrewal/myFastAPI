from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.openapi.utils import get_openapi
import os
from typing import List, Dict, Any, Optional, Callable, Union


def create_custom_openapi(
    app: FastAPI,
    server_url: Optional[str] = None,
    server_description: Optional[str] = None,
    excluded_paths: List[str] = None,
    additional_schemas: Dict[str, Any] = None,
    security_schemes: Dict[str, Any] = None,
    custom_parameters: Dict[str, Any] = None,
    schema_generator: Optional[Callable] = None
) -> Callable:
    """
    Create a custom OpenAPI schema generator function for FastAPI applications.
    
    Args:
        app: The FastAPI application
        server_url: The server URL (defaults to environment variable or localhost)
        server_description: Description for the server
        excluded_paths: List of paths to exclude from OpenAPI schema
        additional_schemas: Additional schemas to add to components.schemas
        security_schemes: Security schemes to add
        custom_parameters: Custom parameters to add
        schema_generator: Optional custom schema generator function
        
    Returns:
        A custom_openapi function to assign to app.openapi
    """
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
            
        # Get server URL from environment variable or use default
        actual_server_url = server_url or os.getenv(
            "API_SERVER_URL", 
            f"http://localhost:{os.getenv('FASTAPI_PORT', '8000')}"
        )
        
        # Get server description from environment or use default
        actual_server_description = server_description or os.getenv(
            "API_SERVER_DESCRIPTION",
            f"{app.title} API"
        )
        
        # Filter routes based on excluded paths
        actual_excluded_paths = excluded_paths or []
        included_routes = [
            route for route in app.routes
            if isinstance(route, APIRoute) and route.path not in actual_excluded_paths
        ]
        
        # Generate the base OpenAPI schema
        if schema_generator:
            openapi_schema = schema_generator(app, included_routes)
        else:
            openapi_schema = get_openapi(
                title=app.title,
                version=app.version,
                description=app.description,
                routes=included_routes,
            )
        
        # Set OpenAPI version
        openapi_schema["openapi"] = "3.1.0"
        
        # Set servers
        openapi_schema["servers"] = [
            {
                "url": actual_server_url,
                "description": actual_server_description
            }
        ]
        
        # Initialize components if not present
        if "components" not in openapi_schema:
            openapi_schema["components"] = {}
            
        # Add additional schemas
        if additional_schemas:
            if "schemas" not in openapi_schema["components"]:
                openapi_schema["components"]["schemas"] = {}
                
            for schema_name, schema in additional_schemas.items():
                openapi_schema["components"]["schemas"][schema_name] = schema
                
        # Add security schemes
        if security_schemes:
            openapi_schema["components"]["securitySchemes"] = security_schemes
            
        # Add custom parameters
        if custom_parameters:
            openapi_schema["components"]["parameters"] = custom_parameters
            
        app.openapi_schema = openapi_schema
        return app.openapi_schema
        
    return custom_openapi

# Common security schemes used across tools
def get_default_security_schemes() -> Dict[str, Any]:
    """
    Returns common security schemes used across tools
    """
    return {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter 'Bearer' followed by your JWT token. Example: 'Bearer eyJhbGciOi...'"
        },
        "OAuth2PasswordBearer": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": "/auth/token",
                    "scopes": {}
                }
            }
        }
    }

# Common session tracking parameters
def get_default_parameters() -> Dict[str, Any]:
    """
    Returns common parameters used across tools for session tracking
    """
    return {
        "ConversationId": {
            "name": "x-conversation-id",
            "in": "header",
            "description": "Conversation identifier for workflow tracking",
            "schema": {"type": "string"},
            "required": False
        },
        "MessageId": {
            "name": "x-message-id", 
            "in": "header",
            "description": "Message identifier for request tracking",
            "schema": {"type": "string"},
            "required": False
        },
        "SessionId": {
            "name": "x-session-id",
            "in": "header", 
            "description": "Session identifier for user tracking",
            "schema": {"type": "string"},
            "required": False
        },
        "UserId": {
            "name": "x-user-id",
            "in": "header",
            "description": "User identifier",
            "schema": {"type": "string"},
            "required": False
        }
    }

# StandardizedToolResult schema
def get_standardized_tool_result_schema() -> Dict[str, Any]:
    """
    Returns the common StandardizedToolResult schema used across tools
    """
    return {
        "StandardizedToolResult": {
            "type": "object",
            "properties": {
                "result_id": {"type": "string", "description": "Unique identifier for this result"},
                "tool_name": {"type": "string", "description": "Name of the tool that generated this result"},
                "status": {"type": "string", "enum": ["completed", "failed", "partial", "error"]},
                "conversation_id": {"type": "string", "description": "Conversation identifier"},
                "message_id": {"type": "string", "description": "Message identifier"},
                "user_id": {"type": "string", "description": "User identifier"},
                "session_id": {"type": "string", "description": "Session identifier"},
                "payload": {"type": "object", "description": "Tool-specific result data"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "persistence": {
                    "type": "object",
                    "properties": {
                        "stored": {"type": "boolean"},
                        "storage_id": {"type": "string"},
                        "storage_type": {"type": "string"}
                    }
                },
                "suggested_tools": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tool_type": {"type": "string"},
                            "tool_hint": {"type": "string"},
                            "reason": {"type": "string"},
                            "parameters": {"type": "object"},
                            "output_label": {"type": "string"},
                            "priority": {"type": "string", "enum": ["low", "medium", "high"]}
                        }
                    }
                },
                "execution_time_ms": {"type": "integer"},
                "timestamp": {"type": "string", "format": "date-time"}
            },
            "required": ["result_id", "tool_name", "status", "payload"]
        }
    }

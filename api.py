from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import Settings
from routers import patients, spam

app = FastAPI(
    title="Dynamic Spam Detector API + Patient Manager",
    description="A comprehensive API for patient management with spam detection capabilities",
    version="1.0.0"
)

# Load settings
settings = Settings()

# Configure CORS middleware with settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(settings, 'allowed_origins', ["http://localhost:8000"]),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include routers
app.include_router(patients.router)
app.include_router(spam.router)

@app.get("/", tags=["Root"])
def home():
    """Welcome endpoint with API information"""
    return {
        "message": "Welcome to Patient + Spam Detection API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "patient-api"}

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import Settings
from routers import patients, spam

app = FastAPI(title="Dynamic Spam Detector API + Patient Manager")

# Load settings
settings = Settings()

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(patients.router)
app.include_router(spam.router)

@app.get("/")
def home():
    return {"message": "Welcome to Patient + Spam Detection API"}
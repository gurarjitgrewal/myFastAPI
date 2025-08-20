from fastapi import FastAPI ,Path, HTTPException,Query
from pydantic import BaseModel,Field,computed_field
from model import SimpleEmailData, DynamicSpamDetector
import json
from fastapi.responses import JSONResponse
from typing import Annotated,Literal,Optional
import os
import sys

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute



app = FastAPI(title="Dynamic Spam Detector API")

from config.settings import Settings
 
settings = Settings()

patients_db = {
    "P001": {"name": "John Doe", "city": "New York", "age": 30, "gender": "male", "height": 1.75, "weight": 70.0},
    "P002": {"name": "Ravi Mehta", "city": "Mumbai", "age": 35, "gender": "male", "height": 1.75, "weight": 85},
    "P003": {"name": "Sneha Kulkarni", "city": "Pune", "age": 22, "gender": "female", "height": 1.6, "weight": 45},
    "P004": {"name": "Arjun Verma", "city": "Mumbai", "age": 40, "gender": "male", "height": 1.8, "weight": 90},
    "P005": {"name": "Neha Sinha", "city": "Kolkata", "age": 30, "gender": "female", "height": 1.55, "weight": 75},
}

# Try to import common module from local directory first
try:
    from common.openapi_utils import (
        create_custom_openapi,
        get_default_security_schemes,
        get_default_parameters
    )
except ModuleNotFoundError:
    # If not found locally, try to find it in the parent directory
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from common.openapi_utils import (
        create_custom_openapi,
        get_default_security_schemes,
        get_default_parameters
)
 
# Define the endpoints you want to exclude
excluded_paths = [
]  
 
# Apply custom OpenAPI schema using the common utility
app.openapi = create_custom_openapi(
    app=app,
    server_url=settings.API_SERVER_URL,
    server_description=settings.API_SERVER_DESCRIPTION,
    excluded_paths=excluded_paths,
    security_schemes=get_default_security_schemes(),
    custom_parameters=get_default_parameters()
)
 
 
#FastAPIInstrumentor.instrument_app(app)
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)
 
#app.include_router(base_router, prefix="/api")
#app.include_router(meta_router, prefix="/api")
#app.include_router(registry_router, prefix="/api")
#app.include_router(session_router, prefix="/api")

# Create instances
data_gen = SimpleEmailData()
detector = DynamicSpamDetector()


class EmailRequest(BaseModel):
    text: str


class newData(BaseModel):
    text: str
    label: int

email=[]
label=[]

@app.post("/train")
def train_model():
    emails = []
    labels = []
    for _ in range(50):
        e, l = data_gen.generate_email()
        emails.append(e)
        labels.append(l)
    email.extend(emails)
    label.extend(labels)
    #print(email,label)
    detector.initial_training(emails, labels)
    
    return {"message": "Initial training complete", "total_emails": len(detector.all_emails)}
    

@app.post("/predict")
def predict_email(request: EmailRequest):
    label, confidence = detector.predict_email(request.text)
    return {
        "prediction": "spam" if label == 1 else "not spam",
        "confidence": confidence
    }


@app.post("/new-input")
def new_input(request: newData):
    detector.learn_from_new_email(request.text, request.label)
    return {"message": "New input recorded and model retrained"}


@app.get("/evaluate")
def evaluate_model():
    emails1 = []
    labels1 = []
    for _ in range(30):
        e, l = data_gen.generate_email()
        emails1.append(e)
        labels1.append(l)
    email.extend(emails1)
    label.extend(labels1)
    acc = detector.evaluate(email, label)
    return {"accuracy": acc}



#---------------------------------------------------------------------------------#
#FastAPI Practice

class Patient(BaseModel):
    id: Annotated[str, Field(..., description="The unique identifier for the patient", example="P001")]
    name: Annotated[str, Field(..., description="The name of the patient", example="John Doe")]
    city: Annotated[str, Field(..., description="The city where the patient resides", example="New York")]
    age: Annotated[int, Field(...,ge=1,le=120,description="The age of the patient", example=30)]
    gender: Annotated[Literal['male','female','other'], Field(..., description='gender of the patient')]
    height: Annotated[float, Field(..., ge=1, description="The height of the patient in meters", example=1.75)]
    weight: Annotated[float, Field(..., ge=1, description="The weight of the patient in kilograms", example=70.0)]

    @computed_field
    @property
    def BMI(self) -> float:
        """Calculate the Body Mass Index (BMI) of the patient."""
        return round(self.weight / (self.height ** 2), 2)
    
    @computed_field
    @property
    def verdict(self) -> str:
        """Determine the health verdict based on BMI."""
        bmi = self.BMI  
        if bmi < 18.5:
            return "Underweight"
        elif 18.5 <= bmi < 24.9:
            return "Normal weight"
        elif 25 <= bmi < 29.9:
            return "Overweight"
        else:
            return "Obesity"
        
class PatientUpdate(BaseModel):
    name: Annotated[Optional[str], Field(None, description="The name of the patient", example="John Doe")]
    city: Annotated[Optional[str], Field(None, description="The city where the patient resides", example="New York")]
    age: Annotated[Optional[int], Field(None, ge=1, le=119, description="The age of the patient", example=30)]
    gender: Annotated[Optional[Literal['male', 'female', 'other']], Field(None, description="The gender of the patient", example="female")]
    height: Annotated[Optional[float], Field(None, ge=1, description="The height of the patient in meters", example=1.75)]
    weight: Annotated[Optional[float], Field(None, ge=1, description="The weight of the patient in kilograms", example=70.0)]


#def load_data():
#    with open("patients.json", "r") as file:
#        data=json.load(file)
#    return data

#def save_data(data):
#    with open("patients.json", "w") as file:
#        json.dump(data, file)

@app.get("/")
def hello():
    return {"message": "Patient Management System API"}

@app.get("/about")
def about():
    return {"message": "A fully functional Patient Management System to manage your patient records."}

@app.get("/view")
def view():
    #data = load_data()
    #return data
    return patients_db

@app.get("/patient/{patient_id}")
def get_patient(patient_id: str = Path(..., description="The ID of the patient to retrieve", example="P001")):
    if patient_id in patients_db:
        return patients_db[patient_id]
    
    raise HTTPException(status_code=404, detail="Patient not found")

@app.get("/sort")
def sort_patients(order: str = Query("asc", description="Sort order: 'asc' for ascending, 'desc' for descending"), sort_by: str = Query("...", description="Field to sort by: 'height' or 'weight' or 'BMI")):
    valid_sort_fields = ["height", "weight", "BMI"]
    if sort_by not in valid_sort_fields:
        raise HTTPException(status_code=400, detail=f"Invalid sort field. Valid fields are: {', '.join(valid_sort_fields)}")
    
    if order not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Invalid sort order. Use 'asc' or 'desc'.")
    

    sorted_data = sorted(
        patients_db.values(), 
        key=lambda x: round(x["weight"] / (x["height"] ** 2), 2) if sort_by == "BMI" else x[sort_by], 
        reverse=(order == "desc")
    )

    return sorted_data

@app.post("/create")
def create_patient(patient: Patient):
    
    if patient.id in patients_db:
        raise HTTPException(status_code=400, detail="Patient with this ID already exists.")

    patients_db[patient.id] = patient.model_dump(exclude=['id'])

    return JSONResponse(status_code=201, content={"message": "Patient created successfully", "patient": patients_db[patient.id]})

@app.put("/update/{patient_id}")
def update_patient(patient_id: str, patient_update: PatientUpdate):
    if patient_id not in patients_db:
        raise HTTPException(status_code=404, detail="Patient not found")

    existing_data = patients_db[patient_id]
    update_data = patient_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        existing_data[key] = value

    patients_db[patient_id] = existing_data
    return {"message": "Patient updated successfully", "patient": patients_db[patient_id]}

@app.delete("/delete/{patient_id}")
def delete_patient(patient_id: str):
    if patient_id not in patients_db:
        raise HTTPException(status_code=404, detail="Patient not found")
    del patients_db[patient_id]
    return {"message": "Patient deleted successfully"}

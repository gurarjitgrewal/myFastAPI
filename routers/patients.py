from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, Literal, Annotated
from pydantic import BaseModel, Field, computed_field
import json, os

router = APIRouter(prefix="/patients", tags=["Patients"])

DATA_FILE = "patients.json"

# ------------------ Helpers ------------------ #
def load_patients():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_patients(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ------------------ Models ------------------ #
class Patient(BaseModel):
    id: Annotated[str, Field(..., description="Patient ID", example="P001")]
    name: str
    city: str
    age: Annotated[int, Field(..., ge=1, le=120)]
    gender: Literal['male','female','other']
    height: Annotated[float, Field(..., ge=1)]
    weight: Annotated[float, Field(..., ge=1)]

    @computed_field
    @property
    def BMI(self) -> float:
        return round(self.weight / (self.height ** 2), 2)

    @computed_field
    @property
    def verdict(self) -> str:
        bmi = self.BMI
        if bmi < 18.5:
            return "Underweight"
        elif 18.5 <= bmi < 24.9:
            return "Normal weight"
        elif 25 <= bmi < 29.9:
            return "Overweight"
        return "Obesity"

class PatientUpdate(BaseModel):
    name: Optional[str]
    city: Optional[str]
    age: Optional[int]
    gender: Optional[Literal['male','female','other']]
    height: Optional[float]
    weight: Optional[float]


@router.post("/upload")
async def upload_patients(file: UploadFile = File(...)):
    """Upload a JSON file containing patient data."""
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json files are allowed")

    content = await file.read()
    try:
        patients = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    save_patients(patients)
    return {"message": "Patients file uploaded successfully", "total_patients": len(patients)}

@router.get("/")
def view_all():
    return load_patients()

@router.get("/{patient_id}")
def get_patient(patient_id: str):
    data = load_patients()
    if patient_id not in data:
        raise HTTPException(status_code=404, detail="Patient not found")
    return data[patient_id]

@router.post("/create")
def create_patient(patient: Patient):
    data = load_patients()
    if patient.id in data:
        raise HTTPException(status_code=400, detail="Patient already exists")
    data[patient.id] = patient.model_dump(exclude=["id"])
    save_patients(data)
    return JSONResponse(status_code=201, content={"message": "Patient created", "patient": data[patient.id]})

@router.put("/update/{patient_id}")
def update_patient(patient_id: str, patient_update: PatientUpdate):
    data = load_patients()
    if patient_id not in data:
        raise HTTPException(status_code=404, detail="Patient not found")
    update_data = patient_update.model_dump(exclude_unset=True)
    data[patient_id].update(update_data)
    save_patients(data)
    return {"message": "Patient updated", "patient": data[patient_id]}

@router.delete("/delete/{patient_id}")
def delete_patient(patient_id: str):
    data = load_patients()
    if patient_id not in data:
        raise HTTPException(status_code=404, detail="Patient not found")
    del data[patient_id]
    save_patients(data)
    return {"message": "Patient deleted"}
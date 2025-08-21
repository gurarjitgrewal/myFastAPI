from fastapi import APIRouter, Path, Query, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, Literal, Annotated
from pydantic import BaseModel, Field, computed_field

router = APIRouter(prefix="/patients", tags=["Patients"])

# In-memory DB
patients_db = {
    "P001": {"name": "John Doe", "city": "New York", "age": 30, "gender": "male", "height": 1.75, "weight": 70.0},
    "P002": {"name": "Ravi Mehta", "city": "Mumbai", "age": 35, "gender": "male", "height": 1.75, "weight": 85},
}

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

@router.get("/")
def view_all():
    return patients_db

@router.get("/{patient_id}")
def get_patient(patient_id: str):
    if patient_id not in patients_db:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patients_db[patient_id]

@router.post("/create")
def create_patient(patient: Patient):
    if patient.id in patients_db:
        raise HTTPException(status_code=400, detail="Patient already exists")
    patients_db[patient.id] = patient.model_dump(exclude=["id"])
    return JSONResponse(status_code=201, content={"message": "Patient created", "patient": patients_db[patient.id]})

@router.put("/update/{patient_id}")
def update_patient(patient_id: str, patient_update: PatientUpdate):
    if patient_id not in patients_db:
        raise HTTPException(status_code=404, detail="Patient not found")
    update_data = patient_update.model_dump(exclude_unset=True)
    patients_db[patient_id].update(update_data)
    return {"message": "Patient updated", "patient": patients_db[patient_id]}

@router.delete("/delete/{patient_id}")
def delete_patient(patient_id: str):
    if patient_id not in patients_db:
        raise HTTPException(status_code=404, detail="Patient not found")
    del patients_db[patient_id]
    return {"message": "Patient deleted"}

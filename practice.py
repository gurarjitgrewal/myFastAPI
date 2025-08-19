from fastapi import FastAPI , Path, HTTPException,Query
import json
from fastapi.responses import JSONResponse

from pydantic import BaseModel, Field,computed_field
from typing import Annotated,Literal,Optional

app = FastAPI()

class Patient(BaseModel):
    id: Annotated[str, Field(..., description="The unique identifier for the patient", example="P001")]
    name: Annotated[str, Field(..., description="The name of the patient", example="John Doe")]
    city: Annotated[str, Field(..., description="The city where the patient resides", example="New York")]
    age: Annotated[int, Field(...,gt=0,lt=120,description="The age of the patient", example=30)]
    gender: Annotated[Literal['male','female','other'], Field(..., description='gender of the patient')]
    height: Annotated[float, Field(..., gt=0, description="The height of the patient in meters", example=1.75)]
    weight: Annotated[float, Field(..., gt=0, description="The weight of the patient in kilograms", example=70.0)]

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
    age: Annotated[Optional[int], Field(None, gt=0, lt=120, description="The age of the patient", example=30)]
    gender: Annotated[Optional[Literal['male', 'female', 'other']], Field(None, description="The gender of the patient", example="female")]
    height: Annotated[Optional[float], Field(None, gt=0, description="The height of the patient in meters", example=1.75)]
    weight: Annotated[Optional[float], Field(None, gt=0, description="The weight of the patient in kilograms", example=70.0)]

def load_data():
    with open("patients.json", "r") as file:
        data=json.load(file)
    return data

def save_data(data):
    with open("patients.json", "w") as file:
        json.dump(data, file)

@app.get("/")
def hello():
    return {"message": "Patient Management System API"}

@app.get("/about")
def about():
    return {"message": "A fully functional Patient Management System to manage your patient records."}

@app.get("/view")
def view():
    data = load_data()
    return data

@app.get("/patient/{patient_id}")
def get_patient(patient_id: str = Path(..., description="The ID of the patient to retrieve", example="P001")):
    data = load_data()

    if patient_id in data:
        return data[patient_id]
    
    raise HTTPException(status_code=404, detail="Patient not found")

@app.get("/sort")
def sort_patients(order: str = Query("asc", description="Sort order: 'asc' for ascending, 'desc' for descending"), sort_by: str = Query("...", description="Field to sort by: 'height' or 'weight' or 'BMI")):
    valid_sort_fields = ["height", "weight", "BMI"]
    if sort_by not in valid_sort_fields:
        raise HTTPException(status_code=400, detail=f"Invalid sort field. Valid fields are: {', '.join(valid_sort_fields)}")
    
    if order not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Invalid sort order. Use 'asc' or 'desc'.")
    data = load_data()

    sorted_data = sorted(data.values(), key=lambda x: x[sort_by], reverse=(order == "desc"))

    return sorted_data

@app.post("/create")
def create_patient(patient: Patient):
    data = load_data()
    if patient.id in data:
        raise HTTPException(status_code=400, detail="Patient with this ID already exists.")

    data[patient.id] = patient.model_dump(exclude=['id'])

    save_data(data)
    return JSONResponse(status_code=201, content={"message": "Patient created successfully", "patient": data[patient.id]})

@app.put("/update/{patient_id}")
def update_patient(patient_id: str, patient_update: PatientUpdate):
    data = load_data()

    if patient_id not in data:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    existing_data_info = data[patient_id]

    update_patient_info= patient_update.model_dump(exclude_unset=True)

    for key, value in update_patient_info.items():
        existing_data_info[key] = value

    existing_data_info['id'] = patient_id  # Ensure the ID remains unchanged
    patient_pydantic_obj= Patient(**existing_data_info)

    existing_data_info= patient_pydantic_obj.model_dump(exclude=['id'])

    data[patient_id] = existing_data_info

    save_data(data)

    return JSONResponse(status_code=200, content={"message": "Patient updated successfully", "patient": existing_data_info})


@app.delete("/delete/{patient_id}")
def delete_patient(patient_id: str):
    data = load_data()
    if patient_id not in data:
        raise HTTPException(status_code=404, detail="Patient not found")

    del data[patient_id]
    save_data(data)

    return JSONResponse(status_code=200, content={"message": "Patient deleted successfully"})
  

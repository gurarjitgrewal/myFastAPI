from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Optional, Literal, Annotated
from pydantic import BaseModel, Field, computed_field
from toolresultformatter import ToolResultFormatter
import json, os, time

router = APIRouter(prefix="/patients", tags=["Patients"])
DATA_FILE = "patients.json"

# ------------- Helpers ------------- #
def load_patients():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_patients(data: dict):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def ok(command: str, data=None, pid: Optional[str] = None, start: float = None):
    exec_time = (time.time() - start) if start else 0.0
    return ToolResultFormatter.format(command=command, stdout=data, execution_time=exec_time, patient_id=pid)

def err(command: str, message: str, pid: Optional[str] = None, start: float = None):
    exec_time = (time.time() - start) if start else 0.0
    return ToolResultFormatter.format(command=command, stderr=message, exit_code=1, execution_time=exec_time, patient_id=pid)

# ------------- Models ------------- #
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

# ------------- Upload JSON ------------- #
@router.post("/upload")
async def upload_patients(
    file: UploadFile = File(..., description="JSON of patients keyed by ID"),
    mode: Literal["replace", "merge"] = "replace"
):
    """
    Upload a patients JSON file from the agent.
    - 'replace': overwrite existing patients.json
    - 'merge': update existing entries and add new ones
    """
    start = time.time()
    if not file.filename.lower().endswith(".json"):
        return err("upload_patients", "Only .json files are allowed", start=start)

    raw = await file.read()
    try:
        incoming = json.loads(raw)
    except json.JSONDecodeError:
        return err("upload_patients", "Invalid JSON file", start=start)

    if not isinstance(incoming, dict):
        return err("upload_patients", "Top-level JSON must be an object mapping patient IDs to records", start=start)

    if mode == "replace":
        save_patients(incoming)
        return ok("upload_patients", {"mode": mode, "total_patients": len(incoming)}, start=start)
    else:
        current = load_patients()
        current.update(incoming)
        save_patients(current)
        return ok("upload_patients", {"mode": mode, "total_patients": len(current)}, start=start)

# ------------- CRUD ------------- #
@router.get("/")
def view_all():
    start = time.time()
    return ok("view_all_patients", load_patients(), start=start)

@router.get("/{patient_id}")
def get_patient(patient_id: str):
    start = time.time()
    data = load_patients()
    if patient_id not in data:
        return err("get_patient", f"Patient {patient_id} not found", pid=patient_id, start=start)
    return ok("get_patient", data[patient_id], pid=patient_id, start=start)

@router.post("/create")
def create_patient(patient: Patient):
    start = time.time()
    data = load_patients()
    if patient.id in data:
        return err("create_patient", f"Patient {patient.id} already exists", pid=patient.id, start=start)
    data[patient.id] = patient.model_dump(exclude=["id"])
    save_patients(data)
    return ok("create_patient", data[patient.id], pid=patient.id, start=start)

@router.put("/update/{patient_id}")
def update_patient(patient_id: str, patient_update: PatientUpdate):
    start = time.time()
    data = load_patients()
    if patient_id not in data:
        return err("update_patient", f"Patient {patient_id} not found", pid=patient_id, start=start)
    patch = patient_update.model_dump(exclude_unset=True)
    data[patient_id].update(patch)
    save_patients(data)
    return ok("update_patient", data[patient_id], pid=patient_id, start=start)

@router.delete("/delete/{patient_id}")
def delete_patient(patient_id: str):
    start = time.time()
    data = load_patients()
    if patient_id not in data:
        return err("delete_patient", f"Patient {patient_id} not found", pid=patient_id, start=start)
    deleted = data.pop(patient_id)
    save_patients(data)
    return ok("delete_patient", {"deleted": deleted}, pid=patient_id, start=start)
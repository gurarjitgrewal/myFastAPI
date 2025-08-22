from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Optional, Literal, Annotated, List, Dict, Any
from pydantic import BaseModel, Field, computed_field, validator
from toolresultformatter import ToolResultFormatter
import json
import os
import time
import threading
import shutil
 
router = APIRouter(prefix="/patients", tags=["Patients"])
 
# Configuration
DATA_FILE = os.getenv("PATIENTS_DATA_FILE", "patients.json")
BACKUP_FILE = f"{DATA_FILE}.backup"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
_file_lock = threading.RLock()  # Reentrant lock for thread safety
 
# ------------- Data Access Layer ------------- #
class PatientRepository:
    """Thread-safe repository for patient data operations"""
    
    @staticmethod
    def _create_backup():
        """Create backup of current data file"""
        if os.path.exists(DATA_FILE):
            shutil.copy2(DATA_FILE, BACKUP_FILE)
    
    @staticmethod
    def _restore_backup():
        """Restore from backup if main file is corrupted"""
        if os.path.exists(BACKUP_FILE):
            shutil.copy2(BACKUP_FILE, DATA_FILE)
            return True
        return False
    
    @staticmethod
    def load_patients() -> Dict[str, Dict[str, Any]]:
        """Thread-safe loading of patient data with error recovery"""
        with _file_lock:
            if not os.path.exists(DATA_FILE):
                return {}
            
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not isinstance(data, dict):
                        raise ValueError("Invalid data format: expected dictionary")
                    return data
            except (json.JSONDecodeError, ValueError, IOError) as e:
                # Try to restore from backup
                if PatientRepository._restore_backup():
                    try:
                        with open(DATA_FILE, "r", encoding="utf-8") as f:
                            return json.load(f)
                    except:
                        pass
                
                # If all fails, return empty dict and log error
                print(f"Error loading patients data: {e}. Starting with empty dataset.")
                return {}
    
    @staticmethod
    def save_patients(data: Dict[str, Dict[str, Any]]) -> bool:
        """Thread-safe atomic saving of patient data"""
        with _file_lock:
            try:
                # Create backup before saving
                PatientRepository._create_backup()
                
                # Write to temporary file first (atomic operation)
                temp_file = f"{DATA_FILE}.tmp"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                # Atomic rename (on most filesystems)
                os.replace(temp_file, DATA_FILE)
                return True
                
            except (IOError, OSError) as e:
                print(f"Error saving patients data: {e}")
                # Clean up temp file if it exists
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass
                return False
 
# ------------- Validation Functions ------------- #
def validate_patient_data(patient: 'Patient') -> List[str]:
    """Comprehensive business logic validation for patient data"""
    errors = []
    
    # Age validation
    if not (0 < patient.age <= 150):
        errors.append("Age must be between 1 and 150 years")
    
    # Height validation (assuming meters)
    if not (0.3 <= patient.height <= 3.0):
        errors.append("Height must be between 0.3 and 3.0 meters")
    
    # Weight validation (assuming kg)
    if not (0.5 <= patient.weight <= 1000):
        errors.append("Weight must be between 0.5 and 1000 kg")
    
    # BMI validation
    bmi = patient.BMI
    if bmi < 10 or bmi > 100:
        errors.append(f"Calculated BMI ({bmi}) seems unrealistic")
    
    # Age-weight reasonableness check
    if patient.age < 18 and patient.weight > 200:
        errors.append("Weight seems unrealistic for given age")
    
    # Name validation
    if not patient.name.strip():
        errors.append("Name cannot be empty")
    
    if len(patient.name) > 100:
        errors.append("Name too long (max 100 characters)")
    
    # City validation
    if not patient.city.strip():
        errors.append("City cannot be empty")
    
    return errors
 
# ------------- Helper Functions ------------- #
def ok(command: str, data=None, pid: Optional[str] = None, start: float = None):
    """Success response formatter"""
    exec_time = (time.time() - start) if start else 0.0
    return ToolResultFormatter.format(
        command=command,
        stdout=data,
        execution_time=exec_time,
        patient_id=pid
    )
 
def err(command: str, message: str, pid: Optional[str] = None, start: float = None):
    """Error response formatter"""
    exec_time = (time.time() - start) if start else 0.0
    return ToolResultFormatter.format(
        command=command,
        stderr=message,
        exit_code=1,
        execution_time=exec_time,
        patient_id=pid
    )
 
def transaction_safe(func):
    """Decorator to ensure atomic operations with rollback capability"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        backup_data = PatientRepository.load_patients()
        
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            # Rollback on any error
            PatientRepository.save_patients(backup_data)
            command = func.__name__.replace('_', ' ')
            return err(command, f"Operation failed: {str(e)}", start=start_time)
    
    return wrapper
 
# ------------- Models ------------- #
class Patient(BaseModel):
    id: Annotated[str, Field(..., description="Patient ID", example="P001", min_length=1, max_length=50)]
    name: Annotated[str, Field(..., min_length=1, max_length=100, description="Patient full name")]
    city: Annotated[str, Field(..., min_length=1, max_length=100, description="Patient city")]
    age: Annotated[int, Field(..., ge=1, le=150, description="Patient age in years")]
    gender: Literal['male', 'female', 'other']
    height: Annotated[float, Field(..., ge=0.3, le=3.0, description="Height in meters")]
    weight: Annotated[float, Field(..., ge=0.5, le=1000.0, description="Weight in kilograms")]
 
    @validator('name', 'city')
    def validate_text_fields(cls, v):
        """Validate and clean text fields"""
        if not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v.strip()
    
    @validator('id')
    def validate_patient_id(cls, v):
        """Validate patient ID format"""
        v = v.strip()
        if not v:
            raise ValueError("Patient ID cannot be empty")
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Patient ID can only contain letters, numbers, hyphens, and underscores")
        return v
 
    @computed_field
    @property
    def BMI(self) -> float:
        """Calculate BMI with proper error handling"""
        if self.height <= 0:
            return 0.0
        return round(self.weight / (self.height ** 2), 2)
 
    @computed_field
    @property
    def verdict(self) -> str:
        """BMI category determination"""
        bmi = self.BMI
        if bmi <= 0:
            return "Invalid BMI"
        elif bmi < 18.5:
            return "Underweight"
        elif 18.5 <= bmi < 24.9:
            return "Normal weight"
        elif 25 <= bmi < 29.9:
            return "Overweight"
        else:
            return "Obesity"
    
    def __init__(self, **data):
        """Initialize with additional validation"""
        super().__init__(**data)
        validation_errors = validate_patient_data(self)
        if validation_errors:
            raise ValueError(f"Validation failed: {'; '.join(validation_errors)}")
 
class PatientUpdate(BaseModel):
    name: Optional[Annotated[str, Field(min_length=1, max_length=100)]] = None
    city: Optional[Annotated[str, Field(min_length=1, max_length=100)]] = None
    age: Optional[Annotated[int, Field(ge=1, le=150)]] = None
    gender: Optional[Literal['male', 'female', 'other']] = None
    height: Optional[Annotated[float, Field(ge=0.3, le=3.0)]] = None
    weight: Optional[Annotated[float, Field(ge=0.5, le=1000.0)]] = None
 
    @validator('name', 'city')
    def validate_text_fields(cls, v):
        """Validate and clean text fields"""
        if v is not None and not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v.strip() if v else v
 
# ------------- File Upload ------------- #
@router.post("/upload")
async def upload_patients(
    file: UploadFile = File(..., description="JSON file containing patients data"),
    mode: Literal["replace", "merge"] = "replace"
):
    """
    Upload patients JSON file with enhanced validation and error handling.
    - 'replace': completely overwrite existing data
    - 'merge': update existing entries and add new ones
    """
    start = time.time()
    
    if not file.filename.lower().endswith(".json"):
        return err("upload_patients", "Only .json files are allowed", start=start)
    
    # Check file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        return err("upload_patients", f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB", start=start)
    
    if len(content) == 0:
        return err("upload_patients", "Empty file provided", start=start)
    
    try:
        incoming = json.loads(content.decode('utf-8'))
    except json.JSONDecodeError as e:
        return err("upload_patients", f"Invalid JSON format: {str(e)}", start=start)
    except UnicodeDecodeError:
        return err("upload_patients", "File encoding error. Please use UTF-8 encoding", start=start)
 
    if not isinstance(incoming, dict):
        return err("upload_patients", "JSON must be an object mapping patient IDs to patient records", start=start)
    
    # Validate all incoming patient data
    validation_errors = []
    valid_patients = {}
    
    for patient_id, patient_data in incoming.items():
        try:
            if not isinstance(patient_data, dict):
                validation_errors.append(f"Patient {patient_id}: data must be an object")
                continue
            
            # Add ID to the data for validation
            patient_data_with_id = {"id": patient_id, **patient_data}
            patient = Patient(**patient_data_with_id)
            valid_patients[patient_id] = patient.dict(exclude={"id"})
            
        except Exception as e:
            validation_errors.append(f"Patient {patient_id}: {str(e)}")
    
    if validation_errors:
        return err("upload_patients", f"Validation errors: {'; '.join(validation_errors[:5])}", start=start)
    
    # Perform the upload operation
    try:
        if mode == "replace":
            if not PatientRepository.save_patients(valid_patients):
                return err("upload_patients", "Failed to save patient data", start=start)
            total_count = len(valid_patients)
        else:
            current = PatientRepository.load_patients()
            current.update(valid_patients)
            if not PatientRepository.save_patients(current):
                return err("upload_patients", "Failed to save merged patient data", start=start)
            total_count = len(current)
        
        return ok("upload_patients", {
            "mode": mode,
            "uploaded_patients": len(valid_patients),
            "total_patients": total_count,
            "message": f"Successfully {mode}d {len(valid_patients)} patients"
        }, start=start)
        
    except Exception as e:
        return err("upload_patients", f"Upload operation failed: {str(e)}", start=start)
 
# ------------- CRUD Operations ------------- #
@router.get("/")
def get_all_patients():
    """Retrieve all patients with their computed fields"""
    start = time.time()
    try:
        data = PatientRepository.load_patients()
        
        # Enrich with computed fields
        enriched_data = {}
        for patient_id, patient_data in data.items():
            try:
                patient = Patient(id=patient_id, **patient_data)
                enriched_data[patient_id] = patient.dict(exclude={"id"})
            except Exception as e:
                print(f"Warning: Invalid patient data for {patient_id}: {e}")
                enriched_data[patient_id] = patient_data  # Return raw data if validation fails
        
        return ok("get_all_patients", {
            "patients": enriched_data,
            "count": len(enriched_data)
        }, start=start)
        
    except Exception as e:
        return err("get_all_patients", f"Failed to retrieve patients: {str(e)}", start=start)
 
@router.get("/{patient_id}")
def get_patient(patient_id: str):
    """Retrieve a specific patient by ID"""
    start = time.time()
    
    try:
        data = PatientRepository.load_patients()
        
        if patient_id not in data:
            return err("get_patient", f"Patient {patient_id} not found", pid=patient_id, start=start)
        
        # Create patient object to get computed fields
        patient = Patient(id=patient_id, **data[patient_id])
        return ok("get_patient", patient.dict(exclude={"id"}), pid=patient_id, start=start)
        
    except Exception as e:
        return err("get_patient", f"Failed to retrieve patient: {str(e)}", pid=patient_id, start=start)
 
@router.post("/create-patient")
def create_patient(patient: Patient):
    """Create a new patient with full validation"""
    start = time.time()
    
    # Manual transaction handling for proper FastAPI parameter detection
    backup_data = PatientRepository.load_patients()
    
    try:
        data = PatientRepository.load_patients()
        
        if patient.id in data:
            return err("create_patient", f"Patient {patient.id} already exists", pid=patient.id, start=start)
        
        # Save patient data (excluding ID as it's the key)
        data[patient.id] = patient.dict(exclude={"id"})
        
        if not PatientRepository.save_patients(data):
            # Rollback on save failure
            PatientRepository.save_patients(backup_data)
            return err("create_patient", "Failed to save patient data", pid=patient.id, start=start)
        
        return ok("create_patient", {
            "patient": patient.dict(exclude={"id"}),
            "message": f"Patient {patient.id} created successfully"
        }, pid=patient.id, start=start)
        
    except Exception as e:
        # Rollback on any error
        PatientRepository.save_patients(backup_data)
        return err("create_patient", f"Failed to create patient: {str(e)}", pid=patient.id, start=start)
 
 
@router.delete("/{patient_id}")
def delete_patient(patient_id: str):
    """Delete a patient by ID"""
    start = time.time()
    
    # Manual transaction handling for proper FastAPI parameter detection
    backup_data = PatientRepository.load_patients()
    
    try:
        data = PatientRepository.load_patients()
        
        if patient_id not in data:
            return err("delete_patient", f"Patient {patient_id} not found", pid=patient_id, start=start)
        
        deleted_patient = data.pop(patient_id)
        
        if not PatientRepository.save_patients(data):
            # Rollback on save failure
            PatientRepository.save_patients(backup_data)
            return err("delete_patient", "Failed to save data after deletion", pid=patient_id, start=start)
        
        return ok("delete_patient", {
            "deleted_patient": deleted_patient,
            "message": f"Patient {patient_id} deleted successfully"
        }, pid=patient_id, start=start)
        
    except Exception as e:
        # Rollback on any error
        PatientRepository.save_patients(backup_data)
        return err("delete_patient", f"Failed to delete patient: {str(e)}", pid=patient_id, start=start)
 
# ------------- Utility Endpoints ------------- #
@router.get("/stats/summary")
def get_patient_statistics():
    """Get statistical summary of all patients"""
    start = time.time()
    
    try:
        data = PatientRepository.load_patients()
        
        if not data:
            return ok("get_patient_statistics", {
                "total_patients": 0,
                "message": "No patients found"
            }, start=start)
        
        patients = []
        for patient_id, patient_data in data.items():
            try:
                patient = Patient(id=patient_id, **patient_data)
                patients.append(patient)
            except Exception:
                continue  # Skip invalid patients
        
        if not patients:
            return ok("get_patient_statistics", {
                "total_patients": len(data),
                "valid_patients": 0,
                "message": "No valid patients found"
            }, start=start)
        
        # Calculate statistics
        ages = [p.age for p in patients]
        bmis = [p.BMI for p in patients]
        gender_counts = {}
        verdict_counts = {}
        
        for patient in patients:
            gender_counts[patient.gender] = gender_counts.get(patient.gender, 0) + 1
            verdict_counts[patient.verdict] = verdict_counts.get(patient.verdict, 0) + 1
        
        stats = {
            "total_patients": len(patients),
            "age_stats": {
                "min": min(ages),
                "max": max(ages),
                "average": round(sum(ages) / len(ages), 1)
            },
            "bmi_stats": {
                "min": min(bmis),
                "max": max(bmis),
                "average": round(sum(bmis) / len(bmis), 1)
            },
            "gender_distribution": gender_counts,
            "bmi_categories": verdict_counts
        }
        
        return ok("get_patient_statistics", stats, start=start)
        
    except Exception as e:
        return err("get_patient_statistics", f"Failed to calculate statistics: {str(e)}", start=start)
 

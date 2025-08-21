from fastapi import APIRouter
from pydantic import BaseModel
from model import SimpleEmailData, DynamicSpamDetector

router = APIRouter(prefix="/spam", tags=["Spam Detection"])

# Initialize model
data_gen = SimpleEmailData()
detector = DynamicSpamDetector()
emails, labels = [], []

class EmailRequest(BaseModel):
    text: str

class NewData(BaseModel):
    text: str
    label: int

@router.post("/train")
def train_model():
    for _ in range(50):
        e, l = data_gen.generate_email()
        emails.append(e)
        labels.append(l)
    detector.initial_training(emails, labels)
    return {"message": "Training complete", "total_emails": len(detector.all_emails)}

@router.post("/predict")
def predict_email(request: EmailRequest):
    label, confidence = detector.predict_email(request.text)
    return {"prediction": "spam" if label == 1 else "not spam", "confidence": confidence}

@router.post("/new-input")
def new_input(request: NewData):
    detector.learn_from_new_email(request.text, request.label)
    return {"message": "New input recorded and model retrained"}

@router.get("/evaluate")
def evaluate_model():
    test_emails, test_labels = [], []
    for _ in range(30):
        e, l = data_gen.generate_email()
        test_emails.append(e)
        test_labels.append(l)
    acc = detector.evaluate(test_emails, test_labels)
    return {"accuracy": acc}
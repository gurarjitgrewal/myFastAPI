# toolresultformatter.py
import uuid, json, time
from datetime import datetime
from typing import Dict, Any, Optional

class ToolResultFormatter:
    @staticmethod
    def format(
        command: str,
        stdout: Any = None,
        stderr: str = "",
        exit_code: int = 0,
        execution_time: Optional[float] = None,
        patient_id: Optional[str] = None,
        step_index: int = 0
    ) -> Dict[str, Any]:
        if execution_time is None:
            execution_time = 0.0
        success = exit_code == 0
        stdout_str = json.dumps(stdout) if isinstance(stdout, (dict, list)) else str(stdout or "")

        return {
            "toolResultId": str(uuid.uuid4()),
            "toolName": "PatientManagerAPI",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "conversationId": str(uuid.uuid4()),
            "conversationMessageId": str(uuid.uuid4()),
            "userContext": {"userId": "api_user", "sessionId": str(uuid.uuid4())},
            "metadata": {
                "dataType": "application/json" if isinstance(stdout, (dict, list)) else "text/plain",
                "dataSize": len(stdout_str) + len(stderr),
                "intent": command,
                "description": f"Executed patient operation: {command}",
                "accessibility": "public",
                "requiresPostProcessing": False,
                "suggestedTools": [],
                "contentSummary": {
                    "fields": list(stdout.keys()) if isinstance(stdout, dict) else [],
                    "recordCount": len(stdout) if isinstance(stdout, list) else (1 if stdout else 0)
                },
                "confidence": 1.0 if success else 0.0
            },
            "payload": {
                "command": command,
                "stdout": stdout,
                "stderr": stderr,
                "exitCode": exit_code,
                "success": success,
                "executionTime": execution_time,
                "patientId": patient_id
            },
            "stepIndex": step_index,
            "parentToolResultId": None,
            "status": 0 if success else 1
        }
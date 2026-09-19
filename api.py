import os
import shutil
import tempfile
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
from fastapi import Depends
from sqlalchemy.orm import Session
from database import get_db, InspectionRecord

# Import your existing OCR and validation pipeline
from legal_metrology_ocr import analyze_package_label

app = FastAPI(title="MetroScan Legal Metrology API")

# Allow Vite frontend to communicate with FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Friendly display names for PCR 2011 rule items
FIELD_DISPLAY_NAMES = {
    "mrp": "Maximum Retail Price (MRP)",
    "net_quantity": "Net Quantity Declared",
    "mfg_date": "Date of Manufacture / Packing",
    "manufacturer": "Manufacturer / Packer Details",
    "consumer_care": "Consumer Care Contact Details",
    "unit_sale_price": "Unit Sale Price (USP)",
    "expiry": "Best Before / Expiry Date",
}

# Legal standards for comparison cards
EXPECTED_STANDARDS = {
    "mrp": "Must declare Maximum Retail Price inclusive of all taxes in standard format (e.g. ₹ / Rs.).",
    "net_quantity": "Must declare quantity in SI units (g, kg, ml, l) with prescribed font height on Principal Display Panel.",
    "mfg_date": "Must declare month and year of manufacture or packing.",
    "manufacturer": "Must state complete name and address of the manufacturer, packer, or importer.",
    "consumer_care": "Must state name, address, telephone number, and email address of consumer care cell.",
    "unit_sale_price": "Must state unit sale price where required under PCR 2011.",
    "expiry": "Must declare expiry or best-before period for relevant or perishable commodities.",
}

@app.get("/api/inspections")
def get_inspections(db: Session = Depends(get_db)):
    records = db.query(InspectionRecord).order_by(InspectionRecord.created_at.desc()).all()
    return [rec.to_dict() for rec in records]

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "MetroScan OCR Backend"}


@app.post("/api/inspect")
async def inspect_package(file: UploadFile = File(...), 
    db: Session = Depends(get_db)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Please upload an image."
        )

    # Save uploaded file temporarily for OpenCV and PaddleOCR
    suffix = os.path.splitext(file.filename or "")[-1] or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        # Run your pipeline
        analysis = analyze_package_label(tmp_path, use_gemini=True)

        compliance = analysis.get("compliance", {})
        final_fields = analysis.get("final_fields", {})
        field_status = compliance.get("field_status", {})

        checks = []
        check_id = 1
        passed_count = 0
        failed_count = 0

        # Build list of mandatory check items
        for field_key, is_declared in field_status.items():
            field_data = final_fields.get(field_key, {})
            is_uncertain = field_data.get("status") == "uncertain"
            is_pass = bool(is_declared) and not is_uncertain

            if is_pass:
                passed_count += 1
                detected_val = (field_data.get("value") or field_data.get("evidence") or "Declared and verified on packaging.")
            else:
                failed_count += 1
                detected_val = (field_data.get("evidence") or "Not visibly declared on package.")

            # detected_val = (
            #     field_data.get("value")
            #     or field_data.get("evidence")
            #     or "Not visibly declared on package."
            # )

            checks.append({
                "id": check_id,
                "key": field_key,
                "name": FIELD_DISPLAY_NAMES.get(field_key, field_key.replace("_", " ").title()),
                "status": "PASS" if is_pass else "FAIL",
                "detected": detected_val,
                "expected": EXPECTED_STANDARDS.get(field_key, "Standard Legal Metrology (PCR 2011) requirement."),
                "evidence": field_data.get("evidence", ""),
                "pointer": field_data.get("pointer_location"),
            })
            check_id += 1

        # Map compliance verdict to frontend status badge string
        raw_verdict = (compliance.get("verdict") or "").lower()
        if "supervision" in raw_verdict:
            status = "NEED HUMAN SUPERVISION"
        elif "non-compliant" in raw_verdict:
            status = "NON-COMPLIANT"
        else:
            status = "COMPLIANT"

        # Unique report identifier and formatted timestamp
        report_id = f"MT-{datetime.now().strftime('%Y%m%d%H%M%S')[-6:]}"
        formatted_date = datetime.now().strftime("%d %b %Y, %I:%M %p")

        # return {
        #     "id": report_id,
        #     "productName": "Scanned Commodity",
        #     "date": formatted_date,
        #     "status": status,
        #     "totalChecks": len(checks),
        #     "passedChecks": passed_count,
        #     "failedChecks": failed_count,
        #     "checks": checks,
        # }

        result_payload = {
        "id": report_id,
        "productName": "Scanned Commodity",
        "date": formatted_date,
        "status": status,
        "totalChecks": len(checks),
        "passedChecks": passed_count,
        "failedChecks": failed_count,
        "checks": checks,
        }

        record = InspectionRecord(
            id=report_id,
            product_name=result_payload["productName"],
            status=result_payload["status"],
            total_checks=result_payload["totalChecks"],
            passed_checks=result_payload["passedChecks"],
            failed_checks=result_payload["failedChecks"],
            checks_json=json.dumps(checks)
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        return result_payload

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
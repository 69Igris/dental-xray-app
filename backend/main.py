from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pydicom
import numpy as np
from PIL import Image
import io
import base64
import requests
import os
import tempfile
import google.generativeai as genai
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Dental X-ray Analysis API")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY")

if not GEMINI_API_KEY or not ROBOFLOW_API_KEY:
    raise ValueError("Missing required environment variables: GEMINI_API_KEY or ROBOFLOW_API_KEY")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://dental-xray-app-liart.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/convert")
async def convert_dicom_to_image(file: UploadFile = File(...)):
    try:
        file_data = await file.read()

        dicom_data = pydicom.dcmread(io.BytesIO(file_data))

        if dicom_data.file_meta.TransferSyntaxUID.is_compressed:
            dicom_data.decompress()

        pixel_array = dicom_data.pixel_array

        pixel_array = (pixel_array - pixel_array.min()) / (pixel_array.max() - pixel_array.min()) * 255
        pixel_array = pixel_array.astype("uint8")  

        image = Image.fromarray(pixel_array)
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")  
        buffer.seek(0)

        image_base64 = base64.b64encode(buffer.read()).decode("utf-8")
        return {"imageBase64": f"data:image/jpeg;base64,{image_base64}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to convert DICOM file: {str(e)}")

@app.post("/analyze")
async def analyze_xray(file: UploadFile = File(...)):
    try:
        file_data = await file.read()

        import base64
        image_base64 = base64.b64encode(file_data).decode("utf-8")

        response = requests.post(
            ROBOFLOW_URL,
            params={"api_key": ROBOFLOW_API_KEY},
            data=image_base64,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Roboflow API error")

        analysis_results = response.json()
        return {"diagnosticReport": analysis_results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)



if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')


ROBOFLOW_URL = "https://detect.roboflow.com/adr/6"

def convert_dicom_to_image(dicom_file_path: str) -> str:
    """Convert DICOM file to base64 encoded PNG image"""
    try:
        dicom_data = pydicom.dcmread(dicom_file_path)
        
        pixel_array = dicom_data.pixel_array
        
        pixel_array = pixel_array.astype(float)
        pixel_array = ((pixel_array - pixel_array.min()) / 
                      (pixel_array.max() - pixel_array.min()) * 255).astype(np.uint8)
        
        image = Image.fromarray(pixel_array)
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_base64}"
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error converting DICOM: {str(e)}")

def call_roboflow_api(image_base64: str) -> dict:
    """Call Roboflow API for object detection"""
    try:
        response = requests.post(
            ROBOFLOW_URL,
            params={
                "api_key": ROBOFLOW_API_KEY,
                "confidence": 30,
                "overlap": 50
            },
            data=image_base64,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, 
                              detail=f"Roboflow API error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"API call failed: {str(e)}")

def generate_diagnostic_report_with_gemini(predictions: dict, image_metadata: Optional[dict] = None) -> str:
    """Generate diagnostic report using Gemini AI"""
    
    if not GEMINI_API_KEY:
        return generate_basic_diagnostic_report(predictions)
    
    try:
        if not predictions.get('predictions'):
            findings_text = "No pathologies detected in the dental X-ray analysis."
        else:
            findings = []
            for pred in predictions['predictions']:
                class_name = pred.get('class', 'Unknown')
                confidence = pred.get('confidence', 0) * 100
                x = pred.get('x', 0)
                y = pred.get('y', 0)
                
                if x < predictions.get('image', {}).get('width', 1000) / 3:
                    location = "left side"
                elif x > 2 * predictions.get('image', {}).get('width', 1000) / 3:
                    location = "right side"
                else:
                    location = "central region"
                
                findings.append(f"- {class_name} detected in {location} with {confidence:.1f}% confidence")
            
            findings_text = "\n".join(findings)
        
        prompt = f"""You are an experienced dental radiologist reviewing a dental X-ray analysis. Based on the automated detection results below, generate a professional diagnostic report in clinical language.

DETECTION RESULTS:
{findings_text}

Please provide a structured diagnostic report with the following sections:

1. CLINICAL FINDINGS: Summarize what was detected
2. RADIOGRAPHIC INTERPRETATION: Clinical significance of findings
3. RECOMMENDATIONS: Suggested follow-up care or treatment considerations
4. CLINICAL NOTES: Any additional observations or disclaimers

Guidelines:
- Use professional medical terminology
- Be concise but thorough
- Include confidence levels appropriately
- Mention the automated nature of detection
- Add standard radiological disclaimers
- Keep the tone professional and clinical

Format the response clearly with section headers."""

        response = model.generate_content(prompt)
        
        if response.text:
            return response.text
        else:
            return generate_basic_diagnostic_report(predictions)
            
    except Exception as e:
        print(f"Gemini AI error: {str(e)}")
        return generate_basic_diagnostic_report(predictions)

def generate_basic_diagnostic_report(predictions: dict) -> str:
    """Generate a basic diagnostic report as fallback"""
    if not predictions.get('predictions'):
        return """DENTAL RADIOGRAPHIC ANALYSIS REPORT

CLINICAL FINDINGS:
No pathologies detected in the submitted dental X-ray image. The automated analysis did not identify any cavities or periapical lesions.

RADIOGRAPHIC INTERPRETATION:
The dental structures appear within normal limits on this automated screening.

RECOMMENDATIONS:
- Continue routine dental care and regular check-ups
- Clinical correlation with physical examination recommended
- This automated analysis should be reviewed by a qualified dental professional

CLINICAL NOTES:
This report is generated through automated image analysis and should be used as a screening tool only. Professional clinical interpretation by a qualified dentist is recommended for definitive diagnosis."""

    report_parts = []
    report_parts.append("DENTAL RADIOGRAPHIC ANALYSIS REPORT\n")
    
    report_parts.append("CLINICAL FINDINGS:")
    for pred in predictions['predictions']:
        confidence = pred.get('confidence', 0) * 100
        class_name = pred.get('class', 'Unknown pathology')
        x = pred.get('x', 0)
        
        if x < predictions.get('image', {}).get('width', 1000) / 3:
            location = "left side"
        elif x > 2 * predictions.get('image', {}).get('width', 1000) / 3:
            location = "right side"
        else:
            location = "central region"
        
        report_parts.append(f"- {class_name.title()} identified in {location} ({confidence:.1f}% confidence)")
    
    report_parts.append("\nRADIOGRAPHIC INTERPRETATION:")
    report_parts.append("The automated analysis has identified potential pathological findings that require clinical attention.")
    
    report_parts.append("\nRECOMMENDations:")
    report_parts.append("- Immediate clinical evaluation recommended")
    report_parts.append("- Further diagnostic imaging may be warranted")
    report_parts.append("- Professional dental consultation advised")
    
    report_parts.append("\nCLINICAL NOTES:")
    report_parts.append("This automated analysis should be confirmed by clinical examination. Results are for screening purposes only.")
    
    return "\n".join(report_parts)

@app.post("/upload-and-analyze")
async def upload_and_analyze(file: UploadFile = File(...)):
    """Upload DICOM file, analyze with Roboflow, and generate diagnostic report"""
    
    if not file.filename.lower().endswith(('.dcm', '.rvg')):
        raise HTTPException(status_code=400, detail="Only .dcm and .rvg files are supported")
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.dcm') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        image_base64 = convert_dicom_to_image(temp_file_path)
        
        predictions = call_roboflow_api(image_base64)
        
        diagnostic_report = generate_diagnostic_report_with_gemini(predictions)
        
        os.unlink(temp_file_path)
        
        return JSONResponse({
            "success": True,
            "image": image_base64,
            "predictions": predictions,
            "diagnostic_report": diagnostic_report,
            "filename": file.filename
        })
        
    except Exception as e:
        if 'temp_file_path' in locals():
            try:
                os.unlink(temp_file_path)
            except:
                pass
        
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    gemini_status = "available" if GEMINI_API_KEY else "not configured"
    return {
        "status": "healthy",
        "gemini_ai": gemini_status,
        "roboflow_api": "configured"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Dental X-ray Analysis API", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    print("Starting Dental X-ray Analysis API...")
    print(f"Gemini AI: {'Enabled' if GEMINI_API_KEY else 'Disabled (using basic reports)'}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
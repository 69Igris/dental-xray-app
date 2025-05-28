# Dental X-ray Analysis App

This is a web application for analyzing dental X-ray images using AI-powered tools. The app supports `.dcm` (DICOM) files and standard image formats (`.jpg`, `.jpeg`, `.png`). It integrates with the Roboflow API for image analysis and provides diagnostic reports.

## Features
- Upload `.dcm`, `.jpg`, `.jpeg`, or `.png` files.
- Convert `.dcm` files to `.jpg` format for compatibility with Roboflow.
- Analyze images using the Roboflow API.
- Display diagnostic reports in the frontend.

## Technologies Used
- **Frontend**: React, Axios, CSS
- **Backend**: FastAPI, Pydicom, Pillow
- **API Integration**: Roboflow API

## Setup Instructions

### Prerequisites
- Node.js and npm installed for the frontend.
- Python 3.8+ installed for the backend.
- Virtual environment for Python dependencies.

---

### Frontend Setup
1. Navigate to the frontend directory
   
2. Install dependencies
    
3. Start the development server
4. Open the app in your browser at http://localhost:3000.


### Backend Setup
1. Navigate to the backend directory:
      cd backend
2. Create and activate a virtual environment:
    python -m venv venv
    source venv/bin/activate
3. Install dependencies:
    pip install -r requirements.txt
4. Start the FastAPI server:
    uvicorn main:app --reload
5. The backend will be available at http://localhost:8000.

### Environment Variables
Create a .env file in the backend directory with the following content:

  1. ROBOFLOW_API_KEY=your_roboflow_api_key
  2. GEMINI_API_KEY=your_gemini_api_key
Replace "your_roboflow_api_key" & "your_gemini_api_key" with your actual Roboflow API key.



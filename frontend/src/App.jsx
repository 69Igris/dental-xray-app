import React, { useState, useRef } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [imageData, setImageData] = useState(null);
  const [predictions, setPredictions] = useState(null);
  const [diagnosticReport, setDiagnosticReport] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [analysisComplete, setAnalysisComplete] = useState(false);
  const fileInputRef = useRef(null);
  const canvasRef = useRef(null);

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      const validTypes = ['.dcm', '.rvg'];
      const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
      
      if (validTypes.includes(fileExtension)) {
        setSelectedFile(file);
        setError('');
        setAnalysisComplete(false);
        setImageData(null);
        setPredictions(null);
        setDiagnosticReport('');
      } else {
        setError('Please select a valid DICOM file (.dcm or .rvg)');
        setSelectedFile(null);
      }
    }
  };

  const drawAnnotations = (imageElement, predictions) => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    
    // Set canvas size to match image
    canvas.width = imageElement.naturalWidth;
    canvas.height = imageElement.naturalHeight;
    
    ctx.drawImage(imageElement, 0, 0);
    
    // Draw bounding boxes
    if (predictions && predictions.predictions) {
      predictions.predictions.forEach((prediction) => {
        const { x, y, width, height, class: className, confidence } = prediction;
        
        // Calculate box coordinates (Roboflow returns center coordinates)
        const boxX = x - width / 2;
        const boxY = y - height / 2;
        
        // Set styles
        ctx.strokeStyle = '#ff0000';
        ctx.lineWidth = 3;
        ctx.fillStyle = 'rgba(255, 0, 0, 0.1)';
        ctx.font = '16px Arial';
        
        // Draw bounding box
        ctx.beginPath();
        ctx.rect(boxX, boxY, width, height);
        ctx.stroke();
        ctx.fill();
        
        // Draw label background
        const labelText = `${className} (${(confidence * 100).toFixed(1)}%)`;
        const textMetrics = ctx.measureText(labelText);
        const labelX = boxX;
        const labelY = boxY - 5;
        
        ctx.fillStyle = 'rgba(255, 0, 0, 0.8)';
        ctx.fillRect(labelX, labelY - 20, textMetrics.width + 10, 25);
        
        // Draw label text
        ctx.fillStyle = 'white';
        ctx.fillText(labelText, labelX + 5, labelY - 2);
      });
    }
  };

  const handleAnalyze = async () => {
    if (!selectedFile) {
      setError('Please select a file first');
      return;
    }

    setLoading(true);
    setError('');
    setAnalysisComplete(false);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await axios.post(
        'http://localhost:8000/upload-and-analyze',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          timeout: 60000, // 60 second timeout
        }
      );

      if (response.data.success) {
        setImageData(response.data.image);
        setPredictions(response.data.predictions);
        setDiagnosticReport(response.data.diagnostic_report);
        setAnalysisComplete(true);
        
        // Draw annotations after a short delay to ensure image is loaded
        setTimeout(() => {
          const img = new Image();
          img.onload = () => {
            drawAnnotations(img, response.data.predictions);
          };
          img.src = response.data.image;
        }, 100);
      } else {
        setError('Analysis failed. Please try again.');
      }
    } catch (err) {
      console.error('Analysis error:', err);
      if (err.code === 'ECONNABORTED') {
        setError('Analysis timed out. Please try again with a smaller file.');
      } else if (err.response?.status === 413) {
        setError('File too large. Please try a smaller DICOM file.');
      } else if (err.response?.data?.detail) {
        setError(`Error: ${err.response.data.detail}`);
      } else {
        setError('Analysis failed. Please check your connection and try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleNewAnalysis = () => {
    setSelectedFile(null);
    setImageData(null);
    setPredictions(null);
    setDiagnosticReport('');
    setAnalysisComplete(false);
    setError('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const formatReport = (report) => {
    return report.split('\n').map((line, index) => {
      if (line.trim() === '') return <br key={index} />;
      
      // Check if line is a header (all caps or ends with colon)
      if (line.match(/^[A-Z\s:]+:?$/) || line.includes('REPORT') || line.includes('FINDINGS') || line.includes('INTERPRETATION') || line.includes('RECOMMENDATIONS') || line.includes('NOTES')) {
        return <h4 key={index} className="report-header">{line}</h4>;
      }
      
      return <p key={index} className="report-line">{line}</p>;
    });
  };

  return (
    <div className="App">
      <header className="app-header">
        <h1>🦷 Dental X-ray Analysis System</h1>
        <p>AI-Powered Diagnostic Tool with Roboflow Detection & Gemini AI Reports</p>
      </header>

      <div className="main-container">
        <div className="left-panel">
          <div className="upload-section">
            <h2>Upload & Analyze</h2>
            
            {!analysisComplete && (
              <div className="file-upload">
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileSelect}
                  accept=".dcm,.rvg"
                  className="file-input"
                />
                
                {selectedFile && (
                  <div className="file-info">
                    <p><strong>Selected:</strong> {selectedFile.name}</p>
                    <p><strong>Size:</strong> {(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
                  </div>
                )}
                
                <button
                  onClick={handleAnalyze}
                  disabled={!selectedFile || loading}
                  className={`analyze-btn ${loading ? 'loading' : ''}`}
                >
                  {loading ? (
                    <>
                      <div className="spinner"></div>
                      Analyzing...
                    </>
                  ) : (
                    'Analyze X-ray'
                  )}
                </button>
              </div>
            )}

            {error && (
              <div className="error-message">
                <p>⚠️ {error}</p>
              </div>
            )}
          </div>

          <div className="image-section">
            {loading && (
              <div className="loading-state">
                <div className="spinner large"></div>
                <p>Processing DICOM file...</p>
                <p className="loading-detail">Converting, analyzing, and generating report...</p>
              </div>
            )}

            {imageData && (
              <div className="image-container">
                <h3>X-ray Analysis Results</h3>
                <div className="image-wrapper">
                  <canvas
                    ref={canvasRef}
                    className="annotated-image"
                    style={{ maxWidth: '100%', height: 'auto' }}
                  />
                </div>
                
                {predictions && (
                  <div className="detection-summary">
                    <h4>Detection Summary</h4>
                    {predictions.predictions && predictions.predictions.length > 0 ? (
                      <ul>
                        {predictions.predictions.map((pred, index) => (
                          <li key={index}>
                            <strong>{pred.class}</strong>: {(pred.confidence * 100).toFixed(1)}% confidence
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="no-detections">No pathologies detected</p>
                    )}
                  </div>
                )}

                <button onClick={handleNewAnalysis} className="new-analysis-btn">
                  Analyze New X-ray
                </button>
              </div>
            )}
          </div>
        </div>

        <div className="right-panel">
          <div className="report-section">
            <h2>📋 Diagnostic Report</h2>
            
            {loading && (
              <div className="report-loading">
                <div className="spinner"></div>
                <p>Generating AI diagnostic report...</p>
              </div>
            )}
            
            {diagnosticReport && (
              <div className="diagnostic-report">
                <div className="report-header-info">
                  <p className="ai-badge">🤖 Generated by Gemini AI</p>
                  <p className="timestamp">Generated: {new Date().toLocaleString()}</p>
                </div>
                
                <div className="report-content">
                  {formatReport(diagnosticReport)}
                </div>
                
                <div className="report-disclaimer">
                  <p className="disclaimer">
                    <strong>⚠️ Important:</strong> This automated analysis is for screening purposes only. 
                    Professional clinical interpretation by a qualified dentist is recommended for definitive diagnosis.
                  </p>
                </div>
              </div>
            )}
            
            {!diagnosticReport && !loading && (
              <div className="report-placeholder">
                <div className="placeholder-content">
                  <h3>🔍 Waiting for Analysis</h3>
                  <p>Upload a dental X-ray DICOM file to generate an AI-powered diagnostic report.</p>
                  
                  <div className="features-list">
                    <h4>Features:</h4>
                    <ul>
                      <li>✅ DICOM file support (.dcm, .rvg)</li>
                      <li>✅ Roboflow AI object detection</li>
                      <li>✅ Visual pathology annotations</li>
                      <li>✅ Gemini AI diagnostic reports</li>
                      <li>✅ Professional clinical language</li>
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <footer className="app-footer">
        <p>Dental X-ray Analysis System - Powered by Roboflow Detection & Google Gemini AI</p>
      </footer>
    </div>
  );
}

export default App;

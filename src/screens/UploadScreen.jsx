import React, { useRef, useState, useEffect } from 'react';
import { ArrowLeft, Camera, Check, UploadCloud, AlertCircle, Play, FolderOpen } from 'lucide-react';

export default function UploadScreen({ onBack, onRunAnalysis }) {
  const [previews, setPreviews] = useState({
    front: null,
    back: null,
    label: null,
  });

  const [files, setFiles] = useState({
    front: null,
    back: null,
    label: null,
  });

  const [isMobile, setIsMobile] = useState(false);

  // Detect whether the device is mobile/tablet
  useEffect(() => {
    const userAgent = navigator.userAgent || navigator.vendor || window.opera;
    const mobileRegex = /android|iphone|ipad|ipod|blackberry|iemobile|opera mini/i;
    const hasTouchScreen = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    
    setIsMobile(mobileRegex.test(userAgent) || (hasTouchScreen && window.innerWidth < 768));
  }, []);

  const fileInputRefs = {
    front: useRef(null),
    back: useRef(null),
    label: useRef(null),
  };

  const handleSlotClick = (key) => {
    if (fileInputRefs[key].current) {
      fileInputRefs[key].current.click();
    }
  };

  const handleFileChange = (key, event) => {
    const file = event.target.files[0];
    if (file) {
      const imageUrl = URL.createObjectURL(file);
      setPreviews((prev) => ({ ...prev, [key]: imageUrl }));
      setFiles((prev) => ({ ...prev, [key]: file }));
    }
  };

  const filledCount = Object.values(previews).filter(Boolean).length;
  const isReady = filledCount >= 1; // Enables analysis if at least one view is ready

  const handleTriggerAnalysis = () => {
    // Priority order: Label close-up -> Back Panel -> Front Panel
    const fileToScan = files.label || files.back || files.front;
    onRunAnalysis(fileToScan);
  };

  return (
    <div>
      {/* Top Header Bar */}
      <div className="screen-header-bar">
        <button onClick={onBack} className="back-action-btn">
          <ArrowLeft size={18} />
          <span>Back</span>
        </button>
        <h2 className="screen-page-title">Upload Package</h2>
        <div style={{ width: 40 }} />
      </div>

      {/* Guide Header */}
      <div className="upload-instruction-card">
        <div className="upload-icon-bubble">
          {isMobile ? <Camera size={24} /> : <UploadCloud size={24} />}
        </div>
        <h3>{isMobile ? "Capture 3 Package Angles" : "Upload 3 Package Images"}</h3>
        <p>
          {isMobile 
            ? "Tapping a slot opens your device camera. Keep text, MRP, batch number, and net weight in focus."
            : "Select image files from your computer. Ensure all mandatory metrology markings are clearly legible."}
        </p>
      </div>

      {/* 3-Slot Section */}
      <div className="slots-container-title">
        <h4>Required Views</h4>
        <span className="slots-counter">{filledCount} / 3 Ready</span>
      </div>

      <div className="slots-grid-3">
        {/* Front Panel Slot */}
        <div 
          onClick={() => handleSlotClick('front')} 
          className={`upload-slot-card ${previews.front ? 'filled' : ''}`}
        >
          <input 
            type="file" 
            accept="image/*" 
            capture={isMobile ? "environment" : undefined}
            ref={fileInputRefs.front} 
            onChange={(e) => handleFileChange('front', e)} 
            style={{ display: 'none' }} 
          />
          <div className="slot-preview-box">
            {previews.front ? (
              <img src={previews.front} alt="Front View" />
            ) : isMobile ? (
              <Camera size={28} />
            ) : (
              <FolderOpen size={28} />
            )}
          </div>
          <p className="slot-label">1. Front Panel</p>
          <p className="slot-desc">Principal Display Panel & Name</p>
          {previews.front && (
            <div className="slot-badge-check">
              <Check size={14} />
            </div>
          )}
        </div>

        {/* Back Panel Slot */}
        <div 
          onClick={() => handleSlotClick('back')} 
          className={`upload-slot-card ${previews.back ? 'filled' : ''}`}
        >
          <input 
            type="file" 
            accept="image/*" 
            capture={isMobile ? "environment" : undefined}
            ref={fileInputRefs.back} 
            onChange={(e) => handleFileChange('back', e)} 
            style={{ display: 'none' }} 
          />
          <div className="slot-preview-box">
            {previews.back ? (
              <img src={previews.back} alt="Back View" />
            ) : isMobile ? (
              <Camera size={28} />
            ) : (
              <FolderOpen size={28} />
            )}
          </div>
          <p className="slot-label">2. Back Panel</p>
          <p className="slot-desc">Manufacturer & Origin Details</p>
          {previews.back && (
            <div className="slot-badge-check">
              <Check size={14} />
            </div>
          )}
        </div>

        {/* Label Close-up Slot */}
        <div 
          onClick={() => handleSlotClick('label')} 
          className={`upload-slot-card ${previews.label ? 'filled' : ''}`}
        >
          <input 
            type="file" 
            accept="image/*" 
            capture={isMobile ? "environment" : undefined}
            ref={fileInputRefs.label} 
            onChange={(e) => handleFileChange('label', e)} 
            style={{ display: 'none' }} 
          />
          <div className="slot-preview-box">
            {previews.label ? (
              <img src={previews.label} alt="Label Close-up" />
            ) : isMobile ? (
              <Camera size={28} />
            ) : (
              <FolderOpen size={28} />
            )}
          </div>
          <p className="slot-label">3. Label Close-up</p>
          <p className="slot-desc">Clear MRP, Net Wt, Date</p>
          {previews.label && (
            <div className="slot-badge-check">
              <Check size={14} />
            </div>
          )}
        </div>
      </div>

      {/* Advisory Note */}
      <div className="info-notice">
        <AlertCircle size={18} className="info-notice-icon" />
        <p className="info-notice-text">
          {isMobile
            ? "Hold camera steady and flat under adequate lighting to ensure sharp OCR character recognition."
            : "Upload clear PNG or JPG photos without glare or heavy shadows over the declaration labels."}
        </p>
      </div>

      {/* Submit Action */}
      <button 
        disabled={!isReady} 
        onClick={handleTriggerAnalysis}
        className="run-inspection-btn"
      >
        <Play size={18} />
        <span>Run Compliance Verification</span>
      </button>
    </div>
  );
}
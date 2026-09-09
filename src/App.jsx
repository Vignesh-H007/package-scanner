import React, { useState, useEffect } from 'react';
import './App.css';
import Header from './components/Header';
import BottomNav from './components/BottomNav';
import DashboardScreen from './screens/DashboardScreen';
import UploadScreen from './screens/UploadScreen';
import ResultScreen from './screens/ResultScreen';
import HistoryScreen from './screens/HistoryScreen';
import ProfileScreen from './screens/ProfileScreen';
import ReportScreen from './screens/ReportScreen';

export default function App() {
  const [currentTab, setCurrentTab] = useState('dashboard');
  const [currentScreen, setCurrentScreen] = useState('dashboard'); 
  const [inspections, setInspections] = useState([]);
  const [activeResult, setActiveResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // Fetch persistent records on initial launch
  useEffect(() => {
    const fetchStoredInspections = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/inspections");
        if (res.ok) {
          const data = await res.json();
          setInspections(data);
        }
      } catch (err) {
        console.error("Could not retrieve inspection history:", err);
      }
    };
    fetchStoredInspections();
  }, []);

  const handleStartScan = () => {
    setCurrentScreen('upload');
  };

  const handleBackToDashboard = () => {
    setCurrentScreen('dashboard');
  };

  const handleRunAnalysis = async (fileToScan) => {
    if (!fileToScan) {
      alert("Please upload at least one image to inspect.");
      return;
    }

    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", fileToScan);

      const res = await fetch("http://localhost:8000/api/inspect", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error(`Server returned error code ${res.status}`);
      }

      const resultData = await res.json();
      setInspections((prev) => [resultData, ...prev]);
      setActiveResult(resultData);
      setCurrentScreen('result');
    } catch (err) {
      alert("Inspection failed: " + err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectInspection = (item) => {
    setActiveResult(item);
    setCurrentScreen('result');
  };

  const handleTabChange = (tab) => {
    setCurrentTab(tab);
    setCurrentScreen(tab);
  };

  const handleLogOut = () => {
    if (window.confirm("Are you sure you want to log out?")) {
      alert("Logged out successfully.");
    }
  };

  return (
    <div className="app-container">
      <Header 
        currentTab={currentTab} 
        setCurrentTab={handleTabChange} 
      />

      <main className="main-content">
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: '80px 0' }}>
            <h3 style={{ fontWeight: 800 }}>Analyzing Package...</h3>
            <p style={{ color: 'var(--text-secondary)', marginTop: 8, fontSize: '0.85rem' }}>
              Running PaddleOCR text detection & Second Gemini Legal Metrology audit
            </p>
          </div>
        ) : currentScreen === 'upload' ? (
          <UploadScreen 
            onBack={handleBackToDashboard} 
            onRunAnalysis={handleRunAnalysis} 
          />
        ) : currentScreen === 'result' ? (
          <ResultScreen 
            onBack={handleBackToDashboard}
            inspectionData={activeResult}
            onOpenReport={() => setCurrentScreen('report')}
          />
        ) : currentScreen === 'report' ? (
          <ReportScreen 
            onBack={() => setCurrentScreen('result')}
            inspectionData={activeResult}
          />
        ) : (
          <>
            {currentTab === 'dashboard' && (
              <>
              <DashboardScreen 
                inspections={inspections}
                onStartScan={handleStartScan}
                onSelectInspection={handleSelectInspection}
              />
              <BottomNav 
              currentTab={currentTab} 
              setCurrentTab={handleTabChange} 
              onOpenScan={handleStartScan} 
              />
              </>
            )}
            {currentTab === 'history' && (
              <>
              <HistoryScreen 
                inspections={inspections}
                onSelectInspection={handleSelectInspection}
              />
              <BottomNav 
              currentTab={currentTab} 
              setCurrentTab={handleTabChange} 
              onOpenScan={handleStartScan} 
              />
              </>
            )}
            {currentTab === 'profile' && (
              <>
              <ProfileScreen 
                onLogOut={handleLogOut}
              />
              <BottomNav 
              currentTab={currentTab} 
              setCurrentTab={handleTabChange} 
              onOpenScan={handleStartScan} 
              />
              </>
            )}
          </>
        )}
      </main>

      {currentScreen === 'dashboard' && (
        <BottomNav 
          currentTab={currentTab} 
          setCurrentTab={handleTabChange} 
          onOpenScan={handleStartScan} 
        />
      )}
    </div>
  );
}
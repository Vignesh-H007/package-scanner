import React from 'react';
import { LayoutDashboard, History, User, ScanLine } from 'lucide-react';

export default function BottomNav({ currentTab, setCurrentTab, onOpenScan }) {
  return (
    <div className="mobile-bottom-nav">
      <div className="bottom-nav-inner">
        <button
          onClick={() => setCurrentTab('dashboard')}
          className={`nav-tab-button ${currentTab === 'dashboard' ? 'active' : ''}`}
        >
          <LayoutDashboard size={20} />
          <span>Home</span>
        </button>

         <button
          onClick={() => setCurrentTab('report')}
          className={`nav-tab-button ${currentTab === 'report' ? 'active' : ''}`}
        >
          <LayoutDashboard size={20} />
          <span>Reports</span>
        </button>

        <div className="fab-wrapper">
          <button onClick={onOpenScan} aria-label="Scan package" className="scan-fab">
            <ScanLine size={24} />
          </button>
        </div>

        <button
          onClick={() => setCurrentTab('history')}
          className={`nav-tab-button ${currentTab === 'history' ? 'active' : ''}`}
        >
          <History size={20} />
          <span>History</span>
        </button>

        <button
          onClick={() => setCurrentTab('profile')}
          className={`nav-tab-button ${currentTab === 'profile' ? 'active' : ''}`}
        >
          <User size={20} />
          <span>Profile</span>
        </button>
      </div>
    </div>
  );
}
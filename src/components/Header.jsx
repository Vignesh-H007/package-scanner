import React from 'react';
import { ShieldCheck } from 'lucide-react';

export default function Header({ currentTab, setCurrentTab, officer = { name: "Arjun Kumar", id: "INSP-4567" } }) {
  return (
    <header className="site-header">
      <div className="header-inner">
        {/* Brand */}
        <div onClick={() => setCurrentTab('dashboard')} className="brand-group">
          <div className="brand-logo">
            <ShieldCheck size={22} />
          </div>
          <div>
            <h1 className="brand-title">Clix</h1>
            <p className="brand-subtitle">Legal Metrology</p>
          </div>
        </div>

        {/* Desktop Navigation */}
        <nav className="desktop-nav">
          <button
            onClick={() => setCurrentTab('dashboard')}
            className={currentTab === 'dashboard' ? 'active' : ''}
          >
            Dashboard
          </button>
          <button
            onClick={() => setCurrentTab('history')}
            className={currentTab === 'history' ? 'active' : ''}
          >
            History
          </button>
          <button
            onClick={() => setCurrentTab('profile')}
            className={currentTab === 'profile' ? 'active' : ''}
          >
            Profile & Help
          </button>
        </nav>

        {/* Inspector Identifier */}
        <div onClick={() => setCurrentTab('profile')} className="officer-badge">
          <div className="officer-details">
            <p className="officer-name">{officer.name}</p>
            <span className="officer-id">{officer.id}</span>
          </div>
          <div className="officer-avatar">AK</div>
        </div>
      </div>
    </header>
  );
}
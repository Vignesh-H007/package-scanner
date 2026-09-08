import React, { useState } from 'react';
import { ShieldCheck, ChevronDown, ChevronUp, HelpCircle, BookOpen, PhoneCall, LogOut } from 'lucide-react';

export default function ProfileScreen({ onLogOut }) {
  const [openHelpIndex, setOpenHelpIndex] = useState(0);

  const officer = {
    name: "Arjun Kumar",
    designation: "Legal Metrology Officer",
    id: "INSP-4567",
    zone: "Bangalore Urban & Industrial Zone"
  };

  const helpTopics = [
    {
      title: "How to take accurate package photos",
      icon: BookOpen,
      content: (
        <div>
          <p>For high OCR reading accuracy, ensure the following:</p>
          <ul>
            <li>Hold the camera parallel to the packaging surface.</li>
            <li>Avoid heavy reflections, glares, or shadows over text lines.</li>
            <li>Capture the entire Principal Display Panel (PDP) within the frame.</li>
          </ul>
        </div>
      )
    },
    {
      title: "PCR 2011 10 Mandatory Declarations",
      icon: HelpCircle,
      content: (
        <div>
          <p>Under the Legal Metrology (Packaged Commodities) Rules, every packaged commodity must declare:</p>
          <ul>
            <li>Name & address of Manufacturer / Packer / Importer</li>
            <li>Country of origin (for imported items)</li>
            <li>Common or generic name of the commodity</li>
            <li>Net quantity in standard SI units (g, kg, ml, l)</li>
            <li>Month and year of manufacture / packing / import</li>
            <li>Maximum Retail Price (MRP) inclusive of all taxes</li>
            <li>Consumer Care contact details (Name, Address, Phone, Email)</li>
            <li>Unit Sale Price (USP) and Batch/Lot number</li>
          </ul>
        </div>
      )
    },
    {
      title: "Support & Legal Escalation Desk",
      icon: PhoneCall,
      content: (
        <div>
          <p>Facing app anomalies or need an immediate legal clarification for a flagged seizure?</p>
          <p style={{ marginTop: 6 }}>
            <strong>Metrology Helpdesk:</strong> 1800-11-4000<br />
            <strong>Field Support Email:</strong> support@legalmetrology.gov.in
          </p>
        </div>
      )
    }
  ];

  const toggleAccordion = (index) => {
    setOpenHelpIndex(openHelpIndex === index ? null : index);
  };

  return (
    <div>
      <div className="section-header" style={{ marginBottom: 16 }}>
        <h2 className="screen-page-title" style={{ fontSize: '1.4rem' }}>Profile & Support</h2>
      </div>

      {/* Inspector Identification Card */}
      <div className="profile-card">
        <div className="profile-avatar-large">AK</div>
        <div className="profile-info">
          <h3>{officer.name}</h3>
          <p className="profile-designation">{officer.designation}</p>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>{officer.zone}</p>
          <span className="profile-id-chip">
            <ShieldCheck size={14} />
            Verified • {officer.id}
          </span>
        </div>
      </div>

      {/* Help & Support Section */}
      <div className="section-header" style={{ marginBottom: 12 }}>
        <h3>Guidelines & Field Help</h3>
      </div>

      <div className="help-section">
        {helpTopics.map((topic, i) => {
          const Icon = topic.icon;
          const isOpen = openHelpIndex === i;
          return (
            <div key={i} className="help-accordion-item">
              <button className="help-accordion-header" onClick={() => toggleAccordion(i)}>
                <div className="help-header-title">
                  <Icon size={18} color="var(--primary-blue)" />
                  <span>{topic.title}</span>
                </div>
                {isOpen ? <ChevronUp size={18} color="#94a3b8" /> : <ChevronDown size={18} color="#94a3b8" />}
              </button>
              {isOpen && <div className="help-accordion-body">{topic.content}</div>}
            </div>
          );
        })}
      </div>

      {/* Logout Action */}
      <button onClick={onLogOut} className="logout-action-btn">
        <LogOut size={18} />
        <span>Log Out of Session</span>
      </button>
    </div>
  );
}
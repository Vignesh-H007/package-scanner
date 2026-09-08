import React from 'react';
import { ScanLine, ArrowRight, CheckCircle2, XCircle, AlertTriangle, PackageCheck } from 'lucide-react';

export default function DashboardScreen({ onStartScan, onSelectInspection, inspections = [] }) {
  const totalAudits = inspections.length;
  const compliantCount = inspections.filter(i => i.status === 'COMPLIANT').length;
  const violationCount = inspections.filter(i => i.status === 'NON-COMPLIANT').length;
  const supervisionCount = inspections.filter(i => i.status === 'NEED HUMAN SUPERVISION').length;

  const stats = [
    { label: "Audits Completed", value: totalAudits, icon: PackageCheck, color: "#2563eb", bg: "#eff6ff" },
    { label: "Compliant", value: compliantCount, icon: CheckCircle2, color: "#16a34a", bg: "#dcfce7" },
    { label: "Violations Found", value: violationCount, icon: XCircle, color: "#e11d48", bg: "#ffe4e6" },
    { label: "Needs Supervision", value: supervisionCount, icon: AlertTriangle, color: "#d97706", bg: "#fef3c7" },
  ];

  const recentItem = inspections[0];

  return (
    <div className="dashboard-stack">
      {/* Hero Card */}
      <section className="hero-card">
        <span className="hero-pill">Legal Metrology (PCR 2011)</span>
        <h2 className="hero-title">Verify Package Compliance</h2>
        <p className="hero-desc">
          Capture package views to automatically inspect mandatory declarations including MRP, Net Quantity, and Country of Origin.
        </p>
        <button onClick={onStartScan} className="cta-button">
          <ScanLine size={18} />
          <span>Start New Inspection</span>
          <ArrowRight size={16} />
        </button>
      </section>

      {/* Summary KPIs */}
      <section>
        <div className="section-header">
          <h3>Inspection Summary</h3>
          <span>This Month</span>
        </div>

        <div className="stats-grid">
          {stats.map((stat, i) => {
            const Icon = stat.icon;
            return (
              <div key={i} className="stat-card">
                <div className="stat-icon" style={{ backgroundColor: stat.bg, color: stat.color }}>
                  <Icon size={18} />
                </div>
                <p className="stat-value">{stat.value}</p>
                <p className="stat-label">{stat.label}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* Recent Inspection Card */}
      <section className="recent-card">
        <div className="section-header">
          <h3>Recent Inspection</h3>
        </div>
        {recentItem ? (
          <div onClick={() => onSelectInspection(recentItem)} className="recent-item">
            <div>
              <p className="recent-name">{recentItem.productName || "Inspected Package"}</p>
              <p className="recent-sub">{recentItem.manufacturer ? `${recentItem.manufacturer} • ` : ''}ID: {recentItem.id}</p>
            </div>
            <span className={`status-badge ${
              recentItem.status === 'COMPLIANT' ? 'pass' : 
              recentItem.status === 'NON-COMPLIANT' ? 'fail' : 'supervision'
            }`}>
              {recentItem.status}
            </span>
          </div>
        ) : (
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            No scans performed yet. Click "Start New Inspection" to begin.
          </p>
        )}
      </section>
    </div>
  );
}
import React from 'react';
import { ArrowLeft, ShieldCheck, Download, Printer } from 'lucide-react';

export default function ReportScreen({ onBack, inspectionData, officer = { name: "Luffy", id: "INSP-4567" } }) {
  if (!inspectionData) {
    return (
      <div>
        <button onClick={onBack} className="back-action-btn">
          <ArrowLeft size={18} />
          <span>Back</span>
        </button>
        <p style={{ textAlign: 'center', marginTop: 40, color: 'var(--text-muted)' }}>
          No inspection record selected.
        </p>
      </div>
    );
  }

  const {
    id = "MT-2026-08842",
    productName = "Scanned Commodity",
    date = "08 Sep 2026, 11:52 AM",
    status = "NON-COMPLIANT",
    totalChecks = 5,
    passedChecks = 3,
    failedChecks = 2,
    checks = []
  } = inspectionData;

  const handlePrint = () => {
    window.print();
  };

  return (
    <div>
      {/* Action Header */}
      <div className="screen-header-bar">
        <button onClick={onBack} className="back-action-btn">
          <ArrowLeft size={18} />
          <span>Back</span>
        </button>
        <h2 className="screen-page-title">Inspection Report</h2>
        <button onClick={handlePrint} className="pdf-download-btn">
          <Download size={15} />
          <span>Save PDF</span>
        </button>
      </div>

      {/* Official Audit Printable Sheet */}
      <div className="report-sheet">
        {/* Brand Header */}
        <div className="report-header-row">
          <div className="brand-logo" style={{ width: 44, height: 44 }}>
            <ShieldCheck size={26} />
          </div>
          <div>
            <h1 className="brand-title" style={{ fontSize: '1.15rem' }}>MetroScan Official Report</h1>
            <p className="brand-subtitle">Legal Metrology (Packaged Commodities) Rules, 2011</p>
          </div>
        </div>

        {/* Legal Disclaimer */}
        <p className="report-legal-notice">
          This report is generated for preliminary statutory assessment purposes under the Legal Metrology Act, 2009. 
          Physical seizure or compound notices should be validated by an authorized Legal Metrology Officer.
        </p>

        {/* Inspection Meta Details */}
        <div className="report-meta-grid">
          <div className="report-meta-item">
            <label>Inspection ID</label>
            <p>{id}</p>
          </div>
          <div className="report-meta-item">
            <label>Date & Time</label>
            <p>{date}</p>
          </div>
          <div className="report-meta-item">
            <label>Inspector Name</label>
            <p>{officer.name}</p>
          </div>
          <div className="report-meta-item">
            <label>Officer ID</label>
            <p>{officer.id}</p>
          </div>
        </div>

        {/* Verified Parameters */}
        <h4 className="report-section-title">Verified Declarations</h4>
        <table className="report-details-table">
          <tbody>
            <tr>
              <td>Product Classification</td>
              <td>{productName}</td>
            </tr>
            {checks.map((chk) => (
              <tr key={chk.id || chk.key}>
                <td>{chk.name}</td>
                <td style={{ color: chk.status === 'PASS' ? 'var(--success)' : 'var(--danger)' }}>
                  {chk.status === 'PASS' ? 'Declared' : 'Missing / Invalid'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Audit Metrics */}
        <div className="report-summary-counts">
          <div className="report-count-box">
            <p className="report-count-val" style={{ 
              color: status === 'COMPLIANT' ? 'var(--success)' : status === 'NON-COMPLIANT' ? 'var(--danger)' : 'var(--warning)' 
            }}>
              {status}
            </p>
            <p className="report-count-lbl">Verdict</p>
          </div>
          <div className="report-count-box">
            <p className="report-count-val" style={{ color: 'var(--success)' }}>{passedChecks}</p>
            <p className="report-count-lbl">Mandatory Passed</p>
          </div>
          <div className="report-count-box">
            <p className="report-count-val" style={{ color: failedChecks > 0 ? 'var(--danger)' : 'var(--text-primary)' }}>
              {failedChecks}
            </p>
            <p className="report-count-lbl">Violations</p>
          </div>
        </div>
      </div>
    </div>
  );
}
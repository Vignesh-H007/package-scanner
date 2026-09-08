import React, { useState } from 'react';
import { ArrowLeft, Check, X, ChevronRight, AlertTriangle } from 'lucide-react';

export default function ResultScreen({ onBack, inspectionData, onOpenReport }) {
  const [selectedCheck, setSelectedCheck] = useState(null);

  if (!inspectionData) {
    return (
      <div>
        <div className="screen-header-bar">
          <button onClick={onBack} className="back-action-btn">
            <ArrowLeft size={18} />
            <span>Back</span>
          </button>
          <h2 className="screen-page-title">Compliance Result</h2>
          <div style={{ width: 40 }} />
        </div>
        <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-secondary)' }}>
          No inspection data available. Please perform an inspection first.
        </div>
      </div>
    );
  }

  const {
    id = "N/A",
    productName = "Inspected Commodity",
    date = "N/A",
    status = "NEED HUMAN SUPERVISION",
    totalChecks = 0,
    passedChecks = 0,
    failedChecks = 0,
    checks = []
  } = inspectionData;

  const getStatusBanner = (verdict) => {
    switch (verdict) {
      case 'COMPLIANT':
        return (
          <div className="result-status-banner status-compliant">
            <Check size={16} />
            <span>COMPLIANT</span>
          </div>
        );
      case 'NON-COMPLIANT':
        return (
          <div className="result-status-banner status-non-compliant">
            <X size={16} />
            <span>NON-COMPLIANT</span>
          </div>
        );
      default:
        return (
          <div className="result-status-banner status-supervision">
            <AlertTriangle size={16} />
            <span>NEED HUMAN SUPERVISION</span>
          </div>
        );
    }
  };

  return (
    <div>
      {/* Top Header Bar */}
      <div className="screen-header-bar">
        <button onClick={onBack} className="back-action-btn">
          <ArrowLeft size={18} />
          <span>Back</span>
        </button>
        <h2 className="screen-page-title">Compliance Result</h2>
        <div style={{ width: 40 }} />
      </div>

      {/* Hero Summary Card */}
      <div className="result-hero-card">
        {getStatusBanner(status)}
        <h3 className="result-product-title">{productName}</h3>
        <p className="result-meta-info">Report ID: {id} • {date}</p>

        {/* Test Count Info Bar */}
        <div className="test-counter-pill-row">
          <div className="test-count-box">
            <span className="test-count-number">{passedChecks} / {totalChecks}</span>
            <span className="test-count-label">Checks Passed</span>
          </div>
          <div className="test-sub-badges">
            <span className="sub-badge-pass">{passedChecks} Pass</span>
            {failedChecks > 0 && (
              <span className="sub-badge-fail">{failedChecks} Violations</span>
            )}
          </div>
        </div>
      </div>

      {/* Rules Checklist */}
      <div className="section-header" style={{ marginBottom: 12 }}>
        <h3>Mandatory Declarations (PCR 2011)</h3>
        <span>Click flagged items to review</span>
      </div>

      <div className="check-items-wrapper">
        {checks.length > 0 ? (
          checks.map((check) => {
            const isFailed = check.status === "FAIL";
            return (
              <div 
                key={check.id || check.key} 
                className={`check-item-row ${isFailed ? 'clickable' : ''}`}
                onClick={() => isFailed && setSelectedCheck(check)}
              >
                <div className="check-item-left">
                  <span className="check-num-badge">{check.id}</span>
                  <p className="check-title">{check.name}</p>
                </div>

                <div className="check-item-right">
                  {isFailed ? (
                    <>
                      <span className="tag-fail">
                        <X size={12} /> FAIL
                      </span>
                      <ChevronRight size={16} color="#94a3b8" />
                    </>
                  ) : (
                    <span className="tag-pass">
                      <Check size={12} /> PASS
                    </span>
                  )}
                </div>
              </div>
            );
          })
        ) : (
          <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>
            No check rules processed for this inspection.
          </div>
        )}
      </div>

      {/* Drill-down Detail Modal */}
      {selectedCheck && (
        <div className="modal-overlay" onClick={() => setSelectedCheck(null)}>
          <div className="detail-modal-sheet" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header-row">
              <div>
                <span className="tag-fail">
                  <X size={12} /> FAILED RULE
                </span>
                <h3 className="result-product-title" style={{ fontSize: '1.1rem', marginTop: 6 }}>
                  {selectedCheck.name}
                </h3>
              </div>
              <button className="close-sheet-btn" onClick={() => setSelectedCheck(null)}>
                <X size={18} />
              </button>
            </div>

            {/* Detected Card */}
            <div className="detail-comparison-card" style={{ borderLeft: '4px solid var(--danger)' }}>
              <p className="card-tag-header card-tag-detected">Detected On Packaging</p>
              <p className="comparison-body-text">{selectedCheck.detected || "Not visibly detected on package."}</p>
            </div>

            {/* Expected Standard Card */}
            <div className="detail-comparison-card" style={{ borderLeft: '4px solid var(--success)' }}>
              <p className="card-tag-header card-tag-expected">Required by PCR 2011</p>
              <p className="comparison-body-text">{selectedCheck.expected || "Legal declaration required under Metrology Rules."}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
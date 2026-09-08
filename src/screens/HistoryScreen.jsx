import React, { useState } from 'react';
import { Search, ChevronRight } from 'lucide-react';

export default function HistoryScreen({ inspections = [], onSelectInspection }) {
  const [filter, setFilter] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  const filteredInspections = inspections.filter((item) => {
    const matchesFilter =
      filter === 'ALL' ||
      (filter === 'COMPLIANT' && item.status === 'COMPLIANT') ||
      (filter === 'VIOLATIONS' && item.status === 'NON-COMPLIANT') ||
      (filter === 'REVIEW' && item.status === 'NEED HUMAN SUPERVISION');

    const matchesSearch =
      (item.productName || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (item.manufacturer || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (item.id || '').toLowerCase().includes(searchTerm.toLowerCase());

    return matchesFilter && matchesSearch;
  });

  const getStatusBadge = (status) => {
    switch (status) {
      case 'COMPLIANT':
        return <span className="status-badge pass">COMPLIANT</span>;
      case 'NON-COMPLIANT':
        return <span className="status-badge fail">VIOLATION</span>;
      default:
        return <span className="status-badge supervision">REVIEW</span>;
    }
  };

  return (
    <div>
      <div className="section-header" style={{ marginBottom: 16 }}>
        <h2 className="screen-page-title" style={{ fontSize: '1.4rem' }}>Inspection Log</h2>
        <span>{filteredInspections.length} recorded</span>
      </div>

      {/* Search & Filter Controls */}
      <div className="history-controls">
        <div className="search-input-wrapper">
          <Search size={18} className="search-input-icon" />
          <input
            type="text"
            className="search-input"
            placeholder="Search product, manufacturer, or ID..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="filter-chips-row">
          <button
            className={`filter-chip ${filter === 'ALL' ? 'active' : ''}`}
            onClick={() => setFilter('ALL')}
          >
            All Inspections
          </button>
          <button
            className={`filter-chip ${filter === 'VIOLATIONS' ? 'active' : ''}`}
            onClick={() => setFilter('VIOLATIONS')}
          >
            Violations
          </button>
          <button
            className={`filter-chip ${filter === 'REVIEW' ? 'active' : ''}`}
            onClick={() => setFilter('REVIEW')}
          >
            Need Review
          </button>
          <button
            className={`filter-chip ${filter === 'COMPLIANT' ? 'active' : ''}`}
            onClick={() => setFilter('COMPLIANT')}
          >
            Compliant
          </button>
        </div>
      </div>

      {/* Results List */}
      <div className="history-items-list">
        {filteredInspections.length > 0 ? (
          filteredInspections.map((item) => (
            <div
              key={item.id}
              className="history-item-card"
              onClick={() => onSelectInspection(item)}
            >
              <div className="history-item-details">
                <h4>{item.productName || "Package Inspection"}</h4>
                <p>{item.manufacturer ? `${item.manufacturer} • ` : ''}{item.date}</p>
                <p style={{ color: 'var(--text-muted)', marginTop: 3 }}>
                  ID: {item.id} • {item.passedChecks !== undefined ? `${item.passedChecks}/${item.totalChecks} Passed` : ''}
                </p>
              </div>

              <div className="history-item-right">
                {getStatusBadge(item.status)}
                <ChevronRight size={18} color="#94a3b8" />
              </div>
            </div>
          ))
        ) : (
          <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)' }}>
            No inspection records match your filter criteria.
          </div>
        )}
      </div>
    </div>
  );
}
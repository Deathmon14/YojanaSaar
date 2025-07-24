// frontend/src/SchemeCard.js
import React from 'react';

function SchemeCard({ scheme }) {
  return (
    <div className="scheme-card">
      <h5>{scheme.title}</h5>
      {scheme.category && <p><strong>Category:</strong> {scheme.category}</p>}
      {scheme.state && <p><strong>State:</strong> {scheme.state}</p>}
      {scheme.link && <p><a href={scheme.link} target="_blank" rel="noopener noreferrer">Learn More</a></p>}
    </div>
  );
}

export default SchemeCard;
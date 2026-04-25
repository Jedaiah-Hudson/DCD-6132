import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import "./ContractDetailPage.css";

const ROLE_OPTIONS = ["Prime", "Sub", "Teaming"];

const ContractDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();

  const [contract, setContract] = useState(null);
  const [role, setRole] = useState("");

  // Fetch contract dynamically (NOT hardcoded)
  useEffect(() => {
    const fetchContract = async () => {
      try {
        const res = await fetch(`/api/contracts/${id}`);
        const data = await res.json();
        setContract(data);
        setRole(data.role || "");
      } catch (err) {
        console.error("Error loading contract:", err);
      }
    };

    fetchContract();
  }, [id]);

  const handleGenerateRFP = () => {
    navigate(`/rfp/${id}`);
  };

  if (!contract) return <div>Loading...</div>;

  return (
    <div className="contract-detail-container">
      <h2>{contract.title}</h2>

      <div className="contract-meta">
        <p><strong>Agency:</strong> {contract.agency}</p>
        <p><strong>NAICS:</strong> {contract.naics}</p>
        <p><strong>Due Date:</strong> {contract.due_date}</p>
        <p><strong>Partner:</strong> {contract.partner}</p>
        <p><strong>Status:</strong> {contract.status}</p>
      </div>

      {/* 🔥 ROLE SELECTOR */}
      <div className="role-section">
        <label className="role-label">Role</label>
        <div className="role-buttons">
          {ROLE_OPTIONS.map((option) => (
            <button
              key={option}
              className={`role-btn ${role === option ? "active" : ""}`}
              onClick={() => setRole(option)}
            >
              {option}
            </button>
          ))}
        </div>
      </div>

      {/* 🔥 GENERATE RFP BUTTON */}
      <button className="rfp-button" onClick={handleGenerateRFP}>
        Generate RFP
      </button>
    </div>
  );
};

export default ContractDetailPage;
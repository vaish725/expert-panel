// Appears once the recommendation is ready; shows the structured
// recommendation with editable fields, Approve / Edit / Reopen actions
// mapped to the client -> server WS messages (PRD 11).

import { useState } from "react";
import type { StructuredRecommendation } from "../../types/debate";
import "./ReviewPanel.css";

interface ReviewPanelProps {
  recommendation: StructuredRecommendation;
  options: string[];
  exportedPath: string | null;
  onApprove: () => void;
  onEdit: (recommendation: StructuredRecommendation) => void;
  onReopen: (followUpQuestion: string) => void;
}

export function ReviewPanel({ recommendation, options, exportedPath, onApprove, onEdit, onReopen }: ReviewPanelProps) {
  const [editing, setEditing] = useState(false);
  const [recommendedOption, setRecommendedOption] = useState(recommendation.recommended_option ?? "");
  const [confidenceNote, setConfidenceNote] = useState(recommendation.confidence_note);
  const [showReopen, setShowReopen] = useState(false);
  const [followUp, setFollowUp] = useState("");

  if (exportedPath) {
    return (
      <div className="review-panel review-panel--done">
        <h2>Report exported</h2>
        <p className="review-panel__path">{exportedPath}</p>
      </div>
    );
  }

  function saveEdit() {
    onEdit({ ...recommendation, recommended_option: recommendedOption || null, confidence_note: confidenceNote });
    setEditing(false);
  }

  return (
    <div className="review-panel">
      <h2>Recommendation</h2>

      {editing ? (
        <div className="review-panel__edit">
          <label>
            Recommended option
            <select value={recommendedOption} onChange={(e) => setRecommendedOption(e.target.value)}>
              <option value="">No clear recommendation</option>
              {options.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label>
            Confidence note
            <textarea value={confidenceNote} onChange={(e) => setConfidenceNote(e.target.value)} rows={4} />
          </label>
          <div className="review-panel__actions">
            <button onClick={saveEdit}>Save edit</button>
            <button className="review-panel__secondary" onClick={() => setEditing(false)}>
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <>
          <p className="review-panel__recommended">{recommendation.recommended_option ?? "No clear recommendation"}</p>
          <p className="review-panel__confidence">{recommendation.confidence_note}</p>

          {Object.entries(recommendation.tradeoffs).map(([option, items]) => (
            <div key={option} className="review-panel__tradeoff">
              <h3>{option}</h3>
              <ul>
                {items.map((item, index) => (
                  <li key={index}>
                    ({item.direction}) {item.claim_id}
                  </li>
                ))}
              </ul>
            </div>
          ))}

          {recommendation.unresolved_disagreements.length > 0 && (
            <div className="review-panel__unresolved">
              <h3>Unresolved disagreements</h3>
              <p>{recommendation.unresolved_disagreements.join(", ")}</p>
            </div>
          )}

          <div className="review-panel__actions">
            <button onClick={onApprove}>Approve</button>
            <button className="review-panel__secondary" onClick={() => setEditing(true)}>
              Edit
            </button>
            <button className="review-panel__secondary" onClick={() => setShowReopen((v) => !v)}>
              Reopen
            </button>
          </div>

          {showReopen && (
            <div className="review-panel__reopen">
              <input
                type="text"
                placeholder="Follow-up question for one more round"
                value={followUp}
                onChange={(e) => setFollowUp(e.target.value)}
              />
              <button
                disabled={!followUp.trim()}
                onClick={() => {
                  onReopen(followUp);
                  setShowReopen(false);
                  setFollowUp("");
                }}
              >
                Reopen debate
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

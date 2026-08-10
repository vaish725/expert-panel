// Live claims list, grouped by status (contested / resolved), each showing
// raised-by persona and stance (PRD 11).

import type { Claim } from "../../types/debate";
import "./Ledger.css";

interface LedgerProps {
  claims: Claim[];
}

export function Ledger({ claims }: LedgerProps) {
  const contested = claims.filter((c) => c.contested);
  const resolved = claims.filter((c) => !c.contested);

  return (
    <aside className="ledger">
      <h2 className="ledger__title">Claims ledger ({claims.length})</h2>

      <LedgerGroup title={`Contested (${contested.length})`} claims={contested} />
      <LedgerGroup title={`Resolved (${resolved.length})`} claims={resolved} />
    </aside>
  );
}

function LedgerGroup({ title, claims }: { title: string; claims: Claim[] }) {
  return (
    <div className="ledger__group">
      <h3 className="ledger__group-title">{title}</h3>
      {claims.length === 0 && <p className="ledger__empty">None yet</p>}
      <ul className="ledger__list">
        {claims.map((claim) => (
          <li key={claim.id} className={`ledger__claim ${claim.contested ? "" : "ledger__claim--resolved"}`}>
            <div className="ledger__claim-meta">
              <span className="ledger__claim-id">{claim.id}</span>
              <span className="ledger__claim-stance">{claim.stance}</span>
              <span className="ledger__claim-persona">{claim.raised_by}</span>
            </div>
            <p className="ledger__claim-text">{claim.text}</p>
            {claim.reinforced_count > 0 && (
              <span className="ledger__claim-reinforced">reinforced x{claim.reinforced_count}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

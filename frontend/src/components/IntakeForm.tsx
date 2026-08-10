// Initial decision submission: question, 2+ options, optional context, and
// the min/max round bounds (PRD 5.1). Not part of the live debate view, so
// it doesn't get its own subfolder like the 4 components PRD 11 names.

import { useState } from "react";
import type { FormEvent } from "react";
import { startDebate } from "../api";
import "./IntakeForm.css";

interface IntakeFormProps {
  onStarted: (threadId: string) => void;
}

export function IntakeForm({ onStarted }: IntakeFormProps) {
  const [decisionQuestion, setDecisionQuestion] = useState("");
  const [options, setOptions] = useState(["", ""]);
  const [context, setContext] = useState("");
  const [minRounds, setMinRounds] = useState(2);
  const [maxRounds, setMaxRounds] = useState(6);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = decisionQuestion.trim().length > 0 && options.filter((o) => o.trim()).length >= 2;

  function updateOption(index: number, value: string) {
    setOptions((prev) => prev.map((o, i) => (i === index ? value : o)));
  }

  function addOption() {
    setOptions((prev) => [...prev, ""]);
  }

  function removeOption(index: number) {
    setOptions((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!canSubmit || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const { thread_id } = await startDebate({
        decision_question: decisionQuestion,
        options: options.filter((o) => o.trim()),
        context,
        min_rounds: minRounds,
        max_rounds: maxRounds,
      });
      onStarted(thread_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "failed to start debate");
      setSubmitting(false);
    }
  }

  return (
    <form className="intake-form" onSubmit={handleSubmit}>
      <h1>Expert Panel</h1>
      <p className="intake-form__subtitle">
        Submit a real decision and watch 4 personas debate it with a live claims ledger and convergence detection.
      </p>

      <label>
        Decision question
        <textarea
          value={decisionQuestion}
          onChange={(e) => setDecisionQuestion(e.target.value)}
          placeholder="Should I take the startup offer or stay at my corporate job?"
          rows={2}
          required
        />
      </label>

      <label>Options</label>
      {options.map((option, index) => (
        <div key={index} className="intake-form__option-row">
          <input
            type="text"
            value={option}
            onChange={(e) => updateOption(index, e.target.value)}
            placeholder={`Option ${index + 1}`}
          />
          {options.length > 2 && (
            <button type="button" className="intake-form__remove" onClick={() => removeOption(index)}>
              remove
            </button>
          )}
        </div>
      ))}
      <button type="button" className="intake-form__secondary" onClick={addOption}>
        Add option
      </button>

      <label>
        Context (optional)
        <textarea
          value={context}
          onChange={(e) => setContext(e.target.value)}
          placeholder="Any relevant details, constraints, or numbers."
          rows={3}
        />
      </label>

      <div className="intake-form__rounds">
        <label>
          Min rounds
          <input type="number" min={1} max={maxRounds} value={minRounds} onChange={(e) => setMinRounds(Number(e.target.value))} />
        </label>
        <label>
          Max rounds
          <input type="number" min={minRounds} max={8} value={maxRounds} onChange={(e) => setMaxRounds(Number(e.target.value))} />
        </label>
      </div>

      {error && <p className="intake-form__error">{error}</p>}

      <button type="submit" disabled={!canSubmit || submitting}>
        {submitting ? "Starting..." : "Start debate"}
      </button>
    </form>
  );
}

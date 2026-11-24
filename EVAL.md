# Evaluation (33 trials)

Ground truth = ClinicalTrials.gov structured fields, hidden from the model.

| Field | Accuracy | Precision (when answered) | Abstained | Hallucinations blocked |
|---|---|---|---|---|
| phase | 56% | 77% | 61% | 0 |
| indication | 88% | 88% | 0% | 0 |
| sponsor | 6% | 67% | 91% | 0 |
| primary_endpoint | 87% | 87% | 9% | 2 |
| status | 3% | 50% | 94% | 0 |

**Overall precision:** 84% · **Residual wrong-answer rate:** 16% · **Ungrounded claims blocked by provenance guard:** 2

Note: the residual rate includes answers that are grounded in the text but disagree with the registry's structured field (e.g. synonym conditions), so it is an upper bound on true hallucination. Spot-check these by hand.

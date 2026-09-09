# TensorMesh Agent Evaluation Scorecard

- Grounding Fidelity Score: **1.000**
- Hallucination Rate: **0.000**
- DFARS Sanctions Precision: **1.000**
- DFARS Sanctions Recall: **1.000**
- Mean Decision Latency: **49.58 ms**

| Case | Expected | Predicted | DFARS | Grounded |
|---|---|---|---|---|
| high_grade_compliant | VIABLE | VIABLE | True | 3/3 |
| sub_economic_cutoff | NON_VIABLE | NON_VIABLE | None | 3/3 |
| covert_ningbo_transshipment | NON_VIABLE | NON_VIABLE | False | 3/3 |
| structurally_discontinuous_fault_block | STRUCTURAL_REJECT | STRUCTURAL_REJECT | None | 3/3 |
| borderline_supervisor_review | SUPERVISOR_REVIEW | SUPERVISOR_REVIEW | None | 1/1 |

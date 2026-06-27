# Workflow: Explain a Topic in the HHS-HCC Model

<required_reading>
**Always pre-loaded:** `references/model-overview.md`

**Then load based on the user's question:**

| User asks about | Load |
|---|---|
| Adult model rules, severity buckets, RXC, HCC_ED | `references/adult-model.md` |
| Child model rules, severity 6_7 / 8PLUS collapsing | `references/child-model.md` |
| Infant model, maturity, severity grid, AGE0/AGE1 swap | `references/infant-model.md` |
| Which claims qualify, lab/DME exclusion, bill types, qualifying CPT/HCPCS | `references/claim-qualification.md` |
| DX→CC, CC→HCC, hierarchy, group collapsing, MCE edits | `references/cc-hcc-hierarchies.md` |
| RXC variables, HCC×RXC interactions, RXC_09 triple | `references/rxc-interactions.md` |
| CSR factors, HIOS variant codes, BY2025 schedule change | `references/csr-adjustments.md` |
| Risk transfer formula, PLRS, IDF, GCF, AV, ARF, metal optimization | `references/risk-transfer-formula.md` |
| Year-over-year changes, what changed in BY{year} | `references/year-changes.md` |
| Where coefficients live, how to load them | `references/coefficient-data.md` |

If the question spans multiple topics, load multiple references.
</required_reading>

<process>
## Step 1: Identify the topic

Map the user's question to one or more references. Common patterns:
- "How is the infant score calculated?" → `infant-model.md`
- "What is HCC042?" → look up in `coefficient-data.md` and the appropriate sub-model reference
- "Why did our risk score change between 2024 and 2025?" → `year-changes.md` plus the relevant sub-model reference
- "How does sickle cell get scored?" → `cc-hcc-hierarchies.md` (DX gating) + sub-model reference (severity placement) + `year-changes.md` (BY2025 change)
- "What's a positive risk transfer?" → `risk-transfer-formula.md`

## Step 2: Read the relevant references

Use the Read tool. Skim the table of contents first if needed.

## Step 3: Answer the question

Cite specific references and section names. Pull concrete numbers (coefficient values, severity placements, factor schedules) from the data files when relevant.

For computational questions ("what's the score for X"), redirect to `workflows/calculate-score.md` instead of estimating.

For lookup questions ("what's the BY2025 Silver coefficient for HHS_HCC042"), use `scripts/lookup.py` rather than guessing.

## Step 4: Disclose source/uncertainty

Always disclose:
- The benefit year the answer applies to. **Always ask the user** which year they're working with — never assume. Coefficients change every year and several model rules change at year boundaries.
- Which CMS source the answer is grounded in (SAS, DIY tables, Python release)
- Any known disagreements between sources (e.g., the AGE0_MALE/AGE1_MALE swap omitted from CMS Python BY2025)
</process>

<success_criteria>
This workflow is complete when:
- [ ] The user's question is answered with specific references cited
- [ ] Concrete numbers are pulled from canonical data, not estimated
- [ ] Year and source uncertainty are disclosed
- [ ] If the question turned out to need calculation or lookup, the user was redirected to the appropriate workflow
</success_criteria>

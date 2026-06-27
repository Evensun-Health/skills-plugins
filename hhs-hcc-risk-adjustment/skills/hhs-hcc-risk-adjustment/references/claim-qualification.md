<scope>
HHS-HCC scoring is **claims-based**: a diagnosis code only contributes to a member's risk score if it appears on a **qualifying** medical claim during the benefit year. Not every claim with an HCC-mapped diagnosis qualifies. This reference describes which claim types qualify, why some don't, and how the qualifying-claim filter affects scoring.

This rule is the source of one of the most common surprises in HHS-HCC scoring: a member can have a qualifying ICD-10 code on a claim and still get no HCC for it, because the claim isn't of a type that CMS accepts as evidence of a clinician-documented condition.
</scope>

<why_qualifying_claims>
The HHS-HCC model is meant to capture conditions that a **clinician has assessed and documented** during a face-to-face (or equivalent telehealth) encounter with the patient. CMS's view is that diagnosis codes appearing on certain claim types are unreliable as evidence of a clinician's diagnostic determination — for example:

- A **lab claim** for a blood draw may carry a diagnosis code that justifies the test (e.g., "diabetes follow-up") even if the lab itself never saw the patient and didn't make any new diagnostic finding.
- A **DME claim** for an oxygen tank may carry "COPD" as the medical-necessity justification, but the equipment supplier didn't diagnose anything.
- A **radiology technical-component claim** for an MRI films-only charge may carry a referring diagnosis without any radiologist read attached.

Allowing diagnoses from these claim types would let issuers inflate risk scores by attaching aggressive diagnoses to ancillary services. The qualifying-claim filter limits credit to claims where a clinician had direct contact with the patient and the documentation reflects that clinician's own assessment.
</why_qualifying_claims>

<qualifying_claim_categories>
Three categories of medical claims qualify, each with its own rule:

<category name="Inpatient (UB-04 / UB form)">
**Rule:** Inpatient hospital, hospice, and SNF claims qualify automatically — no CPT/HCPCS check required.

**SQL implementation:** `form_type = 'I' AND right(bill_type, 3) IN ('111','117','112','113','114')`

**Bill types decoded:**
- 111 — Inpatient hospital, admit through discharge
- 112 — Inpatient hospital, interim first claim
- 113 — Inpatient hospital, interim continuing claim
- 114 — Inpatient hospital, interim last claim
- 117 — Inpatient hospital, replacement of prior claim

The reasoning: an inpatient stay always involves attending and admitting physicians documenting in the chart. The HCPCS-level filter isn't needed because the encounter itself is established by the bill type.

**Tagged in SQL as:** `'BillTypeIP'`
</category>

<category name="Outpatient UB-04 / institutional">
**Rule:** Outpatient hospital, clinic, RHC, FQHC, critical access, home health, and similar UB-form claims qualify **only if** they carry a CPT/HCPCS code that's on the CMS-published qualifying-services list.

**SQL implementation:** `form_type = 'I' AND left(right(bill_type, 3), 2) IN ('13','71','73','76','77','85','87') AND service_code in qualifying list`

**Bill type categories decoded:**
- 13x — Outpatient hospital
- 71x — Rural Health Clinic (RHC)
- 73x — Federally Qualified Health Center (FQHC)
- 76x — Community Mental Health Center (CMHC)
- 77x — Federally Qualified Health Center, alternate
- 85x — Critical Access Hospital
- 87x — Special facility / hospice non-hospital

**Tagged in SQL as:** `'UBServiceCode'`
</category>

<category name="Professional (CMS-1500 / HCFA)">
**Rule:** Professional claims (form_type = 'P', the CMS-1500 form, used by individual physicians, group practices, and similar) qualify **only if** they carry a CPT/HCPCS code on the qualifying list.

**SQL implementation:** `form_type = 'P' AND service_code in qualifying list`

This is the largest source of qualifying claims in most plans. Office visits, surgical procedures performed in office or ASC, ED professional fees, etc.

**Tagged in SQL as:** `'HCFAServiceCode'`
</category>
</qualifying_claim_categories>

<qualifying_service_codes>
The CMS-published list of qualifying CPT/HCPCS codes is what distinguishes a face-to-face clinician encounter from an ancillary service. Conceptually, qualifying codes include:

- **E&M codes** — office visits (99202-99215), hospital visits (99221-99239), ED visits (99281-99285), preventive visits, telehealth E&M, etc.
- **Surgical procedures** with a clinician present (e.g., 10000-69999 series) — the surgeon is making the diagnosis
- **Some specialty visits** — psychiatric (90832-90837), medical nutrition therapy (97802-97804), etc.
- **Telemedicine services** — qualifying codes when modifiers indicate physician-patient interaction
- **Selected radiologist interpretation codes** — the read itself, not the technical component

Common **non-qualifying** services (HCC credit denied even if diagnosis on claim):
- Pure laboratory work (80000-89999) — the lab didn't see the patient
- DME (E-codes) — supplier delivery
- Pure technical-component imaging (TC modifier) — equipment usage only, no read
- Ambulance transport (A0000 series) — transport, not assessment
- Drug administration HCPCS (J-codes) without an associated E&M

CMS publishes the qualifying list as a CPT/HCPCS table with effective-date ranges. The list is updated annually as new CPT codes are released.

**Local lookup:** `references/service-code-reference.csv` contains the full qualifying-services list (21,109 rows). To check whether a CPT/HCPCS code qualifies a claim for risk adjustment, grep for the code in the `SRVC_CD` column and check that `CPT_HCPCSELGBL_RISKADJSTMT_IND = Y` and the service date falls within `SRVC_CD_EFCTV_STRT_DT` / `SRVC_CD_EFCTV_END_DT`. `SRVC_TYPE_CD` distinguishes CPT (01) from HCPCS (02).

**In the user's SQL:** `dbo.ServiceCodeReference` table, with `CPT_HCPCSELGBL_RISKADJSTMT_IND = 'Y'` flagging qualifying codes. The lookup is gated by the service date: `service_date BETWEEN SRVC_CD_EFCTV_strt_DT AND SRVC_CD_EFCTV_END_DT`.

Note: the CMS Python release does **not** implement this filter — the Python software assumes the user has already filtered to qualifying claims before submitting diagnoses to it. The user's SQL implementation does the filter, which is a meaningful value-add.
</qualifying_service_codes>

<example_walkthroughs>
**Example 1: Diabetic patient, three claims, one qualifying:**
- January: Office visit with PCP, diagnosis E11.65 (T2DM with hyperglycemia). CPT 99214. **Qualifies.** HCC021 (Diabetes with Acute Complications) flags.
- March: Lab claim, A1c blood draw, diagnosis E11.65. CPT 83036. **Does not qualify** (lab work). No HCC contribution from this claim.
- June: Endocrinologist visit, diagnosis E11.65. CPT 99213. **Qualifies.** HCC021 already flagged from January, but the June claim independently re-qualifies.

The patient gets HCC021 credit. The lab claim is irrelevant for scoring.

**Example 2: Cancer patient seen only by lab and infusion nurse:**
- Throughout year: Multiple chemotherapy infusion claims, diagnosis C61 (prostate cancer). Most carry HCPCS J-codes for the chemo agents and 96413 for infusion administration. **96413 does qualify** (it's on the list as a chemotherapy administration encounter); but a J-code-only claim with no qualifying CPT does not.
- Throughout year: Lab CBC and PSA panel, diagnosis C61. **Does not qualify.**
- One office visit in February: oncologist E&M, CPT 99214, diagnosis C61. **Qualifies.**

The patient gets HCC012 (Prostate Cancer) credit from the qualifying February visit and qualifying infusion administration claims. If the patient had no qualifying visit or qualifying infusion administration in the year, the cancer would not score even though pharmacy and lab claims exist.

**Example 3: Inpatient admission, no professional claim:**
- Hospital admission for CHF, bill type 111. Diagnoses include I50.9 (heart failure). **Qualifies automatically** (inpatient bill type — no CPT check needed).

The CHF HCC flags from the inpatient claim alone.
</example_walkthroughs>

<implication_for_scoring>
**Practical implications:**

1. **Risk score requires at least one qualifying claim** carrying the relevant diagnosis. Pharmacy data can drive RXC variables but cannot drive HCC variables.
2. **Aggressive coding on lab claims is wasted** — these claims don't contribute to score even with valid HCC-mapped DX.
3. **A single qualifying claim is enough.** There is no "two-encounter" or "frequency" rule in HHS-HCC (unlike some Medicare validation rules).
4. **Member-level result is binary per HCC.** Either the member has at least one qualifying claim with a diagnosis mapping to that HCC, or they don't. Volume of claims doesn't increase the HCC weight.
5. **EDGE submission requires qualifying claims.** Issuers submitting to CMS's EDGE server should only submit claims that meet the qualifying-claim criteria. Submitting non-qualifying claims doesn't help score and can create reconciliation noise.
6. **Supplemental diagnoses** (a CMS mechanism for adding diagnoses from chart audits or non-claim sources) bypass the qualifying-claim filter — see the user's SQL `diy_supplemental` table and the `add_delete_flag = 'A'` rule at lines 208-211 of the DIY Model Script.

**RXC variables (Adult model only) use a different mechanism:** RXCs come from NDC codes on **pharmacy claims** (no qualifying-claim filter — any pharmacy claim with an NDC on the RXC list counts) or HCPCS J-codes on medical claims (with the same medical-claim-type rules as HCCs). Pharmacy claims do not count for HCC scoring directly — only their RXC mapping flows into the model.
</implication_for_scoring>

<related_policies>
- **Paid-through date filter:** the SQL also filters claims by `paid_date <= @paidthrough` to ensure only adjudicated claims are scored. EDGE has its own equivalent filter; using late-paying claims past the snapshot deadline causes reconciliation drift.
- **Service date in benefit year:** claims must have a service date in the benefit year. A January 2025 service date counts for BY2025 even if the claim is paid in March 2025. A claim with December 2024 service date does not count for BY2025 even if paid in 2025.
- **Denials:** the SQL has a commented-out denial filter (e.g., `--and deniedflag = 'A'` at line 248). Most implementations include only "accepted" / paid claims, excluding denied ones. CMS EDGE accepts both, but only paid claims with valid edit codes count for scoring.
</related_policies>

<canonical_data>
- **Qualifying CPT/HCPCS list:** `references/service-code-reference.csv` (local, 21,109 rows). Also published by CMS as part of the EDGE Server Business Rules and the DIY Tables (Table 2 in cy20XX-diy-tables-*.xlsx). In the user's SQL: `dbo.ServiceCodeReference` table.
- **Bill type rules:** codified in the user's SQL Model Script (lines 158-187 of `DIY-Model-Script/DIY Model Script.sql`).
- **Supplemental diagnosis rules:** CMS EDGE Server documentation defines the schema; user's SQL implements the add/delete logic at lines 201-211 of the DIY Model Script.
</canonical_data>

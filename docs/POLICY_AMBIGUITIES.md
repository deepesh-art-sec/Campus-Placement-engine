# College Placement Offer Policy Ambiguities & Configurable Toggles

In real-world campus recruitment, placement policies issued by collegiate Training & Placement (T&P) cells frequently contain implicit rules, contradictory phrasing, and edge-case loopholes. When companies make offers or revise CTCs, these ambiguities lead to student protests, disputes, and coordinator confusion.

The Placement Engine eliminates implicit bias by converting **every known policy ambiguity into an explicit, typed configuration toggle** with an audit-backed default.

---

## Catalog of Ambiguities & Architectural Resolution

### 1. Salary Band Inclusivity at the Exact Cut-Off
- **Written Ambiguity**: Policy states *"Students with an offer below 10 LPA may appear for Dream companies of 10 LPA and above."* Does an offer of exactly 10.00 LPA qualify as a Dream offer, or is it strictly `> 10.00 LPA`?
- **Configurable Toggle**: `is_threshold_inclusive: bool`
- **Default Value**: `True`
- **Chosen Rationale**: In Indian engineering colleges, standard convention treats milestone CTCs (e.g. 10.0 LPA, 12.0 LPA, 20.0 LPA) inclusively ($CTC \ge \text{Threshold}$). If an institution wishes to enforce strict exceedance, setting `is_threshold_inclusive = False` requires $> 10.00\text{ LPA}$ (e.g. 10.01 LPA).
- **Edge-Case Behavior**:
  - If `is_threshold_inclusive = True`: A drive with 10.0 LPA CTC allows students seeking a Dream upgrade.
  - If `is_threshold_inclusive = False`: A drive with 10.0 LPA CTC is blocked under `CLAUSE-2.2-DRIVE-BELOW-DREAM-THRESHOLD`.

---

### 2. Threshold Metric: Total CTC vs. Fixed Base Pay
- **Written Ambiguity**: Announcement brochures advertise *"CTC: 12 LPA"*, but the appointment letter reveals a 7.5 LPA fixed base with 4.5 LPA in retention bonuses, ESOPs, and variables. Does the Dream exception check the inflated Cost-to-Company or guaranteed in-hand fixed salary?
- **Configurable Toggle**: `threshold_basis: ThresholdBasis` (`"ctc"` | `"fixed_pay"`)
- **Default Value**: `ThresholdBasis.CTC`
- **Chosen Rationale**: Campus drive announcements overwhelmingly state CTC rather than fixed pay breakdowns. To ensure deterministic matching against initial drive notifications, the engine defaults to `CTC`. When an institution chooses `fixed_pay`, offers lacking an explicit fixed pay entry are safely routed to `NEEDS_REVIEW` rather than silently approved.

---

### 3. Handling of Off-Campus Offers
- **Written Ambiguity**: Many placement cells enforce *"One student, one offer"*, but omit whether an off-campus offer (secured through external career portals, direct industry applications, or professional referrals) blocks the student from campus drives.
- **Configurable Toggle**: `count_off_campus_offers: bool`
- **Default Value**: `True` (for strict one-offer policies), `False` (for liberal tiered policies)
- **Chosen Rationale**:
  - In Policy 1 (Strict One-Offer): Off-campus offers are counted (`count_off_campus_offers = True`) to prevent students from double-dipping while peers remain unplaced.
  - In Policy 3 (Tier-Based Quota): Off-campus offers do not consume institutional campus slots (`count_off_campus_offers = False`).
- **Edge-Case Behavior**: If `count_off_campus_offers = False`, a student holding an off-campus offer from Google (35 LPA) remains eligible for campus drives according to college policy.

---

### 4. Treatment of Revoked and Declined Offers
- **Written Ambiguity**: If a recruiter withdraws an offer due to macroeconomic conditions, or if a student formally declines a selection, does that offer still count against their quota?
- **Configurable Toggles**:
  - `count_revoked_offers: bool` (Default: `False`)
  - `count_rejected_offers: bool` (Default: `False`)
- **Chosen Rationale**: When a company revokes an offer through no fault of the candidate, penalizing the student by barring them from campus placement violates institutional fairness. The engine defaults to immediately unblocking the student upon receipt of an official `REVOKED` event. Declined offers are barred unless verified and cleared by the T&P Directorate.

---

### 5. Offer Date vs. Acceptance Date Trigger
- **Written Ambiguity**: When does the block take effect? On the date the company verbalizes selection, on the official date on the offer letter, or on the date the student signs the acceptance portal?
- **Configurable Toggle**: `date_trigger_type: DateTriggerType` (`"offer_date"` | `"acceptance_date"`)
- **Default Value**: `DateTriggerType.OFFER_DATE`
- **Chosen Rationale**: Using `OFFER_DATE` prevents tactical delay where shortlisted students delay signing acceptance letters simply to continue attending concurrent ongoing drives. If an offer is dated in the future relative to a drive reference date (e.g. shortlist published on Oct 20 for a drive on Oct 22, and offer received on Oct 23), the offer is properly ignored for Oct 20-22 evaluations.

---

### 6. Progressive Multiplier Calculation
- **Written Ambiguity**: Policy 2 mandates *"Subsequent offers must be at least 1.5x the first offer."* If Student A has an offer of 7.0 LPA and Company B offers 10.5 LPA, does $7.0 \times 1.5 = 10.5$ qualify?
- **Configurable Toggle**: `upgrade_ctc_multiplier: float` (Default: `1.5`)
- **Chosen Rationale**: Mathematical floating-point calculations are rounded to two decimal places:
  $$\text{Required CTC} = \text{round}(\text{Current CTC} \times \text{Multiplier}, 2)$$
  For 7.0 LPA and 1.5x, $\text{Required} = 10.50\text{ LPA}$. An offer of 10.50 LPA is **ALLOWED** under `CLAUSE-2.1-DREAM-UPGRADE-PERMITTED`.

---

## Summary of Configured Policies

| Policy Identifier | Policy Name | Max Offers | Dream Threshold | Upgrade Multiplier | Off-Campus Counted | Revoked Counted |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `policy-001` | Strict One-Offer Policy | 1 | 10.0 LPA | 1.0x | **Yes** | No |
| `policy-002` | Progressive Multiplier | 2 | 12.0 LPA | 1.5x | **Yes** | No |
| `policy-003` | Tier-Based Quota | 3 | 8.0 LPA | 1.0x | **No** | No |

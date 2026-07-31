# HFB Productization Decision Map

Status: Validation workflow built; production corpus pending
Owner: Product Owner
Technical lead: Codex
Started: 2026-06-28

This map records the decisions required to turn HFB into a production research
platform. Tickets are resolved in order; implementation does not advance past a
decision that changes product scope, cost, data policy, or release risk.

## #0: What Is HFB?

Blocked by: None
Type: Grilling

### Question

What enduring research purpose distinguishes HFB from a digital archive,
content website, or general AI assistant?

### Answer

Approved by the Product Owner on 2026-06-28.

HFB is a professional research platform dedicated to Huangfu Mi scholarship
and designed for use by research institutions. Its purpose is to:

- Deepen and broaden Huangfu Mi scholarship through structured research data
  and AI-assisted analysis.
- Improve collaboration efficiency among institutional researchers.
- Turn source materials, evidence, scholarly interpretation, and research
  outputs into a connected and reusable research environment.

HFB is not a public content portal, a general-purpose chatbot, or a medical
diagnosis product.

## #1: What Is The First Complete Research Workflow?

Blocked by: #0
Type: Grilling

### Question

Which single research task must a researcher be able to complete from source
discovery through evidence-backed export in the first public version?

### Answer

Approved by the Product Owner on 2026-06-28.

The first complete workflow is the **Evidence-backed Version Comparison
Workflow** for invited researchers of the _Zhenjiu Jiayi Jing_:

1. Find a passage.
2. Compare the passage across two editions.
3. Inspect the source and evidence for each text.
4. Record a research note.
5. Export a research record with citations.

V1 is not complete until this workflow works end to end with real, reviewed
research data.

## #2: Who Is The First Release For?

Blocked by: #1
Type: Grilling

### Question

Is the first release for the Product Owner's own research, an invited expert
group, or open public use?

### Answer

Approved by the Product Owner on 2026-06-28.

The platform is built for research institutions. The first release is an
invitation-only pilot within a partner research institution for 3-5 people. It
must include:

- At least one _Zhenjiu Jiayi Jing_ subject researcher.
- At least one versionology or textual-criticism researcher.
- The Product Owner.

Public registration and anonymous research access are outside the pilot scope.

## #3: What Is The Minimum Trusted Research Corpus?

Blocked by: #1, #9
Type: Research

### Question

Which editions, passages, people, papers, and collection records are required,
who may verify them, and what usage rights apply?

### Answer

Blocked on partner research institution delivery.

Correction recorded on 2026-06-28:

- The project does not currently possess the two editions.
- The materials must be requested from the partner research institution.
- Legal usability, provenance, completeness, and review status are not yet
  verified.

Still required before this ticket is resolved:

- Exact edition identities and provenance.
- The initial chapter and 50-100 aligned passages.
- Rights or access restrictions for images and transcriptions.
- Named academic reviewer and review status.

## #4: What Evidence Standard Makes An Output Research-Usable?

Blocked by: #1, #3, #11
Type: Grilling

### Question

What must every search result, comparison, graph edge, and AI answer expose so
that a researcher can independently verify it?

### Answer

Pending.

## #5: What Access And Collaboration Model Ships First?

Blocked by: #2, #3
Type: Grilling

### Question

Will the first release be private, invitation-only, or public, and which
research data may users create, share, or export?

### Answer

Pending.

## #6: Which AI And Infrastructure Services Are Acceptable?

Blocked by: #3, #4, #5
Type: Research

### Question

Which hosting region, model providers, storage services, budget, privacy
constraints, and availability target may the production system use?

### Answer

Pending.

## #7: What Is The V1 Scope And Release Gate?

Blocked by: #1, #2, #3, #4, #5, #6
Type: Grilling

### Question

Which capabilities are mandatory for V1, which move to later releases, and
which measurable checks authorize production launch?

### Answer

Pending.

## #8: Reconcile The AI Collaboration Governance

Blocked by: #7
Type: Grilling

### Question

How should the governance documents be updated to reflect the Product Owner's
decision that Codex now owns implementation as technical co-founder while the
Product Owner retains final authority?

### Answer

The operating model is decided by the Product Owner's 2026-06-28 instruction.
The repository documents still assign Codex a review-only role and must be
updated before implementation begins.

## #9: Obtain The Pilot Corpus From The Institution

Blocked by: #2
Type: Grilling

### Question

Can the partner research institution provide two identifiable editions, their
provenance and usage authorization, and an academic reviewer by an agreed
delivery date?

### Answer

In progress.

Confirmed by the Product Owner on 2026-06-28:

- The platform is being developed specifically for a research institution.
- The institution is expected to provide the research materials.
- The exact editions, material formats, provenance, rights, completeness, and
  academic review arrangements are not yet known.

No production research corpus can be accepted until the institution completes
a corpus inventory and authorization review.

## #10: How Do We Build Before The Institution Delivers Its Corpus?

Blocked by: #1
Type: Grilling

### Question

Should engineering continue with a clearly labeled non-production validation
corpus while institutional corpus discovery and authorization happen in
parallel?

### Answer

Approved by the Product Owner on 2026-06-28.

Engineering will first complete the full Evidence-backed Version Comparison
Workflow with a clearly labeled non-production validation corpus. Institutional
corpus inventory, rights review, and academic review proceed in parallel.

Validation data must never be presented, exported, or migrated as approved
research data. Production launch remains blocked on tickets #3 and #9.

## #11: What Is The AI Academic Boundary?

Blocked by: #0
Type: Grilling

### Question

What may AI contribute to scholarship, and which safeguards prevent it from
being mistaken for an authoritative research source?

### Answer

Approved by the Product Owner on 2026-06-28.

- AI may retrieve, compare, summarize, organize, and propose research
  hypotheses.
- Every AI-supported conclusion must expose evidence and citations.
- A researcher must review and confirm scholarly conclusions.
- AI must refuse to answer when supporting evidence is absent.

These rules are release gates, not optional interface guidance.

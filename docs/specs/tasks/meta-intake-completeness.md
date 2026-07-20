# Meta Intake Completeness

**Status:** Queued (after Epic C0 integrity slices; **not** inside Communication)  
**Parents:** [Sequential queue](sales-to-comms-sequential-queue.md) · Acquisition / Flights / SalesInquiry

## Problem

Meta intake loses or under-displays data:

- company name not formed;
- some Meta answers not persisted or not shown;
- UI shows a truncated Lead projection instead of the original submission.

## Chain to verify

```text
Meta payload → Submission raw data → normalized answers → SalesInquiry fields → UI
```

Full Meta payload must be stored and viewable even when individual fields are not yet normalized.

## Scope

- Persist complete raw payload  
- Persist all Meta questions and answers  
- Show original answers on the inquiry card  
- Normalize company name; define B2B inquiry naming rules  
- Verify mapping for current Meta lead forms  
- Fixture with a real full Meta payload  
- Contract test: no form answer is dropped  

Unknown fields before normalization: show as **additional answers**, never drop.

## Acceptance

Operator can open an inquiry and see every answer from the Meta form; company naming follows explicit B2B rules.

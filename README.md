# Post-Incident Report Generator

Turns a crisis call transcript — or raw incident notes — into a structured
post-incident report, and tells you what the source is missing before you send it.

Built by an incident manager, for incident managers.

## The problem

After a P1, someone has to write the report. What they have to work with is a
transcript full of crosstalk and half-finished sentences, or a set of notes typed
in a hurry during the call: fragments, shorthand, timestamps out of order.

Turning that into a clean report takes an hour, it is tedious, and it is the last
thing anyone wants to do after a major incident.

## The part that isn't obvious

Any LLM will happily generate an incident report from messy notes. The output will
read well. It will also, quietly, be wrong in places — a timestamp nobody recorded,
a team's involvement nobody logged, a root cause that was suspected and is now
presented as confirmed.

**A report that reads authoritatively and is subtly wrong is worse than no report.**

So this tool does two things, and keeps them separate:

| | Goes to | Purpose |
|---|---|---|
| **The report** | the stakeholder | Clean. No "not specified" placeholders cluttering it. |
| **The gap analysis** | you, before sending | What the source doesn't say. What the model would otherwise have to guess. |

The gap analysis is the actual value here. It catches things like: the network team
is mentioned but their actions were never recorded; impact is described as "a lot of
users" and never quantified; the root cause is a hypothesis, not a finding.

Generic assistants generate the report and say nothing about what they didn't know.

## Report structure

Ordered as an incident manager actually needs it — resolution before the timeline,
because the reader wants to know it's fixed before they read how:

1. **Incident Details** — ID, priority, business unit, start / end / duration, IM
2. **Description** — what failed, in plain language
3. **Impact** — prose, not bullets: who felt it and what it cost
4. **Resolution** — and explicitly: workaround, or fix?
5. **Timeline of Actions** — chronological, every action attributed to a team
6. **Root Cause** — confirmed, or labelled as suspected. Never blurred.
7. **Post-Incident Actions** — owners, priorities, status

## Two input modes

- **Call transcript** — where the bridge call is recorded
- **Raw notes** — where it isn't. Client consent, internal incidents, smaller
  organisations: not every incident call can be recorded, and a tool that assumes
  otherwise is useless half the time.

## Design decisions

- `temperature=0.2` for the report — this is a structuring task; creativity is a defect
- Empty cells, never invented values. A blank is honest; a plausible guess is a bug
- Root cause hypotheses are labelled `Suspected` and never promoted to fact
- Workaround vs. fix is stated explicitly — a distinction routinely lost in real reports
- Proposed follow-up actions are tagged `[Proposed]` to separate them from ones actually agreed

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file:

```
GOOGLE_API_KEY=your_key_here
```

Free key from [Google AI Studio](https://aistudio.google.com).

## Run

```bash
streamlit run app.py
```

Paste or upload a transcript or notes, generate, review the gaps, download as
**DOCX**, **PDF** or **Markdown**.

## Examples

All fictional. No real incident data.

- `examples/transcript_payment_outage.txt` — a full bridge call transcript
- `examples/notes_payment_outage.txt` — the same incident, as raw notes
- `examples/notes_auth_outage.txt` — deliberately sparse notes, to show the gap
  analysis doing its job

## Roadmap

- [ ] Multilingual output (EN / PL / FR)
- [ ] Timeline visualisation
- [ ] Configurable report templates per organisation
- [ ] Batch processing

## License

MIT

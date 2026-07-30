# Hermes Customer Onboarding Runbook v1

Last updated: 2026-07-30

## Purpose

Customer onboarding is a governed lifecycle from commercial agreement through
provisioning, training, validation, go-live and offboarding. No public
assistant should go live without customer acceptance.

## Stages

### 1. Commercial Qualification

Capture customer organisation, primary contact, assistant purpose, target
audience, expected message volume, WhatsApp number count, classification,
operating hours, languages, escalation needs, required knowledge, requested
integrations, prohibited activities, compliance requirements, commercial plan
and implementation dependencies.

Outputs: approved use case, licence quantity, onboarding scope,
implementation estimate, risk classification and signed agreement or
authorised order.

### 2. Tenant Creation

Create tenant identifier, billing owner, account administrator, data region
where applicable, default security policy, audit scope, onboarding status and
support contacts.

No production assistant activates before tenant creation is complete.

### 3. Subscription And Licence Allocation

Record subscription plan, number of licences, billing cycle, start date,
renewal terms, licence statuses, trial or paid status and suspension rules.
Allocate one assistant licence for each subscribed assistant number.

### 4. Assistant Definition

Complete an Assistant Definition Form for each licence. Required fields include
assistant name, role, purpose, intended audience, classification, success
criteria, allowed topics, prohibited topics, knowledge scope, disclosure scope,
capability scope, tone, language, escalation rules, operating hours, human
owner, approval owner and retention policy.

### 5. WhatsApp Number Provisioning

Provision or connect the dedicated WhatsApp number using the provisioning
checklist. Do not store provider credentials in documentation or ordinary
database fields.

### 6. Knowledge Discovery

Identify required information. Internal assistants need organisation,
brands, roles, priorities, projects, decisions, policies, risks, metrics and
procedures. Parent assistants need programmes, age groups, venues, schedules,
prices, trials, booking, cancellations, refunds, safeguarding, FAQs and
escalation contacts.

Classify every knowledge item by source, owner, verification status, effective
date, sensitivity, disclosure audience and review date.

### 7. Knowledge Preparation

Remove duplicates, identify conflicts, separate public from internal
information, confirm source ownership, pricing validity, policy dates, legal
wording, missing information, reviewers and expiry/review dates.

Do not activate an assistant using unreviewed customer documents merely because
they were uploaded.

### 8. Persona And Response Design

Configure assistant identity, greeting, tone, response length, brand usage,
prohibited claims, evidence language, refusal style, escalation language,
uncertainty language, complaint handling, after-hours wording and handover
wording.

### 9. Policy And Safety Configuration

Define allowed topics, restricted topics, escalation topics, data collection
limits, safeguarding response, payment restrictions, legal and medical
boundaries, complaints, data protection, action permissions, truthfulness,
prompt injection and human override.

Mandatory rule: never claim that an action, booking, payment, email, task or
escalation occurred without a verified execution receipt.

### 10. Test Environment

Test normal enquiries, ambiguity, incorrect assumptions, pricing, age
suitability, unavailable class, complaints, refund, safeguarding, legal threat,
personal data requests, prompt injection, confidential information requests,
execution requests, human escalation, after-hours, unsupported questions,
repeated conversation and contact identity change.

For internal assistants also test priorities, decisions, evidence boundaries,
context continuity, option tracking, capability honesty, execution refusal and
confidential information handling.

### 11. Customer Acceptance

The customer's authorised owner approves assistant name, tone, knowledge
scope, public information, prices, policies, escalation contacts, test results,
known limitations and launch date. Capture an approval record.

No public assistant goes live without acceptance.

### 12. Controlled Go-Live

Recommended launch path: internal pilot, limited audience, monitored soft
launch, full activation.

Monitor connection health, failures, unanswered questions, hallucinated claims,
escalation accuracy, satisfaction, response time, human takeover rate, unsafe
requests and knowledge gaps.

Provide a kill switch or rapid suspension mechanism.

### 13. Early-Life Support

Suggested reviews: day 1, day 3, day 7, day 14 and day 30.

Classify findings as defect, knowledge gap, policy gap, configuration issue,
integration requirement, training requirement or future feature.

Do not convert every complaint into a feature request.

### 14. Ongoing Governance

Each assistant requires named business owner, technical owner, knowledge
reviewer, escalation owner, periodic access review, content review, safety
test, disaster-recovery test, subscription status review and audit review.

Recommended reviews: monthly operations, quarterly knowledge, quarterly
permissions and annual contract.

### 15. Suspension, Cancellation And Offboarding

Use the offboarding runbook. A cancelled licence must not remain operational.

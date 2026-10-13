# Apex Entitlement Dual Active Solution — Presentation Script (English)

> Note: This script was produced from an audio recording, with proper nouns and spoken-language redundancy corrected and re-punctuated. It is segmented to match presentation pacing and can be read aloud directly.

---

## Opening

Let me introduce the **Dual Active Solution for Apex Entitlement**.

---

## 1. Problem Statement

Our **Entitlement Service** is a **core service of Apex**. It primarily determines **whether a user has permission to access data**.

It is a **critical dependency in the business access path**: when it fails, it doesn't just affect Entitlement Service itself — it affects the **normal operation of all Apex services**.

Previously, **network issues** occurred every month, disrupting business continuity and creating **extra recovery work**.

---

## 2. Why Dual Active

We believe that **Entitlement, as a core service, should not depend on a single site or a single access path**.

When GCP or Mongo becomes unreachable due to network problems, we need an **alternative path**.

Before and after:

| Stage | Status |
|---|---|
| Before dual active | At least one incident every month |
| After dual active | From launch to today — **no incidents for more than six months** |

---

## 3. The Core Challenge: Consistency

When building dual active, **the biggest challenge is consistency**.

Because we need to consider **how to synchronize data between two DB clusters**. The scenarios we fear most are:

1. **Permission updates being overwritten** — the approval state may go from `Approved` back to `Pending` after synchronization;
2. **Deleted data being replayed** — when a delete happens on one site and the other site hasn't synced it yet, the deleted data may "resurrect" during a switchover/failover;
3. **Stale data overwriting valid data** — after a site recovers, other (stale) data may overwrite the currently valid data.

---

## 4. Goals

We have two goals:

1. **Availability**: ensure Entitlement never becomes unavailable due to a **single point of failure**;
2. **Data correctness**: to guarantee correctness, we **route users to write to a specific site based on User Region**.

---

## 5. Methodology: Test-Driven

We followed a **test-first** approach:

1. First, define our **availability and recovery objectives**;
2. Conduct **internal and external research**:
   - **Internal**: search **Confluence** for any prior work we have on **active-active**;
   - **External**: research how **MongoDB** implements active-active;
3. First define a **Test Matrix**, and identify the **test cases** we need;
4. Then, combined with the solutions from our research, define the **test data**;
5. Once the test cases are set, **design the Solution based on those test cases**.

In other words: **define the tests first, and let the tests drive the solution design.**

---

## 6. Solution Architecture

Now let's look at the solution.

**Upstream**: Client Users access the Entitlement Service through the **Gateway**.

**The Entitlement Service runs on two sites that back each other up**:

- **GCP site**: mapped to the **MongoDB GCP instance**;
- **HIC site**: mapped to the **Mongo HIC instance**.

**Routing and failover**: under normal circumstances, we route by **User Region**; when one site has an issue (e.g., a circuit break, or **500 / 502 / 503 / 504** errors), we **fall back to the other site in a controlled manner**.

We also have a **loop-prevention mechanism**: failover **happens on one side only**, and the other side rejects outright — preventing traffic from oscillating between the two sites.

**Data synchronization**: the two sites sync via **Flink CDC** for near-real-time replication — Flink CDC is already part of our **existing technology stack**, so we simply reused it.

**Consistency reconciliation**: on top of the near-real-time Flink CDC sync, we run a **fallback reconciliation every 10 minutes** to check whether the data on the two sites is consistent.

**Monitoring**: we also have continuous monitoring watching this path (sync latency, reconciliation drift, etc.).

---

## 7. Bonus Benefit: Blue-Green Deployment

Because **every Apex service goes through the Gateway**, while building this Gateway routing mechanism we also gained **Blue-Green Deployment** capability:

- We can switch **by weight** — e.g., route **20% of traffic** to the new Entitlement site;
- We can also switch **by Region**.

In other words, we can do canary/blue-green releases through this mechanism **without relying on K8s Ingress**.

---

## 8. Summary

To sum up, our approach is:

1. First determine **whether the Dual Active Solution can solve** this problem;
2. Based on research, define our **Test Matrix** and what tests we should run;
3. **Then decide on our Solution**;
4. Then use the Test Matrix to define **how to implement it**;
5. And **provide Test Evidence** step by step.

Thank you.

---

## Appendix: Terminology Checklist (for the author to confirm)

| Transcript (inferred) | Used in this script | Notes |
|---|---|---|
| FrameCTC | **Flink CDC** | Confirmed |
| Search Confidence | **Confluence** | Confirmed |
| "Port头" for monitoring | **continuous monitoring** | Unclear in audio — please supply the concrete component name (Portal / Alert / Dashboard) if needed |
| HotHot | active-active | Consistent with the previous script |
| 全线 | permission | "permission update" |
| Custer | Cluster | slip of tongue |
| Approved / Pending | Approved / Pending | approval state |

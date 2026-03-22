---
title: "Is AI Quietly Steering You Toward Its Own Ecosystem?"
date: 2026-03-22
draft: false
tags: ["AI", "Cloud Architecture", "Data Engineering", "Tech Leadership", "AI Bias"]
description: "Does the AI recommending your infrastructure have a vested interest in what you choose? A personal experience that raised a question worth asking."
---

A personal story that made me pause and think.

Last year, I started building an AI app called **Jarvis** as a side project, hosted on
GCP. I leaned heavily on Gemini to handle the DevOps side - I didn't want to go deep on
deployment when the real value was in the app itself.

Gemini consistently pushed me toward App Engine. Every time I tried to pivot to Cloud Run
(which, in hindsight, was the right fit - a low-traffic app that needs to scale to zero),
the code never quite worked. Eventually Gemini told me: *"For your use case, App Engine
is the right choice."* So I went with it. It also recommended Cloud SQL with pgvector for
my RAG functionality. I followed that suggestion too.

A few months in, the bills told the real story. App Engine + Cloud SQL is not a cheap
combo for a personal project with minimal usage. I ended up manually shutting down
services when not in use and spinning them back up when needed. Not exactly the elegant
solution I had in mind.

---

Fast forward to this month. I came back to the project and shared the whole context with
Claude. Without any prompting from me about my GCP experience, it suggested Cloud Run
straight away. I was skeptical - it had never worked before. But within a few minutes, I
had a working deployment. It also flagged Neon as a cheaper alternative for vector
storage, with a generous free tier.

Same problem. Better outcome. Significantly lower cost.

---

Which brings me to the uncomfortable question I can't stop thinking about.

**Is AI subtly steering users toward its own company's product ecosystem?**

Gemini is Google's AI. App Engine and Cloud SQL are Google products. The recommendations
weren't wrong - they worked. But they were far from optimal for my context.

Most users won't question this. If you're not already familiar with the landscape, you'll
trust the AI and follow its lead. And the AI - intentionally or not - may be optimising
for ecosystem lock-in rather than your best outcome.

This isn't necessarily malicious. It could be training data bias, product familiarity, or
simply that the AI has seen more examples of certain stacks. But the effect is the same.

As AI becomes the default interface for technical decisions - architecture, tooling, cloud
strategy - the companies building these AIs have an unprecedented ability to shape what
gets adopted at scale.

**If your team is using AI to drive infrastructure decisions, worth asking: does the AI
have a vested interest in what it's recommending?**

---

Curious whether others have noticed similar patterns. Has an AI ever nudged you toward a
product decision that, in hindsight, didn't serve you best?

#AI #DataEngineering #CloudArchitecture #AIBias #GCP #LLM #TechLeadership
---
title: "Vibe Coding: Superpower for Prototyping, Liability in Production"
description: "Vibe coding lets anyone build software with plain English, but unchecked AI generation leads to security flaws, credential leaks, design drift, and threatens open-source sustainability."
date: 2026-03-29
tags: ["vibe-coding", "ai-development", "software-engineering", "security", "open-source"]
categories: ["Technology", "AI"]
draft: false
---

*The promise is real. So are the risks nobody is talking about.*

Something significant is happening in how software gets built. Describe what you want in plain language, and an AI writes the code. No syntax to memorise, no framework to learn, no development team required. Andrej Karpathy named it “vibe coding” in early 2025; Collins English Dictionary named it Word of the Year. The numbers tell the story:

- AI now generates ~41% of all code globally (Stack Overflow + independent research).  
- 25% of Y Combinator Winter 2025 startups have codebases that are 95%+ AI-generated.  
- 63% of people using these tools are not professional software engineers (State of Vibe Coding 2025).

That democratisation is genuinely valuable - founders, analysts, and domain experts can now build tools for their own workflows without waiting on a dev team. But as with anything that moves this fast, the risks are quietly accumulating.

## Where it genuinely works

- **Prototyping velocity**: functional applications assembled in hours, not weeks.  
- **Accessible creation**: domain experts build tailored tools without a development team.  
- **Reduced boilerplate**: 20–45% faster task completion on greenfield features.  
- **Cheaper experimentation**: ideas validated as working prototypes in a day instead of a sprint.

## Where it breaks - and the risks nobody is pricing in

These risks apply regardless of who built the app. The determining factor is not background - it is whether anyone has reviewed and understood what was shipped.

### Security vulnerabilities

- CodeRabbit’s analysis of 470 PRs: AI-generated code carries **2.74× higher** vulnerability rates.  
- Veracode 2025 research: **45%** of AI-generated code contains at least one vulnerability.  
- Lovable incident (CVE-2025-48757): critical data-access flaws in **10.3%** of deployed apps - real user data, exploitable in production.  

These are the default output of systems optimised for functional correctness, not security.

### Exposed secrets and credentials - a silent epidemic

AI models are trained on vast public codebases full of hardcoded keys, passwords, and credentials. Ask an AI to “make the API call work” and it frequently embeds the key directly. The builder tests it, it works, and they ship it - credential visible in page source.

The scale is not hypothetical:

- RedHunt Labs: **one in every five** publicly accessible vibe-coded sites exposes at least one sensitive secret (~25,000 unique credentials for OpenAI, Google, ElevenLabs).  
- Escape.tech study of 5,600 vibe-coded apps: **over 400** exposed secrets.  
- Wiz Research’s Moltbook breach (AI-built social network, zero lines of code written by founder): **1.5 million** API tokens, **35,000** email addresses, and thousands of private messages exposed.  

The credentials weren’t stolen through sophisticated attacks - they were simply sitting in the code. Consequences are immediate: leaked Stripe keys enable unauthorised transactions, leaked AWS keys grant cloud access, leaked database credentials expose every record.

### Maintainability

- Bubble.io’s 2025 survey of 793 builders: **63%** spent more time fixing AI-generated code than writing it would have taken.  
- Long iterative chats with tools like ChatGPT, Gemini or Claude cause **design drift**: the AI optimises or discards earlier design decisions mid-conversation, resulting in a patchwork of conflicting patterns (functional vs OOP, inconsistent error handling, mixed naming conventions). This architectural inconsistency is a classic anti-pattern that makes production code brittle and expensive to maintain.  

They coined “prompt purgatory” for the moment the speed advantage vanishes into debugging.

### Vendor lock-in

A codebase built through Cursor, Lovable, or Replit reflects that tool’s patterns at a specific point in time. Switching requires re-explaining an architecture that was never independently understood or documented.

### Open-source sustainability

The January 2026 paper *“Vibe Coding Kills Open Source”* by Koren, Békés, Hinz and Lohmann models the long-run equilibrium:

- At **70%** vibe-coding adoption, per-user revenue for typical open-source projects falls **70%**, with AI productivity gains offsetting only **12%** of costs.  
- Tailwind CSS creator Adam Wathan: documentation traffic down **40%** and revenue down **~80%** - despite Tailwind being more widely used than ever.

## A perspective from the inside

I’ve spent the past six months building **Jarvis** - a production-grade AI assistant deployed on Google Cloud Run, with deep integrations for Gmail, Google Calendar, WhatsApp voice messaging, and a full RAG pipeline over user documents. AI tools were central to the build: they generated thousands of lines of FastAPI endpoints, LangChain agents, OAuth flows, and vector-search logic.

What made the difference was **not avoiding AI**, but the discipline of reading every single line it produced, understanding its intent and architecture, and ruthlessly enforcing security boundaries. Every credential lives in Google Secret Manager - never in code, never in environment variables, never exposed in logs or client bundles. Even when the chatbots suggested mid-conversation design changes that would have broken uniformity, I rejected them and maintained a single, coherent architecture from start to finish.

Vibe coding skips exactly these steps: it hands you working code without requiring comprehension, without forcing secret isolation, without preserving design consistency across long sessions, and without the human oversight that turns a prototype into a trustworthy production system. That missing discipline is precisely why pure vibe coding works brilliantly for demos - and becomes a liability the moment real users and real data are involved.

## The bottom line

Vibe coding is an excellent prototyping tool and a risky production strategy. The concern is not AI-assisted development - it is what happens when “AI-assisted” becomes “AI-unreviewed”: when creation speed outpaces human accountability.

Whether you’re an engineer, founder, or domain expert: validate before deploying, treat security as a mandatory separate pass, never allow credentials anywhere near your code, and ensure someone with relevant expertise can review what handles real users and real data.

**Speed is a feature. Comprehension is the safeguard that turns a superpower into sustainable success.**

---

#VibeCoding #AIDevelopment #SoftwareEngineering #AITools #TechLeadership #DataEngineering
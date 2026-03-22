---
title: "Before ChatGPT: How a Big Four Bank Used AI to Scale a Critical Process"
date: 2026-03-21
draft: false
tags: ["AI", "Machine Learning", "Banking", "Case Study", "Data Engineering", "Human in the Loop"]
description: "How a Big Four bank applied AI to solve a growing operational challenge."
---

During 2019-2020, long before generative AI became a boardroom talking point, a team of data
engineers and data scientists built something quietly remarkable inside one of Australia's
largest banks. There were no large language models involved. No prompts. No ChatGPT.
Just a well-defined problem, a disciplined team, and a willingness to let the data do
the heavy lifting.

This is that story.

## What Worked - Until It Didn't!

One of Australia's Big Four banks was undergoing a significant shift in how it handled
customer complaints. Complaints were arriving through multiple channels - phone, branch,
online, third-party services - and all of them were being funnelled into a central database. 
So far, so good.

The bottleneck came next.

A team of subject matter experts - experienced, knowledgeable people - was responsible
for reading every complaint verbatim and classifying it. Which business division was
responsible? Which entity within that division? What was the nature of the issue? This
classification wasn't bureaucratic box-ticking. It drove how the customer solutions team
responded. Get it wrong, and the complaint ends up with the wrong team, the resolution
is delayed, and the customer experience gets worse before it gets better.

For a period, this worked. When complaint volumes were manageable, having trained humans
read every case made sense. The classifications were accurate. The process was understood.

Then the bank started growing.

New products launched. New customer segments came on board. And with growth came
complaints - which is normal, expected, and in regulated industries like banking, closely
watched. The rate of complaints typically spikes at product launch and gradually
stabilises. The challenge is the period in between.

The manual reading process - which had been a reasonable solution at lower volumes -
became a constraint. The queue grew faster than the team could clear it. Backlogs
developed. The process that was designed to resolve complaints quickly was itself
becoming a source of delay.

Something had to change.

## Laying The Data Foundation

Before any AI could be applied, the data had to be understood. And the data, as is almost
always the case in large organisations, was complicated.

Complaints were being captured across sixteen different source systems. Each system had
its own fields, its own naming conventions, its own quirks. A complaint recorded in one
channel looked structurally different from the same type of complaint recorded in another.
Building anything reliable on top of that fragmentation was impossible.

The first significant piece of work was the creation of a unified data model - a common
structure that all sixteen source systems could be mapped into. This wasn't glamorous
work. It was the kind of patient, methodical data engineering that rarely makes it into
conference talks but determines whether everything built on top of it succeeds or fails.

Two categories of fields were defined clearly and kept separate: the fields sourced
directly from the originating systems, and the fields overlaid by the subject matter
experts during manual classification. That distinction mattered. The SME classifications
were the training signal. The source system fields were the features. Keeping them
separate ensured the model would learn to replicate expert judgment - not accidentally
learn to predict its own inputs.

Once the data model was in place and two years of historical complaints had been
retrofitted into it, the analytical work could begin. Data analysts built Tableau
dashboards on this unified layer. The dashboards met regulatory requirements and gave
leadership visibility into complaint trends they hadn't had before. That alone had value.

But it was only the beginning.

## Teaching a Machine to Read Like an Expert

The supervised learning approach was straightforward in principle, and genuinely difficult
in execution.

The model was trained on the two years of manually classified complaints - tens of
thousands of cases where a skilled human had read the text and made a judgment about
division, entity, and issue type. The model's job was to learn that mapping: given the
text of a complaint and its associated attributes, produce a classification, and attach a
confidence score to it.

Confidence scoring was the key design decision that made the whole system work in
practice.

Rather than deploying a binary model - AI classifies, human reviews exceptions - the
team designed a tiered system built around thresholds. The thresholds reflected something
important: not all AI predictions are equally reliable, and the cost of a wrong
classification in a complaints context is real.

**Above 90% confidence:** The AI classification was accepted directly. These cases
bypassed the manual read queue entirely. The subject matter experts didn't see them
unless something else flagged them downstream.

**Between 70% and 90%:** The AI had a strong view but not a certain one. These cases
went to a lighter-touch review - the SME could see the AI's suggestion and assess at
a higher level rather than reading from scratch.

**Below 70%:** The AI wasn't sure enough to be useful. These cases went to full manual
review, exactly as they would have before the model existed.

This tiered design had an important philosophical underpinning. The goal was never to
replace the subject matter experts. The goal was to give them back time. The cases where
the AI was most confident were, almost by definition, the more routine and
straightforward ones - the kind that didn't benefit much from senior expert attention
anyway. By handling those automatically, the AI freed the SMEs to spend their energy on
the cases that genuinely needed human judgment: the complex, ambiguous, high-stakes
complaints where experience and contextual understanding actually made a difference.

Human in the loop was not a constraint imposed on the system. It was part of the design.

## What Happened in Month One

Within the first month of the tiered system going live, SME efficiency improved by
twenty-five percent. Not as a projected figure in a business case - as a measured
outcome.

The volume of complaints requiring full manual review had dropped significantly. The
cases that still required human attention were, on average, more complex and more
interesting. The queue had shrunk. The backlog had cleared.

Over the following months, as the model was retrained on an ongoing monthly cycle - incorporating new classifications as they were made, staying current with new product types and complaint patterns - efficiency continued to improve. Within a reasonable period, the SME team was operating at roughly half the manual effort that had previously been required to process the same volume of complaints.

The other half of that capacity didn't disappear. It was redirected. Subject matter
experts who had been spending their days reading routine complaint text began working on
analysis, pattern identification, systemic issue detection - the kind of work that
actually reduces future complaints rather than just processing current ones.

This is worth pausing on. The AI system didn't reduce headcount. It changed what the
existing team was able to do.

## When the New System Arrived

A couple of years after the AI model was first deployed, the bank made a significant
investment in a new customer complaints management platform - a proper, purpose-built
system to replace the legacy infrastructure that had been handling complaints across those
sixteen source systems.

The AI model didn't get retired. It got promoted.

Rather than sitting in the background as an efficiency tool for internal teams, the model
was integrated at the point of complaint capture - the front line, where customer service
representatives were handling complaints in real time. As a complaint was being logged,
the classification was being generated.

The downstream impact was material. First Point Resolution - a KPI tracked by the
regulator and a genuine measure of customer experience quality - improved. When a
complaint is classified correctly at the moment it is raised, it reaches the right team
faster. The right team can resolve it faster. The customer gets an answer instead of a
transfer.

A model that began as a backoffice efficiency tool had, over time, become a customer
experience capability.

## What Made It Work

Looking back, a few things stand out as the reasons this project succeeded where similar
efforts in other organisations struggled.

**The data foundation was built properly.** The unified data model and the two years of
clean, labelled historical data were what made supervised learning viable. Shortcuts at
this stage would have undermined everything that followed. The team did the unglamorous
work first.

**The design respected human judgment.** The tiered confidence threshold system was not
a compromise forced on the team by risk-averse stakeholders. It was a deliberate
recognition that AI confidence is not uniform, and that the appropriate response to
uncertainty is to involve humans - not to automate through it. This made the system more
reliable and, importantly, easier for the SME team to trust and adopt.

**The model was maintained, not deployed and forgotten.** Monthly retraining kept the
model current. As new products launched and complaint patterns shifted, the model shifted
with them. A model trained once and left to age would have degraded in accuracy and
eventually required either a costly rebuild or, worse, a quiet return to fully manual
processes.

**The goal was business outcomes, not AI for its own sake.** Nobody on the project was
trying to build impressive technology. They were trying to clear a backlog, protect
the quality of complaint resolution, and give a skilled team more meaningful work to do.
The AI was the method. The outcome was the point.

---

## Why This Story Still Matters

This project was completed in 2020. The technology used was supervised machine learning -
a method that was, by 2020, well understood and widely available. There were no
breakthroughs involved. No novel research. No cutting-edge models that had never been
deployed before.

What there was, was a clearly defined problem, high-quality data built up over years of
human expertise, a thoughtful system design that kept people appropriately involved, and
a team disciplined enough to build the foundation before reaching for the solution.

That combination is rarer than it should be. And it is, in many respects, more important
than the sophistication of the underlying technology.

The businesses being built today - including the small and medium enterprises that have
never had access to this kind of capability - are accumulating data every day. Emails,
documents, service records, client interactions. Most of them don't think of it as
training data. Most of them don't have a team of data engineers to build a unified model
on top of it.

But the principle is the same. Understand the problem. Build the data foundation. Design
for human involvement where it matters. Measure outcomes, not outputs.

The tools are more accessible now than they were in 2020. The large language models that
arrived in the years since have made certain problems dramatically easier to approach.
But the fundamentals haven't changed.

Good AI work doesn’t start with models. It starts with real problems and honest data.

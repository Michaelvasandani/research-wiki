# ResearchOS

## Overview

ResearchOS is a cloud-hosted AI research assistant that helps research labs turn collections of papers into a shared, continuously evolving knowledge base.

Lab members can use a web application to:

* Upload research papers
* Browse the lab’s paper library
* Ask questions through an LLM chatbot
* Receive answers with citations to the original papers
* Explore connections between papers, methods, concepts, datasets, and researchers

The system runs in the cloud on infrastructure such as Amazon EC2, allowing the entire lab to access it without leaving a personal computer running.

---

## Core Idea

Most research chatbots use traditional Retrieval-Augmented Generation, or RAG.

When a user asks a question, the system searches the uploaded papers, retrieves relevant passages, and generates an answer. The next question begins the process again, so the system repeatedly reconstructs knowledge from raw documents.

ResearchOS combines RAG with the **LLM Wiki pattern**.

Instead of only indexing a newly uploaded paper, the AI reads it and integrates its findings into a persistent research wiki. It creates new pages, updates existing topics, connects related ideas, and records where papers support or contradict one another.

Over time, the lab’s knowledge compounds rather than being rediscovered for every question.

```text
Upload paper
     ↓
AI reads and analyzes it
     ↓
LLM Wiki skill updates the knowledge base
     ↓
Obsidian displays the connected research wiki
     ↓
Chatbot answers using the wiki and original papers
```

---

## Obsidian Vault

The shared knowledge base is stored as an **Obsidian vault**.

An Obsidian vault is simply a folder of plain Markdown files. These files can represent:

* Papers
* Concepts
* Methods
* Datasets
* Researchers
* Experiments
* Open research questions
* Literature reviews

The AI creates links between these pages using Obsidian wikilinks.

For example, a paper page could connect to:

```markdown
[[Visible Neural Networks]]

[[Model Interpretability]]

[[Systems Biology]]

[[Yeast Genotype-Phenotype Dataset]]
```

Obsidian automatically turns these links into a navigable knowledge graph. Researchers can follow connections, view backlinks, search the vault, and use graph view to understand how the lab’s research is connected.

The Obsidian vault is stored as plain Markdown, so the lab owns its knowledge and is not locked into a proprietary database.

---

## LLM Wiki Skill

ResearchOS uses an **LLM Wiki skill inspired by Andrej Karpathy’s LLM Wiki pattern**.

The skill instructs the AI agent how to maintain the Obsidian vault consistently.

When a paper is uploaded, the skill guides the agent to:

* Create a structured paper page
* Extract important findings, methods, and limitations
* Identify related pages already in the vault
* Create new concept pages when needed
* Add Obsidian wikilinks
* Update broader topic summaries
* Record contradictions and unanswered questions
* Preserve links to the original source
* Update the wiki index and activity log

The LLM Wiki skill turns the AI from a general chatbot into a dedicated research knowledge-base maintainer.

The implementation follows the central idea of the LLM Wiki pattern: raw sources remain unchanged, while the AI maintains a separate structured wiki that becomes richer as new sources are added.

---

## User Experience

Researchers interact with ResearchOS primarily through a web application.

### Paper Upload

A researcher uploads a PDF. The system stores the original paper, processes its contents, and adds the resulting knowledge to the shared Obsidian vault.

### Research Chat

Researchers can ask questions such as:

> Which papers in our library discuss visible neural networks?

> What methods have been used to improve biological interpretability?

> Where do these two papers disagree?

The chatbot searches both the generated wiki and the original paper content. It returns a synthesized answer with citations to the relevant papers and pages.

### Obsidian Exploration

Researchers can also open the shared vault in Obsidian to:

* Read generated paper summaries
* Browse concepts and methods
* Follow links between related research
* Inspect backlinks
* Explore the graph view
* Correct or expand AI-generated notes

The chatbot provides a conversational interface, while Obsidian provides a visual and navigable interface to the same knowledge.

---

## High-Level Architecture

```text
Lab Members
     │
     ▼
ResearchOS Web Application
├── Upload papers
├── Browse library
└── Research chatbot
     │
     ▼
Cloud Backend on EC2
├── PDF processing
├── LLM Wiki agent
├── Search and retrieval
└── Citation generation
     │
     ▼
Knowledge Storage
├── S3 for original papers
├── Obsidian vault for the generated wiki
├── PostgreSQL for application data
└── Vector and keyword search for paper passages
```

Obsidian itself does not need to run continuously on EC2. The EC2 instance stores and updates the vault’s Markdown files. Researchers can access a synchronized copy of the vault through Obsidian on their own devices.

---

## Project Goal

The goal of ResearchOS is not simply to build another chatbot for PDFs.

It is to create a shared research memory for a lab.

Every uploaded paper strengthens the Obsidian knowledge graph. Every useful analysis can become a permanent wiki page. Every future question benefits from the knowledge that has already been organized.

The long-term vision is a research assistant that remembers everything the lab has read, connects findings across papers, preserves institutional knowledge, and makes that knowledge accessible through both an LLM chatbot and an Obsidian vault.

# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

<!-- What domain did you choose? Why is this knowledge valuable and hard to find through official channels? -->

I am choosing academic requirements for UPenn's undergraduate curriculum in the College of Arts and Sciences. The information is spread across various web pages and is hard to consolidate and the number of different requirements and changing requirements in the current AI landscape make it difficult for AI systems to answer domain specific questions related to distributional requirements.

---

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

| #   | Source                               | Description                                                    | URL or location                                                                                                                                 |
| --- | ------------------------------------ | -------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Penn College of Arts & Sciences page | Overview of Arts & Sciences Curriculum                         | https://www.college.upenn.edu/academics/arts-sciences-curriculum                                                                                |
| 2   | Penn College of Arts & Sciences page | General Education Curriculum for BA and BS degrees             | https://www.college.upenn.edu/academics/arts-sciences-curriculum/general-education-curriculum                                                   |
| 3   | Penn College of Arts & Sciences page | Sectors of Knowledge Gen Ed requirements                       | https://www.college.upenn.edu/academics/arts-sciences-curriculum/general-education/sectors-knowledge                                            |
| 4   | Penn College of Arts & Sciences page | Foundational Approaches Gen Ed requirements                    | https://www.college.upenn.edu/academics/arts-sciences-curriculum/general-education/foundational-approaches                                      |
| 5   | Penn College of Arts & Sciences page | Policies Governing the Sector Requirement                      | https://www.college.upenn.edu/advising-resources/policies-and-procedures/policies-governing-curriculum/policies-governing-sector-requirement    |
| 6   | Penn College of Arts & Sciences page | The Major in BA & BS degree at CAS                             | https://www.college.upenn.edu/academics/arts-and-sciences-curriculum/major                                                                      |
| 7   | Penn College of Arts & Sciences page | Major offered at the College at Penn                           | https://www.college.upenn.edu/academics/arts-sciences-curriculum/major/college-majors                                                           |
| 8   | Penn College of Arts & Sciences page | # Courses required for majors at Penn CAS                      | https://www.college.upenn.edu/advising-resources/policies-and-procedures/policies-governing-curriculum/arts-and-sciences-cu-total               |
| 9   | Penn College of Arts & Sciences page | The Electives in the College Curriculum at Penn                | https://www.college.upenn.edu/academics/arts-sciences-curriculum/electives                                                                      |
| 10  | Penn College of Arts & Sciences page | Policies governing electives in the College Curriculum at Penn | https://www.college.upenn.edu/advising-resources/policies-and-procedures/policies-governing-curriculum/policies-governing-electives             |
| 11  | Penn College of Arts & Sciences page | Policies governing Art & Sciences CU requirements              | https://www.college.upenn.edu/advising-resources/policies-and-procedures/policies-governing-curriculum/policies-governing-arts-sciences-courses |
| 12  | Penn College of Arts & Sciences page | Entry courses to different majors                              | https://www.college.upenn.edu/academics/course-selection/choosing-courses/entry-courses-majors                                                  |

---

## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

**Chunk size:**

**Overlap:**

**Reasoning:**

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:**

**Top-k:**

**Production tradeoff reflection:**

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| #   | Question | Expected answer |
| --- | -------- | --------------- |
| 1   |          |                 |
| 2   |          |                 |
| 3   |          |                 |
| 4   |          |                 |
| 5   |          |                 |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1.

2.

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:**

**Milestone 4 — Embedding and retrieval:**

**Milestone 5 — Generation and interface:**

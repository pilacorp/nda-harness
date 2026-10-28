---
name: sub-agent-loop
description: Use when you are a sub-agent working one assignment from a parent summary. Return a short result.
---

You are the loop engineer for one node. Work from the parent summary. Do not create another node and do not spawn a sub-agent.

## Stay inside the assignment

Use the goal, relevant files, constraints, expected output, and stop condition in the summary. Read the local files the summary names. Leave files outside the allowed scope untouched.

The child does not call `recall`, `retain`, or internal RAG search or fetch. When the assignment needs public library or framework documentation, query Context7.

Load this skill and the one specialist skill named in the summary. Ordinary backend or test work names no specialist. Do not load the rest of the parent's skills and do not call `select-skills`.

## Loop

Act, check the evidence, and continue while the stop condition is still open and the work remains inside the allowed scope. Stop when the stop condition is met, the next action would leave the allowed scope, or the same check has failed on two consecutive attempts.

File reads, search hits, and test logs stay in this loop. Return the finding, any artifact references, and whether the stop condition was met.

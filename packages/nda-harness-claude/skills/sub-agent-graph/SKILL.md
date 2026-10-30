---
name: sub-agent-graph
description: Use when assigning work to a sub-agent. The parent keeps the assignment graph, writes one summary per node, and stores the short result.
---

The parent is the graph engineer. Load this skill before delegating. The child loads `sub-agent-loop` and does the assignment. This skill does not start an orchestrator, a queue, or another memory bank.

## Graph

Write the graph in the current repository task record under a `Sub-agents` heading. Each node records its id, goal, dependency ids, selected specialist id or `none`, and status.

A node with no dependency can start immediately. Nodes that do not share writable files may run together. Nodes that share writable files, or that name each other as dependencies, run one at a time in dependency order.

Stay the coordinator. Give each child one node. Keep the short result and choose the next edge.

## Summary

Write one summary for the node and pass that summary to the child. Include:

- the issue or task reference and repository revision
- the goal
- the relevant files and any cited internal RAG passage with its revision
- the constraints that apply, including allowed file scope and side effects
- the expected output
- the stop condition
- the selected specialist skill id and path, or `none`

Leave out the parent transcript, earlier unrelated attempts, files the child will not touch, credentials, and personal memory beyond a short note already chosen for the summary.

## Queries and skills

Call Hindsight `recall` and `retain` for the project bank in `.nda-harness/profile.json`. Search and fetch internal RAG before writing the summary. Do not put Hindsight credentials or a memory dump into the summary.

Run Jev for the node before spawning. When `select-skills` returns diagnostic `local_agent`, answer those questions in Jev's noul format and submit them with `--answers-file`. The saved model name is `local-agent`. Load a specialist body only when doing that specialist work yourself. The child receives the selected id and path and does not call `select-skills`.

Give the child `sub-agent-loop`. Append the child's finding, artifact references, and stop-condition result to the node.

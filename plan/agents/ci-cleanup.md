---
title: CI Cleanup
status: live
part_of: agentic-sdlc
doc_type: agent-card
layer: adapter-sdlc
---

# CI Cleanup

## Type

Maker.

## Pairing

**Code Reviewer**, implicitly — its output is part of the diff that reaches diff-time review. This
is the roster's weakest explicit pairing after the Task Decomposer's, and the card notes it rather
than asserting a pairing that is not really configured.

## Purpose

Lint and formatting pass over the merged result. Deliberately separated from implementation so that
formatting churn does not obscure semantic changes in review diffs.

## Inputs

- The merged branch
- The repo's declared lint and format configuration

## Outputs

- A formatting-only diff

## Write scope

The integration branch, restricted to formatting-equivalent changes.

## Layer

**Adapter-SDLC.** Lint and format are software nouns, and the tools are per-language.

## Loop and escalation

`max_retries=3`, competence-type. Low-stakes: exhaustion halts the cleanup, not the run.

## Gates

Its output passes through `pr.review` like any other diff content.

## Failure modes

- **Semantic change disguised as formatting.** The one failure that matters. A formatter that
  rewrites more than layout produces a diff reviewers skim rather than read. The transformer
  contract's round-trip stability obligation (`core_adapter_boundary.md` §7) is the relevant
  guarantee.
- **Fighting the transformer.** If this agent and the shared-file transformer disagree about
  formatting, applied intents will churn on every run. Formatter round-trip stability is a declared
  obligation of the adapter precisely to prevent this.

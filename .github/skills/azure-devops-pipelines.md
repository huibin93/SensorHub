# Azure DevOps Pipelines Skill

## Overview
Standards and patterns for Azure DevOps YAML pipelines.

## Monorepo Trigger Pattern

For monorepos, filter triggers by path:

```yaml
trigger:
  branches:
    include:
      - main
  paths:
    include:
      - services/api/*
      - shared/common/*
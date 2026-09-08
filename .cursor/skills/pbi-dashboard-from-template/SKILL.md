---
name: pbi-dashboard-from-template
description: Generates a Power BI semantic model (TMDL) and a matching report (PBIR) from a dashboard template. Use when the user provides a PBIR/PBIP dashboard template, asks to design a report like a template, generate a semantic model, or run pbi-auto.
---

# Power BI dashboard from template

## Data

Default source is public Northwind OData. Nothing is downloaded:

`https://services.odata.org/V4/Northwind/Northwind.svc/`

The semantic model is generated automatically as TMDL (`*.SemanticModel`) with tables, relationships, and measures.

## When the user gives a template

1. Copy their PBIR folder to `templates/dashboard` (or keep their path).
2. Point `config/dashboard.yaml` `template:` at that folder (or pass `--template`).
3. Map template slots in YAML: `cards`, `chart.x` / `chart.y`, `table`, `slicer` using `Table.Column` or `Table.Measure`.
4. Run:

```powershell
python -m pbi_automation generate --template templates/dashboard
python -m pbi_automation launch
```

Layout, positions, and visual types come from the template. Field bindings are rewritten onto the generated model. Theme comes from `templates/themes/corporate.json` unless they pass another JSON.

## Launch (Git + Fabric + Power BI)

Target workspace:
https://app.fabric.microsoft.com/groups/9cff40b2-3355-4759-998a-7b469fa922f6/list?experience=fabric-developer

`pbi-auto launch` generates the PBIP, commits `workspace/`, pushes to GitHub, then calls Fabric **Update from Git**.

1. Workspace ID is in `config/fabric.yaml` / `.env`.
2. Sign in (`az login` or the browser prompt).
3. In the Fabric workspace: Source control → GitHub → repo `Tamadhi/powerbi_automation`, branch `main`, folder `workspace`.
4. Run `python -m pbi_automation launch`

Desktop is optional: `python -m pbi_automation launch --desktop`

## Do not

- Convert `.pbix` in code (Desktop Save As → PBIP only).

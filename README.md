# Law Firm Performance Dashboard (Power BI)

A Power BI project analysing the finances of **Northbridge Partners**, a fictional international law firm with 12 offices, 320 lawyers, 160 clients and 700 matters (January 2025 to October 2026). All data is synthetic.

![Executive summary](screenshots/executive_summary.png)

## Business questions
1. How much are we billing, and is it growing year on year?
2. Are lawyers meeting their billable hours targets (utilisation)?
3. How much of the time we record do we actually bill (realisation), and which fee arrangements lose the most?
4. How quickly do clients pay (collection and debtor days)?

## Data model (star schema)
- **Fact tables:** `fact_time` (82,500 weekly time entries) and `fact_invoice` (5,000 monthly invoices)
- **Dimensions:** `dim_date` (financial year starting 1 May), `dim_lawyer`, `dim_office`, `dim_matter`, `dim_client`, `dim_practice`
- 8 one-to-many, single-direction relationships. `dim_client` and `dim_practice` connect through `dim_matter`, and `dim_office` through `dim_lawyer`. `dim_date` is marked as the date table.
- Practice area is taken from the **matter** (the work done), not the lawyer, to avoid ambiguous filter paths.

![Model view](screenshots/model.png)

**Design note:** billing is recorded against matters and utilisation against lawyers, so each report page only uses slicers that follow the model's relationships. This stops numbers being silently wrong when a slicer is applied.

## Data quality checks (Power Query)
| Issue found | Rows | Fix |
|---|---|---|
| Lawyer IDs in lower case, so they don't join | 8 | Converted to upper case |
| Weekly hours above 60 (typing errors) | 10 | Flagged and excluded |
| Duplicate invoices | 6 | Removed duplicates on InvoiceKey |

## Key DAX measures
Utilisation %, Realisation %, Collection %, Debtor Days, Billed YoY %, Billed Last 12 Months, Average Days to Pay. See `measures.dax`.

## Findings
- **Fixed fees lose the most value.** Fixed-fee work realised 81.6% of recorded time value, against 93.2% for hourly work. Fixed fees were about a quarter of recorded time but caused 44% of all write-offs (£16.1M of £36.9M).
- **Financial services clients pay slowest.** They take about 55 days on average to pay, against about 44 days for energy clients.
- **Privacy & Data Protection and Technology & Communications bill the most,** at about £43M each over the period.
- **Billing is steady** at roughly £13M to £15M a month, and 2026 is broadly flat against 2025.
- **Utilisation is on target overall (99%) but uneven.** Madrid and Sydney run at 94%, against 101% in Amsterdam, London and Frankfurt. Milan trainees (79%) and Dubai partners (83%) are under-used, while Stockholm (114%) and Hong Kong (112%) senior associates are over-stretched, a possible workload and retention risk.
- **£21.3M is unpaid across 390 invoices,** the oldest from June 2026.

**Recommendations:** review how fixed fees are scoped and priced, rebalance work from over-stretched senior associates to under-used teams, and tighten credit control for financial services clients, starting with the oldest unpaid invoices.

## Report pages
| Page | Purpose | Slicers |
|---|---|---|
| Executive summary | Billing, realisation, collection and debtor days | Financial year, client sector, practice area |
| People and utilisation | Billable hours against targets by office and grade | Financial year, region, grade |
| Clients and matters | Fee arrangements, top clients, payment speed, unpaid invoices | Financial year, client sector |

![People and utilisation](screenshots/people.png)
![Clients and matters](screenshots/clients.png)

## Tools
Power BI Desktop, Power Query (M), DAX, Python (pandas, NumPy) for the synthetic data

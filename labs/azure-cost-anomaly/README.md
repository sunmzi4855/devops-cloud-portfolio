# Azure cost anomaly investigation

Daily cloud charges climbed from a seven-day average of **$120 to $312** in a synthetic Azure billing export. This Python lab identifies the two groups responsible for the $192 increase and checks whether the input is complete enough to support that conclusion.

## What drove the increase?

| Resource group | Meter category | Previous daily mean | Nov 17 | Change |
| --- | --- | ---: | ---: | ---: |
| `rg-analytics` | Virtual Machines | $30 | $210 | +$180 |
| `rg-api` | App Service | $60 | $72 | +$12 |
| `rg-shared` | Storage | $30 | $30 | $0 |
| **Total** | | **$120** | **$312** | **+$192** |

Virtual machines accounted for **93.75%** of the increase. App Service had an $80 charge and an $8 refund in different files. Both entries count toward its $72 daily total. To find out whether more compute hours or a higher rate drove the VM increase, compare resource IDs, billed quantities and effective prices across the two periods in a resource-level export.

## Reproduce the investigation

GitHub Actions passed 13 tests and saved the normal-day and spike reports. [View the recorded run and both JSON reports](https://github.com/sunmzi4855/devops-cloud-portfolio/actions/runs/45289136537)

Use Python 3.10 or newer from the repository root. The lab uses the standard library and included sample data.

```sh
cd labs/azure-cost-anomaly
python3 -m unittest -v
python3 cost_watch.py examples/manifest.json --day 2026-11-16
python3 cost_watch.py examples/manifest.json --day 2026-11-17
```

November 16 returns `within_range` and exit code **0**. November 17 returns `spike` and exit code **1**. Each invocation prints JSON. Add `--summary report.md` to append a readable report. The GitHub Actions workflow runs both cases, posts the investigation in its job summary and saves both JSON reports as a downloadable artifact.

## How the decision works

The check compares one past UTC date with the mean of the seven preceding calendar days. By default, a positive daily total must rise by at least **50 billing-currency units** and **30%** to trigger. Both thresholds are inclusive and configurable with `--min-rise` and `--min-percent`. With a zero or negative historical mean there is no meaningful percentage increase, so only the absolute threshold applies to a positive total. The comparisons use decimal arithmetic before display rounding.

Contributions are grouped by subscription, resource group and meter category. A group's contribution is its charge on the selected day minus its own seven-day mean. The JSON includes decreases as well as increases, ranked by signed change. Blank group or meter names remain visible as unassigned.

## Input and coverage

Place one downloaded `ActualCost` run's manifest alongside all its named CSV or CSV.GZ parts. The parser reads `Date`, `SubscriptionId`, `ResourceGroup`, `MeterCategory`, `CostInBillingCurrency`, and `BillingCurrencyCode` from the Enterprise Agreement export. It accepts ISO and U.S. slash-formatted dates and ignores extra columns. [Microsoft's cost-detail schema](https://learn.microsoft.com/en-us/azure/cost-management-billing/dataset-schema/cost-usage-details-ea) · [Microsoft's export manifest example](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-improved-exports)

The CLI checks listed partitions, declared row counts, the billing currency and calendar coverage. Invalid data exits **2** with a diagnostic. A missing date exits **2** with an `insufficient_data` JSON report. A zero-cost day needs an explicit zero-cost row. If a month-boundary window needs records outside the supplied run, the report lists the missing dates. Manifest checks can detect an incomplete download. The billing provider can still add or revise charges in a later export.

[Python implementation](cost_watch.py) · [Automated tests](test_cost_watch.py) · [Synthetic export](examples/manifest.json) · [GitHub Actions workflow](../../.github/workflows/azure-cost-anomaly.yml)

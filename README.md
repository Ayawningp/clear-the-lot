# clear-the-lot

**Every month a permit waits, the funding gap grows. Clear the Lot shows how much.**

Built for the Claude Impact Lab: UCI × SoCal Affordable Housing hackathon — *Clear it* track (getting from land to a buildable property).

---

## The problem

For a low-income family or small nonprofit builder, the gap between "we have the land" and "we can break ground" is often months of permitting and review. That wait isn't free:

- Carrying costs keep running (loan interest, property tax, insurance, site security)
- Construction costs can rise while plans sit in review
- Committed funding (grants, subsidies, loan terms) can expire or be repriced
- Each added month widens the gap between what the home costs and what the family can afford

These costs are rarely shown in one place, so delay looks like an inconvenience instead of what it is: a growing bill.

## What Clear the Lot does

<!-- TODO: confirm the final feature set after the build -->

1. **Inputs** — the project basics: land/loan amount, interest rate, expected permit timeline, estimated construction cost, funding sources and their deadlines.
2. **Delay cost meter** — a month-by-month estimate of what waiting adds, broken down by cost type.
3. **Gap view** — how the affordability/funding gap grows with each month of delay, and the month where committed funding is at risk.
4. **Plain-language summary** — a short explanation a family, advocate, or city reviewer can read and act on.

## Demo

<!-- TODO: add screenshot or GIF and live link -->

## How it works

<!-- TODO: fill in once the model is built -->

- **Carrying cost:** `monthly_cost = loan_balance × (annual_rate / 12) + property_tax / 12 + insurance / 12 + other_fixed`
- **Construction escalation:** `cost_at_month_t = base_cost × (1 + monthly_escalation)^t`
- **Funding gap at month t:** `total_cost(t) − available_funding(t)`

All assumptions are visible and editable in the app. Default values and their sources are listed in [`ASSUMPTIONS.md`](ASSUMPTIONS.md).

## Getting started

<!-- TODO: replace with actual stack/commands -->

```bash
git clone https://github.com/<your-username>/clear-the-lot.git
cd clear-the-lot
# install dependencies
# run the app
```

## Limitations

- Estimates, not financial advice. Outputs depend entirely on the inputs and default assumptions.
- Permit timelines vary widely by city and project type; the tool does not predict them, it prices them.
- Built in a 4-hour hackathon — not validated against real project data yet.

## Team

- Ashton Peng — UC Irvine, Applied Mathematics

## License

<!-- TODO: pick one, e.g. MIT -->

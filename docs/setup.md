# Setup

## Launching it

H.10 needs no key and no account: the Board's site is public. Launch the
plugin and approve its one role, `dgm`. It reads the Board at once, and
every hour after.

Its settings, in the dashboard's Settings form:

- **Raw responses window** and **past the window** (the SDK's): how long the
  Board's responses are kept in the plugin's storage, ten years by default,
  and whether they are then archived, kept or deleted.
- **Synthetic mode**, on a deployment installed for development only: the
  Board's responses recorded on 10 October 2026, committed with the plugin,
  in place of the site. For trying it offline.

## Its dataset

On the deployment's **Data sources** page (deployment admins):

1. **License `<instance>:daily`.** The catalogue's default is public domain:
   kept, no limit on retention, derived use or display, not one person's
   terms. Confirm it, or set your own, with a note saying why.
2. **Entitle** each plugin that reads rates, such as your reporting plugin.
3. **Priority**, where another dataset also prices currencies: put the one
   your valuation should read first.

## Your currencies' instruments

Each rate is about a currency's cash instrument, found by its ISO 4217 code.
The Datasets tab shows each currency's instrument, or why there is none
(not found, or two records match). A currency without one waits: its rates
are recorded once it resolves, at the next check.

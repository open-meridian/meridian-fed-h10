# Pages

Both pages are under **Manage**, for the plugin's admins. Neither shows a
rate. Each is also a read tool on the deployment's MCP, answering what the
page shows.

## Connection (`read_connection`)

How the plugin reaches the Board, and how the last check went:

- the head's status: read, checking, a failed check, or currencies not
  resolved;
- the latest release, its days, and when the Board published it;
- the next release expected, and the last check;
- where it reads from, that no key is needed, the limits it keeps (one page
  at a time, at most one every two seconds, a check every hour), and how
  many responses are kept.

## Datasets (`read_datasets`)

What the plugin serves:

- its one dataset as the deployment's catalogue lists it, with the licence it
  declares;
- the standing wants it keeps current, and the last wants it answered;
- each currency H.10 publishes, one line each: its code, how the Board
  quotes it, what its rate is the price of, and the deployment's instrument
  for it, or why there is none. A row's `…` opens its details.

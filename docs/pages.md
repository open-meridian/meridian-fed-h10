# Pages

Both pages are the data role's, the same on every data plugin, under
**Manage**, for the plugin's admins. Neither shows a rate. Each is also a
read tool on the deployment's MCP, answering what the page shows, under the
same names on every data plugin.

## Connection (`read_connection`)

How the plugin reaches the Board, and how the last check went:

- the head's status: answering, checking, not answering, or currencies not
  resolved;
- **Key:** the mode (Live or Sample data), "No key needed", what the Board
  serves, and where it reads from;
- **Limits and use:** the limits it keeps (the Board states none; one page
  at a time, at most one every two seconds, a check every hour), the pages
  asked, the last check and error, and how many responses are kept;
- **Stream:** it does not stream;
- **The Board's H.10:** the latest release, its days, when the Board
  published it, and the next release expected.

## Datasets (`read_datasets`)

What the plugin serves:

- **Served:** its one dataset as the deployment's catalogue lists it, with
  the terms it declares and whether a deployment admin has licensed it, and
  what it recorded and declined;
- **Wants:** the standing wants it keeps current, and the last wants it
  answered; **Subjects**;
- each currency H.10 publishes, one line each: its code, how the Board
  quotes it, what its rate is the price of, and the deployment's instrument
  for it, or why there is none. A row's `…` opens its details.

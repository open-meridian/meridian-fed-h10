# Overview

The Federal Reserve Board publishes H.10 every week: the noon buying rates in
New York for about two dozen currencies against the US dollar, one rate a
business day. This plugin reads each release from the Board's site and puts
its rates into your deployment's lake, where a reporting plugin values your
positions in another currency.

It is a data plugin: its first-use path, its two pages and its Summary figures are every data plugin's, described once on [Using a data plugin](https://open-meridian.dev/how-to/using-a-data-plugin/). These sections cover what is H.10's own.

## What a rate means here

A rate is a price: the price of one currency's cash in another. The plugin
records each rate exactly as the Board quotes it.

- Most currencies are quoted per US dollar. **CHF 0.8293** on 2 October 2026
  means one US dollar cost 0.8293 francs: the price of the dollar, in francs.
- The euro, the pound and the Australian and New Zealand dollars are quoted
  in US dollars per unit. **EUR 1.1259** means one euro cost 1.1259 dollars:
  the price of the euro, in dollars.

Nothing is turned the other way round. A plugin that needs dollars per franc
divides, and says it did.

## When rates arrive

The Board releases a week's rates on the following Monday at 4:15 p.m. New
York time, or the next business day after a holiday. The plugin checks every
hour and records a new release when it appears. A rate is the noon rate, so a
day's rate belongs to that day; a valuation for yesterday waits for next
Monday's release, and every rate shows its date.

Asked for an older day, the plugin reads that week's release and records it.
Asked for a day not published yet, it says the source has not stated it.

## What it does not do

- It shows no rate on its own pages: rates are read by the plugins that
  value your book.
- It records no index: the Board's dollar indexes are not prices of a
  currency.
- It never inverts or crosses a rate, and never fills a holiday with a
  number.

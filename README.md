![Friktion Mainnet Registry](/banner.png)

# Friktion Mainnet Registry API

This repository is the official up-to-date source of Friktion mainnet data. It contains both the [technical data](https://friktion-labs.github.io/mainnet-tvl-snapshots/staticData.json) and [current Friktion-related market info](https://friktion-labs.github.io/mainnet-tvl-snapshots/friktionSnapshot.json). It is updated multiple times an hour with an automated script hosted in GitHub Actions.

This can be considered an API for the mainnet registry. We chose to use GitHub as opposed to some opaque service so that data and history is transparently available to the public.

The repository is named "mainnet-tvl-snapshots" because it originally contained just the TVL snapshots. We kept the repository name because this API is already in use by many projects such as DefiLlama and Friktion.fi.

## friktionSnapshot.json

This file contains both static data as well as recently-updated market data such as APY, prices, deposits, volt token price, and more. It is updated with the latest information multiple times per hour, and is suitable for use in your own apps that can handle data that updates infrequently. Due to the epoch-based design of many Friktion volts, the APY and other statistics only update once a week.

Public URL: https://friktion-labs.github.io/mainnet-tvl-snapshots/friktionSnapshot.json

## staticData.json

This contains static data that generally doesn't change unless new volts are launched. The smaller filesize and different organization structure may be more useful for apps that don't need user-facing statistics.

Public URL: https://friktion-labs.github.io/mainnet-tvl-snapshots/staticData.json

## How to use this data in an app or code

We recommend making a network request to fetch the latest information so that you have the most up-to-date data.

These files are hosted on GitHub Pages (with CORS support) at https://friktion-labs.github.io/mainnet-tvl-snapshots/

For example, to read `derived_timeseries/mainnet_income_call_btc_sharePricesByGlobalId.json`, use https://friktion-labs.github.io/mainnet-tvl-snapshots/derived_timeseries/mainnet_income_call_btc_sharePricesByGlobalId.json

## Other Development Resources

- https://github.com/Friktion-Labs/sdk - Public Friktion SDK

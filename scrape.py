from email.policy import default
import pandas as pd
import string
import git
import hashlib
import json
from pathlib import Path
import argparse
import datetime
import traceback
import requests
from collections import defaultdict
import time
import datetime
import numpy as np
import traceback


def iterate_file_versions(
    repo_path, filepath, ref="main", commits_to_skip=None, show_progress=False
):
    relative_path = str(Path(filepath).relative_to(repo_path))
    repo = git.Repo(repo_path, odbt=git.GitDB)
    commits = reversed(list(repo.iter_commits(ref, paths=[relative_path])))
    progress_bar = None
    if commits_to_skip:
        # Filter down to just the ones we haven't seen
        new_commits = [
            commit for commit in commits if commit.hexsha not in commits_to_skip
        ]
        commits = new_commits
    if show_progress:
        progress_bar = click.progressbar(commits, show_pos=True, show_percent=True)
    for commit in commits:
        if progress_bar:
            progress_bar.update(1)
        try:
            blob = [b for b in commit.tree.blobs if b.name == relative_path][0]
            yield commit.committed_datetime, commit.hexsha, blob.data_stream.read()
        except Exception:
            # This commit doesn't have a copy of the requested file
            print(traceback.format_exc())
            print(f"commit {commit} was fucked.. Manually exclude it please")
            pass


# MAPPING = {
#     "sol": ["solana", "SOL", "sol"],
#     # "msol": ["msol", "mSOL", "marinade"],
#     # "btc": ["bitcoin", "BTC", "btc"],
#     # "sbr": ["saber", "SBR", "sbr"],
#     # "ftt": ["ftx-token", "FTT", "ftt"],
#     # "usdc": ["usd-coin", "USDC", "usdc"],
#     # "luna": ["terra-luna", "LUNA", "luna"],
#     # "scn": ["socean-staked-sol", "scnSOL", "socean"],
#     # "srm": ["serum", "SRM", "serum"],
#     # "mngo": ["mango-markets", "MNGO", "mngo"],
#     # "ray": ["raydium", "RAY", "ray"],
#     # "eth": ["ethereum", "ETH", "eth"]
# }

DESIRED_COLS = [
    "coinsByCoingeckoId",
    "pricesByCoingeckoId",
    "depositTokenByGlobalId",
    "usdValueByGlobalId",
    # Make sure this is last.
    "sharePricesByGlobalId",
]


def populate_registry():
    try:
        return dict(
            json.loads(
                requests.get(
                    "https://friktion-labs.github.io/mainnet-tvl-snapshots/friktionSnapshot.json"
                ).content
            )
        )
    except Exception as e:
        traceback.print_exc()
        with open("registry.json", "r") as f:
            return dict(json.load(f))


MAINNET_REGISTRY = populate_registry()
EXCLUDE_COMMITS = [
    "218c73176ca660b8592695d055d5db669fd413da",
    "4c57939521ea45765becdae22fc809e4491dfb4a",
    "a21d5be807b7444c79744597202baabe55624cfd",
    "40f62eeb528ae099b14a30c8dbdb2b0770b92fe3",
    "01908a7fe73eacabe6b2e3f973fb559f3fa28030",
    "2f91448b5d639c99235426fa180683d38a3e8dd0",
]


def process_diff(diff, info):
    assert len(diff) == 3
    utc_time = int(datetime.datetime.timestamp(diff[0]) * 1000)
    commit_hash = diff[1]
    if commit_hash in EXCLUDE_COMMITS:
        return
    try:
        content = json.loads(diff[2])
    except Exception as e:
        print(commit_hash + " is ill formatted. Skipped...")
        return

    for metadata in info:
        # Skip incomplete history
        if "sharePricesByGlobalId" not in content.keys():
            return

        row = [utc_time]
        # Populate coin balances
        globalId = metadata["globalId"]
        coingeckoId = metadata["depositTokenCoingeckoId"]
        symbolId = metadata["depositTokenSymbol"]
        output = metadata["output"]

        if DESIRED_COLS[0] in content and coingeckoId in content[DESIRED_COLS[0]]:
            row.append(content[DESIRED_COLS[0]][coingeckoId])
        else:
            row.append("")

        if DESIRED_COLS[1] in content and symbolId in content[DESIRED_COLS[1]]:
            row.append(content[DESIRED_COLS[1]][symbolId])
        else:
            row.append("")

        for col in DESIRED_COLS[2:]:
            if col in content and globalId in content[col]:
                row.append(content[col][globalId])
                # if content[col][globalId]==1.05422:
                #     print(commit_hash)

        if len(row) >= len(DESIRED_COLS) + 1:
            output.append(row)


def parse_tvls(
    diff,
    tvls,
):
    utc_time = int(datetime.datetime.timestamp(diff[0]) * 1000)
    row = [utc_time]
    try:
        content = json.loads(diff[2])
        if "totalTvlUSD" in content:
            row.append(content["totalTvlUSD"])
        tvls.append(row)
    except Exception as e:
        traceback.print_exc()
        print("     error parsing TVLs")
        return


def accum(diff, birdy_tvls):
    utc_time = int(datetime.datetime.timestamp(diff[0]) * 1000)
    row = {"timestamp": utc_time}
    try:
        content = json.loads(diff[2])
        if "usdValueByGlobalId" in content:
            row.update(content["usdValueByGlobalId"])
            birdy_tvls.append(row)
    except Exception as e:
        print(" is ill formatted. Skipped...")
        return


def parse_spot(diff, spots):
    utc_time = int(datetime.datetime.timestamp(diff[0]) * 1000)
    try:
        content = json.loads(diff[2])
        if "pricesByCoingeckoId" in content:
            for symbol, price in content["pricesByCoingeckoId"].items():
                if symbol in spots.keys():
                    spots[symbol].append([utc_time, price])
                else:
                    spots[symbol] = [[utc_time, price]]
    except Exception as e:
        traceback.print_exc()
        print(" is ill formatted. Skipped...")
        return


def get_coingecko_mapping():
    mapping = {}
    for payload in MAINNET_REGISTRY["allMainnetVolts"]:
        if payload["voltType"] == 1:
            mapping[payload["underlyingTokenSymbol"]] = payload[
                "underlyingTokenCoingeckoId"
            ]
    print(mapping)
    return mapping


def parse_args():
    parser = argparse.ArgumentParser(description="Parse Args")
    parser.add_argument("--input_file", type=str, default="friktionSnapshot.json")
    parser.add_argument("--output_file", type=str)
    parser.add_argument("--path_to_repo", type=str, default="./")
    # parser.add_argument('--append', type=str, default=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    diffs = iterate_file_versions(args.path_to_repo, args.input_file)

    info = []
    tvls = []
    spot = {}
    tvls_birdy = []
    assert "allMainnetVolts" in MAINNET_REGISTRY, "metadata parsing error. contact dai"
    # Grab metadata for all vaults
    for payload in MAINNET_REGISTRY["allMainnetVolts"]:
        # print(payload)
        globalId = payload["globalId"]
        for col in DESIRED_COLS:
            datastream_file = Path(
                "derived_timeseries/{}_{}.json".format(globalId, col)
            )
            datastream_file.touch(exist_ok=True)
        print(globalId)

        metadata = {
            "globalId": globalId,
            "depositTokenCoingeckoId": payload["depositTokenCoingeckoId"],
            "depositTokenSymbol": payload["depositTokenSymbol"],
            # Use this to store the output from diff processing
            "output": [],
        }
        info.append(metadata)

    # Get symbol -> CoingeckoId mapping
    mapping = get_coingecko_mapping()

    for diff in diffs:
        process_diff(diff, info)
        parse_tvls(diff, tvls)
        accum(diff, tvls_birdy)
        parse_spot(diff, spot)

    df_tvl = pd.DataFrame(tvls_birdy)
    df_tvl["timestamp"] = pd.to_datetime(df_tvl.timestamp, unit="ms")
    # exclude problem rows
    df_tvl = df_tvl.loc[df_tvl.sum(axis=1) < 3e8]
    df_tvl = df_tvl.set_index("timestamp")
    df_tvl = df_tvl.groupby(df_tvl.index.floor("H")).first()
    df_tvl.index = (df_tvl.index.astype("int") / 10**6).astype("int")
    columns = list(df_tvl.columns)
    # Some weird NaN -> None conversion going on in this comprehension b/c python is gay as fuck
    values = [
        [idx, [row[col] if not np.isnan(row[col]) else None for col in columns]]
        for idx, row in df_tvl.iterrows()
    ]
    tvl_final = []
    tvl_final.append(columns)
    tvl_final += values

    # Write TVLs for Birdy
    tvl_filename = Path("derived_timeseries/tvl_usd_agg.json")
    tvl_filename.touch(exist_ok=True)
    with open("derived_timeseries/tvl_usd_agg.json", "w") as fl:
        json.dump(tvl_final, fl, separators=(",", ":"), indent=2)

    # Write TVLs
    tvl_filename = Path("derived_timeseries/tvl.json")
    tvl_filename.touch(exist_ok=True)
    with open("derived_timeseries/tvl.json", "w") as fl:
        json.dump(tvls, fl, separators=(",", ":"), indent=2)

    for symbol in spot.keys():
        spot_filename = Path("derived_timeseries/spot.json")
        spot_filename.touch(exist_ok=True)
        coingeckoId = mapping[symbol] if symbol in mapping else 0
        if not coingeckoId:
            continue
        print(coingeckoId)
        with open(
            "derived_timeseries/{}_pricesByCoingeckoId.json".format(coingeckoId), "w"
        ) as fl:
            json.dump(spot[symbol], fl, separators=(",", ":"), indent=2)

    for metadata in info:
        for idx, col in enumerate(DESIRED_COLS):
            if (
                "circuits" in metadata["globalId"]
                or col in DESIRED_COLS[:-1]
                or "perp" in metadata["globalId"]
                or "basis" in metadata["globalId"]
                or "pai" in metadata["globalId"]
            ):
                fname = "derived_timeseries/{}_{}.json".format(
                    metadata["globalId"], col
                )
                output = metadata["output"]
                with open(fname, "r") as openfile:
                    try:
                        writedata = json.load(openfile)
                    except:
                        writedata = []

                # Skip captured commits
                cached_rows = [x[0] for x in writedata if len(x)]
                last_timestamp = writedata[-1][0] if len(writedata) else 0

                filtered_rows = list(
                    filter(
                        lambda x: x[0] not in cached_rows and x[0] > last_timestamp
                        # null check
                        and x[1],
                        output,
                    )
                )
                filtered_data = [[x[0], x[idx + 1]] for x in filtered_rows]
                if not len(filtered_data):
                    continue
                # Remove row if it's the same value as the one before
                duplicates_removed = []
                for data_idx, data in enumerate(filtered_data):
                    if data_idx == 0 or filtered_data[data_idx - 1][1] == data[1]:
                        continue
                    else:
                        duplicates_removed.append(data)
                print(len(duplicates_removed))
                writedata.extend(duplicates_removed)
                # print(writedata)
                with open(fname, "w") as fl:
                    json.dump(writedata, fl, separators=(",", ":"), indent=2)

    # # One last pass over sharePricesByGlobalId to get rid of duplicates
    # MISSING_DATA = {
    #     "mainnet_income_call_btc": [
    #         [1639712846000, 1.0],
    #         [1640317646000, 1.05414],
    #         [1640922446000, 1.05874],
    #     ],
    #     "mainnet_income_call_marinade": [
    #         [1640317646000, 1.0],
    #         [1640922446000, 1.01567],
    #     ],
    #     "mainnet_income_call_eth": [
    #         [1640317646000, 1.0],
    #         [1640922446000, 1.00736],
    #     ],
    #     "mainnet_income_call_srm": [
    #         [1640922446000, 1.0],
    #     ],
    #     "mainnet_income_call_luna": [
    #         [1640922446000, 1.0],
    #     ],
    #     "mainnet_income_call_ftt": [
    #         [1640922446000, 1.0],
    #     ],
    #     "mainnet_income_call_socean": [
    #         [1640922446000, 1.0],
    #     ],
    #     "mainnet_income_call_sbr": [
    #         [1640922446000, 1.0],
    #     ],
    #     "mainnet_income_call_mngo": [
    #         [1640922446000, 1.0],
    #     ],
    #     "mainnet_income_call_sol_high": [
    #         [1645607584000, 1.0],
    #     ],
    #     "mainnet_income_call_stsol": [
    #         [1648094950000, 1.0],
    #     ],
    #     "mainnet_income_call_avax": [
    #         [1648094950000, 1.0],
    #     ],
    #     "mainnet_income_call_step": [
    #         [1647490150000, 1.0],
    #     ],
    #     "mainnet_income_put_sol": [
    #         [1640922446000, 1.0],
    #     ],
    #     "mainnet_income_put_mngo": [
    #         [1640922446000, 1.0],
    #     ],
    #     "mainnet_income_put_btc": [
    #         [1640922446000, 1.0],
    #     ],
    #     "mainnet_income_put_eth": [
    #         [1643947750000, 1.0],
    #     ],
    #     "mainnet_income_put_tsUSDC": [
    #         [1644552550000, 1.0],
    #     ],
    #     "mainnet_income_put_pai": [
    #         [1651205350000, 1.0],
    #     ],
    #     "mainnet_income_put_luna": [
    #         [1643342950000, 1.0],
    #     ],
    # }
    # for metadata in info:
    #     fname = "derived_timeseries/{}_sharePricesByGlobalId.json".format(
    #         metadata["globalId"]
    #     )
    #     try:
    #         seed = MISSING_DATA.get(metadata["globalId"])
    #         if not seed:
    #             seed = []

    #         df = pd.read_json(fname)
    #         seed.extend(
    #             (
    #                 df.groupby(pd.to_datetime(df[0], unit="ms").dt.isocalendar().week)
    #                 .first()
    #                 .values.tolist()
    #             )
    #         )
    #         seed = list(map(lambda x: [int(x[0]), x[1]], seed))

    #         filtered_seed = []
    #         timestamps_seen = []
    #         for item in seed:
    #             if item[0] in timestamps_seen:
    #                 continue
    #             else:
    #                 filtered_seed.append(item)
    #                 timestamps_seen.append(item[0])

    #         print(metadata["globalId"])
    #         print(filtered_seed)
    #         with open(fname, "w") as fl:
    #             json.dump(filtered_seed, fl, separators=(",", ":"), indent=2)
    #     except:
    #         print(metadata["globalId"])
    #         print(f"{metadata['globalId']} was borked")

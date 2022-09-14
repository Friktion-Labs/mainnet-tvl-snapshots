const https = require("https");
const fs = require("fs");

function main(friktionSnapshot: { allMainnetVolts: MainnetVolt[] }) {
  const allVoltMints = friktionSnapshot.allMainnetVolts.sort((a, b) =>
    a.shareTokenSymbol.localeCompare(b.shareTokenSymbol)
  ) as MainnetVolt[];
  const legacyFormatTokenList = allVoltMints
    // .filter((token) => !token.shareTokenSymbol.includes("Treasury"))
    .map((token) => {
      let voltParentheses;
      let tagShort: string | undefined;
      let tagLong: string | undefined;
      let tokenNameMiddle;
      if (token.globalId.includes("_circuits")) {
        // console.log(token);
        tokenNameMiddle = token.shareTokenSymbol.replace("fc", "");

        voltParentheses = "";
        tokenNameMiddle = token.shareTokenSymbol.replace("Treasury", "");
        token.shareTokenSymbol = token.shareTokenSymbol
          .replace("Treasury", "")
          .slice(0, 10);
        // console.log(
        //   `${token.globalId} => ${token.shareTokenSymbol} ${tokenNameMiddle}`
        // );
      } else if (token.voltType === 1) {
        voltParentheses = "(Volt 01 Call)";
        tagShort = "volt01";
        tagLong = "volt-01-call";
        tokenNameMiddle = token.shareTokenSymbol.replace("fc", "");
      } else if (token.voltType === 2) {
        voltParentheses = "(Volt 02 Put)";
        tagShort = "volt02";
        tagLong = "volt-02-put";
        tokenNameMiddle = token.shareTokenSymbol.replace("fp", "");
      } else if (token.voltType === 3) {
        voltParentheses = "(Volt 03 Crab)";
        tagShort = "volt03";
        tagLong = "volt-03-crab";
        tokenNameMiddle = token.shareTokenSymbol.replace("fcrab", "");
      } else if (token.voltType === 4) {
        voltParentheses = "(Volt 04 Basis)";
        tagShort = "volt04";
        tagLong = "volt-04-basis";
        tokenNameMiddle = token.shareTokenSymbol.replace("fbasis", "");
      } else if (token.voltType === 5) {
        voltParentheses = "(Volt 05 Prot.)";
        tagShort = "volt05";
        tagLong = "volt-05-prot";
        token.shareTokenSymbol = token.shareTokenSymbol.replace(
          "fprotect",
          "fprot"
        );
        tokenNameMiddle = token.shareTokenSymbol.replace("fprot", "");
      } else {
        console.log(token);
        throw new Error("Unknown volt type");
      }

      // Long symbols are unavoidable in some cases
      if (token.shareTokenSymbol.length > 10) {
        console.log(
          `Warning: ${token.shareTokenSymbol} is ${
            token.shareTokenSymbol.length
          } characters long. Truncating to ${token.shareTokenSymbol.slice(
            0,
            10
          )}`
        );
      }

      const fullName =
        `Friktion ${tokenNameMiddle} ${voltParentheses}`.trimEnd();
      if (fullName.length > 32) {
        throw new Error(
          `Token name for ${fullName} is too long. Metaplex only supports 32 characters`
        );
      }

      return {
        chainId: 101,
        address: token.shareTokenMint,
        // Metaplex limits symbol to 10 characters
        symbol: token.shareTokenSymbol.slice(0, 10),
        // Metaplex limits name to 32 characters
        name: fullName,
        decimals: token.shareTokenDecimals,
        logoURI: `https://friktion-labs.github.io/mainnet-tvl-snapshots/metaplex-token-metadata/${token.shareTokenMint}.png`,
        tags: ["friktion", "friktion-ftoken", tagShort, tagLong].filter(
          (x) => x !== undefined
        ),
        extensions: {
          discord: "https://discord.com/invite/eSkK9X67Qj",
          github: "https://github.com/Friktion-Labs",
          medium: "https://friktionlabs.medium.com/",
          twitter: "https://twitter.com/friktion_labs",
          website: "https://friktion.fi",
        },
      };
    });

  try {
    fs.mkdirSync("./metaplex-token-metadata");
  } catch (e) {}
  const metaplexTokenMetadataTokenList = legacyFormatTokenList.map((legacy) => {
    const metaplexFormat = {
      name: legacy.name,
      symbol: legacy.symbol,
      description: legacy.name,
      image: legacy.logoURI,
      external_url: "https://friktion.fi",
    };
    fs.writeFileSync(
      `metaplex-token-metadata/${legacy.address}.json`,
      JSON.stringify(metaplexFormat, null, 2)
    );
    if (!fs.existsSync(`metaplex-token-metadata/${legacy.address}.png`)) {
      console.log("Missing token image for", legacy);
    }
    return metaplexFormat;
  });
  fs.writeFileSync(
    "legacy-format-token-list.json",
    JSON.stringify(legacyFormatTokenList, null, 2)
  );
  fs.writeFileSync(
    "metaplex-metadata-token-list.json",
    JSON.stringify(metaplexTokenMetadataTokenList, null, 2)
  );

  // legacy-format-token-list.json
}

https
  .get(
    "https://friktion-labs.github.io/mainnet-tvl-snapshots/friktionSnapshot.json",
    (resp: any) => {
      let data = "";
      resp.on("data", (chunk: string) => {
        data += chunk;
      });
      resp.on("end", () => {
        main(JSON.parse(data));
      });
    }
  )
  .on("error", (err: Error) => {
    console.log("Error: " + err.message);
  });

type MainnetVolt = {
  globalId: string;
  voltVaultId: string;
  extraVaultDataId: string;
  vaultAuthority: string;
  quoteMint: string;
  underlyingMint: string;
  depositTokenMint: string;
  shareTokenMint: string;
  shareTokenSymbol: string;
  shareTokenDecimals: number;
  depositPool: string;
  premiumPool: string;
  spotSerumMarketId: string;
  depositTokenSymbol: string;
  depositTokenCoingeckoId: string;
  underlyingTokenSymbol: string;
  underlyingTokenCoingeckoId: string;
  voltType: number;
  apy: number;
  isVoltage: false;
  isInCircuits: false;
  highVoltage: string;
  shareTokenPrice: number;
  depositTokenPrice: number;
  tvlUsd: number;
  tvlDepositToken: number;
  capacityUsd: number;
  capacityDepositToken: number;
  latestEpochYield: number;
  weeklyPy: number;
  monthlyPy: number;
  apr: number;
  apyAfterFees: number;
  performanceFeeRate: number;
  withdrawalFeeRate: number;
  nextAutocompoundingTime: number;
  lastTradedOption: string;
};

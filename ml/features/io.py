from pathlib import Path

import pandas as pd


def read_table(path):
    path = Path(path)

    name = path.name.lower()

    if name.endswith(".parquet"):
        return pd.read_parquet(path)

    if name.endswith(".csv.gz"):
        return pd.read_csv(
            path,
            compression="gzip",
        )

    if name.endswith(".csv"):
        return pd.read_csv(path)

    raise ValueError(
        f"Formato não suportado: {path}"
    )


def write_table(
    df,
    path_without_extension,
    preferred_format="parquet",
):
    path_without_extension = Path(
        path_without_extension
    )

    path_without_extension.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if preferred_format == "parquet":
        path = Path(
            f"{path_without_extension}.parquet"
        )

        try:
            df.to_parquet(
                path,
                index=False,
            )
            return path
        except ImportError:
            pass

    path = Path(
        f"{path_without_extension}.csv.gz"
    )

    df.to_csv(
        path,
        index=False,
        compression="gzip",
    )

    return path

"""
EDA individual dos datasets.

Este módulo documenta o procedimento da Fase 3 / Passo 1.
A execução de produção deve usar os datasets originais configurados
em data/external e gerar saídas em reports/eda.

O relatório completo usado no TCC está versionado em:
    reports/eda/eda_summary.json
    reports/eda/eda_summary.md

Os normalizadores não são substituídos por este script; EDA e
normalização são etapas distintas.
"""

from pathlib import Path
import json


REPORT_DIR = Path("reports/eda")


def load_eda_summary():
    path = REPORT_DIR / "eda_summary.json"

    if not path.exists():
        raise FileNotFoundError(
            "Relatório EDA não encontrado. "
            "Gere a análise antes de continuar."
        )

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def validate_eda_summary():
    report = load_eda_summary()

    assert report["phase"] == 3
    assert report["step"] == 1

    required = {
        "mendeley",
        "v2i",
        "longterm",
        "station",
    }

    assert required == set(
        report["datasets"].keys()
    )

    assert (
        report["datasets"]["mendeley"][
            "rows_normal"
        ]
        == 29990
    )

    assert (
        report["datasets"]["v2i"][
            "beacon_profile_80211n_rows"
        ]
        == 14812
    )

    assert (
        report["datasets"]["station"][
            "frames"
        ]
        == 97290
    )

    print(
        "EDA da Fase 3 / Passo 1 "
        "validada com sucesso."
    )

    return report


if __name__ == "__main__":
    validate_eda_summary()

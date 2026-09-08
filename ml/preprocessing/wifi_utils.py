import numpy as np
import pandas as pd


def channel_to_frequency_mhz(channel):
    """
    Converte canais Wi-Fi conhecidos para frequência central aproximada.

    Retorna NaN quando a conversão não é segura para o escopo atual.
    """
    if pd.isna(channel):
        return np.nan

    try:
        channel = int(channel)
    except (TypeError, ValueError):
        return np.nan

    # 2.4 GHz
    if 1 <= channel <= 13:
        return 2407 + channel * 5

    if channel == 14:
        return 2484

    # 5 GHz
    if 32 <= channel <= 177:
        return 5000 + channel * 5

    # Não inferimos outras bandas apenas pelo número do canal.
    return np.nan

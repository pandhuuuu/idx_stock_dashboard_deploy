import pandas as pd
from functools import lru_cache

DEFAULT_TICKERS = [
    "BBCA","BBRI","BMRI","BRIS","BBNI","BBTN","BJBR","BJTM","BDMN","MEGA",
    "TLKM","EXCL","ISAT","MTEL","TOWR","TBIG",
    "ASII","UNVR","ICBP","INDF","MYOR","KLBF","CPIN","JPFA","ULTJ","SIDO","HMSP","GGRM",
    "ADRO","ADMR","PTBA","ITMG","INDY","HRUM","MBMA","PGAS","MEDC","ENRG",
    "ANTM","MDKA","BRMS","INCO","ARCI","PSAB","DKFT",
    "AALI","LSIP","SSMS","TBLA",
    "AKRA","ERAA","ACES","MAPI","RALS","LPPF",
    "GOTO","BUKA","DCII",
    "BRPT","SMGR","INTP","WSKT","WIKA","ADHI","PTPP","WEGE","WTON",
    "JSMR","CMNP","META",
    "BSDE","CTRA","SMRA","PWON","DMAS",
    "SCMA","MDIA","ELSA","IPCC",
    "KIJA","ASGR","TRON",
    "AMRT","HEAL","SILO","MIKA",
    "FREN","EDGE","NICE","PGEO",
    "SRTG","BNLI","ARTO","BBYB","AGRO",
    "DEFI","WBSA","CDIA","PTRO","BUMI"
]

@lru_cache(maxsize=1)
def get_all_idx_tickers():
    try:
        url = "https://raw.githubusercontent.com/datasets/idx-listed-companies/main/data/idx.csv"
        df = pd.read_csv(url)
        return df["ticker"].dropna().unique().tolist()
    except Exception as e:
        print(f"[AUTO IDX ERROR]: {e}")
        return None

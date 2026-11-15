from pathlib import Path
import numpy as np, pandas as pd, pytest
from fpw.paths import ROOT as R, CODE_ROOT; FP = R/"data/processed/features.parquet"
pytestmark = pytest.mark.skipif(not FP.exists(), reason="S04 not run")
def test_no_inf():
    F = pd.read_parquet(FP); num = F.select_dtypes("number")
    assert not np.isinf(num.to_numpy(dtype=float)).any()

from pathlib import Path
import pandas as pd, pytest
from fpw.paths import ROOT as R, CODE_ROOT; T = R/"reports/tables/T11.csv"
pytestmark = pytest.mark.skipif(not T.exists(), reason="S10 not run")
def test_t11(): t = pd.read_csv(T); assert t.check.str.contains("placebo").any() and t.check.str.contains("leave-one").any()

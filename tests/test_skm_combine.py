import pandas as pd

from skm.models.skm_combine import combine_skm


def test_combine_skm_formula():
    df = pd.DataFrame(
        {
            "delta_p": [0.1, 0.2],
            "D": [1.0, 2.0],
            "C": [1.0, 1.0],
            "R": [1.0, 1.0],
        }
    )
    skm = combine_skm(df)
    # SKM = dp * (1 + 0.3*D + 0.3*C + 0.3*R)
    assert abs(skm.iloc[0] - 0.1 * (1 + 0.3 + 0.3 + 0.3)) < 1e-6
    assert abs(skm.iloc[1] - 0.2 * (1 + 0.6 + 0.3 + 0.3)) < 1e-6

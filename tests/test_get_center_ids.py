import pandas as pd
from opponent_analysis.preprocessing import Preprocessing

preprocessing = Preprocessing()


def test_get_center_ids():
    # Sample data
    event_data_tot = pd.DataFrame(
        {
            "index": [0, 1, 2],
            "match_id": [1, 1, 1],
            "team": ["A", "A", "A"],
            "tactics": [
                None,
                {
                    "lineup": [
                        {"position": {"id": 3}, "player": {"id": 10}},
                        {"position": {"id": 4}, "player": {"id": 11}},
                    ]
                },
                None,
            ],
        }
    )

    # Run the function
    result = preprocessing.get_center_ids(event_data_tot)

    # Check if the center_id column is added and contains the expected values
    assert "center_id" in result.columns
    assert result["center_id"].dropna().tolist() == [[10, 11], [10, 11]]

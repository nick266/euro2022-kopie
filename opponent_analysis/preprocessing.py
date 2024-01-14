from opponent_analysis.config import Config
import pandas as pd


class Preprocessing:
    """Adds additional information to the raw and sorts it"""

    def __init__(
        self,
    ):
        self.conf = Config()

    def get_center_ids(self, event_data_tot: pd.DataFrame):
        """gets the player ids of the centers at the current state of the game.

        Args:
            event_data_tot (pd.DataFrame): _description_

        Returns:
            pd.DataFrame: original dataframe with the an additional column
            with the center player ids
        """
        center_back = pd.DataFrame()
        for index, row in event_data_tot.iterrows():

            if isinstance(row.tactics, dict):
                player_temp = []
                match_id = row.match_id
                team = row.team
                index = row["index"]
                for player in row.tactics["lineup"]:
                    if 2 < player["position"]["id"] < 6:
                        player_temp.append(player["player"]["id"])
                center_back_temp = pd.DataFrame(
                    {
                        "match_id": [match_id],
                        "team": [team],
                        "index": [index],
                        "center_id": [player_temp],
                    }
                )
                center_back = pd.concat([center_back, center_back_temp])
        df_center = pd.merge(
            event_data_tot,
            center_back,
            how="left",
            on=["match_id", "index", "team"],  # noqa: E501
        ).sort_values(["match_id", "team", "index"])
        df_center["center_id"].ffill(inplace=True)
        return df_center

    def add_opponent_team(self, df_preprocessed: pd.DataFrame):
        """Adds the opponent as a new column

        Args:
            df_preprocessed (pd.DataFrame): dataframe with event and 360 data

        Returns:
            pd.DataFrame: original dataframe plus the opponent column
        """
        grouped_teams = df_preprocessed.groupby("match_id").team.unique()
        teams_df_1 = grouped_teams.apply(pd.Series)
        teams_df_1.columns = ["team_1", "team_2"]
        teams_df_1.reset_index(inplace=True)
        teams_df_2 = teams_df_1.copy()
        teams_df_2.columns = ["match_id", "team_2", "team_1"]
        df_teams = pd.concat([teams_df_2, teams_df_1])
        df_teams.columns = ["match_id", "team", "opponent"]
        df_preprocessed = df_preprocessed.merge(
            df_teams, how="left", on=["match_id", "team"]
        )
        return df_preprocessed

    def run_preprocessing(self, df_raw: pd.DataFrame):
        """Runs the different functions and adds a event time to each event

        Args:
            df_raw (pd.DataFrame): the raw merged 360 and event data

        Returns:
            pd.DataFrame: original dataframe sorted and enriched with some
            information
        """
        df_center = self.get_center_ids(df_raw)
        df_with_opponent = self.add_opponent_team(df_center)
        df_preprocessed = df_with_opponent.sort_values(["match_id", "index"])
        df_preprocessed["event_time"] = (
            df_preprocessed.minute.values * 60 + df_preprocessed.second.values
        )
        df_preprocessed.reset_index(inplace=True)
        return df_preprocessed

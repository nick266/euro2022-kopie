from opponent_analysis.config import Config
import pandas as pd


class KPIs:
    """Here all the relevant KPIs are calculated that enrich the event and 360
    data.
    """

    def __init__(
        self,
    ):
        self.conf = Config()

    def get_time_delta_from_opponent_goal_kick(
        self, df_preprocessed: pd.DataFrame
    ):  # noqa: E501
        """Adds the time delta from the last goal kick of the opponent to each
        event

        Args:
            df_preprocessed (pd.DataFrame): the preprocessed data frame

        Returns:
            pd.DataFrame: original dataframe with the additional column
            delta_goal_kick
        """
        mask = (
            df_preprocessed["play_pattern"].shift(1) != "From Goal Kick"
        ) & (  # noqa: E501
            df_preprocessed["play_pattern"] == "From Goal Kick"
        )

        result = df_preprocessed[mask]
        df_goal_kick = pd.DataFrame(
            data={
                "event_time": result.minute.values * 60 + result.second.values,
                "opponent": result.team.values,
                "match_id": result.match_id.values,
                "goal_kick_time": result.minute.values * 60
                + result.second.values,  # noqa: E501
            },
            index=result.timestamp.index,
        ).sort_values(["event_time"])
        df_preprocessed.sort_values("event_time", inplace=True)
        df_preprocessed = pd.merge_asof(
            df_preprocessed,
            df_goal_kick,
            on="event_time",
            by=["match_id", "opponent"],
            direction="backward",
        )
        df_preprocessed["delta_goal_kick"] = (
            df_preprocessed["event_time"] - df_preprocessed["goal_kick_time"]
        )
        return df_preprocessed

    def get_center_events_after_opponent_goal_kick(
        self, df_preprocessed: pd.DataFrame, tolerance: int
    ):  # noqa: E501
        """_summary_

        Args:
            df_preprocessed (pd.DataFrame): the preprocessed data frame
            tolerance (int): the tolerance after each goalkick in which an
            event with a center is taken into account as directly after the
            goal kick

        Returns:
            pd.DataFrame: Dataframe with events of the centers directly after
            the goal kick with their x and y coordinate at that point in time
        """
        mask = df_preprocessed.apply(
            lambda row: row["player_id"] in row["center_id"], axis=1
        )
        df_delta_goal_kick = df_preprocessed[mask][
            ["center_id", "player_id", "location", "delta_goal_kick", "team"]
        ]
        df_result = df_delta_goal_kick[
            df_delta_goal_kick["delta_goal_kick"] < tolerance
        ]
        df_temp = df_result["location"].apply(pd.Series)
        df_temp.columns = ["x", "y"]
        df = pd.concat([df_result, df_temp], axis=1)
        return df

    def get_goals_xg(self, df_preprocessed: pd.DataFrame):
        """_summary_

        Args:
            df (pd.DataFrame):  the preprocessed data frame

        Returns:
            pd.DataFrame: The xgs for each player plus the acctual goals
        """
        df_xg = df_preprocessed.groupby(
            ["team", "player"]
        ).shot_statsbomb_xg.sum()  # noqa: E501
        df_goals = (
            df_preprocessed[df_preprocessed.shot_outcome == "Goal"]
            .groupby(["team", "player"])["shot_outcome"]
            .count()
        )
        df_merged = pd.merge(
            df_xg, df_goals, left_index=True, right_index=True, how="left"
        )
        df_result = df_merged.sort_values(
            ["team", "shot_outcome", "shot_statsbomb_xg"], ascending=False
        )
        df_result.fillna(0, inplace=True)
        return df_result

    def calculate_passed_opponents(self, row: pd.Series):
        """Determines the total passed opponents of a player

        Args:
            row (pd.Series): from each row the start and end of the pass is
              taken. Thereby the number of players is taken from the
              freeze_frame of the 360 data. Incomplete passes are not
              considered in ths KPI.

        Returns:
            npndarray: the number of passed opponents
        """
        passed_opponents = 0
        for player in row["freeze_frame"]:
            if not player["teammate"]:
                if (
                    row["location"][0]
                    < player["location"][0]
                    < row["pass_end_location"][0]
                ):
                    passed_opponents = passed_opponents + 1
        return passed_opponents

    def get_passed_opponents(self, df: pd.DataFrame):
        """adds the passed opponents to the original dataframe and groups it
        by team and player

        Args:
            df (pd.DataFrame): preprocessed dataframe with event and 360 data

        Returns:
            pd.DataFrame: total passed opponents for each player. Team is in
            the index.
        """
        df_passes = df[
            [
                "player",
                "team",
                "match_id",
                "location",
                "pass_end_location",
                "pass_outcome",
                "freeze_frame",
            ]
        ].dropna(
            subset=["location", "pass_end_location", "freeze_frame"], axis=0
        )  # noqa: E501
        df_passes_complete = df_passes[df_passes["pass_outcome"].isnull()]
        df_passes_complete["passed_opponents"] = df_passes_complete.apply(
            self.calculate_passed_opponents, axis=1
        )
        df_result = (
            df_passes_complete.groupby(["team", "player"])
            .passed_opponents.sum()
            .sort_values(ascending=False)
        )
        return df_result

    def get_assists_to_xg(self, df: pd.DataFrame):
        """This function takes a look at the assist that were given to a shot,
        especially the expected goals for that shot.

        Args:
            df (pd.DataFrame): preprocessed dataframe with event and 360 data

        Returns:
            pd.DataFrame: The summed up xgs resulting from an assist of each
            player. team is in the index.
        """
        df_temp = df[["pass_assisted_shot_id", "player"]]
        df_temp.columns = ["id_for_merge", "player_assisted"]
        df_merged = pd.merge(
            df, df_temp, left_on="id", right_on="id_for_merge", how="left"
        )
        df_result = (
            df_merged[["team", "shot_statsbomb_xg", "player_assisted"]]
            .groupby(["team", "player_assisted"])
            .sum()
        )
        return df_result.sort_values(
            ["team", "shot_statsbomb_xg"], ascending=False
        )  # noqa: E501

    def create_high_level_kpis(self, df_match: pd.DataFrame):
        """Summary of some high level KPIs like possession for each team.
        Additionally the mean value and the STD is determined.

        Args:
            df_match (pd.DataFrame): event and 360 data grouped by match_id

        Returns:
            pd.DataFrame: high level KPIs for each match
        """
        kpi_summary = pd.DataFrame()
        for team in df_match.team.unique():
            other_team = [t for t in df_match.team.unique() if t != team]
            team_events = df_match[df_match.team == team]
            other_team_events = df_match[df_match.team == other_team[0]]

            # Total goals
            goals_scored = team_events[
                team_events["shot_outcome"] == "Goal"
            ].shape[  # noqa: E501
                0
            ]  # noqa: E501
            goals_conceded = other_team_events[
                other_team_events["shot_outcome"] == "Goal"
            ].shape[0]
            shots = len(team_events[team_events["type"] == "Shot"])
            shot_statsbomb_xg_scored = team_events["shot_statsbomb_xg"].sum()
            shot_statsbomb_xg_conceded = other_team_events[
                "shot_statsbomb_xg"
            ].sum()  # noqa: E501
            passes = len(team_events[team_events["type"] == "Pass"])
            completed_passes = len(
                team_events[
                    (team_events["type"] == "Pass")
                    & (team_events["pass_outcome"].isnull())
                ]
            )
            pass_accuracy = (completed_passes / passes) * 100
            interceptions = len(
                team_events[team_events["type"] == "Interception"]
            )  # noqa: E501
            clearances = len(team_events[team_events["type"] == "Clearance"])
            team_possession_seconds = team_events[
                (team_events["type"] != "Pressure")
            ].duration.sum()
            other_team_possession_seconds = other_team_events[
                (other_team_events["type"] != "Pressure")
            ].duration.sum()

            kpi_summary_temp = pd.DataFrame(
                {
                    "goals_scored": [goals_scored],
                    "goals_conceded": [goals_conceded],
                    "shot_statsbomb_xg_scored": [shot_statsbomb_xg_scored],
                    "shot_statsbomb_xg_conceded": [shot_statsbomb_xg_conceded],
                    "shots": [shots],
                    "passes": [passes],
                    "pass_accuracy": [pass_accuracy],
                    "interceptions": [interceptions],
                    "clearances": [clearances],
                    "possession": [
                        team_possession_seconds
                        / (
                            other_team_possession_seconds
                            + team_possession_seconds  # noqa: E501
                        )
                    ],
                },
                index=[team],
            )
            kpi_summary = pd.concat(
                [kpi_summary, kpi_summary_temp], ignore_index=False
            )  # noqa: E501
        return kpi_summary

    def run_kpis(self, df_preprocessed: pd.DataFrame):
        """The different functions are executed, the results are stored in
        dataframes, and returned to be displayed in the dashboard

        Args:
            df_preprocessed (pd.DataFrame): event and 360 data preprocessed

        Returns:
            pd.DataFrame: high level KPIs
            pd.DataFrame: center position at opponent goal kick
            pd.DataFrame: xg goals for each player
            pd.DataFrame: assists to xg for each player
            pd.DataFrame: passed opponents by a pass for each player
        """
        df_time_delta = self.get_time_delta_from_opponent_goal_kick(
            df_preprocessed
        )  # noqa: E501
        df_iv_position_at_opponent_goal_kick = (
            self.get_center_events_after_opponent_goal_kick(
                df_time_delta, self.conf.goal_kick_tolerance
            )
        )
        df_kpis = df_preprocessed.groupby(["match_id"]).apply(
            self.create_high_level_kpis
        )
        df_goals_xg = self.get_goals_xg(df_preprocessed)
        df_assists_to_xg = self.get_assists_to_xg(df_preprocessed)
        df_passed_opponents = self.get_passed_opponents(df_preprocessed)
        return (
            df_kpis,
            df_iv_position_at_opponent_goal_kick,
            df_goals_xg,
            df_assists_to_xg,
            df_passed_opponents,
        )

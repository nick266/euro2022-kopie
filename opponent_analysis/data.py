from opponent_analysis.config import Config
import pandas as pd
from statsbombpy import sb
import streamlit as st
import numpy as np


class Data:
    """This class gahters all the functions that are needed to get the data
    from statsbomb and merge them
    """

    def __init__(
        self,
    ):
        self.conf = Config()

    @st.cache_data
    def get_match_id(_self):
        """this function gets the match ids for the tournament specified in
        the config

        Args:
            _self

        Returns:
            numpy.ndarray: array of match ids
        """

        competitions = sb.competitions()
        womens_euro_competition = competitions[
            competitions["competition_name"] == _self.conf.competition_name
        ]
        womens_euro_2022 = womens_euro_competition[
            womens_euro_competition["season_name"] == _self.conf.season_name
        ]
        euro_competition_id = womens_euro_2022.competition_id.unique()[0]
        euro_season_id = womens_euro_2022.season_id.unique()[0]
        matches = sb.matches(
            competition_id=euro_competition_id, season_id=euro_season_id
        )
        match_ids = matches[
            matches.match_date < _self.conf.date_of_analysis
        ].match_id  # noqa: E501
        return match_ids

    @st.cache_data
    def load_statsbomb_data(_self, match_ids: np.ndarray):
        """This function loads the event data and reads the 360 data from local
        json files. It merges them before returning a merged dataframe.

        Args:
            match_ids (np.ndarray): array of match ids

        Returns:
            pd.DataFrame: merged event and 360 data
        """
        event_data_tot = pd.DataFrame()
        for match_id in match_ids:
            event_data = sb.events(match_id=match_id)
            df_360 = pd.read_json(
                f"{_self.conf.path_to_statsbomb_open_data}{match_id}.json"  # noqa: E501
            )
            df_merged = pd.merge(
                event_data,
                df_360,
                how="left",
                left_on="id",
                right_on="event_uuid",  # noqa: E501
            )
            event_data_tot = pd.concat(
                [event_data_tot, df_merged], ignore_index=True
            )  # noqa: E501
        return event_data_tot

    @st.cache_data
    def get_data(_self):
        """Runs all the nesseccary function and returns the data

        Args:
            _self

        Returns:
            pd.DataFrame: event and 360 data merged for the tournament
            specified in the config
        """
        match_ids = _self.get_match_id()
        event_data_tot = _self.load_statsbomb_data(match_ids)
        return event_data_tot

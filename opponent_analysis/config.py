class Config:
    """Here all the values are set that you need to do an analysis of the
    euro 2022 women before the final
    """

    def __init__(self):
        self.goal_kick_tolerance = 5
        self.competition_name = "UEFA Women's Euro"
        self.season_name = "2022"
        self.date_of_analysis = "2022-07-30"
        self.path_to_statsbomb_open_data = "360/"

# Euro 2022
This is the prototype of a dashboard that can be used to analyse the different teams.  \
It uses free statsbomb event- and 360-data of the women euro 2022.
## Get it running
First you need to clone this repo: \
`git clone https://github.com/nick266/euro2022.git` \
Additionally, you will need the 360 data. Therefore you should clone the "open-data" repo of statsbomb by:
`git clone https://github.com/statsbomb/open-data.git` \
Specify the path to the open data folder in the config under "path_to_statsbomb_open_data".
Afterwards you can install the nesseccary packages in a virtual enviroment. \
The enviroment you can create by (on mac): \
`python -m venv venv` \
and activate it by: \
`source venv/bin/activate` \
Now the package can be installed by (using python 3.11.1): \
`poetry install` \
You host the dashboard locally by executing: \
`poetry run streamlit run opponent_analysis/streamlit_app.py`

## To dos

- caching (check)
- colors for dashboard (check)
- possession in percentag (check)
- defender distance (check)
- filter for dates (check)
- average position (cant do)
- soccer field metric (eg pass direction) (check)
- list of players with xgoals and xassits (check)
- line breaking passes (check)
- unit tests (check)
- doc strings (check)
- new metric based on difference in thread of scoring or conceding a goal in after an event
- hide std, mean and other column
- correlation to win/goal for each KPI
- one table for goals, xg and assists
- download option (check)
- player passed by dribbling

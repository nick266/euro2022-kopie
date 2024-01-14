import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.backends.backend_pdf
from mplsoccer import Pitch
import numpy as np
from io import BytesIO
import base64
from opponent_analysis.preprocessing import Preprocessing
from opponent_analysis.data import Data
from opponent_analysis.kpis import KPIs
from opponent_analysis.config import Config
import os

conf = Config()


def fig_to_pdf_base64(fig: matplotlib.figure.Figure):
    """Function for downloading figures from app

    Args:
        fig (matplotlib.figure.Figure): any mtplotlib figure that is displayed

    Returns:
        str: binary data of the PDF file that is base64
    """
    pdf_buffer = BytesIO()
    pdf = matplotlib.backends.backend_pdf.PdfPages(
        pdf_buffer, keep_empty=False
    )  # noqa: E501
    pdf.savefig(fig)
    pdf.close()
    pdf_base64 = base64.b64encode(pdf_buffer.getvalue()).decode("utf-8")
    return pdf_base64


def color_cells(row: pd.Series):
    """returns the color of the cell of the dataframe to indicate whether the
    KPI is over or under or within the average.

    Args:
        row (pd.Series): kpi with std, mean, and a column that indicates
          whether a high value is good or not

    Returns:
        str: color for the row
    """
    cell_color = []
    for val in row:
        if row["high_is_good"] * row["Team Values"] < row["high_is_good"] * (
            row["Average"] - 0.25 * row["STD"]
        ):
            color = "red"
        elif row["high_is_good"] * row["Team Values"] > row["high_is_good"] * (
            row["Average"] + 0.25 * row["STD"]
        ):
            color = "green"
        else:
            color = "orange"
        cell_color.append(f"color: {color}")
    return cell_color


def create_pass_analysis(filtered_data: pd.DataFrame):
    """Plots the passes in the dataframe as vectors on the pitch.
    depending on the outcome of the pass the color is chosen.

    Args:
        filtered_data (pd.DataFrame): dataframe with start and end of passes
        and the outcome of the pass

    Returns:
        matplotlib.figure.Figure: figure of a pitch with passes plotted as
          vectors
    """
    fig, ax = plt.subplots(figsize=(10, 6), tight_layout=True)
    pitch = Pitch(pitch_type="statsbomb", line_zorder=2)

    pitch.draw(ax=ax)

    for idx, row in filtered_data.iterrows():
        if not isinstance(row["pass_outcome"], float):
            color = "red"
            width = 0.5
        elif not isinstance(row["pass_shot_assist"], float):
            color = "silver"
            width = 1
        elif not isinstance(row["pass_goal_assist"], float):
            color = "gold"
            width = 2
        else:
            color = "blue"
            width = 0.5
        pitch.arrows(
            float(row["location"].split("[")[1].split(",")[0]),
            float(row["location"].split("]")[0].split(",")[1]),
            float(row["pass_end_location"].split("[")[1].split(",")[0]),
            float(row["pass_end_location"].split("]")[0].split(",")[1]),
            ax=ax,
            width=width,
            headwidth=5,
            color=color,
            zorder=3,
            alpha=0.7,
        )
    return fig


def create_high_of_center_analysis(df: pd.DataFrame, team: str):
    """To identify the hight of the centers at the moment at which the opponent
      team has a goal kick. Therefore goal kicks are
    detected. Next for every event the timedelta is defined from the goal kick.
    Finally all events are filtered that are close to the goal kick which
    invole a center player. By the location of these events the hight is
    determined.
    This function determines the mean and plots the results on a pitch.

    Args:
        df (pd.DataFrame): _description_
        team (str): _description_

    Returns:
        matplotlib.figure.Figure: plot of the hight and events on the pitch
        int: average distance to the own goal line
        int: average distance to the own goal line for all teams
    """
    if len(df[df.team == team]) == 0:
        return None, None, None
    fig, ax = plt.subplots(figsize=(10, 6), tight_layout=True)
    pitch = Pitch(pitch_type="statsbomb", line_zorder=2)
    pitch.draw(ax=ax)
    average_coord = sum(df[df.team == team].x) / len(df[df.team == team].x)
    average_tot = sum(df.x) / len(df.x)
    ax.vlines(
        x=average_coord,
        ymin=0,
        ymax=pitch.dim.bottom,
        color="blue",
        linestyle="-",
        linewidth=3,
        alpha=0.6,
    )
    ax.vlines(
        x=average_tot,
        ymin=0,
        ymax=pitch.dim.bottom,
        color="black",
        linestyle="--",
        linewidth=1,
        alpha=0.6,
    )
    pitch.scatter(
        114, 34, s=300, color="white", edgecolors="black", zorder=3, ax=ax
    )  # noqa: E501
    pitch.scatter(
        df[df.team == team].x,
        df[df.team == team].y,
        s=150,
        color="red",
        edgecolors="black",
        zorder=3,
        ax=ax,
    )

    return fig, average_coord, average_tot


@st.cache_data
def run_code():
    """Calculates all nesseccary dataframes for the tables and figure

    Returns:
        pd.DataFrame: standard KPIs like xg or pass accuracy
        pd.DataFrame: the center position while opponent goal kick
        pd.DataFrame: expected goals and goals for each player
        pd.DataFrame: assists to expected goals for each player
        pd.DataFrame: the complete preprocced dataframe
        pd.DataFrame: dataframe with the total number of passed by opponents
                    by passing
    """
    csv_file = "df_preprocessed_1.csv"
    if not os.path.exists(csv_file):
        data = Data()
        df_raw = data.get_data()
        p = Preprocessing()
        df_preprocessed = p.run_preprocessing(df_raw)
        kpis = KPIs()
        (
            df_kpis,
            df_iv_position_at_opponent_goal_kick,
            df_goals_xg,
            df_assists_to_xg,
            df_passed_opponents,
        ) = kpis.run_kpis(df_preprocessed)
        df_kpis.to_csv("df_kpis.csv")
        df_iv_position_at_opponent_goal_kick.to_csv(
            "df_iv_position_at_opponent_goal_kick.csv"
        )
        df_goals_xg.to_csv("df_goals_xg.csv")
        half_len_prepro = int(len(df_preprocessed) / 2)
        df_preprocessed[:half_len_prepro].to_csv("df_preprocessed_1.csv")
        df_preprocessed[half_len_prepro:].to_csv("df_preprocessed_2.csv")
        df_assists_to_xg.to_csv("df_assists_to_xg.csv")
        df_passed_opponents.to_csv("df_passed_opponents.csv")
    else:
        df_kpis = pd.read_csv("df_kpis.csv", index_col=[0, 1])
        df_iv_position_at_opponent_goal_kick = pd.read_csv(
            "df_iv_position_at_opponent_goal_kick.csv", index_col=0
        )
        df_goals_xg = pd.read_csv("df_goals_xg.csv", index_col=[0, 1])
        df_preprocessed_1 = pd.read_csv("df_preprocessed_1.csv", index_col=0)
        df_preprocessed_2 = pd.read_csv("df_preprocessed_2.csv", index_col=0)
        df_preprocessed = pd.concat([df_preprocessed_1, df_preprocessed_2])
        df_assists_to_xg = pd.read_csv(
            "df_assists_to_xg.csv", index_col=[0, 1]
        )  # noqa: E501
        df_passed_opponents = pd.read_csv(
            "df_passed_opponents.csv", index_col=[0, 1]
        )  # noqa: E501
    return (
        df_kpis,
        df_iv_position_at_opponent_goal_kick,
        df_goals_xg,
        df_assists_to_xg,
        df_preprocessed,
        df_passed_opponents,
    )  # noqa: E501


(
    df_kpis,
    df_iv_position_at_opponent_goal_kick,
    df_goals_xg,
    df_assists_to_xg,
    df_preprocessed,
    df_passed_opponents,
) = run_code()


st.title("Gegner Analyse")
selected_team = st.selectbox(
    "Wähle ein Team", df_kpis.index.get_level_values(1).unique()
)
team_stats = df_kpis.xs(selected_team, level=1).mean()
average = df_kpis.mean()
std_dev = df_kpis.std()
high_is_good = [1, -1, 1, -1, 1, 1, 1, 1, 1, 1]
result_df = pd.DataFrame(
    {
        "Team Values": team_stats,
        "Average": average,
        "STD": std_dev,
        "high_is_good": high_is_good,
    }
)
styled_result_df = result_df.style.apply(color_cells, axis=1)
st.write(f"High level KPIs für {selected_team}:")
st.write(styled_result_df)

st.write("Die erziehlten Tore im Vergleich zu den xg pro Spielerin")
df_goals_xg.columns = ["xg", "goals"]
st.write(
    df_goals_xg[df_goals_xg.index.get_level_values("team") == selected_team]
)  # noqa: E501

st.write(
    "Die Summe der XGs die durch Pässe der jeweiligen Spielerin entstanden sind"  # noqa: E501
)  # noqa: E501
df_assists_to_xg.columns = ["pass_leading_to_xg"]
st.write(
    df_assists_to_xg[
        df_assists_to_xg.index.get_level_values("team") == selected_team
    ]  # noqa: E501
)

opponent_filter = st.selectbox(
    f"Wähle ein Gegener von {selected_team}",
    np.append(
        df_preprocessed[df_preprocessed["team"] == selected_team][
            "opponent"
        ].unique(),  # noqa: E501
        np.array(["all"]),
    ),
)
if opponent_filter != "all":
    player_filter = st.selectbox(
        "Wähle eine Spielerin",
        np.append(
            df_preprocessed[
                (df_preprocessed["team"] == selected_team)
                & (df_preprocessed["opponent"] == opponent_filter)
            ]["player"].unique(),
            np.array(["all"]),
        ),
    )
else:
    player_filter = st.selectbox(
        "Select Player",
        np.append(
            df_preprocessed[(df_preprocessed["team"] == selected_team)][
                "player"
            ].unique(),
            np.array(["all"]),
        ),
    )
filtered_data = df_preprocessed[(df_preprocessed["team"] == selected_team)]
if opponent_filter != "all":
    filtered_data = filtered_data[
        (filtered_data["opponent"] == opponent_filter)
    ]  # noqa: E501
if player_filter != "all":
    filtered_data = filtered_data[(filtered_data["player"] == player_filter)]
filtered_data = filtered_data[
    [
        "location",
        "pass_end_location",
        "team",
        "match_id",
        "player",
        "pass_outcome",
        "pass_goal_assist",
        "pass_shot_assist",
    ]
].dropna(subset=["location", "pass_end_location"])

st.write(
    f"Alle Pässe von {player_filter} in dem Spiel gegen {opponent_filter}. "
    + "Angekommenen Pässe sind blau, nicht angekomme Pässe sind rot. "
    + "Pässe die zu einem Torschuss geführt haben sind silber, Schüsse die zu einem Tor geführt haben sind golden."  # noqa: E501
)
fig = create_pass_analysis(filtered_data)
st.pyplot(fig)
pdf_base64 = fig_to_pdf_base64(fig)
pdf_href = f'<a href="data:file/pdf;base64,{pdf_base64}" download="plot.pdf">Download PDF</a>'  # noqa: E501
st.markdown(pdf_href, unsafe_allow_html=True)
st.write(
    "Hier ist die Anzahl der überspielten Gegner in Summe pro Spielerin aufgelistet. Es werden nur angekommene Pässe berücksichtigt."  # noqa: E501
)
st.write(
    df_passed_opponents[
        df_passed_opponents.index.get_level_values("team") == selected_team
    ]
)

fig, average_coord, average_tot = create_high_of_center_analysis(
    df=df_iv_position_at_opponent_goal_kick, team=selected_team
)
st.write(
    "Hier sind die Events mit IV Beteiligung direkt nach einem Abstoß durch"
    + f"rote Punkte dargestellt (innerhalb {conf.goal_kick_tolerance}s)"
)
if fig:
    st.pyplot(fig)
    st.write(
        "Aus den events wurde für {selected_team} eine durchschnittliche"
        + f"Distanz zum eigen Torauslinie von {np.round(average_coord,1)} "
        + "yards bestimmt, blaue Linie. \n Der Durchschnitt im Turnier "
        + f"beträgt {np.round(average_tot,1)} yards (schwarze Linie)."  # noqa: E501
    )
    pdf_base64 = fig_to_pdf_base64(fig)
    pdf_href = f'<a href="data:file/pdf;base64,{pdf_base64}" download="plot.pdf">Download PDF</a>'  # noqa: E501
    st.markdown(pdf_href, unsafe_allow_html=True)
else:
    st.write(f"Keine Events gefunden für {selected_team}.")

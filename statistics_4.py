import os
import datetime
import json
import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session
from models import Training, MorningQuiz
from database import get_db
from openai import OpenAI
from dotenv import load_dotenv
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import kaleido

load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
ASSISTANT_ID = os.environ.get("OPENAI_ASSISTANT_ID")


class BaseStatisticsRecord:
    def __init__(
        self,
        session: Session,
        user_id: int,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ):
        self.session = session
        self.user_id = user_id
        self.start_date = start_date
        self.end_date = end_date
        print(
            f"[LOG] Initialized statistics for user_id={user_id} from {start_date} to {end_date}"
        )

    def get_trainings_count(self) -> int:
        count = (
            self.session.query(Training)
            .filter(
                Training.user_id == self.user_id,
                Training.training_start_date >= self.start_date,
                Training.training_start_date < self.end_date,
            )
            .count()
        )
        return count

    def get_training_data(self) -> pd.DataFrame:
        trainings = (
            self.session.query(Training)
            .filter(
                Training.user_id == self.user_id,
                Training.training_start_date >= self.start_date,
                Training.training_start_date < self.end_date,
            )
            .all()
        )

        data = []
        for training in trainings:
            data.append(
                {
                    "date": training.training_start_date,
                    "hardness": training.training_hardness
                    if training.training_hardness
                    else 0,
                    "stress": training.stress_on_next_day
                    if training.stress_on_next_day
                    else 0,
                    "duration": training.training_duration,
                }
            )
        return pd.DataFrame(data)

    def get_sleeping_data(self) -> pd.DataFrame:
        quizzes = (
            self.session.query(MorningQuiz)
            .filter(
                MorningQuiz.user_id == self.user_id,
                MorningQuiz.quiz_datetime >= self.start_date,
                MorningQuiz.quiz_datetime < self.end_date,
            )
            .all()
        )

        data = []
        for quiz in quizzes:
            if quiz.user_sleeping_hours:
                t = quiz.user_sleeping_hours
                hours = t.hour + t.minute / 60 + t.second / 3600
                data.append(
                    {
                        "date": quiz.quiz_datetime,
                        "sleep_hours": hours,
                        "user_feelings": quiz.user_feelings
                        if quiz.user_feelings
                        else 0,
                    }
                )
        return pd.DataFrame(data)

    def generate_plots(self) -> dict:
        training_data = self.get_training_data()
        sleep_data = self.get_sleeping_data()

        # Training metrics plot
        fig1 = make_subplots(specs=[[{"secondary_y": True}]])

        if not training_data.empty:
            fig1.add_trace(
                go.Scatter(
                    x=training_data["date"],
                    y=training_data["hardness"],
                    name="Training Hardness",
                    line=dict(color="#FF9999"),
                )
            )

            fig1.add_trace(
                go.Scatter(
                    x=training_data["date"],
                    y=training_data["stress"],
                    name="Stress Level",
                    line=dict(color="#66B2FF"),
                ),
                secondary_y=True,
            )

        fig1.update_layout(
            title="Training Metrics Over Time",
            template="plotly_white",
            height=500,
            showlegend=True,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
        )

        # Sleep metrics plot
        fig2 = make_subplots(specs=[[{"secondary_y": True}]])

        if not sleep_data.empty:
            fig2.add_trace(
                go.Scatter(
                    x=sleep_data["date"],
                    y=sleep_data["sleep_hours"],
                    name="Sleep Duration",
                    line=dict(color="#99FF99"),
                )
            )

            fig2.add_trace(
                go.Scatter(
                    x=sleep_data["date"],
                    y=sleep_data["user_feelings"],
                    name="Morning Feelings",
                    line=dict(color="#FF99FF"),
                ),
                secondary_y=True,
            )

        fig2.update_layout(
            title="Sleep and Morning Feelings Over Time",
            template="plotly_white",
            height=500,
            showlegend=True,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
        )

        # Save plots as images
        training_plot_path = "training_metrics.png"
        sleep_plot_path = "sleep_metrics.png"

        fig1.write_image(training_plot_path)
        fig2.write_image(sleep_plot_path)

        return {
            "training_plot": training_plot_path,
            "sleep_plot": sleep_plot_path,
            "training_fig": fig1,
            "sleep_fig": fig2,
        }


class WeeklyStatisticsRecord(BaseStatisticsRecord):
    def __init__(
        self, session: Session, user_id: int, week_end: datetime.datetime = None
    ):
        now = datetime.datetime.now()
        week_end = week_end or now
        week_start = week_end - datetime.timedelta(days=7)
        super().__init__(session, user_id, week_start, week_end)


class MonthlyStatisticsRecord(BaseStatisticsRecord):
    def __init__(
        self, session: Session, user_id: int, month_end: datetime.datetime = None
    ):
        now = datetime.datetime.now()
        month_end = month_end or now
        month_start = month_end - datetime.timedelta(days=28)
        super().__init__(session, user_id, month_start, month_end)


if __name__ == "__main__":
    session = next(get_db())
    weekly_stats = WeeklyStatisticsRecord(session, user_id=7)
    plots = weekly_stats.generate_plots()
    print(
        f"Generated plots saved at: {plots['training_plot']} and {plots['sleep_plot']}"
    )

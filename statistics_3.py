import os
import datetime
import json
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sqlalchemy import func, cast, Date
from sqlalchemy.orm import Session
from models import Training, MorningQuiz
from openai import OpenAI
from dotenv import load_dotenv
from loguru import logger

load_dotenv()


# Використовуємо пастельну тему
sns.set_theme(style="whitegrid", palette="pastel")
plt.style.use("seaborn-v0_8-whitegrid")


class BaseStatisticsRecord:
    def __init__(
        self,
        session: Session,
        user_id: int,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        user_full_name: str,
    ):
        """
        Базовий клас для розрахунку статистики за заданий період для конкретного користувача.
        """
        self.session = session
        self.user_id = user_id
        self.start_date = start_date
        self.end_date = end_date
        self.user_full_name = user_full_name
        logger.info(
            f"[BaseStatisticsRecord] Ініціалізовано статистику для user_id={user_id} з {start_date} до {end_date}"
        )

    def get_trainings_count(self) -> int:
        logger.info("[BaseStatisticsRecord] Отримання кількості тренувань...")
        count = (
            self.session.query(Training)
            .filter(
                Training.user_id == self.user_id,
                Training.training_start_date >= self.start_date,
                Training.training_start_date < self.end_date,
            )
            .count()
        )
        logger.info(f"[BaseStatisticsRecord] Кількість тренувань: {count}")
        return count

    def get_average_training_hardness(self) -> float:
        logger.info("[BaseStatisticsRecord] Розрахунок середньої складності тренування...")
        avg = (
            self.session.query(func.avg(Training.training_hardness))
            .filter(
                Training.user_id == self.user_id,
                Training.training_start_date >= self.start_date,
                Training.training_start_date < self.end_date,
            )
            .scalar()
        )
        logger.info(f"[BaseStatisticsRecord] Середня складність: {avg}")
        return avg or 0

    def get_average_stress(self) -> float:
        logger.info("[BaseStatisticsRecord] Розрахунок середнього рівня стресу...")
        avg = (
            self.session.query(func.avg(Training.stress_on_next_day))
            .filter(
                Training.user_id == self.user_id,
                Training.training_start_date >= self.start_date,
                Training.training_start_date < self.end_date,
                Training.stress_on_next_day.isnot(None),
            )
            .scalar()
        )
        logger.info(f"[BaseStatisticsRecord] Середній рівень стресу: {avg}")
        return avg or 0

    def get_sleeping_hours_data(self) -> pd.DataFrame:
        logger.info("[BaseStatisticsRecord] Отримання даних по годинам сну...")
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
                seconds = t.hour * 3600 + t.minute * 60 + t.second
                hours = seconds / 3600
                data.append({"dt": quiz.quiz_datetime, "hours": hours})
        df = pd.DataFrame(data)
        return df

    def get_feelings_data(self) -> pd.DataFrame:
        logger.info("[BaseStatisticsRecord] Отримання даних по самопочуттю...")
        data = (
            self.session.query(MorningQuiz.quiz_datetime, MorningQuiz.user_feelings)
            .filter(
                MorningQuiz.user_id == self.user_id,
                MorningQuiz.quiz_datetime >= self.start_date,
                MorningQuiz.quiz_datetime <= self.end_date,
            )
            .all()
        )
        df = pd.DataFrame(data, columns=["dt", "feelings"])
        return df

    def get_weight_data(self) -> pd.DataFrame:
        """Отримання даних по вазі з ранкових опитувань"""
        logger.info("[BaseStatisticsRecord] Отримання даних по вазі...")
        data = (
            self.session.query(MorningQuiz.quiz_datetime, MorningQuiz.user_weight)
            .filter(
                MorningQuiz.user_id == self.user_id,
                MorningQuiz.quiz_datetime >= self.start_date,
                MorningQuiz.quiz_datetime <= self.end_date,
                MorningQuiz.user_weight.isnot(None)  # Only include records with weight data
            )
            .all()
        )
        df = pd.DataFrame(data, columns=["dt", "weight"])
        return df

    def get_stress_data(self) -> pd.DataFrame:
        logger.info("[BaseStatisticsRecord] Отримання даних по стресу...")
        data = (
            self.session.query(
                Training.training_start_date, Training.stress_on_next_day
            )
            .filter(
                Training.user_id == self.user_id,
                Training.training_start_date >= self.start_date,
                Training.training_start_date < self.end_date,
                Training.stress_on_next_day.isnot(None),
            )
            .all()
        )
        df = pd.DataFrame(data, columns=["dt", "stress"])
        return df

    def get_training_hardness_data(self) -> pd.DataFrame:
        logger.info("[BaseStatisticsRecord] Отримання даних по складності тренувань...")
        data = (
            self.session.query(Training.training_start_date, Training.training_hardness)
            .filter(
                Training.user_id == self.user_id,
                Training.training_start_date >= self.start_date,
                Training.training_start_date < self.end_date,
                Training.training_hardness.isnot(None),
            )
            .all()
        )
        df = pd.DataFrame(data, columns=["dt", "hardness"])
        return df

    def get_soreness_data(self) -> pd.DataFrame:
        logger.info("[BaseStatisticsRecord] Отримання даних по крепатурі...")
        data = (
            self.session.query(
                Training.training_start_date, Training.soreness_on_next_day
            )
            .filter(
                Training.user_id == self.user_id,
                Training.training_start_date >= self.start_date,
                Training.training_start_date < self.end_date,
                Training.soreness_on_next_day.is_(True),
            )
            .all()
        )
        df = pd.DataFrame(data, columns=["dt", "soreness"])
        return df

    def get_daily_trainings(self) -> pd.DataFrame:
        logger.info("[BaseStatisticsRecord] Отримання кількості тренувань по днях...")
        daily_data = (
            self.session.query(
                cast(Training.training_start_date, Date).label("day"),
                func.count(Training.id).label("count"),
            )
            .filter(
                Training.user_id == self.user_id,
                Training.training_start_date >= self.start_date,
                Training.training_start_date < self.end_date,
            )
            .group_by("day")
            .order_by("day")
            .all()
        )
        df = pd.DataFrame(daily_data, columns=["day", "count"])
        return df

    def get_metrics_json(self) -> str:
        logger.info("[BaseStatisticsRecord] Збір метрик у форматі JSON...")
        trainings_count = self.get_trainings_count()
        avg_hardness = self.get_average_training_hardness()
        avg_stress = self.get_average_stress()
        sleep_df = self.get_sleeping_hours_data()
        avg_sleep = sleep_df["hours"].mean() if not sleep_df.empty else 0
        feelings_df = self.get_feelings_data()
        avg_feelings = feelings_df["feelings"].mean() if not feelings_df.empty else 0
        daily_df = self.get_daily_trainings()
        stress_df = self.get_stress_data()
        hardness_df = self.get_training_hardness_data()
        soreness_df = self.get_soreness_data()
        weight_df = self.get_weight_data()
        metrics = {
            "trainings_count": trainings_count,
            "average_training_hardness": avg_hardness,
            "average_stress": avg_stress,
            "average_sleeping_hours": avg_sleep,
            "average_morning_quiz_feelings": avg_feelings,
            "daily_trainings": daily_df.to_dict(orient="records"),
            "stress_data": stress_df.to_dict(orient="records"),
            "sleep_data": sleep_df.to_dict(orient="records"),
            "hardness_data": hardness_df.to_dict(orient="records"),
            "feelings_data": feelings_df.to_dict(orient="records"),
            "soreness_data": soreness_df.to_dict(orient="records"),
            "weight_data": weight_df.to_dict(orient="records"),
        }
        json_metrics = json.dumps(metrics, default=str, indent=2)
        return json_metrics

class WeeklyStatisticsRecord(BaseStatisticsRecord):
    def __init__(
        self,
        session: Session,
        user_id: int,
        week_end: datetime.datetime = None,
        user_full_name: str = None,
    ):
        now = datetime.datetime.now()
        week_end = week_end or now
        week_start = week_end - datetime.timedelta(days=7)
        super().__init__(session, user_id, week_start, week_end, user_full_name)


class MonthlyStatisticsRecord(BaseStatisticsRecord):
    def __init__(
        self,
        session: Session,
        user_id: int,
        month_end: datetime.datetime = None,
        user_full_name: str = None,
    ):
        now = datetime.datetime.now()
        month_end = month_end or now
        month_start = month_end - datetime.timedelta(days=28)
        super().__init__(session, user_id, month_start, month_end, user_full_name)

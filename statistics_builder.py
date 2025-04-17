import os
import datetime
import json
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from sqlalchemy import func, cast, Date
from sqlalchemy.orm import Session
from models import Training, MorningQuiz
from database import get_db
from gpt_statistics_summary_prompt import prompt
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.5,
    api_key=os.environ.get("OPENAI_API_KEY"),
)

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
    ):
        """
        Базовий клас для розрахунку статистики за заданий період для конкретного користувача.
        """
        self.session = session
        self.user_id = user_id
        self.start_date = start_date
        self.end_date = end_date
        print(
            f"[LOG] Ініціалізовано статистику для user_id={user_id} з {start_date} до {end_date}"
        )

    def get_trainings_count(self) -> int:
        print("[LOG] Отримання кількості тренувань...")
        count = (
            self.session.query(Training)
            .filter(
                Training.user_id == self.user_id,
                Training.training_start_date >= self.start_date,
                Training.training_start_date < self.end_date,
            )
            .count()
        )
        print(f"[LOG] Кількість тренувань: {count}")
        return count

    def get_average_training_hardness(self) -> float:
        print("[LOG] Розрахунок середньої складності тренування...")
        avg = (
            self.session.query(func.avg(Training.training_hardness))
            .filter(
                Training.user_id == self.user_id,
                Training.training_start_date >= self.start_date,
                Training.training_start_date < self.end_date,
            )
            .scalar()
        )
        print(f"[LOG] Середня складність: {avg}")
        return avg or 0

    def get_average_stress(self) -> float:
        print("[LOG] Розрахунок середнього рівня стресу...")
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
        print(f"[LOG] Середній рівень стресу: {avg}")
        return avg or 0

    def get_sleeping_hours_data(self) -> pd.DataFrame:
        print("[LOG] Отримання даних по годинам сну...")
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
        print(f"[LOG] Дані по сну: {df}")
        return df

    def get_feelings_data(self) -> pd.DataFrame:
        print("[LOG] Отримання даних по самопочуттю...")
        data = (
            self.session.query(MorningQuiz.quiz_datetime, MorningQuiz.user_feelings)
            .filter(
                MorningQuiz.user_id == self.user_id,
                MorningQuiz.quiz_datetime >= self.start_date,
                MorningQuiz.quiz_datetime < self.end_date,
            )
            .all()
        )
        df = pd.DataFrame(data, columns=["dt", "feelings"])
        print(f"[LOG] Дані по самопочуттю: {df}")
        return df

    def get_stress_data(self) -> pd.DataFrame:
        print("[LOG] Отримання даних по стресу...")
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
        print(f"[LOG] Дані по стресу: {df}")
        return df

    def get_training_hardness_data(self) -> pd.DataFrame:
        print("[LOG] Отримання даних по складності тренувань...")
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
        print(f"[LOG] Дані по складності: {df}")
        return df

    def get_soreness_data(self) -> pd.DataFrame:
        print("[LOG] Отримання даних по крепатурі...")
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
        print(f"[LOG] Дані по крепатурі: {df}")
        return df

    def get_daily_trainings(self) -> pd.DataFrame:
        print("[LOG] Отримання кількості тренувань по днях...")
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
        print(f"[LOG] Дані по днях: {df}")
        return df

    def get_metrics_json(self) -> str:
        print("[LOG] Збір метрик у форматі JSON...")
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
        }
        json_metrics = json.dumps(metrics, default=str, indent=2)
        print(f"[LOG] Метрики у форматі JSON: {json_metrics}")
        return json_metrics

    def generate_individual_figures(self, summary_text: str = None):
        """
        Генерує окремі фігури для кожного графіка та для summary-тексту.

        Створюються окремі зображення для:
          - Графіка рівня стресу
          - Графіка складності тренувань (з позначенням крепатури на тому ж значенні)
          - Графіка годин сну
          - Графіка самопочуття
          - Фігура з summary-текстом (без службової інформації)

        Повертає словник з ключами: "stress", "hardness", "sleep", "feelings", "summary".
        """
        print("[LOG] Генерація окремих фігур...")
        # Отримання даних
        stress_df = self.get_stress_data()
        sleep_df = self.get_sleeping_hours_data()
        hardness_df = self.get_training_hardness_data()
        feelings_df = self.get_feelings_data()
        soreness_df = self.get_soreness_data()

        # Отримання GPT-результату для summary
        metrics = self.get_metrics_json()
        gpt_request = f"{prompt}. {metrics}"
        gpt_result = llm.invoke(gpt_request)
        summary_text = (
            gpt_result.content
            if gpt_result.content is not None
            else "Цього періоду все працює відмінно! Продемонстровано позитивні тенденції."
        )
        print(f"[LOG] Summary: {summary_text}")

        # Фігура 1: Графік рівня стресу
        fig_stress = plt.figure(figsize=(8, 5))
        ax_stress = fig_stress.add_subplot(111)
        if not stress_df.empty:
            sns.lineplot(
                ax=ax_stress,
                x="dt",
                y="stress",
                data=stress_df,
                marker="o",
                color="#6699cc",
            )
        else:
            ax_stress.text(0.5, 0.5, "Немає даних", ha="center", va="center")
        ax_stress.set_title("Стрес", fontsize=14)
        ax_stress.set_xlabel("")
        ax_stress.set_ylabel("")
        fig_stress.tight_layout()

        # Фігура 2: Графік складності тренувань з крепатурою
        fig_hardness = plt.figure(figsize=(8, 5))
        ax_hardness = fig_hardness.add_subplot(111)
        if not hardness_df.empty:
            sns.lineplot(
                ax=ax_hardness,
                x="dt",
                y="hardness",
                data=hardness_df,
                marker="o",
                color="#ff9999",
            )
            # Додаємо маркери для крепатури (відображаємо фактичне значення складності)
            if not soreness_df.empty:
                ax_hardness.scatter(
                    soreness_df["dt"],
                    soreness_df["soreness"] * 0 + hardness_df["hardness"].max() * 0.9,
                    color="red",
                    marker="X",
                    s=100,
                )
        else:
            ax_hardness.text(0.5, 0.5, "Немає даних", ha="center", va="center")
        ax_hardness.set_title("Складність", fontsize=14)
        ax_hardness.set_xlabel("")
        ax_hardness.set_ylabel("")
        fig_hardness.tight_layout()

        # Фігура 3: Графік годин сну
        fig_sleep = plt.figure(figsize=(8, 5))
        ax_sleep = fig_sleep.add_subplot(111)
        if not sleep_df.empty:
            sns.lineplot(
                ax=ax_sleep,
                x="dt",
                y="hours",
                data=sleep_df,
                marker="o",
                color="#99cc99",
            )
        else:
            ax_sleep.text(0.5, 0.5, "Немає даних", ha="center", va="center")
        ax_sleep.set_title("Сон", fontsize=14)
        ax_sleep.set_xlabel("")
        ax_sleep.set_ylabel("")
        fig_sleep.tight_layout()

        # Фігура 4: Графік самопочуття
        fig_feelings = plt.figure(figsize=(8, 5))
        ax_feelings = fig_feelings.add_subplot(111)
        if not feelings_df.empty:
            sns.lineplot(
                ax=ax_feelings,
                x="dt",
                y="feelings",
                data=feelings_df,
                marker="o",
                color="#cc99ff",
            )
        else:
            ax_feelings.text(0.5, 0.5, "Немає даних", ha="center", va="center")
        ax_feelings.set_title("Самопочуття", fontsize=14)
        ax_feelings.set_xlabel("")
        ax_feelings.set_ylabel("")
        fig_feelings.tight_layout()

        # Фігура 5: Summary-текст (без додаткових підписів)
        fig_summary = plt.figure(figsize=(10, 3))
        ax_summary = fig_summary.add_subplot(111)
        ax_summary.axis("off")
        ax_summary.text(
            0.5, 0.5, summary_text, ha="center", va="center", wrap=True, fontsize=12
        )
        fig_summary.tight_layout()

        return {
            "stress": fig_stress,
            "hardness": fig_hardness,
            "sleep": fig_sleep,
            "feelings": fig_feelings,
            "summary": fig_summary,
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


# Приклад використання:
if __name__ == "__main__":
    session = next(get_db())
    user_id = 7

    print("[LOG] Генерація тижневої статистики...")
    weekly_stats = WeeklyStatisticsRecord(
        session, user_id, week_end=datetime.datetime(year=2025, month=2, day=16)
    )
    weekly_figs = weekly_stats.generate_individual_figures()
    print("[LOG] Метрики (JSON):")
    print(weekly_stats.get_metrics_json())

    print("[LOG] Генерація місячної статистики...")
    monthly_stats = MonthlyStatisticsRecord(
        session, user_id, month_end=datetime.datetime(year=2025, month=2, day=28)
    )
    monthly_figs = monthly_stats.generate_individual_figures()
    print("[LOG] Метрики (JSON):")
    print(monthly_stats.get_metrics_json())

    # Для перегляду окремих графіків, наприклад:
    weekly_figs["stress"].show()
    weekly_figs["hardness"].show()
    weekly_figs["sleep"].show()
    weekly_figs["feelings"].show()
    weekly_figs["summary"].show()

    monthly_figs["stress"].show()
    monthly_figs["hardness"].show()
    monthly_figs["sleep"].show()
    monthly_figs["feelings"].show()
    monthly_figs["summary"].show()

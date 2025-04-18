import os
import datetime
import json
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sqlalchemy import func, cast, Date
from sqlalchemy.orm import Session
from models import Training, MorningQuiz
from database import get_db
from openai import OpenAI
from dotenv import load_dotenv
from models import User

load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
ASSISTANT_ID = os.environ.get("OPENAI_ASSISTANT_ID")

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

    def analyze_metrics_with_assistant(
        self, metrics_json: str, user_full_name: str
    ) -> str:
        """
        Аналізує метрики за допомогою існуючого OpenAI Assistant та повертає текстовий аналіз.
        """
        print("[LOG] Аналіз метрик за допомогою OpenAI Assistant...")

        if not ASSISTANT_ID:
            error_msg = "Error: OPENAI_ASSISTANT_ID not found in environment variables"
            print(f"[LOG] Помилка: {error_msg}")
            return error_msg

        thread = client.beta.threads.create()

        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"Будь ласка, проаналізуй ці фітнес-метрики та надай висновки щодо тренувальних звичок користувача, якості сну, рівня стресу та загального прогресу. Ось метрики:\n\n user_full_name: {user_full_name}\n{metrics_json}",
        )

        run = client.beta.threads.runs.create(
            thread_id=thread.id, assistant_id=ASSISTANT_ID
        )

        # Wait for the analysis to complete
        while run.status in ["queued", "in_progress"]:
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

        if run.status == "completed":
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            analysis = messages.data[0].content[0].text.value
            print(f"[LOG] Отримано аналіз від асистента: {analysis}")
            return analysis
        else:
            error_msg = f"Error during analysis. Run status: {run.status}"
            print(f"[LOG] Помилка аналізу: {error_msg}")
            return error_msg

    def generate_individual_figures(self, file_prefix: str = "") -> dict:
        """
        Генерує єдину фігуру з усіма графіками.

        Створюється:
          - Єдина фігура з чотирма графіками (файл "{file_prefix}_stats.png")

        Повертає словник з ключем "stats", де значення — це шлях до збереженого файлу.
        """
        stats_file = f"{file_prefix}_stats.png"

        print("[LOG] Генерація фігури зі статистикою...")
        # Отримання даних
        stress_df = self.get_stress_data()
        sleep_df = self.get_sleeping_hours_data()
        hardness_df = self.get_training_hardness_data()
        feelings_df = self.get_feelings_data()
        soreness_df = self.get_soreness_data()

        # Створюємо фігуру з підграфіками
        fig = plt.figure(figsize=(16, 10))

        # Графік рівня стресу
        ax_stress = plt.subplot(2, 2, 1)
        if not stress_df.empty:
            # Format dates for x-axis
            stress_df["day_month"] = stress_df["dt"].dt.strftime("%d.%m")

            # Plot as line chart with updated x-axis
            sns.lineplot(
                ax=ax_stress,
                x="dt",
                y="stress",
                data=stress_df,
                marker="o",
                color="#6699cc",
            )

            # Format the x-ticks to day.month
            date_ticks = stress_df["dt"].tolist()
            ax_stress.set_xticks(date_ticks)
            ax_stress.set_xticklabels(stress_df["day_month"], rotation=45, ha="right")
        else:
            ax_stress.text(0.5, 0.5, "Немає даних", ha="center", va="center")
        ax_stress.set_title("Стрес", fontsize=14)
        ax_stress.set_xlabel("")
        ax_stress.set_ylabel("")

        # Графік складності тренування
        ax_hardness = plt.subplot(2, 2, 2)
        if not hardness_df.empty:
            # Format dates for x-axis
            hardness_df["day_month"] = hardness_df["dt"].dt.strftime("%d.%m")

            # Plot as line chart with updated x-axis
            sns.lineplot(
                ax=ax_hardness,
                x="dt",
                y="hardness",
                data=hardness_df,
                marker="o",
                color="#ff9999",
            )

            # Format the x-ticks to day.month
            date_ticks = hardness_df["dt"].tolist()
            ax_hardness.set_xticks(date_ticks)
            ax_hardness.set_xticklabels(
                hardness_df["day_month"], rotation=45, ha="right"
            )

            # Plot soreness markers
            if not soreness_df.empty:
                # Знаходимо значення складності для кожної дати з крепатурою
                soreness_hardness = []
                for soreness_date in soreness_df["dt"]:
                    hardness_value = hardness_df[hardness_df["dt"] == soreness_date][
                        "hardness"
                    ].values[0]
                    soreness_hardness.append(hardness_value)
                ax_hardness.scatter(
                    soreness_df["dt"], soreness_hardness, color="red", marker="X", s=100
                )
        else:
            ax_hardness.text(0.5, 0.5, "Немає даних", ha="center", va="center")
        ax_hardness.set_title("Складність", fontsize=14)
        ax_hardness.set_xlabel("")
        ax_hardness.set_ylabel("")

        # Графік годин сну
        ax_sleep = plt.subplot(2, 2, 3)
        if not sleep_df.empty:
            # Format the dates for display on x-axis
            sleep_df["day_month"] = sleep_df["dt"].dt.strftime("%d.%m")

            # Create a bar plot instead of a line plot
            ax_sleep.bar(
                range(len(sleep_df)),
                sleep_df["hours"],
                color="#99cc99",
                alpha=0.7,
                width=0.7,
            )

            # Add labels and customize appearance
            ax_sleep.set_xticks(range(len(sleep_df)))
            ax_sleep.set_xticklabels(sleep_df["day_month"], rotation=45, ha="right")

            # Add grid lines on y-axis only
            ax_sleep.grid(axis="y", linestyle="--", alpha=0.7)

            # Set y-axis limit based on data or fixed maximum
            max_sleep = max(sleep_df["hours"]) if not sleep_df.empty else 8
            ax_sleep.set_ylim(0, max(max_sleep * 1.1, 8))  # Add some padding
        else:
            ax_sleep.text(0.5, 0.5, "Немає даних", ha="center", va="center")
        ax_sleep.set_title("Сон", fontsize=14, fontweight="bold")
        ax_sleep.set_xlabel("")
        ax_sleep.set_ylabel("Hours", fontsize=12)

        # Графік самопочуття
        ax_feelings = plt.subplot(2, 2, 4)
        if not feelings_df.empty:
            # Format dates for x-axis
            feelings_df["day_month"] = feelings_df["dt"].dt.strftime("%d.%m")

            # Plot as line chart with updated x-axis
            sns.lineplot(
                ax=ax_feelings,
                x="dt",
                y="feelings",
                data=feelings_df,
                marker="o",
                color="#cc99ff",
            )

            # Format the x-ticks to day.month
            date_ticks = feelings_df["dt"].tolist()
            ax_feelings.set_xticks(date_ticks)
            ax_feelings.set_xticklabels(
                feelings_df["day_month"], rotation=45, ha="right"
            )
        else:
            ax_feelings.text(0.5, 0.5, "Немає даних", ha="center", va="center")
        ax_feelings.set_title("Самопочуття", fontsize=14)
        ax_feelings.set_xlabel("")
        ax_feelings.set_ylabel("")

        # Налаштування макету
        plt.tight_layout()

        # Зберігаємо фігуру
        fig.savefig(stats_file, dpi=150)
        plt.close(fig)

        return {"stats": stats_file}

    def generate_statistics(self, file_prefix: str = "") -> dict:
        """
        Генерує статистику та повертає шляхи до згенерованих файлів.
        """
        print("[LOG] Генерація статистики...")
        metrics_json = self.get_metrics_json()
        text_summary = self.analyze_metrics_with_assistant(metrics_json, user_full_name)
        return text_summary, self.generate_individual_figures(file_prefix)


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


# Приклад використання:
if __name__ == "__main__":
    session = next(get_db())
    user_id = 7

    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"Користувач з id={user_id} не знайдений")

    user_full_name = user.full_name

    # Тижнева статистика
    week_end = datetime.datetime(2025, 2, 16)
    weekly_stats = WeeklyStatisticsRecord(session, user_id, week_end, user_full_name)
    text_summary, weekly_files = weekly_stats.generate_statistics("weekly")
    print("Weekly statistics files:", weekly_files)
    print("Weekly statistics summary:", text_summary)

    # Місячна статистика
    month_end = datetime.datetime(2025, 2, 28)
    monthly_stats = MonthlyStatisticsRecord(session, user_id, month_end, user_full_name)
    text_summary, monthly_files = monthly_stats.generate_statistics("monthly")
    print("Monthly statistics files:", monthly_files)
    print("Monthly statistics summary:", text_summary)

import os
import datetime
import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from sqlalchemy import func, cast, Date
from sqlalchemy.orm import Session
from models import Training, MorningQuiz
from database import get_db
from openai import OpenAI
from dotenv import load_dotenv
from models import User
from matplotlib.ticker import MaxNLocator

load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
ASSISTANT_ID = os.environ.get("OPENAI_ASSISTANT_ID")

# Встановлюємо стиль для графіків
plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']


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
        
    def get_weight_data(self) -> pd.DataFrame:
        print("[LOG] Отримання даних по вазі...")
        data = (
            self.session.query(MorningQuiz.quiz_datetime, MorningQuiz.user_weight)
            .filter(
                MorningQuiz.user_id == self.user_id,
                MorningQuiz.quiz_datetime >= self.start_date,
                MorningQuiz.quiz_datetime < self.end_date,
                MorningQuiz.user_weight.isnot(None),
            )
            .all()
        )
        df = pd.DataFrame(data, columns=["dt", "weight"])
        print(f"[LOG] Дані по вазі: {df}")
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

    def create_rounded_card(self, ax, title, color):
        """Створює заокруглену картку для графіка з заголовком"""
        # Налаштування фону та рамки
        ax.set_facecolor('white')
        for spine in ax.spines.values():
            spine.set_visible(False)
        
        # Додаємо заголовок у кольоровому прямокутнику
        title_box = patches.FancyBboxPatch(
            xy=(0.5, 0.95),
            width=0.4,
            height=0.1, 
            transform=ax.transAxes,
            boxstyle=patches.BoxStyle("Round", pad=0.02, rounding_size=0.1),
            facecolor=color,
            edgecolor='none',
            alpha=1.0,
            clip_on=False,
            zorder=10
        )
        # Центруємо заголовок
        title_box.set_x(0.3)
        ax.add_patch(title_box)
        
        # Додаємо текст заголовка
        ax.text(
            0.5, 0.95, 
            title, 
            transform=ax.transAxes,
            fontsize=14,
            fontweight='bold',
            color='white',
            ha='center',
            va='center',
            zorder=11
        )
        
        # Налаштування сітки
        ax.grid(True, linestyle='--', alpha=0.2, color='lightgray')
        
        # Налаштування осей
        ax.tick_params(axis='both', which='both', labelsize=8)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=8))
        
        return ax

    def generate_individual_figures(self, file_prefix: str = "") -> dict:
        """
        Генерує єдину фігуру з усіма графіками в стилі зображення.

        Створюється:
          - Єдина фігура з графіками (файл "{file_prefix}_stats.png")

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
        weight_df = self.get_weight_data()

        # Кольори для графіків
        stress_color = '#FFD700'  # Жовтий для стресу
        hardness_color = '#FF0000'  # Червоний для складності
        sleep_color = '#9370DB'  # Фіолетовий для сну
        feelings_color = '#00FF00'  # Зелений для самопочуття
        weight_color = '#00BFFF'  # Блакитний для ваги

        # Створюємо фігуру з підграфіками на світло-блакитному фоні
        fig = plt.figure(figsize=(16, 12), facecolor='#E6E6FA')
        
        # Налаштування макету з відступами
        grid = plt.GridSpec(3, 2, figure=fig, hspace=0.3, wspace=0.3, 
                           left=0.05, right=0.95, bottom=0.05, top=0.95)

        # Графік рівня стресу
        ax_stress = fig.add_subplot(grid[0, 0])
        ax_stress = self.create_rounded_card(ax_stress, "СТРЕС", stress_color)
        
        if not stress_df.empty:
            # Format dates for x-axis
            stress_df["day_month"] = stress_df["dt"].dt.strftime("%d.%m")

            # Plot as line chart with updated x-axis
            ax_stress.plot(
                range(len(stress_df)),
                stress_df["stress"],
                marker="o",
                color=stress_color,
                linewidth=3,
                markersize=10,
                markeredgecolor='white',
                markeredgewidth=1.5
            )

            # Format the x-ticks to day.month
            ax_stress.set_xticks(range(len(stress_df)))
            ax_stress.set_xticklabels(stress_df["day_month"], rotation=45, ha="right")
            
            # Заповнення області під лінією
            ax_stress.fill_between(
                range(len(stress_df)), 
                0, 
                stress_df["stress"], 
                color=stress_color, 
                alpha=0.15
            )
        else:
            ax_stress.text(0.5, 0.5, "Немає даних", ha="center", va="center")

        # Графік складності тренування
        ax_hardness = fig.add_subplot(grid[0, 1])
        ax_hardness = self.create_rounded_card(ax_hardness, "СКЛАДНІСТЬ", hardness_color)
        
        if not hardness_df.empty:
            # Format dates for x-axis
            hardness_df["day_month"] = hardness_df["dt"].dt.strftime("%d.%m")

            # Plot as line chart with updated x-axis
            ax_hardness.plot(
                range(len(hardness_df)),
                hardness_df["hardness"],
                marker="o",
                color=hardness_color,
                linewidth=3,
                markersize=10,
                markeredgecolor='white',
                markeredgewidth=1.5
            )

            # Format the x-ticks to day.month
            ax_hardness.set_xticks(range(len(hardness_df)))
            ax_hardness.set_xticklabels(
                hardness_df["day_month"], rotation=45, ha="right"
            )
            
            # Заповнення області під лінією
            ax_hardness.fill_between(
                range(len(hardness_df)), 
                0, 
                hardness_df["hardness"], 
                color=hardness_color, 
                alpha=0.15
            )

            # Plot soreness markers
            if not soreness_df.empty:
                # Знаходимо значення складності для кожної дати з крепатурою
                for soreness_date in soreness_df["dt"]:
                    if soreness_date in hardness_df["dt"].values:
                        idx = hardness_df[hardness_df["dt"] == soreness_date].index[0]
                        hardness_value = hardness_df.loc[idx, "hardness"]
                        ax_hardness.scatter(
                            idx, hardness_value, color=hardness_color, marker="X", s=120, zorder=10
                        )
        else:
            ax_hardness.text(0.5, 0.5, "Немає даних", ha="center", va="center")

        # Графік годин сну (гістограма)
        ax_sleep = fig.add_subplot(grid[1, 0])
        ax_sleep = self.create_rounded_card(ax_sleep, "СОН", sleep_color)
        
        if not sleep_df.empty:
            # Format the dates for display on x-axis
            sleep_df["day_month"] = sleep_df["dt"].dt.strftime("%d.%m")

            # Create a bar plot with purple bars
            bars = ax_sleep.bar(
                range(len(sleep_df)),
                sleep_df["hours"],
                color=sleep_color,
                alpha=0.8,
                width=0.7,
                edgecolor='none'
            )
            
            # Додаємо значення над стовпцями
            for bar in bars:
                height = bar.get_height()
                ax_sleep.text(
                    bar.get_x() + bar.get_width()/2.,
                    height + 0.1,
                    f'{int(height)}',
                    ha='center',
                    va='bottom',
                    fontsize=9,
                    color='black',
                    fontweight='bold'
                )

            # Add labels and customize appearance
            ax_sleep.set_xticks(range(len(sleep_df)))
            ax_sleep.set_xticklabels(sleep_df["day_month"], rotation=45, ha="right")

            # Set y-axis limit based on data or fixed maximum
            max_sleep = max(sleep_df["hours"]) if not sleep_df.empty else 8
            ax_sleep.set_ylim(0, max(max_sleep * 1.1, 8))  # Add some padding
        else:
            ax_sleep.text(0.5, 0.5, "Немає даних", ha="center", va="center")

        # Графік самопочуття
        ax_feelings = fig.add_subplot(grid[1, 1])
        ax_feelings = self.create_rounded_card(ax_feelings, "САМОПОЧУТТЯ", feelings_color)
        
        if not feelings_df.empty:
            # Format dates for x-axis
            feelings_df["day_month"] = feelings_df["dt"].dt.strftime("%d.%m")

            # Plot as line chart with updated x-axis
            ax_feelings.plot(
                range(len(feelings_df)),
                feelings_df["feelings"],
                marker="o",
                color=feelings_color,
                linewidth=3,
                markersize=10,
                markeredgecolor='white',
                markeredgewidth=1.5
            )

            # Format the x-ticks to day.month
            ax_feelings.set_xticks(range(len(feelings_df)))
            ax_feelings.set_xticklabels(
                feelings_df["day_month"], rotation=45, ha="right"
            )
            
            # Заповнення області під лінією
            ax_feelings.fill_between(
                range(len(feelings_df)), 
                0, 
                feelings_df["feelings"], 
                color=feelings_color, 
                alpha=0.15
            )
        else:
            ax_feelings.text(0.5, 0.5, "Немає даних", ha="center", va="center")

        # Графік ваги
        ax_weight = fig.add_subplot(grid[2, :])
        ax_weight = self.create_rounded_card(ax_weight, "ВАГА", weight_color)
        
        if not weight_df.empty:
            # Format dates for x-axis
            weight_df["day_month"] = weight_df["dt"].dt.strftime("%d.%m")

            # Plot as smooth line chart
            x = np.array(range(len(weight_df)))
            y = weight_df["weight"].values
            
            # Smooth line with gradient
            ax_weight.plot(
                x, y, 
                linewidth=5, 
                color=weight_color,
                alpha=0.9
            )
            
            # Gradient fill under the curve
            ax_weight.fill_between(
                x, 0, y, 
                color=weight_color, 
                alpha=0.2
            )

            # Format the x-ticks to day.month
            ax_weight.set_xticks(range(len(weight_df)))
            ax_weight.set_xticklabels(
                weight_df["day_month"], rotation=45, ha="right"
            )
        else:
            ax_weight.text(0.5, 0.5, "Немає даних", ha="center", va="center")

        # Зберігаємо фігуру
        fig.savefig(stats_file, dpi=150, bbox_inches='tight')
        plt.close(fig)

        return {"stats": stats_file}

    def generate_statistics(self, file_prefix: str = "") -> dict:
        """
        Генерує статистику та повертає шляхи до згенерованих файлів.
        """
        print("[LOG] Генерація статистики...")
        metrics_json = self.get_metrics_json()
        text_summary = self.analyze_metrics_with_assistant(metrics_json, self.user_full_name)
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

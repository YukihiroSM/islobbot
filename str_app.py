import streamlit as st
import datetime
from database import get_db
from models import Training, MorningQuiz
from statistics_builder import WeeklyStatisticsRecord, MonthlyStatisticsRecord

# Отримуємо сесію через get_db()
session = next(get_db())

# Приклад вибору user_id та періоду
user_id = 7
# Для тижневої статистики: встановимо дату завершення періоду
week_end = datetime.datetime(year=2025, month=2, day=16)
weekly_stats = WeeklyStatisticsRecord(session, user_id, week_end=week_end)

# Для місячної статистики:
month_end = datetime.datetime(year=2025, month=2, day=28)
monthly_stats = MonthlyStatisticsRecord(session, user_id, month_end=month_end)

# Вибираємо, яку статистику показувати (наприклад, за тиждень чи місяць)
stats_option = st.sidebar.selectbox(
    "Виберіть період статистики", ("Тижнева", "Місячна")
)

if stats_option == "Тижнева":
    fig = weekly_stats.generate_statistics_figure()[0]
    metrics_json = weekly_stats.get_metrics_json()
else:
    fig = monthly_stats.generate_statistics_figure()[0]
    metrics_json = monthly_stats.get_metrics_json()

st.title("Статистика користувача")
st.plotly_chart(fig, use_container_width=True)

st.header("Summary")
# Відображаємо summary-текст, який повернувся як HTML (якщо потрібно, можна увімкнути unsafe_allow_html)
# Припустимо, що ваш метод generate_statistics_figure повертає tuple (fig, summary_html)
_, summary_html = (
    weekly_stats.generate_statistics_figure()
    if stats_option == "Тижнева"
    else monthly_stats.generate_statistics_figure()
)
st.markdown(summary_html, unsafe_allow_html=True)

st.header("Метрики (JSON)")
st.json(metrics_json)

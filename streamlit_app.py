import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
from sqlalchemy.engine import URL


st.set_page_config(
    page_title="Ireland Agriculture Dashboard",
    page_icon="🌾",
    layout="wide"
)


MYSQL_HOST = "localhost"
MYSQL_PORT = 3306
MYSQL_USER = "root"
MYSQL_PASSWORD = ""
MYSQL_DATABASE = "ireland_agriculture_db"


database_url = URL.create(
    drivername="mysql+pymysql",
    username=MYSQL_USER,
    password=MYSQL_PASSWORD,
    host=MYSQL_HOST,
    port=MYSQL_PORT,
    database=MYSQL_DATABASE
)

engine = create_engine(database_url)


st.markdown(
    """
    <style>
    .main-title {
        font-size: 34px;
        font-weight: 700;
        color: #1f4e3d;
        margin-bottom: 0px;
    }

    .subtitle {
        font-size: 17px;
        color: #555555;
        margin-top: 0px;
        margin-bottom: 25px;
    }

    .section-box {
        background-color: #f7faf6;
        padding: 18px;
        border-radius: 12px;
        border: 1px solid #dbe8d6;
        margin-bottom: 15px;
    }
    </style>
    """,
    unsafe_allow_html=True
)


st.markdown(
    '<p class="main-title">Ireland Agriculture Data Analytics Dashboard</p>',
    unsafe_allow_html=True
)

st.markdown(
    '<p class="subtitle">A simple Streamlit dashboard using the agricultural data saved in the MySQL database.</p>',
    unsafe_allow_html=True
)


try:
    tables_df = pd.read_sql_query("SHOW TABLES", engine)
    available_tables = tables_df.iloc[:, 0].tolist()
except Exception as error:
    st.error(
        "The dashboard could not connect to MySQL. "
        "Make sure MySQL is running and the notebook database cells were executed."
    )
    st.exception(error)
    st.stop()


if "dafm_exports_tidy" in available_tables:
    dafm = pd.read_sql_query("SELECT * FROM dafm_exports_tidy", engine)
else:
    dafm = pd.DataFrame()


if "sentiment_news" in available_tables:
    sentiment = pd.read_sql_query("SELECT * FROM sentiment_news", engine)
else:
    sentiment = pd.DataFrame()


if dafm.empty:
    st.warning(
        "The table 'dafm_exports_tidy' was not found in MySQL. "
        "Run the notebook cells that save the DAFM export data to MySQL."
    )
    st.stop()


dafm.columns = [str(col).strip().lower() for col in dafm.columns]

if not sentiment.empty:
    sentiment.columns = [str(col).strip().lower() for col in sentiment.columns]


year_column = None
value_column = None
category_column = None

for col in dafm.columns:
    if "year" in col:
        year_column = col
        break

for col in dafm.columns:
    if col in ["value", "export_value", "amount", "exports"]:
        value_column = col
        break

if value_column is None:
    numeric_columns = dafm.select_dtypes(include="number").columns.tolist()
    numeric_columns = [col for col in numeric_columns if col != year_column]

    if len(numeric_columns) > 0:
        value_column = numeric_columns[0]

for col in dafm.columns:
    if col not in [year_column, value_column]:
        if dafm[col].dtype == "object":
            category_column = col
            break


if year_column is not None:
    dafm[year_column] = pd.to_numeric(dafm[year_column], errors="coerce")

if value_column is not None:
    dafm[value_column] = pd.to_numeric(dafm[value_column], errors="coerce")


latest_year = dafm[year_column].max() if year_column is not None else None
total_records = len(dafm)

if year_column is not None and value_column is not None:
    total_value = dafm[value_column].sum()
else:
    total_value = None


metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

with metric_col1:
    st.metric("Dataset Records", f"{total_records:,}")

with metric_col2:
    if latest_year is not None and pd.notna(latest_year):
        st.metric("Latest Year", int(latest_year))
    else:
        st.metric("Latest Year", "N/A")

with metric_col3:
    if total_value is not None and pd.notna(total_value):
        st.metric("Total Export Value", f"{total_value:,.2f}")
    else:
        st.metric("Total Export Value", "N/A")

with metric_col4:
    st.metric("MySQL Database", MYSQL_DATABASE)


st.divider()


left_col, right_col = st.columns(2)

with left_col:
    st.subheader("Irish Agri-Food Export Trend")

    if year_column is not None and value_column is not None:
        yearly_exports = dafm.groupby(year_column, as_index=False)[value_column].sum()
        yearly_exports = yearly_exports.sort_values(year_column)

        fig_trend = px.line(
            yearly_exports,
            x=year_column,
            y=value_column,
            markers=True,
            title="Total Export Value by Year"
        )

        fig_trend.update_layout(
            height=430,
            xaxis_title="Year",
            yaxis_title="Export Value",
            margin=dict(l=20, r=20, t=50, b=20)
        )

        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Year and value columns were not found clearly in the export data.")


with right_col:
    st.subheader("Export Category Breakdown")

    if category_column is not None and value_column is not None:
        category_summary = dafm.groupby(category_column, as_index=False)[value_column].sum()
        category_summary = category_summary.sort_values(value_column, ascending=False).head(10)

        fig_category = px.bar(
            category_summary,
            x=value_column,
            y=category_column,
            orientation="h",
            title="Top Export Categories"
        )

        fig_category.update_layout(
            height=430,
            xaxis_title="Export Value",
            yaxis_title="Category",
            margin=dict(l=20, r=20, t=50, b=20)
        )

        st.plotly_chart(fig_category, use_container_width=True)
    else:
        st.info("A suitable category column was not found in the export data.")


st.divider()


sentiment_col, data_col = st.columns(2)

with sentiment_col:
    st.subheader("Agriculture News Sentiment")

    if not sentiment.empty and "sentiment_label" in sentiment.columns:
        sentiment_summary = sentiment["sentiment_label"].value_counts().reset_index()
        sentiment_summary.columns = ["sentiment_label", "count"]

        fig_sentiment = px.pie(
            sentiment_summary,
            names="sentiment_label",
            values="count",
            hole=0.45,
            title="Sentiment Distribution"
        )

        fig_sentiment.update_layout(
            height=420,
            margin=dict(l=20, r=20, t=50, b=20)
        )

        st.plotly_chart(fig_sentiment, use_container_width=True)

    elif not sentiment.empty and "compound" in sentiment.columns:
        sentiment["compound"] = pd.to_numeric(sentiment["compound"], errors="coerce")

        fig_sentiment_hist = px.histogram(
            sentiment,
            x="compound",
            nbins=15,
            title="Sentiment Score Distribution"
        )

        fig_sentiment_hist.update_layout(
            height=420,
            xaxis_title="Compound Sentiment Score",
            yaxis_title="Count",
            margin=dict(l=20, r=20, t=50, b=20)
        )

        st.plotly_chart(fig_sentiment_hist, use_container_width=True)

    else:
        st.info("Sentiment data is not available in the expected format.")


with data_col:
    st.subheader("Export Data Preview")

    st.dataframe(
        dafm.head(20),
        use_container_width=True,
        hide_index=True
    )


st.divider()


st.subheader("Interpretation")

st.write(
    "The dashboard focuses on Irish agri-food export evidence stored in MySQL. "
    "The trend chart shows how export value changes over time, while the category chart highlights the strongest export areas. "
    "The sentiment section adds supporting evidence from agriculture-related news where sentiment data is available."
)

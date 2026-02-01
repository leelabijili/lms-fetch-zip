import streamlit as st
from datetime import date

st.title("Give me a date and I will give the day of the week")

date_picked = st.date_input("Pick a date", value=None)

if date_picked:
    st.subheader(f"{date_picked.strftime('%B %d')} for the next 10 years")

    results = []
    for year in range(date_picked.year, date_picked.year + 10):
        try:
            d = date(year, date_picked.month, date_picked.day)
            day_name = d.strftime("%A")
            results.append({"Year": year, "Date": d, "Day": day_name})
        except ValueError:
            # Feb 29 doesn't exist in non-leap years
            results.append({"Year": year, "Date": f"{year}-{date_picked.month:02d}-{date_picked.day:02d}", "Day": "N/A (invalid date)"})

    st.table([{"Year": r["Year"], "Day of week": r["Day"]} for r in results])

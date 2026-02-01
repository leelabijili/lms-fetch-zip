import streamlit as st

st.title("Product Calculator")

num1 = st.number_input("First number", value=0.0, step=0.1)
num2 = st.number_input("Second number", value=0.0, step=0.1)

product = num1 * num2
st.write(f"The product of **{num1}** and {num2} is **{product}**")
# Simple Streamlit Product Calculator

## Overview

Add a two-file setup: a Streamlit app and a requirements file. The app will use `st.number_input` for the inputs and display the product below.

## Files to Create

### 1. [requirements.txt](requirements.txt)

```
streamlit>=1.28.0
```

### 2. [app.py](app.py)

```python
import streamlit as st

st.title("Product Calculator")

num1 = st.number_input("First number", value=0.0, step=0.1)
num2 = st.number_input("Second number", value=0.0, step=0.1)

product = num1 * num2
st.write(f"The product of {num1} and {num2} is **{product}**")
```

## How to Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

This opens the app in the browser at `http://localhost:8501`. The product updates automatically as the user changes the numbers.

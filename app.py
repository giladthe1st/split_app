import streamlit as st
import pandas as pd
from db import init_db, add_participant, remove_participant, get_participants, \
    add_transaction, update_transaction, delete_transaction, get_transactions
from logic import calculate_balances, min_transfers
import datetime
import json

st.set_page_config(page_title="Split App", layout="wide")
init_db()

st.title("Split App: Bill Splitting Made Easy")

# Sidebar: Participants
st.sidebar.header("Participants")
participants = get_participants()
participant_dict = {pid: name for pid, name in participants}

with st.sidebar.form("add_participant_form"):
    new_name = st.text_input("Add participant by name")
    if st.form_submit_button("Add") and new_name.strip():
        try:
            add_participant(new_name.strip())
            st.experimental_rerun()
        except Exception as e:
            st.warning(f"Could not add: {e}")

if participants:
    st.sidebar.write("### Current Participants:")
    for pid, name in participants:
        col1, col2 = st.sidebar.columns([3,1])
        col1.write(name)
        if col2.button("Remove", key=f"remove_{pid}"):
            remove_participant(pid)
            st.experimental_rerun()

# Main: Transactions
st.header("Transactions")
transactions = get_transactions()

# Transaction Form
with st.expander("Add/Edit Transaction", expanded=True):
    edit_mode = st.selectbox("Mode", ["Add New", "Edit Existing"])
    if edit_mode == "Add New":
        desc = st.text_input("Description")
        amt = st.number_input("Amount", min_value=0.01, step=0.01)
        payer = st.selectbox("Payer", options=participant_dict.keys(), format_func=lambda x: participant_dict[x])
        involved = st.multiselect("Participants Involved", options=participant_dict.keys(), default=list(participant_dict.keys()), format_func=lambda x: participant_dict[x])
        if st.button("Add Transaction") and desc and amt > 0 and payer in involved and involved:
            add_transaction(desc, amt, payer, involved, datetime.datetime.now().isoformat())
            st.success("Transaction added!")
            st.experimental_rerun()
    else:
        txn_options = {tid: f"{desc} (${amt:.2f})" for tid, desc, amt, payer, involved, ts in transactions}
        selected_tid = st.selectbox("Select Transaction to Edit", options=list(txn_options.keys()), format_func=lambda x: txn_options[x] if x in txn_options else str(x))
        if selected_tid:
            txn = next((t for t in transactions if t[0] == selected_tid), None)
            if txn:
                _, desc, amt, payer, involved_json, ts = txn
                desc = st.text_input("Description", value=desc)
                amt = st.number_input("Amount", min_value=0.01, step=0.01, value=float(amt))
                payer = st.selectbox("Payer", options=participant_dict.keys(), index=list(participant_dict.keys()).index(payer), format_func=lambda x: participant_dict[x])
                involved = st.multiselect("Participants Involved", options=participant_dict.keys(), default=json.loads(involved_json), format_func=lambda x: participant_dict[x])
                if st.button("Update Transaction") and desc and amt > 0 and payer in involved and involved:
                    update_transaction(selected_tid, desc, amt, payer, involved, datetime.datetime.now().isoformat())
                    st.success("Transaction updated!")
                    st.experimental_rerun()
                if st.button("Delete Transaction"):
                    delete_transaction(selected_tid)
                    st.success("Transaction deleted!")
                    st.experimental_rerun()

# Transactions Table
if transactions:
    st.subheader("All Transactions")
    df = pd.DataFrame([
        {
            "Description": desc,
            "Amount": amt,
            "Payer": participant_dict.get(payer, str(payer)),
            "Involved": ", ".join([participant_dict.get(pid, str(pid)) for pid in json.loads(involved)]),
            "Timestamp": ts
        }
        for tid, desc, amt, payer, involved, ts in transactions
    ])
    st.dataframe(df, use_container_width=True)
else:
    st.info("No transactions yet. Add one above!")

# Summary
st.header("Summary & Balances")
balances = calculate_balances(participants, transactions)
if balances:
    bal_df = pd.DataFrame([
        {"Participant": participant_dict.get(pid, str(pid)), "Balance": round(amt, 2)}
        for pid, amt in balances.items()
    ])
    st.dataframe(bal_df, use_container_width=True)

    st.subheader("Settle Up")
    transfers = min_transfers(balances)
    if transfers:
        for from_id, to_id, amt in transfers:
            st.write(f"{participant_dict.get(from_id, str(from_id))} → {participant_dict.get(to_id, str(to_id))}: ${amt:.2f}")
    else:
        st.success("All settled!")
else:
    st.info("Add participants and transactions to see balances.")

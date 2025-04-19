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
                involved_default = json.loads(involved_json)
                # Filter involved_default to only valid participants
                valid_involved_default = [pid for pid in involved_default if pid in participant_dict]
                if len(valid_involved_default) < len(involved_default):
                    st.warning("Some participants in this transaction were removed from the group. They have been excluded from the edit form.")
                involved = st.multiselect("Participants Involved", options=participant_dict.keys(), default=valid_involved_default, format_func=lambda x: participant_dict[x])
                # If payer is not in the new involved list, auto-select a new payer and warn
                if payer not in involved and involved:
                    payer = involved[0]
                    st.warning("Payer was not in the new involved list. Automatically switched payer to a valid participant.")
                payer = st.selectbox("Payer", options=involved if involved else participant_dict.keys(), index=(involved.index(payer) if payer in involved else 0), format_func=lambda x: participant_dict[x])
                update_clicked = st.button("Update Transaction")
                if update_clicked:
                    if not involved:
                        st.error("You must select at least one participant involved in the transaction.")
                    elif payer not in involved:
                        st.error("Payer must be one of the involved participants.")
                    elif not desc or amt <= 0:
                        st.error("Please provide a valid description and amount.")
                    else:
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
    # --- WhatsApp-friendly summary ---
    expense_lines = ["*Expenses:*"]
    for tid, desc, amt, payer, involved_json, ts in transactions[::-1]:
        involved_names = ", ".join([participant_dict.get(pid, str(pid)) for pid in json.loads(involved_json) if pid in participant_dict])
        payer_name = participant_dict.get(payer, str(payer))
        expense_lines.append(f"- {desc}: ${amt:.2f}\n  Paid by: {payer_name}\n  Split among: {involved_names}")
    if len(expense_lines) == 1:
        expense_lines.append("No expenses recorded.")

    balance_lines = ["*Balances:*"]
    for pid, amt in balances.items():
        balance_lines.append(f"{participant_dict.get(pid, str(pid))}: {'+' if amt >= 0 else ''}${amt:.2f}")

    settle_lines = ["*Settle Up:*"]
    if transfers:
        for from_id, to_id, amt in transfers:
            settle_lines.append(f"{participant_dict.get(from_id, str(from_id))} ➔ {participant_dict.get(to_id, str(to_id))}: ${amt:.2f}")
    else:
        settle_lines.append("All settled!")

    wa_summary = "\n\n".join([
        "\n".join(expense_lines),
        "\n".join(balance_lines),
        "\n".join(settle_lines)
    ])
    st.code(wa_summary, language="")
    st.caption("Click the 'Copy' button above to copy the summary, then paste into WhatsApp or any chat.")
    # ---
    if transfers:
        for from_id, to_id, amt in transfers:
            st.write(f"{participant_dict.get(from_id, str(from_id))} → {participant_dict.get(to_id, str(to_id))}: ${amt:.2f}")
    else:
        st.success("All settled!")
else:
    st.info("Add participants and transactions to see balances.")

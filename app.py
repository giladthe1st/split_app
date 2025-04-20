import streamlit as st
import pandas as pd
from db import init_db, add_participant, remove_participant, get_participants, \
    add_transaction, update_transaction, delete_transaction, get_transactions, \
    create_split, get_splits, get_split
from logic import calculate_balances, min_transfers
import datetime
import json

st.set_page_config(page_title="Split App", layout="wide")
init_db()

st.title("Split App: Split Bills in Seconds")

# --- Sidebar: Splits/Hangouts ---
splits = get_splits()
split_names = {sid: name for sid, name, _, _, _ in splits}
if "selected_split" not in st.session_state:
    st.session_state.selected_split = splits[0][0] if splits else None

st.sidebar.header("💬 Hangouts / Splits")
if splits:
    selected = st.sidebar.selectbox(
        "Select a hangout/split:",
        options=[s[0] for s in splits],
        format_func=lambda sid: split_names[sid],
        index=[s[0] for s in splits].index(st.session_state.selected_split) if st.session_state.selected_split in split_names else 0
    )
    st.session_state.selected_split = selected
else:
    st.sidebar.info("No hangouts yet. Create one below!")

with st.sidebar.expander("➕ Create New Hangout/Split", expanded=True):
    new_split_name = st.text_input("Hangout/Split Name", key="new_split_name")
    new_split_desc = st.text_area("Description (optional)", key="new_split_desc")
    new_split_date = st.date_input("Date of Hangout", value=datetime.date.today(), key="new_split_date")
    if st.button("Create Hangout/Split"):
        if not new_split_name.strip():
            st.warning("Please enter a name for the hangout/split.")
        else:
            split_id = create_split(new_split_name.strip(), new_split_desc.strip(), str(new_split_date), datetime.datetime.now().isoformat())
            st.session_state.selected_split = split_id
            st.success(f"Created '{new_split_name.strip()}'!")
            st.rerun()

if not st.session_state.selected_split:
    st.warning("Please create or select a hangout/split to continue.")
    st.stop()

# Sidebar: Participants
st.sidebar.header("Who's joining the split?")
participants = get_participants(st.session_state.selected_split)
participant_dict = {pid: name for pid, name in participants}

with st.sidebar.form("add_participant_form"):
    new_name = st.text_input("Enter a name (e.g., Sam)")
    if st.form_submit_button("Add"):
        if not new_name.strip():
            st.warning("Please enter a name.")
        else:
            try:
                add_participant(new_name.strip(), st.session_state.selected_split)
                st.success(f"Added {new_name.strip()}!")
                st.rerun()
            except Exception as e:
                st.warning(f"Could not add: {e}")

if participants:
    st.sidebar.write("### Current Participants:")
    for pid, name in participants:
        col1, col2 = st.sidebar.columns([3,1])
        col1.write(f"👤 {name}")
        if col2.button("Remove", key=f"remove_{pid}"):
            remove_participant(pid, st.session_state.selected_split)
            st.rerun()

# Main: Add a Bill
st.header("Add a Bill or Expense")
transactions = get_transactions(st.session_state.selected_split)

with st.expander("Add or Edit a Bill", expanded=True):
    if "edit_mode" not in st.session_state:
        st.session_state.edit_mode = "Add New"

    col1, col2 = st.columns([0.1, 1])

    add_clicked = col1.button(
        "Add New",
        key="add_new_btn",
        type="primary" if st.session_state.edit_mode == "Add New" else "secondary"
    )
    edit_clicked = col2.button(
        "Edit Existing",
        key="edit_existing_btn",
        type="primary" if st.session_state.edit_mode == "Edit Existing" else "secondary"
    )

    if add_clicked:
        st.session_state.edit_mode = "Add New"
        st.rerun()
    elif edit_clicked:
        st.session_state.edit_mode = "Edit Existing"
        st.rerun()

    edit_mode = st.session_state.edit_mode
    if edit_mode == "Add New":
        desc = st.text_input("What was the bill for? (e.g., Pizza)")
        amt = st.number_input("How much was it?", min_value=0.01, step=0.01)
        payer = st.selectbox("Who paid?", options=participant_dict.keys(), format_func=lambda x: participant_dict[x])
        involved = st.multiselect("Who shared this?", options=participant_dict.keys(), default=list(participant_dict.keys()), format_func=lambda x: participant_dict[x])
        if st.button("Split this bill"):
            if not desc:
                st.error("Please describe the bill (e.g., 'Groceries').")
            elif amt <= 0:
                st.error("Amount must be greater than zero.")
            elif not involved:
                st.error("Please select at least one participant.")
            elif payer not in involved:
                st.error("The payer must be one of the participants involved.")
            else:
                add_transaction(st.session_state.selected_split, desc, amt, payer, involved, datetime.datetime.now().isoformat())
                st.success("Bill added and split!")
                st.rerun()
    else:
        if not transactions:
            st.info("No bills to edit yet. Add one first!")
        else:
            txn_options = {tid: f"{desc} (${amt:.2f})" for tid, _, desc, amt, payer, involved, _, ts in transactions}
            selected_tid = st.selectbox("Which bill do you want to edit?", options=list(txn_options.keys()), format_func=lambda x: txn_options[x] if x in txn_options else str(x))
            if selected_tid:
                txn = next((t for t in transactions if t[0] == selected_tid), None)
                if txn:
                    _, _, desc, amt, payer, involved_json, _, ts = txn
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
                        update_transaction(selected_tid, st.session_state.selected_split, desc, amt, payer, involved, datetime.datetime.now().isoformat())
                        st.success("Transaction updated!")
                        st.rerun()
                if st.button("Delete Transaction"):
                    delete_transaction(selected_tid)
                    st.success("Transaction deleted!")
                    st.rerun()

# Transactions Table
if transactions:
    st.subheader("All Bills & Expenses")
    for tid, _, desc, amt, payer, involved_json, settled_json, ts in transactions:
        involved_ids = json.loads(involved_json)
        # --- Parse settled_json as dict {debtor_id: bool}, or convert from list for backward compatibility
        try:
            settled_map = json.loads(settled_json)
            if isinstance(settled_map, list):
                # Old format: list of settled ids
                settled_map = {str(pid): True for pid in settled_map}
        except Exception:
            settled_map = {}
        updated = False
        with st.expander(f"{desc} (${amt:.2f}) - {ts.split('T')[0] if 'T' in ts else ts}"):
            st.write(f"**Payer:** {participant_dict.get(payer, str(payer))}")
            st.write(f"**Shared By:** {', '.join([participant_dict.get(pid, str(pid)) for pid in involved_ids])}")
            st.write("**Settled:**")
            new_settled_map = settled_map.copy()
            for pid in involved_ids:
                if pid == payer:
                    continue  # Payer doesn't owe themselves
                checked = bool(settled_map.get(str(pid), False))
                new_checked = st.checkbox(f"{participant_dict.get(pid, str(pid))} paid {participant_dict.get(payer, str(payer))}", value=checked, key=f"settled_{tid}_{pid}")
                if new_checked != checked:
                    new_settled_map[str(pid)] = new_checked
                    updated = True
            if updated:
                update_transaction(tid, st.session_state.selected_split, desc, amt, payer, involved_ids, ts, json.dumps(new_settled_map))
                st.success("Updated settlement status!")
                st.rerun()
else:
    st.info("No bills yet. Add your first one above!")

# Summary
st.header("Who Owes What? 🧾")
balances = calculate_balances(participants, transactions)
if balances:
    bal_df = pd.DataFrame([
        {"Participant": participant_dict.get(pid, str(pid)), "Balance": round(amt, 2)}
        for pid, amt in balances.items()
    ])
    # Use color for balances: positive = green, negative = red
    def color_bal(val):
        color = 'green' if val >= 0 else 'red'
        return f'color: {color}'
    st.dataframe(
    bal_df.style
        .map(color_bal, subset=["Balance"])
        .format({"Balance": "{:.2f}"}),
    use_container_width=True
)

    st.subheader("Settle Up")
    transfers = min_transfers(balances)
    # --- WhatsApp-friendly summary ---
    expense_lines = ["*Expenses:*"]
    for tid, _, desc, amt, payer, involved_json, settled_json, ts in transactions[::-1]:
        involved_names = ", ".join([participant_dict.get(pid, str(pid)) for pid in json.loads(involved_json) if pid in participant_dict])
        payer_name = participant_dict.get(payer, str(payer))
        expense_lines.append(f"- {desc}: ${amt:.2f}\n  Paid by: {payer_name}\n  Split among: {involved_names}")
    if len(expense_lines) == 1:
        expense_lines.append("No expenses recorded.")

    balance_lines = ["*Balances:*"]
    for pid, amt in balances.items():
        balance_lines.append(f"{participant_dict.get(pid, str(pid))}: {'+' if amt >= 0 else ''}${amt:.2f}")

    import os
    settled_transfers_path = os.path.join(os.path.dirname(__file__), 'settled_transfers.json')
    try:
        with open(settled_transfers_path, 'r') as f:
            settled_transfers = json.load(f)
    except Exception:
        settled_transfers = {}

    settle_lines = ["*Settle Up:*"]
    transfer_checkboxes = []
    if transfers:
        for from_id, to_id, amt in transfers:
            key = f"{st.session_state.selected_split}_{from_id}_{to_id}_{amt}"
            checked = settled_transfers.get(key, False)
            label = f"{participant_dict.get(from_id, str(from_id))} ➔ {participant_dict.get(to_id, str(to_id))}: ${amt:.2f}"
            new_checked = st.checkbox(label, value=checked, key=f"settle_{key}")
            if new_checked != checked:
                settled_transfers[key] = new_checked
                with open(settled_transfers_path, 'w') as f:
                    json.dump(settled_transfers, f)
            if new_checked:
                label += " ✅"
            transfer_checkboxes.append(label)
        settle_lines.extend(transfer_checkboxes)
    else:
        settle_lines.append("All settled!")

    wa_summary = "\n\n".join([
        "\n".join(expense_lines),
        "\n".join(balance_lines),
        "\n".join(settle_lines)
    ])
    st.code(wa_summary, language="")
    # ---
else:
    st.info("Add everyone and a bill to see who owes what.")

import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import os
import hashlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# -------------------- FILES --------------------
USER_FILE = "users.csv"
EXPENSE_FILE = "expenses.csv"
CATEGORY_FILE = "categories.csv"

DEFAULT_CATEGORIES = ["Food", "Shopping", "Travel", "Rent", "Entertainment", "Others"]

# -------------------- AUTH --------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    if not os.path.exists(USER_FILE):
        pd.DataFrame(columns=["username", "password"]).to_csv(USER_FILE, index=False)
    return pd.read_csv(USER_FILE)

def save_user(username, password):
    users = load_users()
    if username.strip() == "" or password.strip() == "":
        return False
    if username in users['username'].values:
        return False
    new_user = pd.DataFrame([[username, hash_password(password)]], columns=["username", "password"])
    new_user.to_csv(USER_FILE, mode='a', header=False, index=False)
    return True

def authenticate(username, password):
    users = load_users()
    hashed = hash_password(password)
    user = users[(users['username'] == username) & (users['password'] == hashed)]
    return not user.empty

# -------------------- CATEGORIES --------------------
def load_categories():
    if not os.path.exists(CATEGORY_FILE):
        pd.DataFrame(DEFAULT_CATEGORIES, columns=["category"]).to_csv(CATEGORY_FILE, index=False)
    return pd.read_csv(CATEGORY_FILE)

def save_category(cat):
    df = load_categories()
    cat = cat.strip()
    if cat and cat not in df['category'].values:
        pd.DataFrame([[cat]], columns=["category"]).to_csv(CATEGORY_FILE, mode='a', header=False, index=False)
        return True
    return False

# -------------------- EXPENSES (with stable IDs) --------------------
COLUMNS = ["id", "date", "category", "amount", "description"]

def ensure_expense_file():
    if not os.path.exists(EXPENSE_FILE):
        pd.DataFrame(columns=COLUMNS).to_csv(EXPENSE_FILE, index=False)
    else:
        df = pd.read_csv(EXPENSE_FILE)
        # Migrate older file without id column
        if "id" not in df.columns:
            if df.empty:
                df = pd.DataFrame(columns=COLUMNS)
            else:
                df.insert(0, "id", range(1, len(df) + 1))
            df.to_csv(EXPENSE_FILE, index=False)

def load_expenses():
    ensure_expense_file()
    df = pd.read_csv(EXPENSE_FILE)
    # Normalize dtypes
    if not df.empty:
        if "amount" in df.columns:
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
        if "id" in df.columns:
            df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)
    return df

def next_id():
    df = load_expenses()
    return (df["id"].max() + 1) if not df.empty else 1

def save_expense(date, category, amount, desc):
    if str(date).strip() == "" or str(category).strip() == "" or str(amount).strip() == "":
        raise ValueError("Missing fields")
    _id = next_id()
    row = pd.DataFrame([[int(_id), date, category, float(amount), str(desc)]], columns=COLUMNS)
    row.to_csv(EXPENSE_FILE, mode='a', header=not os.path.getsize(EXPENSE_FILE), index=False)

def delete_expense(expense_id: int):
    df = load_expenses()
    df = df[df["id"] != int(expense_id)]
    df.to_csv(EXPENSE_FILE, index=False)

def update_expense(expense_id: int, date, category, amount, desc):
    df = load_expenses()
    idx = df.index[df["id"] == int(expense_id)]
    if len(idx) == 0:
        raise ValueError("Expense not found")
    i = idx[0]
    df.at[i, "date"] = date
    df.at[i, "category"] = category
    df.at[i, "amount"] = float(amount)
    df.at[i, "description"] = desc
    df.to_csv(EXPENSE_FILE, index=False)

# -------------------- UI HELPERS --------------------
def clear_root(root):
    for w in root.winfo_children():
        w.destroy()

def back_button(parent, show_menu_fn):
    tk.Button(parent, text="⬅ Back to Menu", command=lambda: (clear_root(root), show_menu_fn()), width=20).pack(pady=10)

def build_table(parent, df, columns=None, height=12):
    if df is None or df.empty:
        cols = columns if columns else []
        tree = ttk.Treeview(parent, columns=cols, show="headings", height=height)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=120, anchor="center")
        tree.pack(fill="x", padx=10)
        return tree

    cols = columns if columns else list(df.columns)
    tree = ttk.Treeview(parent, columns=cols, show="headings", height=height)
    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, width=120, anchor="center")
    # Insert rows
    for _, row in df.iterrows():
        tree.insert("", "end", values=[row[c] for c in cols])
    tree.pack(fill="both", expand=True, padx=10, pady=5)
    return tree

# -------------------- SECTIONS --------------------
def dashboard_section(root, show_menu):
    clear_root(root)
    frame = tk.Frame(root); frame.pack(fill="both", expand=True)
    tk.Label(frame, text="🏠 Dashboard Overview", font=("Arial", 18, "bold")).pack(pady=10)

    df = load_expenses()
    total = df["amount"].sum() if not df.empty else 0
    count = len(df)
    tk.Label(frame, text=f"Total Expenses: ₹{total:.2f}", font=("Arial", 14)).pack(pady=3)
    tk.Label(frame, text=f"Records: {count}", font=("Arial", 12)).pack(pady=3)

    # quick totals by category
    box = tk.Frame(frame); box.pack(pady=10)
    cats = df.groupby("category")["amount"].sum().sort_values(ascending=False) if not df.empty else pd.Series(dtype=float)
    for cat, val in cats.items():
        tk.Label(box, text=f"{cat}: ₹{val:.2f}", relief="groove", padx=8, pady=4).pack(side="left", padx=4)

    back_button(frame, show_menu)

def add_expense_section(root, show_menu):
    clear_root(root)
    frame = tk.Frame(root); frame.pack(fill="both", expand=True)
    tk.Label(frame, text="➕ Add Expense", font=("Arial", 18, "bold")).pack(pady=10)

    form = tk.Frame(frame); form.pack(pady=8)

    tk.Label(form, text="Date (YYYY-MM-DD):").grid(row=0, column=0, sticky="e", padx=5, pady=4)
    date_entry = tk.Entry(form); date_entry.grid(row=0, column=1, padx=5, pady=4)

    tk.Label(form, text="Category:").grid(row=1, column=0, sticky="e", padx=5, pady=4)
    cats = load_categories()["category"].tolist()
    category_var = tk.StringVar(value=cats[0] if cats else "")
    category_menu = ttk.Combobox(form, textvariable=category_var, values=cats, state="readonly", width=27)
    category_menu.grid(row=1, column=1, padx=5, pady=4)

    tk.Label(form, text="Amount:").grid(row=2, column=0, sticky="e", padx=5, pady=4)
    amount_entry = tk.Entry(form); amount_entry.grid(row=2, column=1, padx=5, pady=4)

    tk.Label(form, text="Description:").grid(row=3, column=0, sticky="e", padx=5, pady=4)
    desc_entry = tk.Entry(form); desc_entry.grid(row=3, column=1, padx=5, pady=4)

    def save():
        try:
            save_expense(date_entry.get().strip(), category_var.get().strip(), float(amount_entry.get()), desc_entry.get().strip())
            messagebox.showinfo("Success", "Expense Added!")
            date_entry.delete(0, "end"); amount_entry.delete(0, "end"); desc_entry.delete(0, "end")
        except Exception as e:
            messagebox.showerror("Error", f"Invalid Input\n{e}")

    tk.Button(frame, text="Save Expense", command=save, width=18).pack(pady=6)
    back_button(frame, show_menu)

def history_section(root, show_menu):
    clear_root(root)
    frame = tk.Frame(root); frame.pack(fill="both", expand=True)
    tk.Label(frame, text="📋 Expense History", font=("Arial", 18, "bold")).pack(pady=10)

    df = load_expenses()
    tree = build_table(frame, df, columns=COLUMNS)
    back_button(frame, show_menu)

def explorer_section(root, show_menu):
    clear_root(root)
    frame = tk.Frame(root); frame.pack(fill="both", expand=True)
    tk.Label(frame, text="🔎 Explorer (Filters)", font=("Arial", 18, "bold")).pack(pady=10)

    control = tk.Frame(frame); control.pack(pady=6)

    # Category filter
    tk.Label(control, text="Category:").grid(row=0, column=0, padx=4, pady=2)
    cats = ["All"] + load_categories()["category"].tolist()
    cat_var = tk.StringVar(value="All")
    cat_cb = ttk.Combobox(control, textvariable=cat_var, values=cats, state="readonly", width=18)
    cat_cb.grid(row=0, column=1, padx=4, pady=2)

    # Date filters
    tk.Label(control, text="From (YYYY-MM-DD):").grid(row=0, column=2, padx=4, pady=2)
    from_entry = tk.Entry(control, width=16); from_entry.grid(row=0, column=3, padx=4, pady=2)

    tk.Label(control, text="To (YYYY-MM-DD):").grid(row=0, column=4, padx=4, pady=2)
    to_entry = tk.Entry(control, width=16); to_entry.grid(row=0, column=5, padx=4, pady=2)

    # Search
    tk.Label(control, text="Search:").grid(row=0, column=6, padx=4, pady=2)
    search_entry = tk.Entry(control, width=20); search_entry.grid(row=0, column=7, padx=4, pady=2)

    result_frame = tk.Frame(frame); result_frame.pack(fill="both", expand=True, pady=6)
    tree = None

    def run_filter():
        nonlocal tree
        for w in result_frame.winfo_children():
            w.destroy()

        df = load_expenses()

        # Category
        if cat_var.get() != "All":
            df = df[df["category"] == cat_var.get()]

        # Date range (string compare works for YYYY-MM-DD)
        f = from_entry.get().strip()
        t = to_entry.get().strip()
        if f:
            df = df[df["date"] >= f]
        if t:
            df = df[df["date"] <= t]

        # Search in description/date/category
        q = search_entry.get().strip().lower()
        if q:
            df = df[df.apply(lambda r: q in str(r["description"]).lower() or
                                       q in str(r["category"]).lower() or
                                       q in str(r["date"]).lower(), axis=1)]

        tree = build_table(result_frame, df, columns=COLUMNS, height=14)

    tk.Button(frame, text="Apply Filters", command=run_filter, width=16).pack(pady=4)
    run_filter()
    back_button(frame, show_menu)

def update_delete_section(root, show_menu):
    clear_root(root)
    frame = tk.Frame(root); frame.pack(fill="both", expand=True)
    tk.Label(frame, text="✏️ Update & 🗑 Delete", font=("Arial", 18, "bold")).pack(pady=10)

    df = load_expenses()
    table_frame = tk.Frame(frame); table_frame.pack(fill="both", expand=True)
    tree = build_table(table_frame, df, columns=COLUMNS, height=12)

    # Edit form
    form = tk.LabelFrame(frame, text="Edit Selected"); form.pack(fill="x", padx=10, pady=8)

    tk.Label(form, text="ID:").grid(row=0, column=0, padx=4, pady=4, sticky="e")
    id_var = tk.StringVar(); id_entry = tk.Entry(form, textvariable=id_var, state="readonly", width=10)
    id_entry.grid(row=0, column=1, padx=4, pady=4)

    tk.Label(form, text="Date:").grid(row=0, column=2, padx=4, pady=4, sticky="e")
    date_var = tk.StringVar(); date_entry = tk.Entry(form, textvariable=date_var, width=16)
    date_entry.grid(row=0, column=3, padx=4, pady=4)

    tk.Label(form, text="Category:").grid(row=0, column=4, padx=4, pady=4, sticky="e")
    cats = load_categories()["category"].tolist()
    cat_var = tk.StringVar()
    cat_cb = ttk.Combobox(form, textvariable=cat_var, values=cats, state="readonly", width=18)
    cat_cb.grid(row=0, column=5, padx=4, pady=4)

    tk.Label(form, text="Amount:").grid(row=1, column=0, padx=4, pady=4, sticky="e")
    amt_var = tk.StringVar(); amt_entry = tk.Entry(form, textvariable=amt_var, width=12)
    amt_entry.grid(row=1, column=1, padx=4, pady=4)

    tk.Label(form, text="Description:").grid(row=1, column=2, padx=4, pady=4, sticky="e")
    desc_var = tk.StringVar(); desc_entry = tk.Entry(form, textvariable=desc_var, width=40)
    desc_entry.grid(row=1, column=3, columnspan=3, padx=4, pady=4, sticky="w")

    def refresh_table():
        for i in tree.get_children():
            tree.delete(i)
        refreshed = load_expenses()
        for _, row in refreshed.iterrows():
            tree.insert("", "end", values=[row[c] for c in COLUMNS])

    def on_select(_event=None):
        sel = tree.selection()
        if not sel:
            return
        vals = tree.item(sel[0], "values")
        if not vals:
            return
        id_var.set(vals[0])
        date_var.set(vals[1])
        cat_var.set(vals[2])
        amt_var.set(vals[3])
        desc_var.set(vals[4])

    tree.bind("<<TreeviewSelect>>", on_select)

    def do_update():
        try:
            if not id_var.get():
                messagebox.showwarning("Select", "Please select a record first.")
                return
            update_expense(int(id_var.get()), date_var.get().strip(), cat_var.get().strip(), float(amt_var.get()), desc_var.get().strip())
            messagebox.showinfo("Updated", "Expense updated.")
            refresh_table()
        except Exception as e:
            messagebox.showerror("Error", f"Update failed\n{e}")

    def do_delete():
        if not id_var.get():
            messagebox.showwarning("Select", "Please select a record first.")
            return
        if messagebox.askyesno("Confirm", "Delete selected expense?"):
            try:
                delete_expense(int(id_var.get()))
                id_var.set(""); date_var.set(""); cat_var.set(""); amt_var.set(""); desc_var.set("")
                refresh_table()
                messagebox.showinfo("Deleted", "Expense deleted.")
            except Exception as e:
                messagebox.showerror("Error", f"Delete failed\n{e}")

    btns = tk.Frame(frame); btns.pack(pady=6)
    tk.Button(btns, text="Update", command=do_update, width=14).pack(side="left", padx=6)
    tk.Button(btns, text="Delete", command=do_delete, width=14).pack(side="left", padx=6)

    back_button(frame, show_menu)

def summary_section(root, show_menu):
    clear_root(root)
    frame = tk.Frame(root); frame.pack(fill="both", expand=True)
    tk.Label(frame, text="📊 Summary", font=("Arial", 18, "bold")).pack(pady=10)

    df = load_expenses()
    if df.empty:
        tk.Label(frame, text="No expenses recorded yet.", fg="red").pack(pady=5)
        back_button(frame, show_menu)
        return

    total = df["amount"].sum()
    tk.Label(frame, text=f"Total Expenses: ₹{total:.2f}", font=("Arial", 14)).pack(pady=5)

    # Bar chart
    fig1, ax1 = plt.subplots()
    df.groupby("category")["amount"].sum().plot(kind="bar", ax=ax1)
    ax1.set_title("Expenses by Category"); ax1.set_xlabel("Category"); ax1.set_ylabel("Amount")
    canvas1 = FigureCanvasTkAgg(fig1, master=frame)
    canvas1.draw()
    canvas1.get_tk_widget().pack(fill="x", padx=10, pady=6)

    back_button(frame, show_menu)

def categories_section(root, show_menu):
    clear_root(root)
    frame = tk.Frame(root); frame.pack(fill="both", expand=True)
    tk.Label(frame, text="📂 Categories", font=("Arial", 18, "bold")).pack(pady=10)

    df = load_categories()
    tree = build_table(frame, df, columns=["category"], height=10)

    box = tk.Frame(frame); box.pack(pady=6)
    tk.Label(box, text="New Category:").pack(side="left", padx=4)
    cat_entry = tk.Entry(box, width=28); cat_entry.pack(side="left", padx=4)

    def add_category():
        if save_category(cat_entry.get().strip()):
            messagebox.showinfo("Success", "Category added!")
            cat_entry.delete(0, "end")
            # Refresh table
            for i in tree.get_children():
                tree.delete(i)
            for _, row in load_categories().iterrows():
                tree.insert("", "end", values=row.tolist())
        else:
            messagebox.showwarning("Note", "Category exists or invalid.")

    tk.Button(box, text="Add", command=add_category, width=10).pack(side="left", padx=4)
    back_button(frame, show_menu)

# -------------------- MENU --------------------
def show_menu():
    clear_root(root)
    menu_frame = tk.Frame(root); menu_frame.pack(fill="both", expand=True)
    tk.Label(menu_frame, text="💰 Expense Tracker", font=("Arial", 20, "bold")).pack(pady=10)

    tk.Button(menu_frame, text="🏠 Dashboard", width=30, command=lambda: dashboard_section(root, show_menu)).pack(pady=4)
    tk.Button(menu_frame, text="➕ Add Expense", width=30, command=lambda: add_expense_section(root, show_menu)).pack(pady=4)
    tk.Button(menu_frame, text="📋 Expense History", width=30, command=lambda: history_section(root, show_menu)).pack(pady=4)
    tk.Button(menu_frame, text="🔎 Explorer (Filters)", width=30, command=lambda: explorer_section(root, show_menu)).pack(pady=4)
    tk.Button(menu_frame, text="✏️ Update & 🗑 Delete", width=30, command=lambda: update_delete_section(root, show_menu)).pack(pady=4)
    tk.Button(menu_frame, text="📊 Summary", width=30, command=lambda: summary_section(root, show_menu)).pack(pady=4)
    tk.Button(menu_frame, text="📂 Categories", width=30, command=lambda: categories_section(root, show_menu)).pack(pady=4)

# -------------------- LOGIN --------------------
def login_page():
    clear_root(root)
    login_frame = tk.Frame(root); login_frame.pack(fill="both", expand=True)
    tk.Label(login_frame, text="🔐 Login", font=("Arial", 18, "bold")).pack(pady=10)

    form = tk.Frame(login_frame); form.pack(pady=8)
    tk.Label(form, text="Username:").grid(row=0, column=0, sticky="e", padx=5, pady=4)
    username_entry = tk.Entry(form, width=28); username_entry.grid(row=0, column=1, padx=5, pady=4)

    tk.Label(form, text="Password:").grid(row=1, column=0, sticky="e", padx=5, pady=4)
    password_entry = tk.Entry(form, show="*", width=28); password_entry.grid(row=1, column=1, padx=5, pady=4)

    def on_login():
        u, p = username_entry.get(), password_entry.get()
        if authenticate(u, p):
            messagebox.showinfo("Success", "Login Successful")
            show_menu()
        else:
            messagebox.showerror("Error", "Invalid credentials")

    def on_signup():
        u, p = username_entry.get(), password_entry.get()
        if save_user(u, p):
            messagebox.showinfo("Success", "Signup Successful. Please login.")
        else:
            messagebox.showerror("Error", "Signup failed. Username may exist or fields are empty.")

    btns = tk.Frame(login_frame); btns.pack(pady=8)
    tk.Button(btns, text="Login", command=on_login, width=12).pack(side="left", padx=6)
    tk.Button(btns, text="Signup", command=on_signup, width=12).pack(side="left", padx=6)

# -------------------- MAIN --------------------
root = tk.Tk()
root.title("Expense Tracker")
root.geometry("880x680")

ensure_expense_file()
login_page()

root.mainloop()

"""Synthetic law firm finance data (fictional firm 'Northbridge Partners') for a Power BI star-schema project."""
import numpy as np, pandas as pd, os
rng = np.random.default_rng(42)
os.makedirs("data", exist_ok=True)

# ---- dim_date
dates = pd.date_range("2025-01-01", "2026-10-31", freq="D")
dim_date = pd.DataFrame({"Date": dates})
dim_date["Year"] = dim_date.Date.dt.year
dim_date["MonthNo"] = dim_date.Date.dt.month
dim_date["Month"] = dim_date.Date.dt.strftime("%b")
dim_date["YearMonth"] = dim_date.Date.dt.strftime("%Y-%m")
dim_date["Quarter"] = "Q" + dim_date.Date.dt.quarter.astype(str)
# UK-style financial year starting 1 May (common in law firms)
dim_date["FinancialYear"] = np.where(dim_date.MonthNo >= 5, "FY" + (dim_date.Year + 1).astype(str).str[-2:], "FY" + dim_date.Year.astype(str).str[-2:])
dim_date["IsWorkingDay"] = dim_date.Date.dt.weekday < 5

# ---- dim_office
offices = [("LON","London","United Kingdom","GBP"),("MAN","Manchester","United Kingdom","GBP"),("PAR","Paris","France","EUR"),
           ("FRA","Frankfurt","Germany","EUR"),("AMS","Amsterdam","Netherlands","EUR"),("MAD","Madrid","Spain","EUR"),
           ("MIL","Milan","Italy","EUR"),("STO","Stockholm","Sweden","EUR"),("DUB","Dubai","United Arab Emirates","USD"),
           ("SIN","Singapore","Singapore","USD"),("HKG","Hong Kong","China","USD"),("SYD","Sydney","Australia","USD")]
dim_office = pd.DataFrame(offices, columns=["OfficeKey","Office","Country","ReportingCurrency"])
dim_office["Region"] = dim_office.Country.map(lambda c: "UK" if c=="United Kingdom" else ("Europe" if c in ["France","Germany","Netherlands","Spain","Italy","Sweden"] else ("Middle East" if c=="United Arab Emirates" else "Asia Pacific")))

# ---- dim_practice
practices = ["Technology & Communications","Intellectual Property","Privacy & Data Protection","Corporate","Dispute Resolution","Employment","Life Sciences","Energy & Utilities"]
dim_practice = pd.DataFrame({"PracticeKey": [f"P{i+1}" for i in range(len(practices))], "PracticeArea": practices})

# ---- dim_lawyer
grades = {"Partner":(0.15,650,1300),"Senior Associate":(0.25,450,1500),"Associate":(0.40,350,1600),"Trainee":(0.20,200,1100)}
n_law = 320
g = rng.choice(list(grades), n_law, p=[v[0] for v in grades.values()])
off_w = np.array([0.30,0.06,0.09,0.09,0.07,0.06,0.06,0.04,0.04,0.06,0.07,0.06]); off_w/=off_w.sum()
dim_lawyer = pd.DataFrame({
    "LawyerKey": [f"L{i:04d}" for i in range(1, n_law+1)],
    "Grade": g,
    "OfficeKey": rng.choice(dim_office.OfficeKey, n_law, p=off_w),
    "PracticeKey": rng.choice(dim_practice.PracticeKey, n_law),
})
dim_lawyer["HourlyRate"] = [round(grades[x][1]*rng.uniform(0.85,1.2), -1) for x in g]
dim_lawyer["AnnualTargetHours"] = [grades[x][2] for x in g]
dim_lawyer["Utilisation_bias"] = rng.normal(1.0, 0.12, n_law).clip(0.6, 1.35)

# ---- dim_client
sectors = ["Technology","Telecoms","Financial Services","Life Sciences","Retail","Media & Sport","Energy","Public Sector","Automotive"]
n_cli = 160
dim_client = pd.DataFrame({
    "ClientKey": [f"C{i:04d}" for i in range(1, n_cli+1)],
    "ClientName": [f"Client {i:03d}" for i in range(1, n_cli+1)],
    "Sector": rng.choice(sectors, n_cli),
    "ClientCountry": rng.choice(dim_office.Country.unique(), n_cli),
    "PaymentBehaviour": rng.choice(["Prompt","Average","Slow"], n_cli, p=[0.45,0.4,0.15]),
})

# ---- dim_matter
n_mat = 700
mat = pd.DataFrame({
    "MatterKey": [f"M{i:05d}" for i in range(1, n_mat+1)],
    "ClientKey": rng.choice(dim_client.ClientKey, n_mat),
    "PracticeKey": rng.choice(dim_practice.PracticeKey, n_mat),
    "FeeArrangement": rng.choice(["Hourly","Fixed fee","Capped fee"], n_mat, p=[0.6,0.25,0.15]),
    "OpenDate": rng.choice(dates[dates < "2026-09-01"], n_mat),
})
mat["OpenDate"] = pd.to_datetime(mat.OpenDate)
mat["CloseDate"] = mat.OpenDate + pd.to_timedelta(rng.integers(60, 420, n_mat), unit="D")
mat.loc[mat.CloseDate > "2026-10-31", "CloseDate"] = pd.NaT
mat["Status"] = np.where(mat.CloseDate.isna(), "Open", "Closed")
dim_matter = mat

# ---- fact_time (weekly entries per lawyer per matter)
weeks = pd.date_range("2025-01-06", "2026-10-26", freq="W-MON")
rows = []
for _, L in dim_lawyer.iterrows():
    pool = dim_matter[dim_matter.PracticeKey == L.PracticeKey].MatterKey.values
    weekly_target = L.AnnualTargetHours / 46
    for w in weeks:
        if rng.random() < 0.08:  # holiday week
            continue
        live = dim_matter[(dim_matter.MatterKey.isin(pool)) & (dim_matter.OpenDate <= w) & ((dim_matter.CloseDate.isna()) | (dim_matter.CloseDate >= w))].MatterKey.values
        if len(live) == 0:
            continue
        k = min(len(live), rng.integers(1, 4))
        chosen = rng.choice(live, k, replace=False)
        total = max(0, rng.normal(weekly_target * L.Utilisation_bias, weekly_target * 0.2))
        split = rng.dirichlet(np.ones(k)) * total
        for m, h in zip(chosen, split):
            h = round(h * 4) / 4
            if h <= 0: continue
            rows.append((w + pd.Timedelta(days=int(rng.integers(0, 5))), L.LawyerKey, m, h, True))
        # non-billable time (business development, training)
        nb = round(max(0, rng.normal(4, 2)) * 4) / 4
        if nb > 0:
            rows.append((w + pd.Timedelta(days=int(rng.integers(0, 5))), L.LawyerKey, None, nb, False))
fact_time = pd.DataFrame(rows, columns=["Date","LawyerKey","MatterKey","Hours","IsBillable"])
fact_time = fact_time.merge(dim_lawyer[["LawyerKey","HourlyRate"]], on="LawyerKey")
fact_time["StandardValue"] = np.where(fact_time.IsBillable, fact_time.Hours * fact_time.HourlyRate, 0).round(2)
fact_time = fact_time.drop(columns="HourlyRate")
fact_time.insert(0, "TimeEntryKey", [f"T{i:07d}" for i in range(1, len(fact_time)+1)])

# ---- fact_invoice (monthly billing per matter)
bill = fact_time[fact_time.IsBillable].copy()
bill["BillMonth"] = bill.Date.dt.to_period("M")
agg = bill.groupby(["MatterKey","BillMonth"], as_index=False).StandardValue.sum()
agg = agg.merge(dim_matter[["MatterKey","ClientKey","FeeArrangement"]], on="MatterKey").merge(dim_client[["ClientKey","PaymentBehaviour"]], on="ClientKey")
real = {"Hourly":(0.93,0.05),"Fixed fee":(0.82,0.10),"Capped fee":(0.86,0.08)}
agg["RealisationRate"] = [np.clip(rng.normal(*real[f]), 0.55, 1.05) for f in agg.FeeArrangement]
agg["InvoiceDate"] = (agg.BillMonth.dt.to_timestamp("M") + pd.Timedelta(days=10))
agg = agg[agg.InvoiceDate <= "2026-10-31"]
agg["BilledAmount"] = (agg.StandardValue * agg.RealisationRate).round(2)
agg["WriteOff"] = (agg.StandardValue - agg.BilledAmount).round(2)
delay = {"Prompt":(30,10),"Average":(55,15),"Slow":(95,25)}
agg["PaidDate"] = [d + pd.Timedelta(days=int(max(5, rng.normal(*delay[p])))) for d, p in zip(agg.InvoiceDate, agg.PaymentBehaviour)]
agg.loc[agg.PaidDate > "2026-10-31", "PaidDate"] = pd.NaT
agg["PaidAmount"] = np.where(agg.PaidDate.isna(), 0, agg.BilledAmount)
agg["Currency"] = "GBP"
fact_invoice = agg[["MatterKey","ClientKey","InvoiceDate","StandardValue","BilledAmount","WriteOff","PaidDate","PaidAmount","Currency"]].rename(columns={"StandardValue":"TimeValueBilled"})
fact_invoice.insert(0, "InvoiceKey", [f"INV{i:06d}" for i in range(1, len(fact_invoice)+1)])

# ---- deliberate data quality issues to find and fix (a real-world touch)
dq = fact_time.sample(25, random_state=1).index
fact_time.loc[dq[:10], "Hours"] = fact_time.loc[dq[:10], "Hours"] * 10     # typo outliers
fact_time.loc[dq[10:18], "LawyerKey"] = fact_time.loc[dq[10:18], "LawyerKey"].str.lower()  # inconsistent keys
dup = fact_invoice.sample(6, random_state=2)
fact_invoice = pd.concat([fact_invoice, dup])  # duplicate invoices

for name, df in {"dim_date":dim_date,"dim_office":dim_office,"dim_practice":dim_practice,
                 "dim_lawyer":dim_lawyer.drop(columns="Utilisation_bias"),"dim_client":dim_client.drop(columns="PaymentBehaviour"),
                 "dim_matter":dim_matter,"fact_time":fact_time,"fact_invoice":fact_invoice}.items():
    df.to_csv(f"data/{name}.csv", index=False)
    print(name, len(df))

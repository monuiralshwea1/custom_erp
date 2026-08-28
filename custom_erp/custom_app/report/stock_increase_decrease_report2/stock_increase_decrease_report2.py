import frappe
from frappe import _

def execute(filters=None):
    if not filters:
        filters = {}

    conditions = ""

    if filters.get("item_code"):
        conditions += " AND sle.item_code = %(item_code)s"

    if filters.get("item_group"):
        conditions += " AND item.item_group = %(item_group)s"

    if filters.get("branch"):
        conditions += " AND sed.branch = %(branch)s"

    show_summary = bool(filters.get("show_summary"))

    query = """
        SELECT
            sle.posting_date,
            sle.posting_time,
            se.stock_entry_type,  -- Fetching Stock Entry Type instead of voucher_type
            sle.voucher_no,
            sle.warehouse,
            sed.branch,
            sle.item_code,
            item.item_name,
            item.item_group,
            (sle.qty_after_transaction - sle.actual_qty) AS qty_before,
            CASE WHEN sle.actual_qty > 0 THEN sle.actual_qty ELSE 0 END AS in_qty,
            CASE WHEN sle.actual_qty < 0 THEN ABS(sle.actual_qty) ELSE 0 END AS out_qty,
            sle.qty_after_transaction AS qty_after
        FROM `tabStock Ledger Entry` sle
        INNER JOIN `tabItem` item ON item.name = sle.item_code
        LEFT JOIN `tabStock Entry` se ON se.name = sle.voucher_no  -- Link to Stock Entry Main Table
        LEFT JOIN `tabStock Entry Detail` sed ON sed.parent = sle.voucher_no
            AND sed.item_code = sle.item_code
            AND (sed.t_warehouse = sle.warehouse OR sed.s_warehouse = sle.warehouse)
        WHERE sle.is_cancelled = 0
        AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s
        {conditions}
        ORDER BY sle.posting_date {order}, sle.posting_time {order}
    """.format(conditions=conditions, order="ASC" if show_summary else "DESC")

    data = frappe.db.sql(query, filters, as_dict=1)

    if show_summary:
        return get_summary_columns(), build_summary(data)

    columns = [
        {"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": _("Time"), "fieldname": "posting_time", "fieldtype": "Time", "width": 80},
        {"label": _("Stock Entry Type"), "fieldname": "stock_entry_type", "fieldtype": "Data", "width": 140},
        {"label": _("Voucher No"), "fieldname": "voucher_no", "fieldtype": "Dynamic Link", "options": "voucher_type", "width": 150},
        {"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 120},
        {"label": _("Item"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
        {"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 150},
        {"label": _("Qty Before"), "fieldname": "qty_before", "fieldtype": "Float", "width": 100},
        {"label": _("In Qty"), "fieldname": "in_qty", "fieldtype": "Float", "width": 100},
        {"label": _("Out Qty"), "fieldname": "out_qty", "fieldtype": "Float", "width": 100},
        {"label": _("Qty After"), "fieldname": "qty_after", "fieldtype": "Float", "width": 100}
    ]

    return columns, data


def get_summary_columns():
    return [
        {"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 120},
        {"label": _("Item"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
        {"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 150},
        {"label": _("Qty Before"), "fieldname": "qty_before", "fieldtype": "Float", "width": 100},
        {"label": _("In Qty"), "fieldname": "in_qty", "fieldtype": "Float", "width": 100},
        {"label": _("Out Qty"), "fieldname": "out_qty", "fieldtype": "Float", "width": 100},
        {"label": _("Qty After"), "fieldname": "qty_after", "fieldtype": "Float", "width": 100}
    ]


def build_summary(rows):
    groups = {}
    order = []
    for r in rows:
        key = (r.get("branch") or "", r.get("item_code"))
        g = groups.get(key)
        if g is None:
            g = {
                "branch": r.get("branch"),
                "item_code": r.get("item_code"),
                "item_name": r.get("item_name"),
                "item_group": r.get("item_group"),
                "qty_before": r.get("qty_before") or 0,
                "in_qty": 0,
                "out_qty": 0,
                "qty_after": r.get("qty_after") or 0,
            }
            groups[key] = g
            order.append(key)
        g["in_qty"] += r.get("in_qty") or 0
        g["out_qty"] += r.get("out_qty") or 0
        g["qty_after"] = r.get("qty_after") or 0

    for key in order:
        g = groups[key]
        g["qty_before"] = round(g["qty_before"], 3)
        g["in_qty"] = round(g["in_qty"], 3)
        g["out_qty"] = round(g["out_qty"], 3)
        g["qty_after"] = round(g["qty_after"], 3)

    return [groups[key] for key in order]
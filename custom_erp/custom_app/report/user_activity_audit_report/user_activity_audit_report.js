// خيارات مُترجَمة صراحةً لضمان ظهورها بالعربية في قائمة الفلاتر
const ACTIVITY_TYPE_OPTIONS = [
	"Login",
	"Logout",
	"Failed Login",
	"Impersonate",
	"Route Visit",
	"Document View",
	"Document Create",
	"Document Update",
	"Document Delete",
	"Document Submit",
	"Document Cancel",
	"Document Amend",
	"Document Print",
	"Report Export",
	"File Download",
	"Access Denied",
	"Error",
	"Other",
]
	.map((t) => __(t))
	.join("\n");

const OUTCOME_OPTIONS = ["Success", "Failure", "Denied", "N/A"].map((t) => __(t)).join("\n");

const SOURCE_OPTIONS = ["Custom App", "Frappe"].map((t) => __(t)).join("\n");

frappe.query_reports["User Activity Audit Report"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.now_date(), -7),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.now_date(),
		},
		{
			fieldname: "user",
			label: __("User"),
			fieldtype: "Link",
			options: "User",
		},
		{
			fieldname: "activity_type",
			label: __("Activity Type"),
			fieldtype: "Select",
			options: ACTIVITY_TYPE_OPTIONS,
		},
		{
			fieldname: "reference_doctype",
			label: __("Document Type"),
			fieldtype: "Link",
			options: "DocType",
		},
		{
			fieldname: "reference_name",
			label: __("Document"),
			fieldtype: "Dynamic Link",
			options: "reference_doctype",
			get_query: () => {
				const doctype =
					frappe.query_report && frappe.query_report.get_filter_value
						? frappe.query_report.get_filter_value("reference_doctype")
						: null;
				return {
					doctype: "User Activity Audit Log",
					filters: { reference_doctype: doctype },
					fields: ["name", "reference_name"],
					limit: 50,
				};
			},
		},
		{
			fieldname: "page_route",
			label: __("Page Route"),
			fieldtype: "Data",
		},
		{
			fieldname: "outcome",
			label: __("Outcome"),
			fieldtype: "Select",
			options: OUTCOME_OPTIONS,
		},
		{
			fieldname: "ip_address",
			label: __("IP Address"),
			fieldtype: "Data",
		},
		{
			fieldname: "source",
			label: __("Event Source"),
			fieldtype: "Select",
			options: SOURCE_OPTIONS,
		},
		{
			fieldname: "page_length",
			label: __("Rows per Page"),
			fieldtype: "Int",
			default: 100,
			reqd: 1,
		},
		{
			fieldname: "page",
			label: __("Page"),
			fieldtype: "Int",
			default: 1,
			reqd: 1,
		},
	],

	onload(report) {
		report.page.add_inner_message(__("User Activity Audit Report"));

		// أدوات تنقّل بين الصفحات (الترقيم يتم على الخادم)
		report.page.add_inner_button(__("Previous Page"), () => {
			const page = parseInt(frappe.query_report.get_filter_value("page") || 1, 10);
			if (page > 1) {
				frappe.query_report.set_filter_value("page", page - 1);
				report.refresh();
			}
		});

		report.page.add_inner_button(__("Next Page"), () => {
			const page = parseInt(frappe.query_report.get_filter_value("page") || 1, 10);
			frappe.query_report.set_filter_value("page", page + 1);
			report.refresh();
		});

		report.page.add_inner_button(__("Audit Settings"), () => {
			frappe.set_route("Form", "User Activity Audit Settings");
		});
	},
};

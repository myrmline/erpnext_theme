"""Build the application context the assistant sees.

The browser only says *where* the user is (route, doctype, docname). Every
value that reaches the model is read here, on the server, as the current user,
through Frappe's own permission checks:

* the document must pass `frappe.has_permission(..., "read")`;
* field-level (permlevel) restrictions are applied before any value is read;
* hidden fields, password fields and layout-only fields are never included;
* lists go through `frappe.get_list`, which applies user permissions and
  permission query conditions.

If any check fails, that part of the context is silently left out. The model is
never told that something exists but is restricted.
"""

from __future__ import annotations

import frappe
from frappe.model import no_value_fields
from frappe.utils import cint, strip_html

from theme_myrmex.chatbot.utils import sanitize_route, truncate

# Never described to the model, regardless of the user's own permissions.
ALWAYS_EXCLUDED_DOCTYPES = {
	"Chatbot Settings",
	"Chatbot Conversation",
	"Chatbot Message",
	"Theme Settings",
	"User",
	"Access Log",
	"Activity Log",
	"Version",
	"Error Log",
	"Integration Request",
	"OAuth Client",
	"OAuth Bearer Token",
	"OAuth Authorization Code",
	"Social Login Key",
	"LDAP Settings",
	"Email Account",
	"System Settings",
	"Payment Gateway Account",
	"Connected App",
	"Token Cache",
	"User Permission",
}

SKIPPED_FIELDTYPES = set(no_value_fields) | {
	"Password",
	"Attach",
	"Attach Image",
	"Signature",
	"Geolocation",
	"Barcode",
	"Button",
	"Image",
	"Heading",
	"HTML",
	"Fold",
	"Table",
	"Table MultiSelect",
}

HTML_FIELDTYPES = {"Text Editor", "HTML Editor", "Markdown Editor"}

MAX_VALUE_CHARS = 300
MAX_CHILD_ROWS = 10
MAX_CHILD_COLUMNS = 6
MAX_LIST_ITEMS = 10


def build_context(settings, client_context: dict | None, user: str | None = None) -> dict:
	"""Return a small, permission-safe description of where the user is."""
	user = user or frappe.session.user
	client_context = client_context if isinstance(client_context, dict) else {}

	context: dict = {
		"user": _describe_user(user),
		"application": _describe_application(),
	}

	if not cint(client_context.get("include_page", 1)):
		# The user switched page context off in the chat panel.
		return context

	route = sanitize_route(client_context.get("route"))
	excluded = excluded_doctypes(settings)

	if cint(settings.get("share_page_context")) and route:
		context["page"] = _describe_page(route, client_context, excluded)

	doctype, docname = _target_from_route(route)

	if doctype and doctype in excluded:
		return context

	if docname and cint(settings.get("share_document_context")):
		document = describe_document(doctype, docname, cint(settings.get("max_context_fields")) or 40)
		if document:
			context["document"] = document

	if doctype and cint(settings.get("share_recent_activity")):
		recent = recent_documents(doctype, user)
		if recent:
			context["my_recent_changes"] = recent

	if cint(settings.get("share_open_tasks")):
		tasks = open_tasks(user)
		if tasks:
			context["my_open_tasks"] = tasks

	return context


def excluded_doctypes(settings) -> set[str]:
	extra = {line.strip() for line in (settings.get("excluded_doctypes") or "").splitlines()}
	return ALWAYS_EXCLUDED_DOCTYPES | {name for name in extra if name}


# ---------------------------------------------------------------------------
# Pieces
# ---------------------------------------------------------------------------


def _describe_user(user: str) -> dict:
	full_name = frappe.utils.get_fullname(user)
	return {
		"full_name": full_name,
		# Roles help the model tailor guidance ("ask your Accounts Manager").
		# Automatic roles carry no information, so they are dropped.
		"roles": sorted(set(frappe.get_roles(user)) - {"All", "Guest", "Desk User"})[:25],
		"language": frappe.local.lang or "en",
		"time_zone": frappe.utils.get_system_timezone(),
		"today": str(frappe.utils.today()),
	}


def _describe_application() -> dict:
	apps = []
	for app in frappe.get_installed_apps():
		try:
			version = frappe.get_attr(f"{app}.__version__")
		except Exception:
			version = ""
		apps.append(f"{app} {version}".strip())
	return {
		"site_name": frappe.db.get_single_value("System Settings", "app_name") or "",
		"installed_apps": apps,
		"country": frappe.db.get_default("country") or "",
		"currency": frappe.db.get_default("currency") or "",
	}


def _describe_page(route: list[str], client_context: dict, excluded: set[str]) -> dict:
	page: dict = {"route": "/".join(route), "view": route[0]}

	doctype, docname = _target_from_route(route)
	if doctype and doctype not in excluded and frappe.has_permission(doctype, "read"):
		meta = frappe.get_meta(doctype)
		page["doctype"] = doctype
		page["module"] = meta.module
		page["doctype_description"] = truncate(meta.description, MAX_VALUE_CHARS)
		page["is_submittable"] = bool(meta.is_submittable)
		if docname:
			page["docname"] = docname
	elif route[0] == "Workspaces" and len(route) > 1:
		workspace = route[-1]
		if frappe.db.exists("Workspace", workspace):
			page["workspace"] = workspace
			page["module"] = frappe.db.get_value("Workspace", workspace, "module") or ""

	title = client_context.get("page_title")
	if isinstance(title, str):
		page["title"] = truncate(title, 120)
	return page


def _target_from_route(route: list[str]) -> tuple[str | None, str | None]:
	"""Map a Desk route to (doctype, docname) when it points at a record type.

	Only real, non-table DocTypes are accepted; anything else returns (None, None).
	"""
	if len(route) < 2 or route[0] not in ("Form", "List", "Report", "Tree", "Kanban", "Calendar"):
		return None, None

	doctype = route[1]
	if not frappe.db.exists("DocType", doctype):
		return None, None
	if cint(frappe.get_cached_value("DocType", doctype, "istable")):
		return None, None

	docname = route[2] if route[0] == "Form" and len(route) > 2 else None
	if docname and docname.startswith("new-"):
		docname = None
	return doctype, docname


def describe_document(doctype: str, docname: str, max_fields: int = 40) -> dict | None:
	"""Readable fields of one document, or None when the user may not read it."""
	if not frappe.has_permission(doctype, "read", doc=docname):
		return None
	try:
		doc = frappe.get_doc(doctype, docname)
	except frappe.DoesNotExistError:
		return None

	if not doc.has_permission("read"):
		return None

	# Strip values this user's permlevels do not cover, before reading anything.
	doc.apply_fieldlevel_read_permissions()
	meta = doc.meta

	fields: dict = {}
	for df in meta.fields:
		if len(fields) >= max_fields:
			break
		if not _is_shareable_field(df):
			continue
		value = doc.get(df.fieldname)
		# Empty values and unticked boxes carry no information for the model.
		if value in (None, "", 0, 0.0):
			continue
		fields[df.label or df.fieldname] = _format_value(df, value)

	tables: dict = {}
	for table_df in meta.get_table_fields():
		if table_df.hidden or not hasattr(doc, table_df.fieldname):
			continue
		rows = doc.get(table_df.fieldname) or []
		if not rows:
			continue
		tables[table_df.label or table_df.fieldname] = _describe_rows(table_df.options, rows)

	summary = {
		"doctype": doctype,
		"name": doc.name,
		# The title field may itself be permlevel-restricted and already removed.
		"title": truncate((meta.title_field and doc.get(meta.title_field)) or doc.name, 140),
		"status": _doc_status(doc),
		"last_modified": str(doc.modified),
		"fields": fields,
	}
	if tables:
		summary["tables"] = tables
	return summary


def _is_shareable_field(df) -> bool:
	if df.fieldtype in SKIPPED_FIELDTYPES:
		return False
	if cint(df.hidden):
		return False
	if df.fieldname.startswith("_"):
		return False
	return True


def _format_value(df, value) -> str:
	if df.fieldtype == "Check":
		return "yes" if cint(value) else "no"
	if df.fieldtype in HTML_FIELDTYPES:
		value = strip_html(str(value))
	return truncate(value, MAX_VALUE_CHARS)


def _describe_rows(child_doctype: str, rows) -> dict:
	child_meta = frappe.get_meta(child_doctype)
	columns = [
		df
		for df in child_meta.fields
		if cint(df.in_list_view) and _is_shareable_field(df)
	][:MAX_CHILD_COLUMNS]

	sample = []
	for row in rows[:MAX_CHILD_ROWS]:
		entry = {}
		for df in columns:
			# apply_fieldlevel_read_permissions deletes restricted attributes.
			if not hasattr(row, df.fieldname):
				continue
			value = row.get(df.fieldname)
			if value not in (None, ""):
				entry[df.label or df.fieldname] = _format_value(df, value)
		if entry:
			sample.append(entry)

	return {"row_count": len(rows), "rows": sample, "truncated": len(rows) > MAX_CHILD_ROWS}


def _doc_status(doc) -> str:
	if doc.get("status"):
		return str(doc.status)
	return {0: "Draft", 1: "Submitted", 2: "Cancelled"}.get(cint(doc.docstatus), "")


def recent_documents(doctype: str, user: str) -> list[dict]:
	"""The user's own recent edits in this DocType, through get_list."""
	meta = frappe.get_meta(doctype)
	fields = ["name", "modified"]
	title_field = meta.title_field if meta.title_field and meta.title_field != "name" else None
	if title_field and meta.has_field(title_field):
		fields.append(title_field)

	try:
		rows = frappe.get_list(
			doctype,
			filters={"modified_by": user},
			fields=fields,
			order_by="modified desc",
			limit_page_length=5,
		)
	except (frappe.PermissionError, frappe.DoesNotExistError):
		return []
	except Exception:
		frappe.log_error(title="Myrmex Assistant: recent documents failed")
		return []

	return [
		{
			"name": row.name,
			"title": truncate(row.get(title_field) or row.name, 120) if title_field else row.name,
			"modified": str(row.modified),
		}
		for row in rows
	]


def open_tasks(user: str) -> list[dict]:
	"""Open ToDo assignments for the user, through get_list."""
	try:
		rows = frappe.get_list(
			"ToDo",
			filters={"allocated_to": user, "status": "Open"},
			fields=["reference_type", "reference_name", "description", "date", "priority"],
			order_by="date asc, modified desc",
			limit_page_length=MAX_LIST_ITEMS,
		)
	except frappe.PermissionError:
		return []

	return [
		{
			"about": f"{row.reference_type} {row.reference_name}".strip() if row.reference_type else "",
			"description": truncate(strip_html(row.description or ""), 160),
			"due": str(row.date or ""),
			"priority": row.priority or "",
		}
		for row in rows
	]

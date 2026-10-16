# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import calendar

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, add_years, get_datetime, today

from erpnext.projects.doctype.project.project import get_timeline_data


class TestProjectTimeline(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		self.project = f"_Test Timeline {frappe.generate_hash(length=10)}"

	def add_time_log(self, from_time, *, docstatus=0, project=None):
		# Insert only the child rows this query consumes, without unrelated
		# employee, company, billing, or Timesheet validation dependencies.
		frappe.get_doc(
			doctype="Timesheet Detail",
			name=frappe.generate_hash(length=10),
			parent=self.project,
			parenttype="Timesheet",
			parentfield="time_logs",
			project=project or self.project,
			from_time=from_time,
			docstatus=docstatus,
		).db_insert()

	def test_project_without_time_logs_has_empty_timeline(self):
		self.assertEqual(get_timeline_data("Project", self.project), {})

	def test_daily_counts_exclude_cancelled_other_project_and_old_logs(self):
		first_day = add_days(today(), -2)
		second_day = add_days(today(), -1)
		cutoff = add_years(today(), -1)
		self.add_time_log(f"{first_day} 09:00:00")
		self.add_time_log(f"{first_day} 17:30:00", docstatus=1)
		self.add_time_log(f"{second_day} 00:00:00")
		self.add_time_log(f"{first_day} 12:00:00", docstatus=2)
		self.add_time_log(f"{first_day} 10:00:00", project=f"{self.project} other")
		self.add_time_log(f"{add_days(cutoff, -1)} 23:59:59")
		self.add_time_log(f"{cutoff} 00:00:00")
		self.add_time_log(f"{cutoff} 00:00:01")

		def midnight_epoch(day):
			return calendar.timegm(get_datetime(day).timetuple())

		timeline = get_timeline_data("Project", self.project)
		self.assertEqual(
			timeline,
			{midnight_epoch(first_day): 2, midnight_epoch(second_day): 1, midnight_epoch(cutoff): 1},
		)
		self.assertTrue(all(isinstance(timestamp, int) for timestamp in timeline))
		self.assertEqual(len(frappe.parse_json(frappe.as_json(timeline))), 3)

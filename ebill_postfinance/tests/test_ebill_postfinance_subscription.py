# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from freezegun import freeze_time

from odoo.tools import file_open

from .common import CommonCase


@freeze_time("2019-06-21 09:06:00")
class TestEbillPostfinanceSubscription(CommonCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_import_subscription_status(self):
        with file_open(
            "ebill_postfinance/tests/examples/subscription_update.csv"
        ) as csvfile:
            self.service._import_subscription_file(csvfile)

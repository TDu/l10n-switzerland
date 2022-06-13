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
        cls.EbillPaymentContract = cls.env["ebill.payment.contract"]

    def test_import_subscription_status(self):
        with file_open(
            "ebill_postfinance/tests/examples/subscription_update.csv"
        ) as csvfile:
            self.service._import_subscription_file(csvfile)

        contract = self.EbillPaymentContract.search(
            [("postfinance_billerid", "=", "41100000000000001")]
        )
        self.assertTrue(contract)
        self.assertEqual(contract.partner_id.email, "hans.muster@mail.ch")

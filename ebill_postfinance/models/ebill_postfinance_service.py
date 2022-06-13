# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import csv
import logging
import logging.config

# from ..ebilling_postfinance.ebilling_postfinance import ebilling_postfinance
from ebilling_postfinance import ebilling_postfinance

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EbillPostfinanceService(models.Model):
    _name = "ebill.postfinance.service"
    _description = "Postfinance eBill service configuration"

    name = fields.Char(required=True)
    username = fields.Char()
    password = fields.Char()
    biller_id = fields.Char(string="Biller ID", size=17, required=True)
    use_test_service = fields.Boolean(string="Testing", help="Target the test service")
    partner_bank_id = fields.Many2one(
        comodel_name="res.partner.bank", string="Bank account", ondelete="restrict"
    )
    invoice_message_ids = fields.One2many(
        comodel_name="ebill.postfinance.invoice.message",
        inverse_name="service_id",
        string="Invoice Messages",
        readonly=True,
    )
    ebill_payment_contract_ids = fields.One2many(
        comodel_name="ebill.payment.contract",
        inverse_name="postfinance_service_id",
        string="Contracts",
        readonly=True,
    )
    active = fields.Boolean(default=True)
    file_type_to_use = fields.Selection(
        string="Invoice Format",
        default="EAI.XML",
        required=True,
        selection=[
            ("XML", "ybinvoice"),
            ("EAI.XML", "Custom XML (SAPiDoc)"),
            # ("eai.edi", "Custom EDIFACT"),
            ("struct.pdf", "Factur X"),
        ],
    )
    operation_timeout = fields.Integer(
        string="HTTP Timeout",
        default="600",
        help="Timeout for each HTTP (GET, POST) request in seconds.",
    )

    def _get_service(self):
        return ebilling_postfinance.WebService(
            self.use_test_service,
            self.username,
            self.password,
            self.biller_id,
            self.operation_timeout,
        )

    def test_ping(self):
        """Test the service from the UI."""
        self.ensure_one()
        msg = ["Test connection to service"]
        res = self.ping_service()
        if res:
            msg.append("Success pinging service \n  Receive :{}".format(res))
        else:
            msg.append(" - Failed pinging service")
        raise UserError("\n".join(msg))

    def ping_service(self, test_error=False, test_exception=False):
        """Ping the service, uses the authentication.

        test_error: will create an unhandled error in the repsonse
        test_exception: will create a FaultException

        """
        service = self._get_service()
        return service.ping()

    def search_invoice(self, transaction_id=None):
        """Get invoice status from the server.

        transaction_id:
        """
        service = self._get_service()
        res = service.search_invoices(transaction_id)
        if res.InvoiceCount == 0:
            _logger.info("Search invoice returned no invoice")
            return res
        if res.InvoiceCount < res.TotalInvoiceCount:
            # TODO handle the case where there is more to download ?
            _logger.info("Search invoice has more to download")
        for message in res.InvoiceList.SearchInvoice:
            record = self.invoice_message_ids.search(
                [("transaction_id", "=", message.TransactionId)]
            )
            if record:
                record.update_message_from_server_data(message)
            else:
                _logger.warning(f"Could not find record for message {message}")
        return res

    def upload_file(self, transaction_id, file_type, data):
        service = self._get_service()
        res = service.upload_files(transaction_id, file_type, data)
        return res

    def get_invoice_list(self, archive_data=False):
        service = self._get_service()
        res = service.get_invoice_list(archive_data)
        return res

    def get_process_protocol_list(self, archive_data=False):
        service = self._get_service()
        res = service.get_process_protocol_list(archive_data)
        return res

    def initiate_ebill_recipient_subscription(self, recipient_email):
        """Initiate subscripiton of eBill recipient.

        recipient_email: email's payer to initiate subscription

        response: {
            'SubscriptionInitiationToken': Token to use for confirmation,
            Message: Human readable explanation of problem.
            }
        """
        service = self._get_service()
        res = service.initiate_ebill_recipient_subscription(recipient_email)
        return res

    def get_ebill_recipient_subscription_status(self, recipient_id):
        r"""Get a payer subscription status

        recipient_id: eBillRecipientID (N17) or
                      eBillRecipient email address (^\S+@\S+$) or
                      eBillRecipient UIDHR (CHE[0-9]{9})
        """
        service = self._get_service()
        res = service.get_ebill_recipient_subscription_status(recipient_id)
        return res

    def get_ebill_recipient_subscription_status_bulk(self, recipient_ids):
        r"""Get a payer subscription status

        recipient_ids: a list of
                      eBillRecipientID (N17) or
                      eBillRecipient email address (^\S+@\S+$) or
                      eBillRecipient UIDHR (CHE[0-9]{9})
        """
        service = self._get_service()
        res = service.get_ebill_recipient_subscription_status_bulk(recipient_ids)
        return res

    def get_registration_protocol_list(self, archive_data=False):
        service = self._get_service()
        res = service.get_registration_protocol_list(archive_data)
        for registration_protocol in res or {}:
            self.get_registration_protocol(registration_protocol.CreateDate)
        return res

    def get_registration_protocol(self, create_date, archive_data=False):
        service = self._get_service()
        res = service.get_registration_protocol(create_date, archive_data)
        return res

    @api.model
    def cron_update_invoices(self):
        services = self.search([])
        for service in services:
            service.search_invoice()

    # Related to subscription updates

    def _import_subscription_file(self, file_data):
        reader = csv.reader(file_data, delimiter=";")
        next(reader)  # Ditch the header
        for row in reader:
            self._import_subscription_change(row)
            return  # FIXME for testing only

    def _import_subscription_change(self, data):
        """
        action: 1=registration, 2=direct regsitration, 3=cancelation
        """
        action = int(data[0])
        billerid = data[1]
        if billerid != self.biller_id:
            raise UserError(
                _(
                    f"Error importing postfinance subscription unknown biller ID {billerid}"
                )
            )
        recipient_id = data[2]

        existing_contract = self.env["ebill.payment.contract"].search(
            [
                ("postfinance_billerid", "=", recipient_id),
                ("postfinance_service_id", "=", self.id),
            ],
            limit=1,  # To help for now
        )
        if action == 3:
            if existing_contract:
                existing_contract.state = "cancel"
            return

        partner_type = data[3]
        # language = data[4]
        given_name = data[5]
        family_name = data[6]
        company_name = data[7]
        address = data[8]
        zip_code = data[9]
        city = data[10]
        # country = data[11]
        email = data[12]
        # uid = data[13]
        # credit_account = data[14]
        # creditor_ref= data[15]

        if not existing_contract:
            partner = self.env["res.partner"].search([("email", "ilike", email)])
            if not partner:
                partner_name = (
                    company_name
                    if partner_type == "COMPANY"
                    else " ".join([given_name, family_name])
                )
                partner = self.env["res.partner"].create(
                    {
                        "name": partner_name,
                        "street": address,
                        "zip": zip_code,
                        "city": city,
                        "email": email,
                        "is_company": partner_type == "COMPANY"
                        # add the language
                        # add the country
                    }
                )

            self.env["ebill.payment.contract"].create(
                {
                    "partner_id": partner.id,
                    "postfinance_billerid": recipient_id,
                    "postfinance_service_id": self.id,
                    # "transmit_method_id":
                }
            )

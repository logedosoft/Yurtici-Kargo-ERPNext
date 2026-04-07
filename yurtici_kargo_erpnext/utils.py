# Copyright (c) 2025, Logedosoft Business Solutions and contributors
# For license information, please see license.txt

import frappe, json
from frappe import msgprint, _
import requests
from bs4 import BeautifulSoup
import json
import xml.sax.saxutils


@frappe.whitelist()
def test_connection(docYIKSettings):
	"""
	Test connection to Yurtiçi Kargo API.
	Called from client side to verify API credentials.

	Args:
		docYIKSettings: JSON string containing Yurtici Kargo Ayarlari settings

	Returns:
		dict with op_result (bool) and op_message (str)
	"""
	# Parse JSON string from client side
	docYIKSettings = json.loads(docYIKSettings)

	# Create a frappe document from the JSON data
	docYIKSettings = frappe.get_doc(docYIKSettings)

	# Call queryShipment with TEST key
	return queryShipment("TEST", docYIKSettings)


def queryShipment(key, docYIKSettings=None):
	"""
	Query shipment information from Yurtiçi Kargo API.

	Args:
		key: The cargo key to query
		docYIKSettings: Optional Yurtici Kargo Ayarlari document. If None, will be fetched.

	Returns:
		dict with op_result (bool) and op_message (str)
	"""
	dctResult = frappe._dict({"op_result": False, "op_message": ""})

	# Get settings if not provided
	if docYIKSettings is None:
		docYIKSettings = frappe.get_doc("Yurtici Kargo Ayarlari")

	# Get password using get_password method
	docYIKSettings.api_password = docYIKSettings.get_password("api_password")

	# Build SOAP request
	soap_request = """<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ship="http://yurticikargo.com.tr/ShippingOrderDispatcherServices">
   <soapenv:Header/>
   <soapenv:Body>
	  <ship:queryShipment>
		 <wsUserName>{{ docYIKSettings.api_user_name }}</wsUserName>
		 <wsPassword>{{ docYIKSettings.api_password }}</wsPassword>
		 <wsLanguage>{{ docYIKSettings.user_language }}</wsLanguage>
		 <keys>{{ key }}</keys>
		 <keyType>0</keyType>
		 <addHistoricalData>false</addHistoricalData>
		 <onlyTracking>false</onlyTracking>
	  </ship:queryShipment>
   </soapenv:Body>
</soapenv:Envelope>"""

	try:
		soap_request = frappe.render_template(
			soap_request, context={"docYIKSettings": docYIKSettings, "key": key}, is_path=False
		)

		# Send SOAP request
		headers = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": ""}

		response = requests.post(
			docYIKSettings.web_service_url, data=soap_request.encode("utf-8"), headers=headers, timeout=30
		)

		# Parse response with BeautifulSoup
		soup = BeautifulSoup(response.content, "xml")

		# Find ShippingDeliveryVO element
		shipping_vo = soup.find("ShippingDeliveryVO")

		if not shipping_vo:
			dctResult.op_message = "Invalid response from Yurtiçi Kargo API"
			return dctResult

		# Extract outFlag and outResult
		out_flag = shipping_vo.find("outFlag")
		out_result = shipping_vo.find("outResult")

		out_flag_value = out_flag.text if out_flag else None
		out_result_value = out_result.text if out_result else ""

		# Check for authentication problem (outFlag=1)
		if out_flag_value == "1":
			err_code = shipping_vo.find("errCode")
			err_code_value = err_code.text if err_code else ""
			dctResult.op_message = f"Authentication error: {out_result_value} (Error Code: {err_code_value})"
			return dctResult

		# Check for valid response (outFlag=0)
		if out_flag_value == "0":
			# Check for error in shippingDeliveryDetailVO
			detail_vo = shipping_vo.find("shippingDeliveryDetailVO")

			if detail_vo:
				err_code = detail_vo.find("errCode")
				err_message = detail_vo.find("errMessage")

				if err_code and err_code.text != "0":
					dctResult.op_message = err_message.text if err_message else f"Error code: {err_code.text}"
					return dctResult

				# Valid response - extract shipment details
				cargo_key = detail_vo.find("cargoKey")
				invoice_key = detail_vo.find("invoiceKey")
				job_id = detail_vo.find("jobId")
				operation_code = detail_vo.find("operationCode")
				operation_message = detail_vo.find("operationMessage")
				operation_status = detail_vo.find("operationStatus")

				count = shipping_vo.find("count")
				sender_cust_id = shipping_vo.find("senderCustId")

				dctResult.op_result = True
				dctResult.op_message = out_result_value
				dctResult.data = {
					"count": count.text if count else "0",
					"sender_cust_id": sender_cust_id.text if sender_cust_id else "",
					"cargo_key": cargo_key.text if cargo_key else "",
					"invoice_key": invoice_key.text if invoice_key else "",
					"job_id": job_id.text if job_id else "0",
					"operation_code": operation_code.text if operation_code else "",
					"operation_message": operation_message.text if operation_message else "",
					"operation_status": operation_status.text if operation_status else "",
				}
			else:
				dctResult.op_result = True
				dctResult.op_message = out_result_value
		else:
			dctResult.op_message = (
				f"Unexpected response: outFlag={out_flag_value}, outResult={out_result_value}"
			)

	except requests.exceptions.RequestException as e:
		dctResult.op_message = f"Network error: {str(e)}"
	except Exception as e:
		dctResult.op_message = f"Error processing response: {str(e)}"

	return dctResult


def _get_customer_phone(customer):
	"""
	Get and format customer phone number from Contact doctype.

	Args:
		customer: Customer name

	Returns:
		Formatted 11-digit phone number or empty string
	"""
	try:
		# Find contact linked to customer
		contact_name = frappe.db.get_value(
			"Dynamic Link",
			{"link_doctype": "Customer", "link_name": customer, "parenttype": "Contact"},
			"parent",
		)

		if not contact_name:
			return ""

		# Get phone from contact
		contact = frappe.get_doc("Contact", contact_name)
		phone = contact.phone or contact.mobile_no or ""

		if phone:
			return _format_phone(phone)

		return ""
	except Exception:
		return ""


def _format_phone(raw):
	"""
	Normalize phone number to 11-digit Turkish format.

	Args:
		raw: Raw phone number string

	Returns:
		Formatted 11-digit string starting with 0
	"""
	if not raw:
		return ""

	# Remove all non-digit characters
	digits = "".join(filter(str.isdigit, raw))

	# If starts with 90 (country code), remove it
	if digits.startswith("90") and len(digits) > 2:
		digits = digits[2:]

	# If starts with 0, keep as is
	if digits.startswith("0"):
		return digits[:11] if len(digits) >= 11 else digits

	# If doesn't start with 0, add 0
	if len(digits) >= 10:
		return "0" + digits[:10]

	return digits


def dn_validate(doc, method):
	"""
	Validation hook for Delivery Note documents.
	Validates Yurtiçi Kargo related fields and settings.
	Only runs for submit operations (docstatus == 1).
	"""
	# Only validate on submit, not on draft saves
	if doc.docstatus == 1:
		# Validate that delivery method is set (it's a required field)
		if doc.custom_ld_delivery_method == "Yurtiçi Kargo":
			# Check if prevention of submission without printing label is enabled
			settings = frappe.get_single("Yurtici Kargo Ayarlari")
			if settings.prevent_delivery_note_submission_without_printing_label:
				# Check if label has been printed
				if not doc.custom_ld_yik_print_count or doc.custom_ld_yik_print_count == 0:
					frappe.throw(_("Önce Kargo etiketi yazdırın!"))


def createShipment(dn_name, docYIKSettings=None):
	"""
	Create a shipment with Yurtiçi Kargo API for a Delivery Note.

	Args:
		dn_name: Name of the Delivery Note document
		docYIKSettings: Optional Yurtici Kargo Ayarlari document. If None, will be fetched.

	Returns:
		dict with op_result (bool) and op_message (str)
		If successful, also contains data with cargo_key and job_id
	"""
	import re
	
	dctResult = frappe._dict({"op_result": False, "op_message": ""})

	try:
		# Get Delivery Note document
		dn = frappe.get_doc("Delivery Note", dn_name)

		# Check if this is for Yurtiçi Kargo
		if dn.custom_ld_delivery_method != "Yurtiçi Kargo":
			dctResult.op_message = "Delivery Note is not for Yurtiçi Kargo"
			return dctResult

		# Get settings if not provided
		if docYIKSettings is None:
			docYIKSettings = frappe.get_doc("Yurtici Kargo Ayarlari")

		# Get password using get_password method
		docYIKSettings.api_password = docYIKSettings.get_password("api_password")

		# Get address
		addr = None
		if dn.shipping_address_name:
			addr = frappe.get_doc("Address", dn.shipping_address_name)

		# Get customer phone
		customer_phone = _get_customer_phone(dn.customer)

		# Prepare data for SOAP request
		# cargoKey, invoiceKey, waybillNo: max 20 chars, use dn.name[:20]
		dn_name_truncated = dn.name[:20]

		# receiverCustName: min 5 chars, min 4 letters
		receiver_cust_name = dn.customer_name or ""
		if len(receiver_cust_name) < 5 or sum(c.isalpha() for c in receiver_cust_name) < 4:
			dctResult.op_message = _(
				"Invalid customer name: must be at least 5 characters with at least 4 letters"
			)
			return dctResult

		# receiverAddress: min 10, max 200 chars, do NOT include city/town
		address_line1 = addr.address_line1 if addr and addr.address_line1 else ""
		address_line2 = addr.address_line2 if addr and addr.address_line2 else ""
		receiver_address = f"{address_line1} {address_line2}".strip()
		if len(receiver_address) < 10:
			dctResult.op_message = _("Address must be at least 10 characters")
			return dctResult
		if len(receiver_address) > 200:
			receiver_address = receiver_address[:200]

		if not customer_phone:
			receiver_phone = docYIKSettings.default_phone
		else:
			receiver_phone = customer_phone

		# receiverPhone1: 11 digits, leading 0
		if (
			not receiver_phone
			or len(receiver_phone) != 11
			or not receiver_phone.isdigit()
			or not receiver_phone.startswith("0")
		):
			dctResult.op_message = _("Invalid phone number: must be 11 digits starting with 0")
			return dctResult

		# cityName
		city_name = addr.city if addr and addr.city else ""
		if not city_name:
			dctResult.op_message = _("City is required")
			return dctResult

		# townName: addr.county or addr.city
		town_name = addr.county if addr and addr.county else addr.city if addr and addr.city else ""
		if not town_name:
			dctResult.op_message = _("Town or city is required")
			return dctResult

		# cargoCount: int(dn.total_qty) or 1
		cargo_count = int(dn.total_qty) if dn.total_qty else 1

		# taxNumber: 10 digits (company) or 11 digits (individual)
		#tax_number = dn.tax_id if dn.tax_id and ((len(dn.tax_id) == 10) or (len(dn.tax_id) == 11)) else ""
		raw_tax = re.sub(r"\D", "", dn.tax_id or "")
		tax_number = raw_tax if len(raw_tax) in (10, 11) else ""

		# description: DN:{dn.name} truncated to 255
		description = f"DN:{dn.name}"[:255]

		# orgGeoCode
		org_geo_code = docYIKSettings.branch_code or ""
		if not org_geo_code:
			dctResult.op_message = _("Branch code is required in settings")
			return dctResult

		# Build SOAP request
		soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ship="http://yurticikargo.com.tr/ShippingOrderDispatcherServices">
   <soapenv:Header/>
   <soapenv:Body>
	  <ship:createShipment>
		 <wsUserName>{xml.sax.saxutils.escape(docYIKSettings.api_user_name)}</wsUserName>
		 <wsPassword>{xml.sax.saxutils.escape(docYIKSettings.api_password)}</wsPassword>
		 <userLanguage>{xml.sax.saxutils.escape(docYIKSettings.user_language)}</userLanguage>
		 <ShippingOrderVO>
			<cargoKey>{xml.sax.saxutils.escape(dn_name_truncated)}</cargoKey>
			<invoiceKey>{xml.sax.saxutils.escape(dn_name_truncated)}</invoiceKey>
			<receiverCustName>{xml.sax.saxutils.escape(receiver_cust_name)}</receiverCustName>
			<receiverAddress>{xml.sax.saxutils.escape(receiver_address)}</receiverAddress>
			<receiverPhone1>{xml.sax.saxutils.escape(receiver_phone)}</receiverPhone1>
			<cityName>{xml.sax.saxutils.escape(city_name)}</cityName>
			<townName>{xml.sax.saxutils.escape(town_name)}</townName>
			<cargoCount>{cargo_count}</cargoCount>
			<waybillNo>{xml.sax.saxutils.escape(dn_name_truncated)}</waybillNo>
			<taxNumber>{xml.sax.saxutils.escape(tax_number)}</taxNumber>
			<description>{xml.sax.saxutils.escape(description)}</description>
			<orgGeoCode>{xml.sax.saxutils.escape(org_geo_code)}</orgGeoCode>
		 </ShippingOrderVO>
	  </ship:createShipment>
   </soapenv:Body>
</soapenv:Envelope>"""

		# Send SOAP request
		headers = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": ""}

		response = requests.post(
			docYIKSettings.web_service_url, data=soap_request.encode("utf-8"), headers=headers, timeout=30
		)

		if docYIKSettings.enable_detailed_logging:
			frappe.log_error("YIK REQUEST", f"Request={soap_request}\nResponse={response} - {response.content}")

		# Parse response with BeautifulSoup
		soup = BeautifulSoup(response.content, "xml")

		# Find ShippingOrderResultVO element
		shipping_order_result_vo = soup.find("ShippingOrderResultVO")

		if not shipping_order_result_vo:
			dctResult.op_message = "Invalid response from Yurtiçi Kargo API"
			return dctResult

		# Extract outFlag and outResult
		out_flag = shipping_order_result_vo.find("outFlag")
		out_result = shipping_order_result_vo.find("outResult")

		out_flag_value = out_flag.text if out_flag else None
		out_result_value = out_result.text if out_result else ""

		# Check for authentication problem (outFlag=1)
		if out_flag_value == "1":
			detail_vo   = shipping_order_result_vo.find("shippingOrderDetailVO")
			err_code    = detail_vo.find("errCode").text    if detail_vo and detail_vo.find("errCode")    else ""
			err_message = detail_vo.find("errMessage").text if detail_vo and detail_vo.find("errMessage") else out_result_value
			dctResult.op_message = "[{0}] {1}".format(err_code, err_message)
			return dctResult

		# Check for valid response (outFlag=0)
		if out_flag_value == "0":
			# jobId lives at ShippingOrderResultVO level, not inside shippingOrderDetailVO
			job_id_node = shipping_order_result_vo.find("jobId")
			job_id_value = job_id_node.text if job_id_node else "0"

			detail_vo = shipping_order_result_vo.find("shippingOrderDetailVO")  # lowercase s

			if detail_vo:
				cargo_key_node   = detail_vo.find("cargoKey")
				invoice_key_node = detail_vo.find("invoiceKey")

				dctResult.op_result  = True
				dctResult.op_message = out_result_value
				dctResult.data = {
					"cargo_key":   cargo_key_node.text   if cargo_key_node   else dn_name_truncated,
					"invoice_key": invoice_key_node.text if invoice_key_node else dn_name_truncated,
					"job_id":      job_id_value,
				}
			else:
				dctResult.op_result  = True
				dctResult.op_message = out_result_value
				dctResult.data = {
					"cargo_key":   dn_name_truncated,
					"invoice_key": dn_name_truncated,
					"job_id":      job_id_value,
				}
		else:
			dctResult.op_message = (
				f"Unexpected response: outFlag={out_flag_value}, outResult={out_result_value}"
			)

	except requests.exceptions.RequestException as e:
		dctResult.op_message = f"Network error: {str(e)}"
	except Exception as e:
		dctResult.op_message = f"Error processing response: {str(e)}"

	return dctResult


def dn_on_submit(doc, method=None):
	"""
	On submit hook for Delivery Note documents.
	Creates a shipment with Yurtiçi Kargo API if delivery method is Yurtiçi Kargo.
	"""
	# Only process if delivery method is Yurtiçi Kargo
	if doc.custom_ld_delivery_method == "Yurtiçi Kargo":
		# Create shipment
		result = createShipment(doc.name)

		if result.op_result:
			# Update Delivery Note with cargo key and job ID
			frappe.db.set_value(
				"Delivery Note",
				doc.name,
				{
					"custom_ld_yik_cargo_key": result.data.get("cargo_key", ""),
					"custom_ld_yik_job_id": result.data.get("job_id", "0"),
				},
			)
			frappe.msgprint(
				_("Shipment created successfully. Cargo Key: {0}").format(result.data.get("cargo_key", ""))
			)
		else:
			# If shipment creation failed, prevent submission and show error
			frappe.throw(_("Failed to create shipment: {0}").format(result.op_message))

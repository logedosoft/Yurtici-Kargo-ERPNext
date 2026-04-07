# Copyright (c) 2025, Logedosoft Business Solutions and contributors
# For license information, please see license.txt

import frappe, json
from frappe import msgprint, _
import requests
from bs4 import BeautifulSoup
import json

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

def queryShipment(key, docYIKSettings = None):
    """
    Query shipment information from Yurtiçi Kargo API.
    
    Args:
        key: The cargo key to query
        docYIKSettings: Optional Yurtici Kargo Ayarlari document. If None, will be fetched.
    
    Returns:
        dict with op_result (bool) and op_message (str)
    """
    dctResult = frappe._dict({
        'op_result': False,
        'op_message': ''
    })
    
    # Get settings if not provided
    if docYIKSettings is None:
        docYIKSettings = frappe.get_doc("Yurtici Kargo Ayarlari")
    
    # Get password using get_password method
    docYIKSettings.api_password = docYIKSettings.get_password('api_password')
    
    # Build SOAP request
    soap_request = '''<?xml version="1.0" encoding="utf-8"?>
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
</soapenv:Envelope>'''
    
    try:
        frappe.log_error("L1", soap_request)
        soap_request = frappe.render_template(soap_request, context={"docYIKSettings": docYIKSettings, "key": key}, is_path=False)
        frappe.log_error("L2", soap_request)

        # Send SOAP request
        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': ''
        }
        
        response = requests.post(
            docYIKSettings.web_service_url,
            data=soap_request.encode('utf-8'),
            headers=headers,
            timeout=30
        )
        
        # Parse response with BeautifulSoup
        soup = BeautifulSoup(response.content, 'xml')
        
        # Find ShippingDeliveryVO element
        shipping_vo = soup.find('ShippingDeliveryVO')
        
        if not shipping_vo:
            dctResult.op_message = "Invalid response from Yurtiçi Kargo API"
            return dctResult
        
        # Extract outFlag and outResult
        out_flag = shipping_vo.find('outFlag')
        out_result = shipping_vo.find('outResult')
        
        out_flag_value = out_flag.text if out_flag else None
        out_result_value = out_result.text if out_result else ""
        
        # Check for authentication problem (outFlag=1)
        if out_flag_value == '1':
            err_code = shipping_vo.find('errCode')
            err_code_value = err_code.text if err_code else ""
            dctResult.op_message = f"Authentication error: {out_result_value} (Error Code: {err_code_value})"
            return dctResult
        
        # Check for valid response (outFlag=0)
        if out_flag_value == '0':
            # Check for error in shippingDeliveryDetailVO
            detail_vo = shipping_vo.find('shippingDeliveryDetailVO')
            
            if detail_vo:
                err_code = detail_vo.find('errCode')
                err_message = detail_vo.find('errMessage')
                
                if err_code and err_code.text != '0':
                    dctResult.op_message = err_message.text if err_message else f"Error code: {err_code.text}"
                    return dctResult
                
                # Valid response - extract shipment details
                cargo_key = detail_vo.find('cargoKey')
                invoice_key = detail_vo.find('invoiceKey')
                job_id = detail_vo.find('jobId')
                operation_code = detail_vo.find('operationCode')
                operation_message = detail_vo.find('operationMessage')
                operation_status = detail_vo.find('operationStatus')
                
                count = shipping_vo.find('count')
                sender_cust_id = shipping_vo.find('senderCustId')
                
                dctResult.op_result = True
                dctResult.op_message = out_result_value
                dctResult.data = {
                    'count': count.text if count else '0',
                    'sender_cust_id': sender_cust_id.text if sender_cust_id else '',
                    'cargo_key': cargo_key.text if cargo_key else '',
                    'invoice_key': invoice_key.text if invoice_key else '',
                    'job_id': job_id.text if job_id else '0',
                    'operation_code': operation_code.text if operation_code else '',
                    'operation_message': operation_message.text if operation_message else '',
                    'operation_status': operation_status.text if operation_status else ''
                }
            else:
                dctResult.op_result = True
                dctResult.op_message = out_result_value
        else:
            dctResult.op_message = f"Unexpected response: outFlag={out_flag_value}, outResult={out_result_value}"
            
    except requests.exceptions.RequestException as e:
        dctResult.op_message = f"Network error: {str(e)}"
    except Exception as e:
        dctResult.op_message = f"Error processing response: {str(e)}"
    
    return dctResult

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
                    frappe.throw(
                        _("Önce Kargo etiketi yazdırın!")
                    )
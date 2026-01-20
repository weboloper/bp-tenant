"""
NetGSM SMS Provider - Turkey's popular SMS gateway

API Documentation: https://www.netgsm.com.tr/dokuman/
"""
import logging
import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from django.conf import settings

from .base import BaseSMSProvider, SMSResult, BulkSMSResult, SMSStatus

logger = logging.getLogger(__name__)


class NetGSMProvider(BaseSMSProvider):
    """
    NetGSM SMS Provider implementation.

    Handles:
    - Single SMS sending
    - Bulk SMS sending (XML API)
    - Delivery reports
    - Balance checking
    """

    # API Endpoints
    BASE_URL = "https://api.netgsm.com.tr"
    SEND_SMS_URL = f"{BASE_URL}/sms/send/get"
    SEND_BULK_URL = f"{BASE_URL}/sms/send/xml"
    REPORT_URL = f"{BASE_URL}/sms/report"
    BALANCE_URL = f"{BASE_URL}/balance/list/get"

    # NetGSM Error Codes
    ERROR_CODES = {
        '00': 'Başarısız gönderim',
        '01': 'Geçersiz kullanıcı adı veya şifre',
        '02': 'Bakiye yetersiz',
        '03': 'Geçersiz başlık (msgheader)',
        '04': 'Mesaj başlığı tanımlı değil',
        '05': 'Mesaj başlığı kullanım izni yok',
        '06': 'Geçersiz mesaj',
        '07': 'Gönderilecek numara yok',
        '08': 'Gönderim tarih formatı hatalı',
        '09': 'Birden fazla gönderim yapılıyor',
        '10': 'Mesaj boyu aşıldı',
        '11': 'Sistem hatası',
        '20': 'Tanımsız hata',
        '30': 'Geçersiz paket ID',
        '40': 'Aynı içerikli SMS var',
        '50': 'Başlık tanımlı değil',
        '51': 'Başlık izni yok',
        '52': 'Başlık aktif değil',
        '60': 'Hesabınız aktif değil',
        '70': 'Hatalı sorgulama',
        '80': 'Gönderim sınırı aşıldı',
        '100': 'Sistem hatası',
    }

    # Delivery Status Codes
    DELIVERY_CODES = {
        '0': SMSStatus.PENDING,      # Beklemede
        '1': SMSStatus.DELIVERED,    # İletildi
        '2': SMSStatus.FAILED,       # Zaman aşımı
        '3': SMSStatus.REJECTED,     # Hatalı numara
        '4': SMSStatus.REJECTED,     # Operatör red
        '5': SMSStatus.REJECTED,     # Bilinmiyor
        '6': SMSStatus.REJECTED,     # Kara liste
        '11': SMSStatus.PENDING,     # Operatöre iletildi
        '12': SMSStatus.SENT,        # Gönderildi
    }

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        sender_id: Optional[str] = None
    ):
        """
        Initialize NetGSM provider.

        Args:
            username: NetGSM API username (defaults to settings)
            password: NetGSM API password (defaults to settings)
            sender_id: Default sender ID (defaults to settings)
        """
        config = getattr(settings, 'NETGSM_CONFIG', {})

        self.username = username or config.get('username', '')
        self.password = password or config.get('password', '')
        self.default_sender_id = sender_id or config.get('sender_id', 'BPSALON')

        self.timeout = 30  # Request timeout in seconds

    def send(
        self,
        phone: str,
        message: str,
        sender_id: Optional[str] = None
    ) -> SMSResult:
        """
        Send a single SMS via NetGSM.

        Args:
            phone: Recipient phone number
            message: Message content
            sender_id: Sender ID (optional)

        Returns:
            SMSResult with send status
        """
        if not self.validate_phone(phone):
            return SMSResult(
                success=False,
                status=SMSStatus.FAILED,
                error_code='INVALID_PHONE',
                error_message='Geçersiz telefon numarası'
            )

        if not self.validate_message(message):
            return SMSResult(
                success=False,
                status=SMSStatus.FAILED,
                error_code='INVALID_MESSAGE',
                error_message='Geçersiz mesaj içeriği'
            )

        formatted_phone = self.format_phone_for_provider(phone)
        credits = self.calculate_credits(message)

        params = {
            'usercode': self.username,
            'password': self.password,
            'gsmno': formatted_phone,
            'message': message,
            'msgheader': sender_id or self.default_sender_id,
            'dil': 'TR',  # Turkish character support
        }

        try:
            response = requests.get(
                self.SEND_SMS_URL,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()

            result_code = response.text.strip()

            # Successful send returns message ID (numeric)
            if result_code.isdigit() and len(result_code) > 5:
                logger.info(f"SMS sent successfully to {phone}, ID: {result_code}")
                return SMSResult(
                    success=True,
                    message_id=result_code,
                    status=SMSStatus.SENT,
                    credits_used=credits,
                    raw_response={'code': result_code}
                )
            else:
                error_msg = self.ERROR_CODES.get(result_code, f'Bilinmeyen hata: {result_code}')
                logger.error(f"SMS send failed to {phone}: {error_msg}")
                return SMSResult(
                    success=False,
                    status=SMSStatus.FAILED,
                    error_code=result_code,
                    error_message=error_msg,
                    raw_response={'code': result_code}
                )

        except requests.RequestException as e:
            logger.exception(f"NetGSM API error: {e}")
            return SMSResult(
                success=False,
                status=SMSStatus.FAILED,
                error_code='API_ERROR',
                error_message=str(e)
            )

    def send_bulk(
        self,
        recipients: List[str],
        message: str,
        sender_id: Optional[str] = None
    ) -> BulkSMSResult:
        """
        Send SMS to multiple recipients via NetGSM XML API.

        Args:
            recipients: List of phone numbers
            message: Message content
            sender_id: Sender ID (optional)

        Returns:
            BulkSMSResult with batch status
        """
        if not recipients:
            return BulkSMSResult(
                success=False,
                error_message='Alıcı listesi boş'
            )

        if not self.validate_message(message):
            return BulkSMSResult(
                success=False,
                error_message='Geçersiz mesaj içeriği'
            )

        # Validate and format phone numbers
        valid_phones = []
        for phone in recipients:
            if self.validate_phone(phone):
                valid_phones.append(self.format_phone_for_provider(phone))

        if not valid_phones:
            return BulkSMSResult(
                success=False,
                error_message='Geçerli telefon numarası bulunamadı'
            )

        credits_per_msg = self.calculate_credits(message)

        # Build XML payload
        xml_content = self._build_bulk_xml(
            valid_phones,
            message,
            sender_id or self.default_sender_id
        )

        try:
            response = requests.post(
                self.SEND_BULK_URL,
                data=xml_content.encode('utf-8'),
                headers={'Content-Type': 'application/xml; charset=utf-8'},
                timeout=self.timeout
            )
            response.raise_for_status()

            result_code = response.text.strip()

            # Parse response
            if result_code.isdigit() and len(result_code) > 5:
                successful = len(valid_phones)
                logger.info(f"Bulk SMS sent, Batch ID: {result_code}, Count: {successful}")
                return BulkSMSResult(
                    success=True,
                    batch_id=result_code,
                    total=len(recipients),
                    successful=successful,
                    failed=len(recipients) - successful,
                    credits_used=successful * credits_per_msg
                )
            else:
                error_msg = self.ERROR_CODES.get(result_code, f'Bilinmeyen hata: {result_code}')
                logger.error(f"Bulk SMS failed: {error_msg}")
                return BulkSMSResult(
                    success=False,
                    total=len(recipients),
                    failed=len(recipients),
                    error_message=error_msg
                )

        except requests.RequestException as e:
            logger.exception(f"NetGSM Bulk API error: {e}")
            return BulkSMSResult(
                success=False,
                total=len(recipients),
                failed=len(recipients),
                error_message=str(e)
            )

    def _build_bulk_xml(
        self,
        phones: List[str],
        message: str,
        sender_id: str
    ) -> str:
        """Build XML payload for bulk SMS."""
        phones_xml = '\n'.join([f'<no>{phone}</no>' for phone in phones])

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<mainbody>
    <header>
        <company dession="1">Netgsm</company>
        <usercode>{self.username}</usercode>
        <password>{self.password}</password>
        <type>1:n</type>
        <msgheader>{sender_id}</msgheader>
    </header>
    <body>
        <msg><![CDATA[{message}]]></msg>
        {phones_xml}
    </body>
</mainbody>"""

    def get_delivery_report(self, message_id: str) -> SMSResult:
        """
        Get delivery status for a sent message.

        Args:
            message_id: NetGSM message ID

        Returns:
            SMSResult with current status
        """
        params = {
            'usercode': self.username,
            'password': self.password,
            'bulkid': message_id,
            'type': '0',  # Summary report
        }

        try:
            response = requests.get(
                self.REPORT_URL,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()

            result = response.text.strip()

            # Parse delivery status
            if result.startswith('00') or result.startswith('01'):
                # Extract status code from response
                parts = result.split(' ')
                if len(parts) >= 2:
                    status_code = parts[1] if len(parts) > 1 else '0'
                    status = self.DELIVERY_CODES.get(status_code, SMSStatus.UNKNOWN)

                    return SMSResult(
                        success=True,
                        message_id=message_id,
                        status=status,
                        raw_response={'result': result}
                    )

            # Error response
            error_msg = self.ERROR_CODES.get(result[:2], f'Bilinmeyen hata: {result}')
            return SMSResult(
                success=False,
                message_id=message_id,
                status=SMSStatus.UNKNOWN,
                error_code=result[:2],
                error_message=error_msg
            )

        except requests.RequestException as e:
            logger.exception(f"NetGSM Report API error: {e}")
            return SMSResult(
                success=False,
                message_id=message_id,
                status=SMSStatus.UNKNOWN,
                error_code='API_ERROR',
                error_message=str(e)
            )

    def get_balance(self) -> Dict[str, Any]:
        """
        Get account balance from NetGSM.

        Returns:
            Dict with balance info
        """
        params = {
            'usercode': self.username,
            'password': self.password,
            'tip': '1',  # SMS balance
        }

        try:
            response = requests.get(
                self.BALANCE_URL,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()

            result = response.text.strip()

            # Parse balance response
            # Format: "credit_amount currency"
            parts = result.split()

            if len(parts) >= 1 and parts[0].replace('.', '').replace(',', '').isdigit():
                balance = float(parts[0].replace(',', '.'))
                currency = parts[1] if len(parts) > 1 else 'TL'

                return {
                    'success': True,
                    'provider': 'netgsm',
                    'balance': balance,
                    'currency': currency,
                    'raw_response': result
                }
            else:
                error_msg = self.ERROR_CODES.get(result[:2], f'Bakiye sorgulanamadı: {result}')
                return {
                    'success': False,
                    'provider': 'netgsm',
                    'error': error_msg,
                    'raw_response': result
                }

        except requests.RequestException as e:
            logger.exception(f"NetGSM Balance API error: {e}")
            return {
                'success': False,
                'provider': 'netgsm',
                'error': str(e)
            }

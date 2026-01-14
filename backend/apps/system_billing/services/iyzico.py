"""
iyzico Checkout Form Integration Service

This service handles all iyzico API interactions for payment processing.
Uses iyzico Checkout Form (not direct API) for PCI compliance.

Documentation: https://docs.iyzico.com/en/payment-methods/checkoutform
"""

import hashlib
import base64
import json
import uuid
from decimal import Decimal
from typing import Dict, Any, Optional
from dataclasses import dataclass

import requests
from django.conf import settings
from django.utils.translation import gettext_lazy as _


@dataclass
class IyzicoResult:
    """Result object for iyzico operations"""
    success: bool
    data: Dict[str, Any]
    error_message: Optional[str] = None

    @property
    def transaction_id(self) -> Optional[str]:
        """Get payment ID from response"""
        return self.data.get('paymentId')

    @property
    def token(self) -> Optional[str]:
        """Get checkout token from response"""
        return self.data.get('token')

    @property
    def checkout_form_content(self) -> Optional[str]:
        """Get checkout form HTML content"""
        return self.data.get('checkoutFormContent')


class IyzicoService:
    """
    iyzico Checkout Form service for payment processing.

    Usage:
        service = IyzicoService()
        result = service.initialize_checkout(
            amount=Decimal('100.00'),
            currency='TRY',
            buyer_info={...},
            callback_url='https://...'
        )
    """

    def __init__(self, test_mode: bool = None):
        """
        Initialize iyzico service.

        Args:
            test_mode: Use sandbox environment (defaults to DEBUG setting)
        """
        self.test_mode = test_mode if test_mode is not None else settings.DEBUG

        # Get credentials from settings
        self.api_key = settings.IYZICO_API_KEY
        self.secret_key = settings.IYZICO_SECRET_KEY

        # Set base URL based on mode
        if self.test_mode:
            self.base_url = 'https://sandbox-api.iyzipay.com'
        else:
            self.base_url = 'https://api.iyzipay.com'

    def initialize_checkout(
        self,
        amount: Decimal,
        currency: str,
        buyer_info: Dict[str, Any],
        basket_items: list[Dict[str, Any]],
        callback_url: str,
        conversation_id: Optional[str] = None,
        enabled_installments: Optional[list[int]] = None,
    ) -> IyzicoResult:
        """
        Initialize iyzico Checkout Form.

        Args:
            amount: Total payment amount
            currency: Currency code (TRY, USD, EUR, GBP)
            buyer_info: Buyer information dict with keys:
                - id: Buyer unique ID
                - name: First name
                - surname: Last name
                - email: Email address
                - identity_number: TC/Tax number (11 digits)
                - phone: Phone number (+905XXXXXXXXX)
                - address: Address
                - city: City
                - country: Country
                - zip_code: Zip code (optional)
            basket_items: List of basket items, each with:
                - id: Item ID
                - name: Item name
                - category1: Main category
                - category2: Sub category (optional)
                - item_type: PHYSICAL or VIRTUAL
                - price: Item price
            callback_url: URL for payment callback
            conversation_id: Unique conversation ID (auto-generated if None)
            enabled_installments: List of allowed installments (e.g. [1, 2, 3, 6, 9])

        Returns:
            IyzicoResult with checkout form content
        """
        # Generate conversation ID if not provided
        if not conversation_id:
            conversation_id = f"payment_{uuid.uuid4().hex[:12]}"

        # Prepare request data
        request_data = {
            'locale': 'tr',
            'conversationId': conversation_id,
            'price': str(amount),
            'paidPrice': str(amount),
            'currency': currency,
            'basketId': conversation_id,
            'paymentGroup': 'SUBSCRIPTION',
            'callbackUrl': callback_url,
            'enabledInstallments': enabled_installments or [1],
            'buyer': {
                'id': str(buyer_info['id']),
                'name': buyer_info['name'],
                'surname': buyer_info['surname'],
                'gsmNumber': buyer_info['phone'],
                'email': buyer_info['email'],
                'identityNumber': buyer_info['identity_number'],
                'registrationAddress': buyer_info['address'],
                'city': buyer_info['city'],
                'country': buyer_info['country'],
            },
            'shippingAddress': {
                'contactName': f"{buyer_info['name']} {buyer_info['surname']}",
                'city': buyer_info['city'],
                'country': buyer_info['country'],
                'address': buyer_info['address'],
            },
            'billingAddress': {
                'contactName': f"{buyer_info['name']} {buyer_info['surname']}",
                'city': buyer_info['city'],
                'country': buyer_info['country'],
                'address': buyer_info['address'],
            },
            'basketItems': basket_items,
        }

        # Add zip code if provided
        if buyer_info.get('zip_code'):
            request_data['shippingAddress']['zipCode'] = buyer_info['zip_code']
            request_data['billingAddress']['zipCode'] = buyer_info['zip_code']

        # Make API request
        return self._make_request(
            endpoint='/payment/iyzipos/checkoutform/initialize/auth/ecom',
            data=request_data
        )

    def retrieve_checkout_result(
        self,
        token: str,
        conversation_id: Optional[str] = None
    ) -> IyzicoResult:
        """
        Retrieve checkout form result after user completes payment.

        This method should be called in the callback endpoint to verify
        the payment status.

        Args:
            token: Checkout form token from initialize or callback
            conversation_id: Original conversation ID (optional)

        Returns:
            IyzicoResult with payment details
        """
        request_data = {
            'locale': 'tr',
            'token': token,
        }

        if conversation_id:
            request_data['conversationId'] = conversation_id

        return self._make_request(
            endpoint='/payment/iyzipos/checkoutform/auth/ecom/detail',
            data=request_data
        )

    def refund_payment(
        self,
        payment_transaction_id: str,
        amount: Optional[Decimal] = None,
        currency: str = 'TRY',
        reason: str = '',
        conversation_id: Optional[str] = None
    ) -> IyzicoResult:
        """
        Refund a payment (full or partial).

        Args:
            payment_transaction_id: iyzico payment transaction ID
            amount: Refund amount (None for full refund)
            currency: Currency code
            reason: Refund reason
            conversation_id: Unique conversation ID

        Returns:
            IyzicoResult with refund details
        """
        if not conversation_id:
            conversation_id = f"refund_{uuid.uuid4().hex[:12]}"

        request_data = {
            'locale': 'tr',
            'conversationId': conversation_id,
            'paymentTransactionId': payment_transaction_id,
            'currency': currency,
        }

        if amount:
            request_data['price'] = str(amount)

        if reason:
            request_data['description'] = reason

        return self._make_request(
            endpoint='/payment/refund',
            data=request_data
        )

    def cancel_payment(
        self,
        payment_id: str,
        reason: str = '',
        conversation_id: Optional[str] = None
    ) -> IyzicoResult:
        """
        Cancel a payment (before day-end).

        Args:
            payment_id: iyzico payment ID
            reason: Cancellation reason
            conversation_id: Unique conversation ID

        Returns:
            IyzicoResult with cancellation details
        """
        if not conversation_id:
            conversation_id = f"cancel_{uuid.uuid4().hex[:12]}"

        request_data = {
            'locale': 'tr',
            'conversationId': conversation_id,
            'paymentId': payment_id,
        }

        if reason:
            request_data['description'] = reason

        return self._make_request(
            endpoint='/payment/cancel',
            data=request_data
        )

    def get_payment_detail(
        self,
        payment_id: str,
        conversation_id: Optional[str] = None
    ) -> IyzicoResult:
        """
        Get payment details by payment ID.

        Args:
            payment_id: iyzico payment ID
            conversation_id: Conversation ID (optional)

        Returns:
            IyzicoResult with payment details
        """
        request_data = {
            'locale': 'tr',
            'paymentId': payment_id,
        }

        if conversation_id:
            request_data['conversationId'] = conversation_id

        return self._make_request(
            endpoint='/payment/detail',
            data=request_data
        )

    def _make_request(
        self,
        endpoint: str,
        data: Dict[str, Any]
    ) -> IyzicoResult:
        """
        Make authenticated API request to iyzico.

        Args:
            endpoint: API endpoint path
            data: Request data

        Returns:
            IyzicoResult object
        """
        url = f"{self.base_url}{endpoint}"

        try:
            # Generate authorization header
            auth_header = self._generate_auth_header(data)

            # Prepare headers
            headers = {
                'Authorization': auth_header,
                'Content-Type': 'application/json',
                'x-iyzi-rnd': str(uuid.uuid4()),
            }

            # Make request
            response = requests.post(
                url,
                json=data,
                headers=headers,
                timeout=30
            )

            # Parse response
            response_data = response.json()

            # Check if request was successful
            success = response_data.get('status') == 'success'

            if not success:
                error_message = response_data.get('errorMessage', 'Unknown error')
                return IyzicoResult(
                    success=False,
                    data=response_data,
                    error_message=error_message
                )

            return IyzicoResult(
                success=True,
                data=response_data
            )

        except requests.exceptions.RequestException as e:
            return IyzicoResult(
                success=False,
                data={},
                error_message=f"Network error: {str(e)}"
            )
        except Exception as e:
            return IyzicoResult(
                success=False,
                data={},
                error_message=f"Unexpected error: {str(e)}"
            )

    def _generate_auth_header(self, request_data: Dict[str, Any]) -> str:
        """
        Generate iyzico authorization header.

        Format: IYZWS {api_key}:{signature}
        Signature: base64(sha256(api_key + random_string + secret_key + request_body))

        Args:
            request_data: Request data to be signed

        Returns:
            Authorization header value
        """
        # Convert request data to JSON string
        request_string = json.dumps(request_data, separators=(',', ':'), ensure_ascii=False)

        # Generate random string
        random_string = str(uuid.uuid4())

        # Create signature string
        signature_string = (
            self.api_key +
            random_string +
            self.secret_key +
            request_string
        )

        # Generate SHA256 hash
        signature_hash = hashlib.sha256(signature_string.encode('utf-8')).digest()

        # Encode to base64
        signature = base64.b64encode(signature_hash).decode('utf-8')

        # Return authorization header
        return f"IYZWS {self.api_key}:{signature}"

    @staticmethod
    def format_basket_item(
        item_id: str,
        name: str,
        category: str,
        price: Decimal,
        item_type: str = 'VIRTUAL'
    ) -> Dict[str, Any]:
        """
        Format basket item for iyzico API.

        Args:
            item_id: Item unique ID
            name: Item name
            category: Item category
            price: Item price
            item_type: PHYSICAL or VIRTUAL

        Returns:
            Formatted basket item dict
        """
        return {
            'id': str(item_id),
            'name': name,
            'category1': category,
            'itemType': item_type,
            'price': str(price),
        }

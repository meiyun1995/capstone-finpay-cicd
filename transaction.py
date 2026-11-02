"""Data model for transactions accepted by the validation API."""

from dataclasses import dataclass


@dataclass
class Transaction:
    """Hold transaction identifiers, an amount, and a currency code.

    Attributes:
        transaction_id: Caller-provided transaction identifier.
        account_id: Caller-provided account identifier.
        amount: Validated numeric amount, greater than zero and at most 10000.
        currency: Supported uppercase currency code (SGD, USD, or EUR).

    Type annotations do not enforce runtime validation. The API validates
    input before constructing this dataclass.
    """

    transaction_id: str
    account_id: str
    amount: float
    currency: str

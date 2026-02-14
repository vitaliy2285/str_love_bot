from dataclasses import dataclass


@dataclass
class PaymentResult:
    success: bool
    provider: str
    transaction_id: str


class PaymentGateway:
    """Заглушка платежного шлюза. Готово для интеграции с ЮKassa."""

    def pay(self, user_id: int, item_code: str, amount_rub: int) -> PaymentResult:
        fake_tx = f"mock-{user_id}-{item_code}-{amount_rub}"
        return PaymentResult(success=True, provider="mock-yookassa", transaction_id=fake_tx)

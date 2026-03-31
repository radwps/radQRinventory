from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Sequence


@dataclass
class Part:
    sku: str
    name: str
    container_label: str
    starting_qty: int
    on_hand: int
    reorder_level: int = 0
    external_id: str | None = None


@dataclass
class Transaction:
    created_at: str
    sku: str
    part_name: str
    action: str
    quantity: int
    delta: int
    batch_id: str | None = None
    operator: str | None = None
    note: str | None = None
    source: str | None = None


@dataclass
class KitComponent:
    sku: str
    part_name: str
    qty_per_kit: int
    on_hand: int


@dataclass
class Kit:
    code: str
    name: str
    external_id: str | None = None
    components: List[KitComponent] | None = None


@dataclass
class ActionResult:
    ok: bool
    message: str
    batch_id: str | None = None
    touched_parts: List[Part] | None = None
    transactions_created: int = 0


class InventoryError(Exception):
    pass


class NotFoundError(InventoryError):
    pass


class ValidationError(InventoryError):
    pass


class InventoryStore(ABC):
    @abstractmethod
    def list_parts(self) -> Sequence[Part]:
        raise NotImplementedError

    @abstractmethod
    def get_part(self, sku: str) -> Part:
        raise NotImplementedError

    @abstractmethod
    def list_transactions(self, limit: int = 50) -> Sequence[Transaction]:
        raise NotImplementedError

    @abstractmethod
    def list_kits(self) -> Sequence[Kit]:
        raise NotImplementedError

    @abstractmethod
    def get_kit(self, code: str) -> Kit:
        raise NotImplementedError

    @abstractmethod
    def apply_part_action(
        self,
        sku: str,
        action: str,
        quantity: int,
        operator: str = "",
        note: str = "",
        source: str = "",
    ) -> ActionResult:
        raise NotImplementedError

    @abstractmethod
    def apply_kit_action(
        self,
        code: str,
        action: str,
        operator: str = "",
        note: str = "",
        source: str = "",
    ) -> ActionResult:
        raise NotImplementedError
